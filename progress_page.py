#############################################################################
# progress_page.py
#
# Rich analytics dashboard:
#   - Current streak + longest streak
#   - Weekly step/calorie/distance trend (last 8 weeks)
#   - Personal records (best single-day steps, longest workout, etc.)
#   - Workout frequency heatmap (last 90 days)
#   - Apple Health overlay when available
#############################################################################

from collections import defaultdict
from datetime import date, timedelta, datetime

import pandas as pd
import streamlit as st

from data_fetcher import get_user_workouts


# ── Helpers ───────────────────────────────────────────────────────────────────

def to_date(s):
    if not s:
        return None
    try:
        return datetime.fromisoformat(str(s)[:19]).date()
    except Exception:
        return None


def compute_streaks(workout_dates):
    """Return (current_streak, longest_streak) in days."""
    if not workout_dates:
        return 0, 0
    unique = sorted(set(workout_dates), reverse=True)
    today = date.today()
    # current streak
    current = 0
    cursor = today
    for d in unique:
        if d == cursor or d == cursor - timedelta(days=1):
            current += 1
            cursor = d - timedelta(days=1) if d == cursor else d - timedelta(days=1)
        else:
            break
    # longest streak
    longest = 1
    run = 1
    for i in range(1, len(unique)):
        if (unique[i - 1] - unique[i]).days == 1:
            run += 1
            longest = max(longest, run)
        else:
            run = 1
    return current, longest


def _week_label(d: date) -> str:
    monday = d - timedelta(days=d.weekday())
    return monday.strftime('%b %d')


# ── Main ──────────────────────────────────────────────────────────────────────

def display_progress_page(user_id: str):
    st.title('Progress')

    _inject_css()

    # ── Load data ─────────────────────────────────────────────────────────────
    try:
        bq_workouts = get_user_workouts(user_id)
    except Exception:
        bq_workouts = []

    ah = st.session_state.get('apple_health', {})
    daily_steps_ah = ah.get('daily_steps', {})
    daily_cal_ah = ah.get('daily_calories', {})
    ah_workouts = ah.get('workouts', [])

    # Build a unified workout list for dates
    workout_dates_bq = [to_date(w['start_timestamp']) for w in bq_workouts if to_date(w['start_timestamp'])]
    workout_dates_ah = [to_date(w['start']) for w in ah_workouts if to_date(w['start'])]
    all_workout_dates = list(set(workout_dates_bq + workout_dates_ah))

    current_streak, longest_streak = compute_streaks(all_workout_dates)

    # ── Streak banner ─────────────────────────────────────────────────────────
    c1, c2, c3, c4 = st.columns(4)
    c1.markdown(_metric_card('Current Streak', f'{current_streak} days'), unsafe_allow_html=True)
    c2.markdown(_metric_card('Longest Streak', f'{longest_streak} days'), unsafe_allow_html=True)
    c3.markdown(_metric_card('Total Workouts', str(len(bq_workouts) + len(ah_workouts))), unsafe_allow_html=True)

    goals = st.session_state.get('user_goals', {})
    weekly_goal = goals.get('weekly_workouts', 3)
    this_week_count = sum(
        1 for d in all_workout_dates
        if d >= date.today() - timedelta(days=date.today().weekday())
    )
    c4.markdown(_metric_card('This Week', f'{this_week_count} / {weekly_goal}'), unsafe_allow_html=True)

    st.divider()

    # ── Weekly trend charts ───────────────────────────────────────────────────
    st.subheader('Weekly Trends')
    _render_weekly_trends(bq_workouts, daily_steps_ah, daily_cal_ah)

    st.divider()

    # ── Workout frequency heatmap ─────────────────────────────────────────────
    st.subheader('Workout Frequency — last 90 days')
    _render_heatmap(all_workout_dates)

    st.divider()

    # ── Personal records ──────────────────────────────────────────────────────
    st.subheader('Personal Records')
    _render_personal_records(bq_workouts, daily_steps_ah)

    st.divider()

    # ── Progress vs goals ─────────────────────────────────────────────────────
    if goals:
        st.subheader('Progress vs Goals')
        _render_goal_progress(bq_workouts, daily_steps_ah, goals)


# ── Weekly trends ─────────────────────────────────────────────────────────────

def _render_weekly_trends(bq_workouts, daily_steps_ah, daily_cal_ah):
    today = date.today()
    weeks = []
    for w in range(7, -1, -1):
        monday = today - timedelta(days=today.weekday()) - timedelta(weeks=w)
        weeks.append(monday)

    # Steps per week
    weekly_steps = {}
    weekly_cal = {}
    weekly_workouts = {}
    weekly_dist = {}

    for monday in weeks:
        label = _week_label(monday)
        weekly_steps[label] = 0
        weekly_cal[label] = 0
        weekly_workouts[label] = 0
        weekly_dist[label] = 0.0
        for i in range(7):
            d = (monday + timedelta(days=i)).isoformat()
            weekly_steps[label] += daily_steps_ah.get(d, 0)
            weekly_cal[label] += daily_cal_ah.get(d, 0)

    for w in bq_workouts:
        d = to_date(w['start_timestamp'])
        if not d:
            continue
        lbl = _week_label(d)
        if lbl in weekly_workouts:
            weekly_workouts[lbl] += 1
            weekly_dist[lbl] += w.get('distance', 0)
            if not daily_steps_ah:
                weekly_steps[lbl] += w.get('steps', 0)
            if not daily_cal_ah:
                weekly_cal[lbl] += w.get('calories_burned', 0)

    tab1, tab2, tab3, tab4 = st.tabs(['Steps', 'Calories', 'Workouts', 'Distance'])

    df_steps = pd.DataFrame({'Week': list(weekly_steps.keys()), 'Steps': list(weekly_steps.values())})
    df_cal = pd.DataFrame({'Week': list(weekly_cal.keys()), 'Calories': list(weekly_cal.values())})
    df_wo = pd.DataFrame({'Week': list(weekly_workouts.keys()), 'Workouts': list(weekly_workouts.values())})
    df_dist = pd.DataFrame({'Week': list(weekly_dist.keys()), 'Distance (mi)': list(weekly_dist.values())})

    with tab1:
        st.bar_chart(df_steps.set_index('Week'), color='#111827')
    with tab2:
        st.bar_chart(df_cal.set_index('Week'), color='#e74c3c')
    with tab3:
        st.bar_chart(df_wo.set_index('Week'), color='#27ae60')
    with tab4:
        st.bar_chart(df_dist.set_index('Week'), color='#2980b9')


# ── Heatmap ───────────────────────────────────────────────────────────────────

def _render_heatmap(workout_dates):
    """Simple text-based calendar heatmap."""
    today = date.today()
    start = today - timedelta(days=89)
    date_set = set(workout_dates)

    weeks = []
    current_week: list = []
    cursor = start
    # pad to Monday
    while cursor.weekday() != 0:
        current_week.append(None)
        cursor += timedelta(days=1)
    while cursor <= today:
        current_week.append(cursor)
        if len(current_week) == 7:
            weeks.append(current_week)
            current_week = []
        cursor += timedelta(days=1)
    if current_week:
        while len(current_week) < 7:
            current_week.append(None)
        weeks.append(current_week)

    day_labels = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
    rows = {day: [] for day in day_labels}

    for week in weeks:
        for i, d in enumerate(week):
            if d is None:
                rows[day_labels[i]].append('□')
            elif d in date_set:
                rows[day_labels[i]].append('■')
            else:
                rows[day_labels[i]].append('□')

    month_labels = []
    prev_month = None
    for week in weeks:
        first_real = next((d for d in week if d), None)
        if first_real:
            m = first_real.strftime('%b')
            if m != prev_month:
                month_labels.append(m)
                prev_month = m
            else:
                month_labels.append('')
        else:
            month_labels.append('')

    # Render as compact grid
    header = '&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;' + ''.join(
        f'<span style="font-size:0.65rem;color:#aaa;width:18px;display:inline-block;text-align:center">{m}</span>'
        for m in month_labels
    )
    st.markdown(header, unsafe_allow_html=True)

    for day, cells in rows.items():
        row_html = (
            f'<span style="font-size:0.65rem;color:#888;width:28px;display:inline-block">{day}</span>'
            + ''.join(
                f'<span title="{weeks[wi][["Mon","Tue","Wed","Thu","Fri","Sat","Sun"].index(day)] or ""}" '
                f'style="font-size:0.7rem">{c}</span>'
                for wi, c in enumerate(cells)
            )
        )
        st.markdown(row_html, unsafe_allow_html=True)

    st.caption('■ = workout day  □ = rest day')


# ── Personal records ──────────────────────────────────────────────────────────

def _render_personal_records(bq_workouts, daily_steps_ah: dict):
    records = {}

    if bq_workouts:
        records['Most Steps in a Workout'] = f"{max(w.get('steps', 0) for w in bq_workouts):,}"
        records['Longest Distance'] = f"{max(w.get('distance', 0) for w in bq_workouts):.2f} mi"
        records['Most Calories Burned'] = f"{max(w.get('calories_burned', 0) for w in bq_workouts):,.0f} cal"

        # Longest streak
        dates = sorted(set(
            to_date(w['start_timestamp']) for w in bq_workouts
            if to_date(w['start_timestamp'])
        ))
        _, longest = compute_streaks(dates)
        records['Longest Workout Streak'] = f'{longest} days'

    if daily_steps_ah:
        best_day_steps = max(daily_steps_ah.values())
        best_day_date = max(daily_steps_ah, key=daily_steps_ah.get)
        records['Best Step Day (iPhone)'] = f"{best_day_steps:,.0f} steps on {best_day_date}"

    if not records:
        st.caption('No workout data yet — complete some workouts to see your records.')
        return

    cols = st.columns(min(len(records), 3))
    for i, (label, value) in enumerate(records.items()):
        with cols[i % 3]:
            st.markdown(
                f'<div style="background:#F9FAFB;border-left:3px solid #111827;'
                f'border-radius:8px;padding:14px 16px;margin-bottom:12px">'
                f'<div style="font-size:0.75rem;color:#6B7280;text-transform:uppercase;letter-spacing:0.8px">{label}</div>'
                f'<div style="font-size:1.3rem;font-weight:700;color:#111827;margin-top:4px">{value}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )


# ── Goal progress ─────────────────────────────────────────────────────────────

def _render_goal_progress(bq_workouts, daily_steps_ah: dict, goals: dict):
    daily_goal = goals.get('daily_steps_goal', 8_000)
    weekly_wo_goal = goals.get('weekly_workouts', 3)

    today = date.today()
    week_start = today - timedelta(days=today.weekday())

    # Steps today
    today_steps = daily_steps_ah.get(today.isoformat(), 0)
    if not today_steps and bq_workouts:
        today_steps = sum(
            w.get('steps', 0) for w in bq_workouts
            if to_date(w['start_timestamp']) == today
        )

    # Workouts this week
    wo_this_week = sum(
        1 for w in bq_workouts
        if to_date(w['start_timestamp']) and to_date(w['start_timestamp']) >= week_start
    )

    col1, col2 = st.columns(2)
    with col1:
        pct = min(today_steps / daily_goal, 1.0) if daily_goal else 0
        st.markdown(f'**Daily Steps — {today_steps:,.0f} / {daily_goal:,}**')
        st.progress(pct)
        _progress_label(pct)

    with col2:
        pct2 = min(wo_this_week / weekly_wo_goal, 1.0) if weekly_wo_goal else 0
        st.markdown(f'**Weekly Workouts — {wo_this_week} / {weekly_wo_goal}**')
        st.progress(pct2)
        _progress_label(pct2)


def _progress_label(pct: float):
    if pct >= 1.0:
        st.success('✅ Goal achieved!')
    elif pct >= 0.75:
        st.info(f'Almost there — {pct*100:.0f}% complete')
    elif pct >= 0.5:
        st.caption(f'{pct*100:.0f}% of the way there, keep going!')
    else:
        st.caption(f'{pct*100:.0f}% complete — you\'ve got this!')


# ── UI helpers ────────────────────────────────────────────────────────────────

def _metric_card(label, value):
    return (
        f'<div style="background:#fff;border:1px solid #E8E8ED;border-radius:12px;'
        f'padding:20px 16px;text-align:center;box-shadow:0 1px 4px rgba(0,0,0,.07);margin-bottom:10px">'
        f'<div style="font-size:1.7rem;font-weight:700;color:#111827;letter-spacing:-0.5px">{value}</div>'
        f'<div style="font-size:0.72rem;color:#6B7280;text-transform:uppercase;letter-spacing:1.2px;margin-top:4px">{label}</div>'
        f'</div>'
    )


def _inject_css():
    st.markdown("""
        <style>
        [data-testid="stMetric"] { background:#F9FAFB; border-radius:12px; padding:12px; }
        [data-testid="stProgress"] > div > div { background-color: #111827 !important; }
        </style>
    """, unsafe_allow_html=True)
