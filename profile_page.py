#############################################################################
# profile_page.py
#
# User profile, achievements & badge system.
#   - Profile card with avatar, name, goals summary
#   - Achievement badges (unlocked dynamically based on real stats)
#   - Lifetime stats summary
#   - Account settings (display name, sign-out)
#############################################################################

from datetime import date, timedelta, datetime

import streamlit as st

from data_fetcher import get_user_workouts, get_user_profile

# ── Badge definitions ─────────────────────────────────────────────────────────

def _check_badges(stats):
    """Return list of unlocked badge dicts."""

    definitions = [
        # Workout count milestones
        ('first_workout',   'First Step',        'Complete your first workout',
         lambda s: s['total_workouts'] >= 1),
        ('workout_5',       'Getting Started',   'Complete 5 workouts',
         lambda s: s['total_workouts'] >= 5),
        ('workout_10',      'Ten Strong',        'Complete 10 workouts',
         lambda s: s['total_workouts'] >= 10),
        ('workout_25',      'On Fire',           'Complete 25 workouts',
         lambda s: s['total_workouts'] >= 25),
        ('workout_50',      'Unstoppable',       'Complete 50 workouts',
         lambda s: s['total_workouts'] >= 50),
        ('workout_100',     'Legend',            'Complete 100 workouts',
         lambda s: s['total_workouts'] >= 100),
        # Steps milestones
        ('steps_10k',       '10K Steps',         'Log 10,000 total steps',
         lambda s: s['total_steps'] >= 10_000),
        ('steps_100k',      'Step Master',       'Log 100,000 total steps',
         lambda s: s['total_steps'] >= 100_000),
        ('steps_1m',        'Million Stepper',   'Log 1,000,000 total steps',
         lambda s: s['total_steps'] >= 1_000_000),
        # Distance milestones
        ('dist_10mi',       'Explorer',          'Cover 10 miles in workouts',
         lambda s: s['total_distance'] >= 10),
        ('dist_50mi',       'Globe Trotter',     'Cover 50 miles in workouts',
         lambda s: s['total_distance'] >= 50),
        ('dist_marathon',   'Marathon Runner',   'Cover 26.2 miles in a week',
         lambda s: s['best_week_dist'] >= 26.2),
        # Calorie milestones
        ('cal_1000',        'Calorie Crusher',   'Burn 1,000 calories total',
         lambda s: s['total_calories'] >= 1_000),
        ('cal_10k',         'Inferno',           'Burn 10,000 calories total',
         lambda s: s['total_calories'] >= 10_000),
        # Streaks
        ('streak_3',        'Consistent',        '3-day workout streak',
         lambda s: s['current_streak'] >= 3),
        ('streak_7',        'Week Warrior',      '7-day workout streak',
         lambda s: s['current_streak'] >= 7),
        ('streak_30',       'Iron Will',         '30-day workout streak',
         lambda s: s['current_streak'] >= 30),
        # Goals / features used
        ('set_goals',       'Goal Setter',       'Set your fitness goals',
         lambda s: s['has_goals']),
        ('apple_health',    'iPhone Athlete',    'Connect Apple Health data',
         lambda s: s['has_apple_health']),
        ('nutrition',       'Food Aware',        'Generate a nutrition plan',
         lambda s: s['has_nutrition_plan']),
        ('body_metrics',    'Body Tracker',      'Log body measurements',
         lambda s: s['has_body_metrics']),
        ('session',         'Live Trainer',      'Complete a live session',
         lambda s: s['has_completed_session']),
    ]

    unlocked = []
    for badge_id, name, desc, checker in definitions:
        try:
            is_unlocked = checker(stats)
        except Exception:
            is_unlocked = False
        unlocked.append({'id': badge_id, 'name': name, 'desc': desc, 'unlocked': is_unlocked})

    return unlocked


# ── Stats aggregator ──────────────────────────────────────────────────────────

def _aggregate_stats(user_id: str) -> dict:
    try:
        bq_workouts = get_user_workouts(user_id)
    except Exception:
        bq_workouts = []

    ah = st.session_state.get('apple_health', {})
    ah_steps = ah.get('total_steps', 0)
    ah_cal = ah.get('total_calories', 0)

    total_steps = max(sum(w.get('steps', 0) for w in bq_workouts), ah_steps)
    total_cal = max(sum(w.get('calories_burned', 0) for w in bq_workouts), ah_cal)
    total_dist = sum(w.get('distance', 0) for w in bq_workouts)

    # Best week distance
    from collections import defaultdict
    week_dist = defaultdict(float)
    for w in bq_workouts:
        try:
            d = datetime.fromisoformat(str(w['start_timestamp'])[:19]).date()
            monday = (d - timedelta(days=d.weekday())).isoformat()
            week_dist[monday] += w.get('distance', 0)
        except Exception:
            pass
    best_week_dist = max(week_dist.values(), default=0)

    # Streaks
    from progress_page import compute_streaks, to_date
    workout_dates = [to_date(w['start_timestamp']) for w in bq_workouts if to_date(w['start_timestamp'])]
    ah_dates = [to_date(w['start']) for w in ah.get('workouts', []) if to_date(w['start'])]
    all_dates = list(set(workout_dates + ah_dates))
    current_streak, _ = compute_streaks(all_dates)

    return {
        'total_workouts': len(bq_workouts) + len(ah.get('workouts', [])),
        'total_steps': total_steps,
        'total_calories': total_cal,
        'total_distance': total_dist,
        'best_week_dist': best_week_dist,
        'current_streak': current_streak,
        'has_goals': bool(st.session_state.get('user_goals')),
        'has_apple_health': bool(ah),
        'has_nutrition_plan': bool(st.session_state.get(f'meal_plan_{date.today().isoformat()}')),
        'has_body_metrics': bool(st.session_state.get('body_metrics_log')),
        'has_completed_session': bool(st.session_state.get('completed_sessions')),
    }


# ── Main ──────────────────────────────────────────────────────────────────────

def display_profile_page(user_id: str):
    st.title('Profile')

    _inject_css()

    # ── Profile card ──────────────────────────────────────────────────────────
    try:
        bq_profile = get_user_profile(user_id)
    except Exception:
        bq_profile = {}

    from auth_page import get_current_display_name, get_current_user_id
    display_name = get_current_display_name()
    supabase_user = st.session_state.get('supabase_user', {})
    email = supabase_user.get('email', '')
    username = bq_profile.get('username', '')
    goals = st.session_state.get('user_goals', {})

    initials = ''.join(p[0].upper() for p in display_name.split()[:2]) if display_name else '?'

    st.markdown(f"""
        <div style="background:#111827;border-radius:16px;padding:32px;color:white;margin-bottom:24px">
            <div style="width:56px;height:56px;border-radius:50%;background:rgba(255,255,255,.15);
                        display:inline-flex;align-items:center;justify-content:center;
                        font-size:1.3rem;font-weight:700;margin-bottom:14px">{initials}</div>
            <div style="font-size:1.6rem;font-weight:700;letter-spacing:-0.3px">{display_name}</div>
            {'<div style="color:rgba(255,255,255,.5);font-size:0.88rem;margin-top:2px">@' + username + '</div>' if username else ''}
            <div style="color:rgba(255,255,255,.4);font-size:0.82rem;margin-top:2px">{email}</div>
            {'<div style="margin-top:14px;background:rgba(255,255,255,.1);display:inline-block;padding:5px 14px;border-radius:6px;font-size:0.82rem;letter-spacing:.2px">' + goals.get("primary_goal","") + ' &nbsp;·&nbsp; ' + goals.get("experience","") + '</div>' if goals else ''}
        </div>
    """, unsafe_allow_html=True)

    st.divider()

    # ── Aggregate stats ───────────────────────────────────────────────────────
    with st.spinner('Loading your stats…'):
        stats = _aggregate_stats(user_id)

    st.subheader('Lifetime Stats')
    c1, c2, c3, c4 = st.columns(4)
    c1.metric('Workouts', stats['total_workouts'])
    c2.metric('Steps', f"{stats['total_steps']:,.0f}")
    c3.metric('Miles', f"{stats['total_distance']:.1f}")
    c4.metric('Calories', f"{stats['total_calories']:,.0f}")

    st.divider()

    # ── Achievements ──────────────────────────────────────────────────────────
    st.subheader('Achievements')
    badges = _check_badges(stats)
    unlocked = [b for b in badges if b['unlocked']]
    locked = [b for b in badges if not b['unlocked']]

    st.markdown(f'**{len(unlocked)} / {len(badges)} badges earned**')
    prog_pct = len(unlocked) / len(badges) if badges else 0
    st.progress(prog_pct)

    if unlocked:
        st.markdown('**Earned**')
        cols = st.columns(4)
        for i, badge in enumerate(unlocked):
            with cols[i % 4]:
                st.markdown(
                    f'<div style="background:#F9FAFB;border:1px solid #111827;border-radius:12px;'
                    f'padding:14px;text-align:center;margin-bottom:10px">'
                    f'<div style="font-weight:700;font-size:0.88rem;color:#111827;margin-bottom:4px">{badge["name"]}</div>'
                    f'<div style="font-size:0.7rem;color:#6B7280">{badge["desc"]}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

    with st.expander(f'{len(locked)} locked badges'):
        cols2 = st.columns(4)
        for i, badge in enumerate(locked):
            with cols2[i % 4]:
                st.markdown(
                    f'<div style="background:#F9FAFB;border:1px dashed #D1D5DB;border-radius:12px;'
                    f'padding:14px;text-align:center;margin-bottom:10px;opacity:.55">'
                    f'<div style="font-weight:600;font-size:0.85rem;color:#9CA3AF;margin-bottom:4px">{badge["name"]}</div>'
                    f'<div style="font-size:0.7rem;color:#D1D5DB">{badge["desc"]}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

    st.divider()

    # ── Account settings ──────────────────────────────────────────────────────
    st.subheader('Account Settings')

    with st.form('update_display_name_form'):
        new_name = st.text_input('Display name', value=display_name)
        if st.form_submit_button('Update Name'):
            try:
                from supabase_client import get_supabase_client
                client = get_supabase_client()
                client.auth.update_user({'data': {'display_name': new_name}})
                if st.session_state.get('supabase_user'):
                    st.session_state['supabase_user']['user_metadata']['display_name'] = new_name
                st.success('Name updated.')
                st.rerun()
            except Exception as e:
                st.error(f'Could not update: {e}')

    st.markdown('---')
    if st.button('Sign Out', type='secondary'):
        from auth_page import sign_out
        sign_out()
        st.rerun()


# ── CSS ───────────────────────────────────────────────────────────────────────

def _inject_css():
    st.markdown("""
        <style>
        [data-testid="stMetric"] { background:#F9FAFB; border-radius:12px; padding:12px; }
        [data-testid="stProgress"] > div > div { background-color: #111827 !important; }
        </style>
    """, unsafe_allow_html=True)
