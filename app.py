#############################################################################
# app.py  —  SDS Fitness
#############################################################################

import streamlit as st

st.set_page_config(
    page_title='SDS Fitness',
    page_icon='🏃',
    layout='wide',
    initial_sidebar_state='expanded',
)

from auth_page import (
    display_auth_page, display_user_sidebar,
    get_current_user_id, get_current_display_name,
)
from ai_coach_page import display_ai_coach_page, load_goals_from_supabase
from apple_health_page import display_apple_health_page
from community_page import display_community_page
from activity_page import display_activity_page
from workout_plan_page import display_workout_plan_page
from workout_session_page import display_workout_session_page
from progress_page import display_progress_page
from nutrition_page import display_nutrition_page
from body_metrics_page import display_body_metrics_page
from profile_page import display_profile_page
from data_fetcher import get_user_profile, get_user_workouts, get_genai_advice

GLOBAL_CSS = """
<style>
/* ── Design tokens ── */
:root {
    --bg:        #F7F7F8;
    --surface:   #FFFFFF;
    --border:    #E8E8ED;
    --text:      #111827;
    --muted:     #6B7280;
    --accent:    #111827;
    --accent-lt: #F3F4F6;
    --radius:    12px;
    --shadow:    0 1px 4px rgba(0,0,0,.07);
}

/* Page background */
.stApp { background: var(--bg); }
.block-container { padding-top: 2rem !important; max-width: 1100px; }

/* ── Stat cards ── */
.stat-card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 22px 16px;
    text-align: center;
    margin-bottom: 10px;
    box-shadow: var(--shadow);
}
.stat-value {
    font-size: 1.9rem;
    font-weight: 700;
    color: var(--text);
    letter-spacing: -0.5px;
}
.stat-label {
    font-size: 0.72rem;
    color: var(--muted);
    text-transform: uppercase;
    letter-spacing: 1.2px;
    margin-top: 4px;
}

/* ── Profile banner ── */
.profile-banner {
    background: var(--text);
    border-radius: 16px;
    padding: 28px 32px;
    color: white;
    margin-bottom: 24px;
}
.profile-name { font-size: 1.6rem; font-weight: 700; margin: 0; letter-spacing: -0.3px; }
.profile-username { font-size: 0.9rem; color: rgba(255,255,255,.55); margin: 4px 0 0; }

/* ── Streak badge ── */
.streak-badge {
    background: #111827;
    border-radius: 8px;
    padding: 7px 16px;
    color: white;
    font-weight: 600;
    font-size: 0.88rem;
    display: inline-block;
    margin: 0 0 18px;
    letter-spacing: 0.1px;
}

/* ── Streamlit overrides ── */
[data-testid="stMetric"] {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 14px 16px;
    box-shadow: var(--shadow);
}
[data-testid="stProgress"] > div > div { background-color: #111827 !important; }
[data-testid="stSidebar"] { background: var(--surface) !important; border-right: 1px solid var(--border); }

/* Buttons */
.stButton > button {
    border-radius: 8px !important;
    font-weight: 500 !important;
    font-size: 0.9rem !important;
    border: 1px solid var(--border) !important;
    background: var(--surface) !important;
    color: var(--text) !important;
    box-shadow: none !important;
    transition: background .15s, border-color .15s;
}
.stButton > button:hover {
    background: var(--accent-lt) !important;
    border-color: #9CA3AF !important;
}
.stButton > button[kind="primary"] {
    background: var(--text) !important;
    color: white !important;
    border-color: var(--text) !important;
}
.stButton > button[kind="primary"]:hover {
    background: #374151 !important;
}

/* Inputs */
.stTextInput input, .stNumberInput input, .stTextArea textarea {
    border-radius: 8px !important;
    border: 1px solid var(--border) !important;
    font-size: 0.92rem !important;
}

/* Sidebar nav radio */
[data-testid="stSidebar"] .stRadio label {
    font-size: 0.9rem;
    color: var(--text);
    padding: 3px 0;
}
[data-testid="stSidebar"] .stRadio { gap: 2px; }

/* Tabs */
[data-baseweb="tab"] { border-radius: 8px !important; font-size: 0.88rem !important; }
[data-baseweb="tab-list"] { gap: 2px; }

/* Expanders */
[data-testid="stExpander"] {
    border: 1px solid var(--border) !important;
    border-radius: var(--radius) !important;
    box-shadow: none !important;
}

/* Info / success / warning boxes */
[data-testid="stAlert"] { border-radius: var(--radius) !important; }

/* Hide streamlit branding */
#MainMenu, footer { visibility: hidden; }
</style>
"""

PAGES = [
    'Home',
    'Progress',
    'Activity',
    'Session',
    'Workout Plan',
    'AI Coach',
    'Apple Health',
    'Nutrition',
    'Body Metrics',
    'Community',
    'Profile',
]

_BQ_FALLBACK_KEY = 'bq_user_id_override'


def _resolve_bq_user_id(supabase_uid):
    override = st.session_state.get(_BQ_FALLBACK_KEY)
    if override:
        return override
    try:
        get_user_profile(supabase_uid)
        return supabase_uid
    except Exception:
        return None


def _bq_id_picker():
    st.info("Link a demo User ID (user1, user2, user3) to load workout data.")
    with st.form('bq_id_form'):
        uid = st.text_input('Demo User ID', placeholder='user1')
        if st.form_submit_button('Link', type='primary'):
            try:
                get_user_profile(uid)
                st.session_state[_BQ_FALLBACK_KEY] = uid
                st.rerun()
            except Exception:
                st.error(f'User "{uid}" not found.')


def _get_streak(bq_workouts):
    from progress_page import compute_streaks, to_date
    ah = st.session_state.get('apple_health', {})
    bq_dates = [to_date(w['start_timestamp']) for w in bq_workouts if to_date(w['start_timestamp'])]
    ah_dates = [to_date(w['start']) for w in ah.get('workouts', []) if to_date(w['start'])]
    current, _ = compute_streaks(list(set(bq_dates + ah_dates)))
    return current


def _sidebar_nav():
    """Renders sidebar navigation and returns selected page label."""
    with st.sidebar:
        st.markdown("## SDS Fitness")
        st.markdown("---")
        selected = st.radio("Navigation", PAGES, label_visibility="collapsed")
        st.markdown("---")
    return selected


def display_app_page():
    st.markdown(GLOBAL_CSS, unsafe_allow_html=True)

    authenticated = display_auth_page()
    if not authenticated:
        return

    display_user_sidebar()
    load_goals_from_supabase()

    supabase_uid = get_current_user_id()
    bq_user_id = _resolve_bq_user_id(supabase_uid)

    page = _sidebar_nav()

    if bq_user_id is None:
        _bq_id_picker()
        if page == 'Apple Health':
            display_apple_health_page()
        elif page == 'Nutrition':
            display_nutrition_page('anon')
        elif page == 'Body Metrics':
            display_body_metrics_page()
        else:
            st.info("Link a demo User ID in the sidebar to unlock this page.")
        return

    _render_page(page, bq_user_id)


def _render_page(page, user_id):
    if page == 'Home':
        _render_home(user_id)
    elif page == 'Progress':
        display_progress_page(user_id)
    elif page == 'Activity':
        display_activity_page(user_id)
    elif page == 'Session':
        display_workout_session_page(user_id)
    elif page == 'Workout Plan':
        display_workout_plan_page(user_id)
    elif page == 'AI Coach':
        display_ai_coach_page(user_id)
    elif page == 'Apple Health':
        display_apple_health_page()
    elif page == 'Nutrition':
        display_nutrition_page(user_id)
    elif page == 'Body Metrics':
        display_body_metrics_page()
    elif page == 'Community':
        display_community_page(user_id)
    elif page == 'Profile':
        display_profile_page(user_id)


def _render_home(user_id):
    try:
        profile = get_user_profile(user_id)
    except Exception:
        st.error('Could not load profile.')
        return

    workouts = get_user_workouts(user_id)
    ah = st.session_state.get('apple_health', {})

    total_steps    = max(sum(w.get('steps', 0) for w in workouts), ah.get('total_steps', 0))
    total_calories = max(sum(w.get('calories_burned', 0) for w in workouts), ah.get('total_calories', 0))
    total_distance = sum(w.get('distance', 0) for w in workouts)

    display_name = get_current_display_name()
    streak = _get_streak(workouts)
    goals  = st.session_state.get('user_goals', {})

    goal_pill = (
        f'<div style="margin-top:10px;background:rgba(255,255,255,.12);'
        f'display:inline-block;padding:4px 12px;border-radius:6px;font-size:.82rem;letter-spacing:.2px">'
        f'{goals["primary_goal"]} &nbsp;·&nbsp; {goals["experience"]}</div>'
        if goals else ''
    )
    st.markdown(f"""
        <div class="profile-banner">
            <p class="profile-name">{profile.get('full_name', display_name)}</p>
            <p class="profile-username">@{profile.get('username','')} &nbsp;·&nbsp; {len(profile.get('friends',[]))} friends</p>
            {goal_pill}
        </div>
    """, unsafe_allow_html=True)

    if streak > 0:
        st.markdown(f'<div class="streak-badge">{streak}-day streak</div>', unsafe_allow_html=True)

    col1, col2, col3, col4 = st.columns(4)
    col1.markdown(f'<div class="stat-card"><div class="stat-value">{len(workouts)}</div><div class="stat-label">Workouts</div></div>', unsafe_allow_html=True)
    col2.markdown(f'<div class="stat-card"><div class="stat-value">{total_steps:,.0f}</div><div class="stat-label">Steps</div></div>', unsafe_allow_html=True)
    col3.markdown(f'<div class="stat-card"><div class="stat-value">{total_distance:.1f}</div><div class="stat-label">Miles</div></div>', unsafe_allow_html=True)
    col4.markdown(f'<div class="stat-card"><div class="stat-value">{total_calories:,.0f}</div><div class="stat-label">Calories</div></div>', unsafe_allow_html=True)

    if ah:
        st.success('Apple Health connected — stats include real iPhone data.')
    else:
        st.info('Connect Apple Health data via the sidebar for real device tracking.')

    sessions = st.session_state.get('completed_sessions', [])
    if sessions:
        from datetime import date
        today_sessions = [s for s in sessions if s.get('date') == date.today().isoformat()]
        if today_sessions:
            s = today_sessions[0]
            st.markdown("**Today's session**")
            c1, c2, c3 = st.columns(3)
            c1.metric('Duration', f'{s["duration_min"]} min')
            c2.metric('Sets completed', s['total_sets'])
            c3.metric('Est. calories', s['cal_estimate'])

    st.divider()

    try:
        advice = get_genai_advice(user_id)
        st.markdown("**Today's tip**")
        st.info(advice['content'])
    except Exception:
        pass

    if goals:
        st.markdown(f"**Active goal — {goals['primary_goal']}**")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric('Focus', goals.get('focus_area', '—'))
        c2.metric('Level', goals.get('experience', '—'))
        c3.metric('Workouts / week', goals.get('weekly_workouts', '—'))
        c4.metric('Daily step target', f"{goals.get('daily_steps_goal', 0):,}")
    else:
        st.info('Set your goals via AI Coach in the sidebar to unlock personalised planning.')


if __name__ == '__main__':
    display_app_page()
