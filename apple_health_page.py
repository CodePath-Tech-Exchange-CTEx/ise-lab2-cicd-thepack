#############################################################################
# apple_health_page.py
#
# Apple Health integration page.
#
# How it works:
#   1. User exports their Apple Health data from the iPhone Health app:
#      Health → Profile picture → Export All Health Data → share the ZIP
#   2. They upload either the full ZIP or the extracted export.xml here.
#   3. We STREAM-parse the XML so we don't load multi-GB files into memory.
#   4. Parsed data is stored in st.session_state['apple_health'] so other
#      pages (AI Coach) can read it without re-parsing. The summary is also
#      cached to a user-specific pickle on disk so a process restart
#      doesn't force a re-upload.
#
# Why streaming: Apple Health exports for long-term users are often
# 500MB – 2GB of XML. ET.fromstring() would load the full tree, blow past
# the Streamlit process memory limit, and the process would restart —
# which wipes session_state and kicks the user back to the sign-in page
# (what the user saw as "it logs me out").
#############################################################################

import io
import os
import pickle
import tempfile
import zipfile
import xml.etree.ElementTree as ET
from collections import defaultdict
from datetime import datetime, timedelta

import streamlit as st
import pandas as pd


# Cap heart-rate sample count we retain — we only need the average anyway.
_MAX_HR_SAMPLES_RETAINED = 50_000

# Where we pickle parsed summaries so a process restart doesn't lose them.
_CACHE_DIR = os.path.join(tempfile.gettempdir(), 'lykos_apple_health_cache')


# ── Public entry point ────────────────────────────────────────────────────────

def display_apple_health_page():
    """Main page renderer."""
    st.title('Apple Health')

    _how_to_export_guide()

    # Try to restore previously-parsed summary from disk (survives process restart)
    _restore_cached_summary_if_missing()

    uploaded = st.file_uploader(
        'Upload your Apple Health export',
        type=['zip', 'xml'],
        help='Export from iPhone: Health app → profile icon → Export All Health Data. '
             'ZIPs up to ~2GB are supported.',
    )

    if uploaded is not None:
        data = _safe_parse_upload(uploaded)
        if data is not None:
            st.session_state['apple_health'] = data
            _cache_summary_to_disk(data)
            st.success(
                f'✅ Loaded {len(data["workouts"])} workouts and '
                f'{data["total_steps"]:,.0f} steps from Apple Health'
            )

    # Render dashboard from whatever we have (just-uploaded OR previously cached)
    data = st.session_state.get('apple_health')
    if not data:
        _show_placeholder_state()
        return

    if st.button('Clear Apple Health data', type='secondary'):
        st.session_state.pop('apple_health', None)
        _clear_cached_summary()
        st.rerun()

    _render_dashboard(data)


# ── Safe parse wrapper (the whole point of this refactor) ─────────────────────

def _safe_parse_upload(uploaded_file):
    """Stream-parses the upload. Catches OOM and other fatal errors so the
    Streamlit process never dies (which is what was logging users out)."""
    try:
        with st.spinner('Parsing health data… this can take a minute for large exports.'):
            return _parse_upload_streaming(uploaded_file)
    except MemoryError:
        st.error(
            '⚠️ Your export is too large to parse in memory on this server. '
            'Try exporting a shorter date range from the Health app, or run the app '
            'locally with more RAM.'
        )
        return None
    except zipfile.BadZipFile:
        st.error('The file is not a valid Apple Health ZIP. Did you upload the correct export?')
        return None
    except ET.ParseError as e:
        st.error(f'Could not parse the Apple Health XML: {e}')
        return None
    except Exception as e:
        st.error(f'Unexpected error while parsing the upload: {e}')
        return None


# ── Streaming parser ──────────────────────────────────────────────────────────

def _parse_upload_streaming(uploaded_file):
    """Stream-parses a ZIP or XML Apple Health export without loading the
    whole file into memory."""

    name = (uploaded_file.name or '').lower()

    # Spool the upload to a tmp file so we can stream from disk instead of
    # holding the whole bytes object in memory.
    with tempfile.NamedTemporaryFile(delete=False, suffix='_apple_health') as tmp:
        tmp_path = tmp.name
        # Copy in 4MB chunks
        while True:
            chunk = uploaded_file.read(4 * 1024 * 1024)
            if not chunk:
                break
            tmp.write(chunk)

    try:
        if name.endswith('.zip'):
            return _parse_zip_streaming(tmp_path)
        if name.endswith('.xml'):
            with open(tmp_path, 'rb') as f:
                return _parse_xml_stream(f)
        st.error('Unsupported file type. Upload a .zip or .xml export.')
        return None
    finally:
        try:
            os.remove(tmp_path)
        except OSError:
            pass


def _parse_zip_streaming(zip_path: str):
    """Open export.xml inside the ZIP as a stream and parse without
    decompressing to memory."""
    with zipfile.ZipFile(zip_path) as zf:
        # Apple Health zips store the XML at 'apple_health_export/export.xml'
        target = None
        for info in zf.infolist():
            if info.filename.endswith('export.xml'):
                target = info
                break
        if target is None:
            st.error(
                'Could not find export.xml inside the ZIP. '
                'Make sure you uploaded the unmodified Apple Health export.'
            )
            return None

        with zf.open(target, 'r') as xml_stream:
            return _parse_xml_stream(xml_stream)


def _parse_xml_stream(xml_stream) -> dict:
    """Uses ET.iterparse() so we only hold one element in memory at a time.
    Frees each element as soon as we've consumed it."""

    daily_steps = defaultdict(float)
    daily_calories = defaultdict(float)
    daily_distance = defaultdict(float)
    hr_sum = 0.0
    hr_count = 0
    hr_samples_by_day = defaultdict(list)
    workouts = []

    # Use 'end' events so we only touch fully-formed elements.
    context = ET.iterparse(xml_stream, events=('end',))
    for _, elem in context:
        tag = elem.tag
        if tag == 'Record':
            _process_record(elem, daily_steps, daily_calories, daily_distance,
                            hr_samples_by_day)
            # Update HR aggregate
            if elem.get('type') == 'HKQuantityTypeIdentifierHeartRate':
                try:
                    v = float(elem.get('value', 0))
                    hr_sum += v
                    hr_count += 1
                except (ValueError, TypeError):
                    pass
            # CRITICAL: release memory
            elem.clear()
        elif tag == 'Workout':
            w = _process_workout(elem)
            if w is not None:
                workouts.append(w)
            elem.clear()
        # Don't clear WorkoutStatistics / MetadataEntry here — their parent
        # Workout still needs to read them on its own 'end' event. They get
        # freed when the parent Workout is cleared.

    workouts.sort(key=lambda w: w['start'], reverse=True)

    # Cap the daily HR sample lists to avoid huge memory for chart rendering
    trimmed_hr = {}
    for day, samples in hr_samples_by_day.items():
        trimmed_hr[day] = samples[:200]  # keep at most 200 samples per day

    avg_hr = (hr_sum / hr_count) if hr_count else 0.0

    return {
        'workouts': workouts,
        'daily_steps': dict(daily_steps),
        'daily_calories': dict(daily_calories),
        'daily_distance': dict(daily_distance),
        'daily_hr_samples': trimmed_hr,
        'total_steps': sum(daily_steps.values()),
        'total_calories': sum(daily_calories.values()),
        'total_distance_km': sum(daily_distance.values()),
        'avg_heart_rate': avg_hr,
        # Backwards-compat key for code that reads heart_rate_readings
        'heart_rate_readings': [],
        'parsed_at': datetime.utcnow().isoformat(),
    }


def _process_record(elem, daily_steps, daily_calories, daily_distance,
                    hr_samples_by_day):
    rtype = elem.get('type', '')
    start = (elem.get('startDate', '') or '')[:10]  # YYYY-MM-DD
    if not start:
        return
    try:
        value = float(elem.get('value', 0))
    except (ValueError, TypeError):
        return

    if rtype == 'HKQuantityTypeIdentifierStepCount':
        daily_steps[start] += value
    elif rtype == 'HKQuantityTypeIdentifierDistanceWalkingRunning':
        daily_distance[start] += value
    elif rtype == 'HKQuantityTypeIdentifierActiveEnergyBurned':
        daily_calories[start] += value
    elif rtype == 'HKQuantityTypeIdentifierHeartRate':
        # Retain a bounded sample per day so the UI can chart HR
        samples = hr_samples_by_day[start]
        if len(samples) < 200:
            samples.append(value)
        # Cap total memory
        if len(hr_samples_by_day) > _MAX_HR_SAMPLES_RETAINED:
            return


WORKOUT_TYPE_LABELS = {
    'HKWorkoutActivityTypeRunning': '🏃 Running',
    'HKWorkoutActivityTypeWalking': '🚶 Walking',
    'HKWorkoutActivityTypeCycling': '🚴 Cycling',
    'HKWorkoutActivityTypeSwimming': '🏊 Swimming',
    'HKWorkoutActivityTypeHighIntensityIntervalTraining': '⚡ HIIT',
    'HKWorkoutActivityTypeFunctionalStrengthTraining': '💪 Strength',
    'HKWorkoutActivityTypeYoga': '🧘 Yoga',
    'HKWorkoutActivityTypeElliptical': '🏋️ Elliptical',
    'HKWorkoutActivityTypeStairClimbing': '🪜 Stair Climbing',
}


def _process_workout(elem):
    activity = elem.get('workoutActivityType', 'HKWorkoutActivityTypeOther')
    label = WORKOUT_TYPE_LABELS.get(
        activity,
        '🏅 ' + activity.replace('HKWorkoutActivityType', ''),
    )
    start_str = elem.get('startDate', '') or ''
    end_str = elem.get('endDate', '') or ''
    try:
        duration_min = float(elem.get('duration', 0) or 0)
    except (ValueError, TypeError):
        duration_min = 0.0
    unit = elem.get('durationUnit', 'min')
    if unit == 's':
        duration_min /= 60.0

    stats = {}
    for ws in elem.findall('WorkoutStatistics'):
        ws_type = ws.get('type', '')
        raw = ws.get('sum') or ws.get('average') or 0
        try:
            stats[ws_type] = float(raw or 0)
        except (ValueError, TypeError):
            pass

    return {
        'type': label,
        'date': start_str[:10],
        'start': start_str,
        'end': end_str,
        'duration_min': round(duration_min, 1),
        'calories': stats.get('HKQuantityTypeIdentifierActiveEnergyBurned', 0),
        'distance_km': stats.get('HKQuantityTypeIdentifierDistanceWalkingRunning', 0),
        'steps': stats.get('HKQuantityTypeIdentifierStepCount', 0),
        'avg_hr': stats.get('HKQuantityTypeIdentifierHeartRate', 0),
    }


# ── On-disk cache (survives process restart) ──────────────────────────────────

def _cache_path_for_user() -> str:
    os.makedirs(_CACHE_DIR, exist_ok=True)
    uid = _current_uid()
    return os.path.join(_CACHE_DIR, f'{uid}.pkl')


def _current_uid() -> str:
    user = st.session_state.get('supabase_user') or {}
    return user.get('id') or 'anonymous'


def _cache_summary_to_disk(data: dict):
    """Persist parsed summary so a process restart keeps the data."""
    try:
        with open(_cache_path_for_user(), 'wb') as f:
            pickle.dump(data, f)
    except Exception:
        pass  # Non-fatal


def _restore_cached_summary_if_missing():
    if st.session_state.get('apple_health'):
        return
    try:
        path = _cache_path_for_user()
        if os.path.exists(path):
            with open(path, 'rb') as f:
                st.session_state['apple_health'] = pickle.load(f)
    except Exception:
        pass


def _clear_cached_summary():
    try:
        path = _cache_path_for_user()
        if os.path.exists(path):
            os.remove(path)
    except Exception:
        pass


# ── Export guide ──────────────────────────────────────────────────────────────

def _how_to_export_guide():
    with st.expander('📱 How to export from your iPhone', expanded=False):
        st.markdown("""
**Steps to export your Apple Health data:**

1. Open the **Health** app on your iPhone
2. Tap your **profile picture** (top-right)
3. Scroll down and tap **Export All Health Data**
4. Tap **Export** and wait (may take a minute for large datasets)
5. Share or save the **export.zip** file — then upload it here

You can also extract the zip and upload just the **export.xml** file.

**Note:** Large exports (5+ years of data) can take 30–60 seconds to parse.
If the page shows a spinner, leave it — it's working.
        """)


# ── Placeholder ───────────────────────────────────────────────────────────────

def _show_placeholder_state():
    col1, col2, col3 = st.columns(3)
    col1.metric('📱 Device', 'Not connected')
    col2.metric('👟 Total Steps', '—')
    col3.metric('🏃 Workouts', '—')
    st.info('Upload your Apple Health export above to see your real fitness data.')


# ── Dashboard ─────────────────────────────────────────────────────────────────

def _render_dashboard(data: dict):
    """Renders the parsed health data as charts and tables."""

    # ── Summary metrics ───────────────────────────────────────────────────────
    c1, c2, c3, c4 = st.columns(4)
    c1.metric('Total Steps', f"{data['total_steps']:,.0f}")
    c2.metric('Workouts', len(data['workouts']))
    c3.metric('Distance (km)', f"{data['total_distance_km']:.1f}")
    c4.metric('Avg Heart Rate',
              f"{data['avg_heart_rate']:.0f} bpm" if data['avg_heart_rate'] else '—')

    st.divider()

    # ── Daily steps chart (last 30 days) ──────────────────────────────────────
    st.subheader('Daily Steps — last 30 days')
    if data['daily_steps']:
        today = datetime.today().date()
        date_range = [(today - timedelta(days=i)).isoformat() for i in range(29, -1, -1)]
        steps_values = [data['daily_steps'].get(d, 0) for d in date_range]
        df_steps = pd.DataFrame({'Date': date_range, 'Steps': steps_values})
        df_steps['Date'] = pd.to_datetime(df_steps['Date'])
        st.bar_chart(df_steps.set_index('Date')['Steps'], color='#111827')
    else:
        st.caption('No step data found.')

    # ── Calories chart (last 30 days) ─────────────────────────────────────────
    st.subheader('Active Calories — last 30 days')
    if data['daily_calories']:
        today = datetime.today().date()
        date_range = [(today - timedelta(days=i)).isoformat() for i in range(29, -1, -1)]
        cal_values = [data['daily_calories'].get(d, 0) for d in date_range]
        df_cal = pd.DataFrame({'Date': date_range, 'Calories': cal_values})
        df_cal['Date'] = pd.to_datetime(df_cal['Date'])
        st.bar_chart(df_cal.set_index('Date')['Calories'], color='#e74c3c')
    else:
        st.caption('No calorie data found.')

    st.divider()

    # ── Workout list ──────────────────────────────────────────────────────────
    st.subheader(f'Recent Workouts ({len(data["workouts"])} total)')
    if not data['workouts']:
        st.caption('No workouts found in your export.')
        return

    recent = data['workouts'][:20]
    rows = []
    for w in recent:
        rows.append({
            'Type': w['type'],
            'Date': w['date'],
            'Duration (min)': w['duration_min'],
            'Calories': f"{w['calories']:.0f}" if w['calories'] else '—',
            'Distance (km)': f"{w['distance_km']:.2f}" if w['distance_km'] else '—',
            'Steps': f"{w['steps']:,.0f}" if w['steps'] else '—',
        })

    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    # ── Workout type breakdown ────────────────────────────────────────────────
    st.subheader('Workout Types')
    if data['workouts']:
        type_counts = defaultdict(int)
        for w in data['workouts']:
            type_counts[w['type']] += 1
        df_types = pd.DataFrame(
            {'Type': list(type_counts.keys()), 'Count': list(type_counts.values())}
        ).sort_values('Count', ascending=False)
        st.bar_chart(df_types.set_index('Type')['Count'])
