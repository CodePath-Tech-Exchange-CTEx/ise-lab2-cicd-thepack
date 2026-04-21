#############################################################################
# app.py  —  Lykos
#############################################################################

import base64
import os
import streamlit as st

st.set_page_config(
    page_title='Lykos',
    page_icon='🐺',
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


def _logo_b64() -> str:
    logo_path = os.path.join(os.path.dirname(__file__), 'lykos.png')
    try:
        with open(logo_path, 'rb') as f:
            return base64.b64encode(f.read()).decode()
    except Exception:
        return ''


# ── Design system ──────────────────────────────────────────────────────────────
GLOBAL_CSS = """
<style>
/* ── Tokens ── */
:root {
    --black:    #0A0A0A;
    --charcoal: #1C1C1C;
    --orange:   #FF4500;
    --blue:     #005FFF;
    --purple:   #8000FF;
    --red:      #FF1A1A;
    --green:    #00C853;
    --bg:       #F2F2F2;
    --surface:  #FFFFFF;
    --border:   #D4D4D4;
    --text:     #0A0A0A;
    --muted:    #555555;
    --radius:   12px;
    --shadow:   0 3px 14px rgba(0,0,0,.13);
    --shadow-sm:0 1px 5px rgba(0,0,0,.09);
}

/* ── Page ── */
.stApp { background: var(--bg); }
.block-container { padding-top: 1.8rem !important; max-width: 1120px; }

/* ── Profile banner ── */
.profile-banner {
    background: #0A0A0A;
    border-radius: 16px;
    padding: 32px 36px;
    color: white;
    margin-bottom: 20px;
    box-shadow: 0 6px 28px rgba(0,0,0,.35);
    border-left: 5px solid #FF4500;
}
.profile-name {
    font-size: 1.8rem; font-weight: 900; margin: 0;
    letter-spacing: -0.6px; color: #FFFFFF;
}
.profile-username { font-size: .9rem; color: rgba(255,255,255,.6); margin: 5px 0 0; }
.profile-goal-pill {
    display: inline-block;
    margin-top: 14px;
    background: #FF4500;
    padding: 5px 16px;
    border-radius: 20px;
    font-size: .82rem;
    font-weight: 700;
    color: white;
    letter-spacing: .2px;
}

/* ── Streak badge ── */
.streak-badge {
    display: inline-block;
    background: #FF4500;
    border-radius: 20px;
    padding: 6px 18px;
    color: white;
    font-weight: 800;
    font-size: .85rem;
    margin-right: 8px;
    margin-bottom: 16px;
    letter-spacing: .3px;
}
.badge-pill {
    display: inline-block;
    background: #0A0A0A;
    border-radius: 20px;
    padding: 6px 18px;
    color: white;
    font-weight: 700;
    font-size: .82rem;
    margin-right: 8px;
    margin-bottom: 16px;
}

/* ── Stat cards ── */
.stat-card {
    background: var(--surface);
    border: 1.5px solid var(--border);
    border-radius: var(--radius);
    padding: 22px 16px;
    text-align: center;
    margin-bottom: 10px;
    box-shadow: var(--shadow-sm);
    transition: transform .15s, box-shadow .15s;
}
.stat-card:hover { transform: translateY(-3px); box-shadow: var(--shadow); }
.stat-value { font-size: 1.9rem; font-weight: 900; letter-spacing: -0.5px; }
.stat-label {
    font-size: .7rem;
    color: var(--muted);
    text-transform: uppercase;
    letter-spacing: 1.4px;
    font-weight: 700;
    margin-top: 6px;
}

/* ── Section label ── */
.section-label {
    font-size: .72rem;
    color: var(--muted);
    text-transform: uppercase;
    letter-spacing: 1.4px;
    font-weight: 700;
    margin: 22px 0 8px;
}

/* ── Tip card ── */
.tip-card {
    background: #FFFFFF;
    border: 1.5px solid var(--border);
    border-left: 5px solid #FF4500;
    border-radius: var(--radius);
    padding: 18px 22px;
    margin: 12px 0;
}
.tip-label {
    font-size: .7rem;
    text-transform: uppercase;
    letter-spacing: 1.4px;
    color: #FF4500;
    font-weight: 800;
    margin-bottom: 8px;
}
.tip-text { color: #0A0A0A; font-size: .95rem; line-height: 1.6; }

/* ── Streamlit metric cards ── */
[data-testid="stMetric"] {
    background: var(--surface);
    border: 1.5px solid var(--border);
    border-radius: var(--radius);
    padding: 14px 16px;
    box-shadow: var(--shadow-sm);
}
[data-testid="stMetricLabel"] { font-weight: 700 !important; color: var(--muted) !important; }
[data-testid="stMetricValue"] { font-weight: 900 !important; color: var(--text) !important; }

/* ── Progress bar ── */
[data-testid="stProgress"] > div > div { background: #FF4500 !important; }

/* ── Sidebar — jet black ── */
[data-testid="stSidebar"] {
    background: #0A0A0A !important;
    border-right: none !important;
}
[data-testid="stSidebar"] * { color: rgba(255,255,255,.82) !important; }
[data-testid="stSidebar"] hr { border-color: rgba(255,255,255,.1) !important; }
[data-testid="stSidebar"] .stRadio label {
    font-size: .9rem !important;
    padding: 4px 0 !important;
}
[data-testid="stSidebar"] .stRadio [data-baseweb="radio"] div:first-child {
    border-color: rgba(255,255,255,.35) !important;
}
/* Logo invert — black logo → white on dark sidebar */
[data-testid="stSidebar"] img { filter: brightness(0) invert(1) !important; }
/* Sign Out button — visible ghost style on dark sidebar */
[data-testid="stSidebar"] .stButton > button {
    background: transparent !important;
    color: #FFFFFF !important;
    border: 1.5px solid rgba(255,255,255,.4) !important;
}
[data-testid="stSidebar"] .stButton > button:hover {
    background: rgba(255,255,255,.12) !important;
    border-color: rgba(255,255,255,.8) !important;
    transform: none !important;
}

/* ── Buttons ── */
.stButton > button {
    border-radius: 10px !important;
    font-weight: 700 !important;
    font-size: .9rem !important;
    border: 1.5px solid var(--border) !important;
    background: var(--surface) !important;
    color: var(--text) !important;
    box-shadow: none !important;
    transition: background .12s, border-color .12s, transform .1s;
}
.stButton > button:hover {
    background: #EBEBEB !important;
    border-color: var(--text) !important;
    transform: translateY(-1px);
}
.stButton > button[kind="primary"] {
    background: #0A0A0A !important;
    color: white !important;
    border-color: #0A0A0A !important;
}
.stButton > button[kind="primary"]:hover {
    background: #2A2A2A !important;
    border-color: #2A2A2A !important;
}

/* ── Inputs ── */
.stTextInput input, .stNumberInput input,
.stTextArea textarea, .stSelectbox > div {
    border-radius: 10px !important;
    border: 1.5px solid var(--border) !important;
    font-size: .92rem !important;
    background: #FFFFFF !important;
    color: var(--text) !important;
}

/* ── Tabs ── */
[data-baseweb="tab"] { border-radius: 8px !important; font-size: .88rem !important; font-weight: 600 !important; }
[data-baseweb="tab-list"] { gap: 2px; }
[data-baseweb="tab"][aria-selected="true"] {
    background: #0A0A0A !important;
    color: white !important;
}

/* ── Expanders ── */
[data-testid="stExpander"] {
    border: 1.5px solid var(--border) !important;
    border-radius: var(--radius) !important;
    box-shadow: none !important;
}

/* ── Alerts ── */
[data-testid="stAlert"] { border-radius: var(--radius) !important; }

/* ── Divider ── */
hr { border-color: #D4D4D4 !important; }

/* ── Hide Streamlit chrome ── */
#MainMenu, footer { visibility: hidden; }
</style>
"""

PAGES = [
    'Home', 'Progress', 'Activity', 'Session',
    'Workout Plan', 'AI Coach', 'Apple Health',
    'Nutrition', 'Body Metrics', 'Community', 'Profile',
]

_NAV_ICONS = {
    'Home': '🏠', 'Progress': '📈', 'Activity': '⚡', 'Session': '🏋️',
    'Workout Plan': '📋', 'AI Coach': '🤖', 'Apple Health': '📱',
    'Nutrition': '🥗', 'Body Metrics': '📊', 'Community': '👥', 'Profile': '👤',
}

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


def _get_streak(bq_workouts):
    from progress_page import compute_streaks, to_date
    ah = st.session_state.get('apple_health', {})
    bq_dates = [to_date(w['start_timestamp']) for w in bq_workouts if to_date(w['start_timestamp'])]
    ah_dates = [to_date(w['start']) for w in ah.get('workouts', []) if to_date(w['start'])]
    current, _ = compute_streaks(list(set(bq_dates + ah_dates)))
    return current


def _sidebar_nav():
    logo_b64 = _logo_b64()
    with st.sidebar:
        # Logo + brand
        logo_html = (
            f'<img src="data:image/png;base64,{logo_b64}" '
            f'style="width:52px;height:52px;object-fit:contain;display:block;margin-bottom:10px">'
            if logo_b64 else ''
        )
        st.markdown(f"""
            <div style="padding:8px 0 4px">
                {logo_html}
                <div style="font-size:1.5rem;font-weight:900;color:white;
                            letter-spacing:-0.5px;line-height:1">Lykos</div>
                <div style="font-size:.72rem;color:rgba(255,255,255,.38);
                            letter-spacing:.8px;text-transform:uppercase;margin-top:3px">
                    Fitness
                </div>
            </div>
        """, unsafe_allow_html=True)

        st.markdown('<hr style="margin:14px 0 10px">', unsafe_allow_html=True)

        pages_with_icons = [f'{_NAV_ICONS[p]}  {p}' for p in PAGES]
        selected_idx = st.radio(
            'nav', pages_with_icons, label_visibility='collapsed', index=0,
        )
        selected = selected_idx.split('  ', 1)[1] if '  ' in selected_idx else selected_idx

        st.markdown('<hr style="margin:10px 0">', unsafe_allow_html=True)
        display_user_sidebar()

    return selected


def display_app_page():
    st.markdown(GLOBAL_CSS, unsafe_allow_html=True)

    authenticated = display_auth_page()
    if not authenticated:
        return

    load_goals_from_supabase()

    supabase_uid = get_current_user_id()
    bq_user_id   = _resolve_bq_user_id(supabase_uid)
    if bq_user_id is None:
        bq_user_id = 'user1'

    page = _sidebar_nav()
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


# ── Home page ──────────────────────────────────────────────────────────────────

def _stat_card(col, value, label, color):
    col.markdown(
        f'<div class="stat-card" style="border-top:4px solid {color}">'
        f'<div class="stat-value" style="color:{color}">{value}</div>'
        f'<div class="stat-label">{label}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )


def _render_home(user_id):
    try:
        profile = get_user_profile(user_id)
    except Exception:
        profile = {'full_name': 'Demo User', 'username': 'demo', 'friends': []}

    workouts       = get_user_workouts(user_id)
    ah             = st.session_state.get('apple_health', {})
    total_steps    = max(sum(w.get('steps', 0) for w in workouts), ah.get('total_steps', 0))
    total_calories = max(sum(w.get('calories_burned', 0) for w in workouts), ah.get('total_calories', 0))
    total_distance = sum(w.get('distance', 0) for w in workouts)
    display_name   = get_current_display_name()
    streak         = _get_streak(workouts)
    goals          = st.session_state.get('user_goals', {})

    # ── Profile banner ────────────────────────────────────────────────────────
    goal_pill = ''
    if goals:
        goal_pill = (
            f'<div class="profile-goal-pill">'
            f'{goals["primary_goal"]} &nbsp;·&nbsp; {goals["experience"]}'
            f'</div>'
        )

    st.markdown(f"""
        <div class="profile-banner">
            <p class="profile-name">{profile.get('full_name', display_name)}</p>
            <p class="profile-username">
                @{profile.get('username', '')}
                &nbsp;·&nbsp;
                {len(profile.get('friends', []))} friends
            </p>
            {goal_pill}
        </div>
    """, unsafe_allow_html=True)

    # ── Badges ────────────────────────────────────────────────────────────────
    badges_html = ''
    if streak > 0:
        badges_html += f'<div class="streak-badge">🔥 {streak}-day streak</div>'
    if ah:
        badges_html += '<div class="badge-pill">📱 Apple Health</div>'
    if badges_html:
        st.markdown(f'<div style="margin-bottom:6px">{badges_html}</div>', unsafe_allow_html=True)

    # ── Stats ─────────────────────────────────────────────────────────────────
    c1, c2, c3, c4 = st.columns(4)
    _stat_card(c1, str(len(workouts)),      'Workouts',    '#FF4500')
    _stat_card(c2, f'{total_steps:,.0f}',   'Total Steps', '#8000FF')
    _stat_card(c3, f'{total_distance:.1f}', 'Miles',       '#005FFF')
    _stat_card(c4, f'{total_calories:,.0f}','Calories',    '#FF1A1A')

    st.divider()

    # ── Today's session ───────────────────────────────────────────────────────
    sessions = st.session_state.get('completed_sessions', [])
    if sessions:
        from datetime import date
        today_sessions = [s for s in sessions if s.get('date') == date.today().isoformat()]
        if today_sessions:
            s = today_sessions[0]
            st.markdown('<div class="section-label">Today\'s Session</div>', unsafe_allow_html=True)
            tc1, tc2, tc3 = st.columns(3)
            tc1.metric('Duration',       f'{s["duration_min"]} min')
            tc2.metric('Sets completed',  s['total_sets'])
            tc3.metric('Est. calories',  f'~{s["cal_estimate"]} cal')
            st.divider()

    # ── Daily tip ─────────────────────────────────────────────────────────────
    try:
        advice = get_genai_advice(user_id)
        st.markdown(
            f'<div class="tip-card">'
            f'<div class="tip-label">Today\'s Tip</div>'
            f'<div class="tip-text">{advice["content"]}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
    except Exception:
        pass

    # ── Active goal ───────────────────────────────────────────────────────────
    if goals:
        st.markdown('<div class="section-label">Active Goal</div>', unsafe_allow_html=True)
        g1, g2, g3, g4 = st.columns(4)
        g1.metric('Goal',        goals.get('primary_goal', '—'))
        g2.metric('Focus',       goals.get('focus_area', '—'))
        g3.metric('Level',       goals.get('experience', '—'))
        g4.metric('Daily Steps', f"{goals.get('daily_steps_goal', 0):,}")
    else:
        st.info('Set your goals via AI Coach to unlock personalised planning.')

    if ah:
        st.success('Apple Health connected — stats include real iPhone data.')
    else:
        st.caption('Connect Apple Health data for device-level tracking.')


if __name__ == '__main__':
    display_app_page()
