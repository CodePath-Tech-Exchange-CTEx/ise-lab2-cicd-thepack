#############################################################################
# apple_health_page.py
#
# Apple Health integration page.
#
# How it works:
#   1. User exports their Apple Health data from the iPhone Health app:
#      Health → Profile picture → Export All Health Data → share the ZIP
#   2. They upload either the full ZIP or the extracted export.xml here.
#   3. We parse the XML and display steps, workouts, heart-rate, calories.
#   4. Parsed data is stored in st.session_state['apple_health'] so other
#      pages (AI Coach) can read it without re-parsing.
#
# Supported record types:
#   HKQuantityTypeIdentifierStepCount
#   HKQuantityTypeIdentifierDistanceWalkingRunning
#   HKQuantityTypeIdentifierActiveEnergyBurned
#   HKQuantityTypeIdentifierHeartRate
#   HKWorkoutActivityType* (workouts)
#############################################################################

import io
import zipfile
import xml.etree.ElementTree as ET
from collections import defaultdict
from datetime import datetime, timedelta

import streamlit as st
import pandas as pd


# ── Public entry point ────────────────────────────────────────────────────────

def display_apple_health_page():
    """Main page renderer."""
    st.title('Apple Health')

    _how_to_export_guide()

    uploaded = st.file_uploader(
        'Upload your Apple Health export',
        type=['zip', 'xml'],
        help='Export from iPhone: Health app → profile icon → Export All Health Data',
    )

    if uploaded is None:
        _show_placeholder_state()
        return

    with st.spinner('Parsing health data…'):
        data = _parse_upload(uploaded)

    if data is None:
        st.error('Could not read the file. Make sure you upload export.xml or the Apple Health ZIP.')
        return

    # Cache in session state so AI Coach can access it
    st.session_state['apple_health'] = data
    st.success(f'✅ Loaded {len(data["workouts"])} workouts and {data["total_steps"]:,} steps from Apple Health')

    _render_dashboard(data)


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
        """)


# ── Placeholder ───────────────────────────────────────────────────────────────

def _show_placeholder_state():
    col1, col2, col3 = st.columns(3)
    col1.metric('📱 Device', 'Not connected')
    col2.metric('👟 Total Steps', '—')
    col3.metric('🏃 Workouts', '—')
    st.info('Upload your Apple Health export above to see your real fitness data.')


# ── Parsing ───────────────────────────────────────────────────────────────────

def _parse_upload(uploaded_file):
    """Accepts a ZIP or XML file and returns a parsed health data dict."""
    name = uploaded_file.name.lower()
    raw = uploaded_file.read()

    if name.endswith('.zip'):
        xml_bytes = _extract_xml_from_zip(raw)
        if xml_bytes is None:
            return None
    elif name.endswith('.xml'):
        xml_bytes = raw
    else:
        return None

    return _parse_health_xml(xml_bytes)


def _extract_xml_from_zip(zip_bytes: bytes):
    """Extracts export.xml from the Apple Health ZIP archive."""
    try:
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
            for name in zf.namelist():
                if name.endswith('export.xml'):
                    return zf.read(name)
    except Exception:
        pass
    return None


# ── XML parser ────────────────────────────────────────────────────────────────

RECORD_TYPES = {
    'HKQuantityTypeIdentifierStepCount': 'steps',
    'HKQuantityTypeIdentifierDistanceWalkingRunning': 'distance_km',
    'HKQuantityTypeIdentifierActiveEnergyBurned': 'calories',
    'HKQuantityTypeIdentifierHeartRate': 'heart_rate',
}

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


def _parse_health_xml(xml_bytes: bytes) -> dict:
    """Parses Apple Health export.xml and returns structured data."""
    tree = ET.fromstring(xml_bytes)

    # Daily aggregates
    daily_steps = defaultdict(float)
    daily_calories = defaultdict(float)
    daily_distance = defaultdict(float)
    heart_rate_readings = []

    for record in tree.findall('Record'):
        rtype = record.get('type', '')
        start = record.get('startDate', '')[:10]  # YYYY-MM-DD
        try:
            value = float(record.get('value', 0))
        except ValueError:
            continue

        if rtype == 'HKQuantityTypeIdentifierStepCount':
            daily_steps[start] += value
        elif rtype == 'HKQuantityTypeIdentifierDistanceWalkingRunning':
            daily_distance[start] += value
        elif rtype == 'HKQuantityTypeIdentifierActiveEnergyBurned':
            daily_calories[start] += value
        elif rtype == 'HKQuantityTypeIdentifierHeartRate':
            heart_rate_readings.append({'date': start, 'bpm': value})

    # Workouts
    workouts = []
    for wo in tree.findall('Workout'):
        activity = wo.get('workoutActivityType', 'HKWorkoutActivityTypeOther')
        label = WORKOUT_TYPE_LABELS.get(activity, '🏅 ' + activity.replace('HKWorkoutActivityType', ''))
        start_str = wo.get('startDate', '')
        end_str = wo.get('endDate', '')
        duration_min = float(wo.get('duration', 0))
        unit = wo.get('durationUnit', 'min')
        if unit == 's':
            duration_min /= 60.0

        # Pull workout statistics sub-elements
        stats = {}
        for ws in wo.findall('WorkoutStatistics'):
            ws_type = ws.get('type', '')
            try:
                stats[ws_type] = float(ws.get('sum', 0) or ws.get('average', 0) or 0)
            except ValueError:
                pass

        workouts.append({
            'type': label,
            'date': start_str[:10],
            'start': start_str,
            'end': end_str,
            'duration_min': round(duration_min, 1),
            'calories': stats.get('HKQuantityTypeIdentifierActiveEnergyBurned', 0),
            'distance_km': stats.get('HKQuantityTypeIdentifierDistanceWalkingRunning', 0),
            'steps': stats.get('HKQuantityTypeIdentifierStepCount', 0),
            'avg_hr': stats.get('HKQuantityTypeIdentifierHeartRate', 0),
        })

    workouts.sort(key=lambda w: w['start'], reverse=True)

    total_steps = sum(daily_steps.values())
    total_calories = sum(daily_calories.values())
    total_distance = sum(daily_distance.values())
    avg_hr = (
        sum(r['bpm'] for r in heart_rate_readings) / len(heart_rate_readings)
        if heart_rate_readings else 0
    )

    return {
        'workouts': workouts,
        'daily_steps': dict(daily_steps),
        'daily_calories': dict(daily_calories),
        'daily_distance': dict(daily_distance),
        'heart_rate_readings': heart_rate_readings,
        'total_steps': total_steps,
        'total_calories': total_calories,
        'total_distance_km': total_distance,
        'avg_heart_rate': avg_hr,
    }


# ── Dashboard ─────────────────────────────────────────────────────────────────

def _render_dashboard(data: dict):
    """Renders the parsed health data as charts and tables."""

    # ── Summary metrics ───────────────────────────────────────────────────────
    c1, c2, c3, c4 = st.columns(4)
    c1.metric('Total Steps', f"{data['total_steps']:,.0f}")
    c2.metric('Workouts', len(data['workouts']))
    c3.metric('Distance (km)', f"{data['total_distance_km']:.1f}")
    c4.metric('Avg Heart Rate', f"{data['avg_heart_rate']:.0f} bpm" if data['avg_heart_rate'] else '—')

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
