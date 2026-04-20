#############################################################################
# body_metrics_page.py
#
# Body metrics tracker:
#   - Log weight, body fat %, and measurements (chest, waist, hips, arms, thighs)
#   - Trend chart (weight over time)
#   - BMI calculator
#   - Logs stored in session state + Supabase body_metrics table
#############################################################################

from datetime import date, datetime

import pandas as pd
import streamlit as st

# ── Main ──────────────────────────────────────────────────────────────────────

def display_body_metrics_page():
    st.title('Body Metrics')

    _inject_css()

    # Load from Supabase on first visit
    if 'metrics_loaded' not in st.session_state:
        _load_from_supabase()
        st.session_state.metrics_loaded = True

    if 'body_metrics_log' not in st.session_state:
        st.session_state.body_metrics_log = []

    logs = st.session_state.body_metrics_log

    # ── Latest snapshot ───────────────────────────────────────────────────────
    latest = logs[0] if logs else {}

    col1, col2, col3, col4 = st.columns(4)
    col1.metric('Weight', f'{latest.get("weight_kg", "—")} kg' if latest else '—')
    col2.metric('Body Fat', f'{latest.get("body_fat_pct", "—")}%' if latest and latest.get('body_fat_pct') else '—')
    bmi = _bmi(latest.get('weight_kg'), latest.get('height_cm')) if latest else None
    col3.metric('BMI', f'{bmi:.1f}' if bmi else '—')
    col4.metric('Last Updated', latest.get('date', '—') if latest else '—')

    if bmi:
        _bmi_category(bmi)

    st.divider()

    # ── Log entry ─────────────────────────────────────────────────────────────
    st.subheader("Log Today's Measurements")

    with st.form('body_metrics_form', clear_on_submit=False):
        c1, c2, c3 = st.columns(3)
        weight_kg = c1.number_input('Weight (kg)', 30.0, 300.0,
                                    value=float(latest.get('weight_kg') or 70) if latest else 70.0,
                                    step=0.1)
        height_cm = c2.number_input('Height (cm)', 100.0, 250.0,
                                    value=float(latest.get('height_cm') or 170) if latest else 170.0,
                                    step=0.5)
        body_fat = c3.number_input('Body fat % (optional)', 0.0, 60.0,
                                   value=float(latest.get('body_fat_pct') or 0) if latest else 0.0,
                                   step=0.1)

        st.markdown('**Measurements (cm) — all optional**')
        m1, m2, m3, m4, m5 = st.columns(5)
        chest = m1.number_input('Chest', 0.0, 200.0, step=0.5,
                                value=float(latest.get('chest_cm') or 0) if latest else 0.0)
        waist = m2.number_input('Waist', 0.0, 200.0, step=0.5,
                                value=float(latest.get('waist_cm') or 0) if latest else 0.0)
        hips = m3.number_input('Hips', 0.0, 200.0, step=0.5,
                               value=float(latest.get('hips_cm') or 0) if latest else 0.0)
        arms = m4.number_input('Arms', 0.0, 100.0, step=0.5,
                               value=float(latest.get('arms_cm') or 0) if latest else 0.0)
        thighs = m5.number_input('Thighs', 0.0, 100.0, step=0.5,
                                 value=float(latest.get('thighs_cm') or 0) if latest else 0.0)

        notes = st.text_input('Notes (optional)', placeholder='e.g. after morning workout, fasted')
        submitted = st.form_submit_button('Save Measurements', type='primary', use_container_width=True)

    if submitted:
        entry = {
            'date': date.today().isoformat(),
            'time': datetime.now().strftime('%H:%M'),
            'weight_kg': round(weight_kg, 1),
            'height_cm': round(height_cm, 1),
            'body_fat_pct': round(body_fat, 1) if body_fat > 0 else None,
            'chest_cm': round(chest, 1) if chest > 0 else None,
            'waist_cm': round(waist, 1) if waist > 0 else None,
            'hips_cm': round(hips, 1) if hips > 0 else None,
            'arms_cm': round(arms, 1) if arms > 0 else None,
            'thighs_cm': round(thighs, 1) if thighs > 0 else None,
            'notes': notes.strip() if notes else None,
        }
        # Don't duplicate today's entry — replace it
        existing_today = [l for l in logs if l['date'] == entry['date']]
        for old in existing_today:
            logs.remove(old)
        logs.insert(0, entry)
        st.session_state.body_metrics_log = logs
        _save_to_supabase(entry)
        st.success('✅ Measurements saved!')
        st.rerun()

    st.divider()

    # ── Charts ────────────────────────────────────────────────────────────────
    if len(logs) >= 2:
        st.subheader('Weight Trend')
        _render_weight_chart(logs)

        if any(l.get('body_fat_pct') for l in logs):
            st.subheader('Body Fat % Trend')
            _render_bodyfat_chart(logs)

        if any(l.get('waist_cm') for l in logs):
            st.subheader('Measurements (cm)')
            _render_measurements_chart(logs)

    elif len(logs) == 1:
        st.info('Log at least 2 measurements to see trend charts.')

    st.divider()

    # ── History table ─────────────────────────────────────────────────────────
    if logs:
        st.subheader('Measurement History')
        df = pd.DataFrame(logs)
        display_cols = [c for c in ['date', 'weight_kg', 'body_fat_pct', 'waist_cm', 'chest_cm', 'arms_cm', 'notes'] if c in df.columns]
        st.dataframe(df[display_cols], use_container_width=True, hide_index=True)

        if st.button('Clear all local data', type='secondary'):
            st.session_state.body_metrics_log = []
            st.rerun()


# ── Charts ────────────────────────────────────────────────────────────────────

def _render_weight_chart(logs: list):
    df = pd.DataFrame([{'Date': l['date'], 'Weight (kg)': l['weight_kg']} for l in reversed(logs)])
    df['Date'] = pd.to_datetime(df['Date'])
    st.line_chart(df.set_index('Date'), color='#111827')

    if len(logs) >= 2:
        first = logs[-1]['weight_kg']
        last = logs[0]['weight_kg']
        delta = last - first
        sign = '▼' if delta < 0 else '▲'
        color = '#27ae60' if delta < 0 else '#e74c3c'
        st.markdown(
            f'<span style="color:{color};font-weight:700">{sign} {abs(delta):.1f} kg</span> '
            f'since {logs[-1]["date"]}',
            unsafe_allow_html=True,
        )


def _render_bodyfat_chart(logs: list):
    rows = [{'Date': l['date'], 'Body Fat (%)': l['body_fat_pct']} for l in reversed(logs) if l.get('body_fat_pct')]
    df = pd.DataFrame(rows)
    df['Date'] = pd.to_datetime(df['Date'])
    st.line_chart(df.set_index('Date'), color='#e74c3c')


def _render_measurements_chart(logs: list):
    measurement_cols = {'Waist': 'waist_cm', 'Chest': 'chest_cm', 'Hips': 'hips_cm', 'Arms': 'arms_cm', 'Thighs': 'thighs_cm'}
    rows = []
    for l in reversed(logs):
        row = {'Date': l['date']}
        for label, key in measurement_cols.items():
            if l.get(key):
                row[label] = l[key]
        rows.append(row)
    df = pd.DataFrame(rows).set_index('Date')
    df.index = pd.to_datetime(df.index)
    st.line_chart(df.dropna(axis=1, how='all'))


# ── BMI ───────────────────────────────────────────────────────────────────────

def _bmi(weight_kg, height_cm):
    if not weight_kg or not height_cm:
        return None
    h_m = height_cm / 100
    return round(weight_kg / (h_m ** 2), 1)


def _bmi_category(bmi: float):
    if bmi < 18.5:
        st.warning(f'BMI {bmi} — Underweight')
    elif bmi < 25:
        st.success(f'BMI {bmi} — Healthy weight ✅')
    elif bmi < 30:
        st.warning(f'BMI {bmi} — Overweight')
    else:
        st.error(f'BMI {bmi} — Obese')


# ── Supabase ──────────────────────────────────────────────────────────────────

def _save_to_supabase(entry: dict):
    try:
        from supabase_client import get_supabase_client
        from auth_page import get_current_user_id
        uid = get_current_user_id()
        if not uid:
            return
        client = get_supabase_client()
        row = {'user_id': uid, **{k: v for k, v in entry.items() if v is not None}}
        client.table('body_metrics').upsert(row, on_conflict='user_id,date').execute()
    except Exception:
        pass


def _load_from_supabase():
    try:
        from supabase_client import get_supabase_client
        from auth_page import get_current_user_id
        uid = get_current_user_id()
        if not uid:
            return
        client = get_supabase_client()
        res = client.table('body_metrics').select('*').eq('user_id', uid).order('date', desc=True).limit(60).execute()
        if res.data:
            st.session_state.body_metrics_log = res.data
    except Exception:
        pass


def _inject_css():
    st.markdown("""
        <style>
        .stNumberInput input { border-radius: 8px; }
        </style>
    """, unsafe_allow_html=True)
