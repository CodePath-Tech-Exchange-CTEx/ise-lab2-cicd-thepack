#############################################################################
# ai_coach_page.py
#
# AI Coach page: goal setting + personalized exercise suggestions.
#
# The coach analyses:
#   • User goals (set on this page and stored in session / Supabase)
#   • BigQuery workout history (steps, calories, distance)
#   • Apple Health data (if uploaded on the Apple Health page)
#
# It then calls Vertex AI / Gemini to generate:
#   • A progress summary
#   • A personalised exercise plan for today
#   • Concrete next-step advice
#############################################################################

import json
from datetime import datetime

import streamlit as st
import vertexai
from vertexai.generative_models import GenerativeModel

from data_fetcher import get_user_workouts, get_user_profile, get_workout_plan, PROJECT_ID

# ── Constants ─────────────────────────────────────────────────────────────────

FITNESS_GOALS = [
    'Lose Weight',
    'Build Muscle',
    'Improve Endurance',
    'Increase Flexibility',
    'General Fitness',
    'Train for a Race',
    'Reduce Stress',
]

EXPERIENCE_LEVELS = ['Beginner', 'Intermediate', 'Advanced']

FOCUS_AREAS = ['Chest', 'Back', 'Legs', 'Shoulders', 'Arms', 'Core', 'Full Body']


# ── Main entry point ──────────────────────────────────────────────────────────

def display_ai_coach_page(user_id: str):
    """Renders the full AI Coach tab."""
    st.title('AI Coach')

    # Step 1 – Goal setup
    goals = _render_goal_setup()
    if goals is None:
        return  # user hasn't set goals yet

    st.divider()

    # Step 2 – Progress snapshot
    with st.spinner('Analysing your progress…'):
        progress = _build_progress_context(user_id)

    _render_progress_snapshot(progress)
    st.divider()

    # Step 3 – AI coaching advice
    st.subheader('Coaching Advice')
    with st.spinner('Generating your personalised advice…'):
        advice = _get_coaching_advice(user_id, goals, progress)
    st.info(advice)

    st.divider()

    # Step 4 – Exercise suggestions
    st.subheader("Today's Exercises")
    _render_exercise_suggestions(user_id, goals, progress)


# ── Goal setup ────────────────────────────────────────────────────────────────

def _render_goal_setup():
    """Renders the goal-setting form. Returns the goals dict or None if not set."""

    st.subheader('Your Fitness Goals')

    # Load from session state if already set
    existing = st.session_state.get('user_goals')

    with st.expander('Set / update your goals', expanded=existing is None):
        with st.form('goals_form'):
            col1, col2 = st.columns(2)
            with col1:
                primary_goal = st.selectbox(
                    'Primary goal',
                    FITNESS_GOALS,
                    index=FITNESS_GOALS.index(existing['primary_goal']) if existing else 0,
                )
                experience = st.selectbox(
                    'Experience level',
                    EXPERIENCE_LEVELS,
                    index=EXPERIENCE_LEVELS.index(existing['experience']) if existing else 0,
                )
                focus_area = st.selectbox(
                    'Preferred focus area',
                    FOCUS_AREAS,
                    index=FOCUS_AREAS.index(existing['focus_area']) if existing else 0,
                )
            with col2:
                weekly_workouts = st.slider(
                    'Workouts per week',
                    min_value=1, max_value=7,
                    value=existing['weekly_workouts'] if existing else 3,
                )
                daily_steps_goal = st.number_input(
                    'Daily step goal',
                    min_value=1_000, max_value=30_000,
                    step=500,
                    value=existing['daily_steps_goal'] if existing else 8_000,
                )
                notes = st.text_area(
                    'Anything else (injuries, preferences…)',
                    value=existing.get('notes', '') if existing else '',
                    max_chars=300,
                    placeholder='e.g. bad left knee, prefer no jumping',
                )

            save = st.form_submit_button('Save Goals', type='primary', use_container_width=True)

        if save:
            goals = {
                'primary_goal': primary_goal,
                'experience': experience,
                'focus_area': focus_area,
                'weekly_workouts': weekly_workouts,
                'daily_steps_goal': daily_steps_goal,
                'notes': notes,
                'updated_at': datetime.utcnow().isoformat(),
            }
            st.session_state['user_goals'] = goals
            _persist_goals_to_supabase(goals)
            st.success('Goals saved!')
            st.rerun()

    return st.session_state.get('user_goals')


# ── Progress context builder ──────────────────────────────────────────────────

def _build_progress_context(user_id: str) -> dict:
    """Aggregates BigQuery + Apple Health data into a progress summary dict."""
    # BigQuery workouts
    try:
        bq_workouts = get_user_workouts(user_id)
    except Exception:
        bq_workouts = []

    bq_total_steps = sum(w.get('steps', 0) for w in bq_workouts)
    bq_total_cal = sum(w.get('calories_burned', 0) for w in bq_workouts)
    bq_total_dist = sum(w.get('distance', 0) for w in bq_workouts)

    # Apple Health (if uploaded)
    ah = st.session_state.get('apple_health', {})
    ah_total_steps = ah.get('total_steps', 0)
    ah_total_cal = ah.get('total_calories', 0)
    ah_workouts = ah.get('workouts', [])
    ah_avg_hr = ah.get('avg_heart_rate', 0)

    # Combine
    has_ah = bool(ah)
    total_steps = (ah_total_steps or bq_total_steps)
    total_cal = (ah_total_cal or bq_total_cal)
    all_workouts = bq_workouts if not ah_workouts else ah_workouts
    total_workout_count = len(all_workouts)

    # Last-7-days steps from Apple Health
    recent_daily_steps = {}
    if ah.get('daily_steps'):
        from datetime import timedelta
        today = datetime.today().date()
        for i in range(7):
            d = (today - timedelta(days=i)).isoformat()
            recent_daily_steps[d] = ah['daily_steps'].get(d, 0)

    return {
        'total_steps': total_steps,
        'total_calories': total_cal,
        'total_distance': bq_total_dist if not has_ah else ah.get('total_distance_km', 0),
        'total_workout_count': total_workout_count,
        'avg_heart_rate': ah_avg_hr,
        'recent_daily_steps': recent_daily_steps,
        'has_apple_health': has_ah,
        'bq_workouts': bq_workouts,
        'latest_workout': bq_workouts[0] if bq_workouts else (ah_workouts[0] if ah_workouts else None),
    }


# ── Progress snapshot UI ──────────────────────────────────────────────────────

def _render_progress_snapshot(progress: dict):
    st.subheader('Progress Snapshot')

    goals = st.session_state.get('user_goals', {})
    daily_goal = goals.get('daily_steps_goal', 8_000)
    weekly_goal = goals.get('weekly_workouts', 3)

    col1, col2, col3, col4 = st.columns(4)
    col1.metric('Total Steps', f"{progress['total_steps']:,.0f}")
    col2.metric('Calories Burned', f"{progress['total_calories']:,.0f}")
    col3.metric('Total Workouts', progress['total_workout_count'])
    col4.metric(
        'Avg Heart Rate',
        f"{progress['avg_heart_rate']:.0f} bpm" if progress['avg_heart_rate'] else '—',
    )

    # Progress bar vs daily step goal
    if progress['recent_daily_steps']:
        latest_day = max(progress['recent_daily_steps'].keys())
        today_steps = progress['recent_daily_steps'].get(latest_day, 0)
        pct = min(today_steps / daily_goal, 1.0)
        st.markdown(f'**Daily Step Goal** ({today_steps:,.0f} / {daily_goal:,})')
        st.progress(pct)

    if not progress['has_apple_health']:
        st.caption('Upload Apple Health data on the Apple Health tab for richer insights.')


# ── Gemini-powered coaching advice ────────────────────────────────────────────

@st.cache_data(ttl=1800, show_spinner=False)
def _get_coaching_advice(user_id: str, goals: dict, progress: dict) -> str:
    """Calls Gemini to generate personalised coaching advice."""
    try:
        profile = get_user_profile(user_id)
        name = profile.get('full_name', 'Athlete')
    except Exception:
        name = 'Athlete'

    latest = progress.get('latest_workout')
    latest_str = ''
    if latest:
        if 'steps' in latest:
            latest_str = (
                f"Last workout: {latest.get('steps', 0):,} steps, "
                f"{latest.get('distance', 0):.1f} mi, "
                f"{latest.get('calories_burned', 0):,.0f} cal."
            )
        elif 'duration_min' in latest:
            latest_str = (
                f"Last workout: {latest.get('type', 'exercise')} for "
                f"{latest.get('duration_min', 0):.0f} min, "
                f"{latest.get('calories', 0):.0f} cal."
            )

    prompt = f"""You are an expert personal fitness coach. Write a short (3-4 sentences),
encouraging, and highly personalised coaching message for {name}.

Their goals:
- Primary goal: {goals['primary_goal']}
- Experience level: {goals['experience']}
- Target workouts per week: {goals['weekly_workouts']}
- Daily step goal: {goals['daily_steps_goal']:,}
- Notes: {goals.get('notes') or 'none'}

Their current stats:
- Total workouts logged: {progress['total_workout_count']}
- Total steps: {progress['total_steps']:,.0f}
- Total calories burned: {progress['total_calories']:,.0f}
- {latest_str}

Be specific, motivating, and acknowledge their actual progress.
Give one concrete action they should take today.
"""

    vertexai.init(project=PROJECT_ID, location='us-central1')
    model = GenerativeModel('gemini-2.5-flash-lite')
    response = model.generate_content(prompt)
    return response.text.strip()


# ── Exercise suggestions ──────────────────────────────────────────────────────

def _render_exercise_suggestions(user_id: str, goals: dict, progress: dict):
    """Generates and displays a personalised exercise plan."""

    focus = goals.get('focus_area', 'Full Body')
    if focus == 'Full Body':
        focus = 'Core'  # fall back to core for the free-exercise-db mapping

    # Allow manual refresh
    col1, col2 = st.columns([3, 1])
    with col1:
        st.caption(f'Tailored for **{goals["primary_goal"]}** · **{goals["experience"]}** level · Focus: **{goals["focus_area"]}**')
    with col2:
        refresh = st.button('New suggestions', use_container_width=True)

    # Clear cache on refresh
    if refresh:
        get_workout_plan.clear()
        st.rerun()

    with st.spinner('Building your personalised workout…'):
        plan = _get_ai_exercise_plan(user_id, goals, progress, focus)

    if not plan:
        st.warning('Could not generate a plan right now. Try a different focus area.')
        return

    for i, ex in enumerate(plan):
        with st.container(border=True):
            c1, c2 = st.columns([1, 2])
            with c1:
                if ex.get('imageUrl'):
                    st.image(ex['imageUrl'], use_container_width=True)
            with c2:
                st.markdown(f"### {i+1}. {ex['name']}")
                col_a, col_b, col_c = st.columns(3)
                col_a.metric('Sets', ex.get('sets', '—'))
                col_b.metric('Reps', ex.get('reps', '—'))
                col_c.metric('Level', ex.get('level', '—').capitalize())

                muscles = ', '.join(ex.get('primaryMuscles', []))
                if muscles:
                    st.caption(f'Muscles: {muscles}')
                equipment = ex.get('equipment', 'body only')
                st.caption(f'Equipment: {equipment}')
                if ex.get('tip'):
                    st.info(ex['tip'])

                with st.expander('Full instructions'):
                    for step, instruction in enumerate(ex.get('instructions', []), 1):
                        st.write(f'{step}. {instruction}')


@st.cache_data(ttl=3600, show_spinner=False)
def _get_ai_exercise_plan(user_id: str, goals: dict, progress: dict, focus: str) -> list:
    """Generates an AI exercise plan enriched with goal & progress context."""
    import json as _json

    try:
        from data_fetcher import (
            get_all_exercises, get_user_profile,
            FREE_EXERCISE_IMG_BASE, FOCUS_TO_MUSCLES,
        )
        all_exercises = get_all_exercises()
        target_muscles = FOCUS_TO_MUSCLES.get(focus, [focus.lower()])
        candidates = [
            ex for ex in all_exercises
            if any(m in ex.get('primaryMuscles', []) for m in target_muscles)
            and ex.get('images')
        ]
    except Exception:
        return []

    if not candidates:
        return []

    # Build compact exercise list for Gemini
    exercise_list = [
        {
            'id': ex['id'],
            'name': ex['name'],
            'primaryMuscles': ex['primaryMuscles'],
            'equipment': ex.get('equipment', 'body only'),
            'level': ex.get('level', 'intermediate'),
        }
        for ex in candidates
    ]

    try:
        profile = get_user_profile(user_id)
        name = profile.get('full_name', 'Athlete')
    except Exception:
        name = 'Athlete'

    prompt = f"""You are a certified personal trainer creating a customised {focus} workout.

User context:
- Name: {name}
- Goal: {goals['primary_goal']}
- Experience: {goals['experience']}
- Notes: {goals.get('notes') or 'none'}
- Total workouts logged: {progress['total_workout_count']}

Choose 5-6 exercises from the list below that best fit this user's goal and experience level.
Prefer exercises that are appropriate for a {goals['experience'].lower()} and that support {goals['primary_goal'].lower()}.

Return ONLY a valid JSON array. Each item must have exactly these keys:
"id" (from the list), "sets" (integer), "reps" (string, e.g. "8-12"), "tip" (≤15-word form cue).
No markdown, no explanation — just the JSON array.

Exercise list:
{_json.dumps(exercise_list)}
"""

    try:
        vertexai.init(project=PROJECT_ID, location='us-central1')
        model = GenerativeModel('gemini-2.5-flash-lite')
        response = model.generate_content(prompt)
        raw = response.text.strip().removeprefix('```json').removeprefix('```').removesuffix('```').strip()
        selected = _json.loads(raw)
    except Exception:
        return []

    exercise_map = {ex['id']: ex for ex in candidates}
    plan = []
    for item in selected:
        ex = exercise_map.get(item['id'])
        if not ex:
            continue
        plan.append({
            'name': ex['name'],
            'primaryMuscles': ex.get('primaryMuscles', []),
            'secondaryMuscles': ex.get('secondaryMuscles', []),
            'equipment': ex.get('equipment', 'body only'),
            'level': ex.get('level', ''),
            'instructions': ex.get('instructions', []),
            'imageUrl': f"{FREE_EXERCISE_IMG_BASE}/{ex['images'][0]}",
            'sets': item['sets'],
            'reps': item['reps'],
            'tip': item.get('tip', ''),
        })

    return plan


# ── Supabase persistence (optional, non-blocking) ─────────────────────────────

def _persist_goals_to_supabase(goals: dict):
    """Saves goals to Supabase user_goals table. Silently skips if table doesn't exist."""
    try:
        from supabase_client import get_supabase_client
        from auth_page import get_current_user_id
        uid = get_current_user_id()
        if not uid:
            return
        client = get_supabase_client()
        client.table('user_goals').upsert({
            'user_id': uid,
            **{k: str(v) if not isinstance(v, (str, int, float, bool)) else v
               for k, v in goals.items()},
        }).execute()
    except Exception:
        pass  # Silently skip if Supabase table doesn't exist yet


def load_goals_from_supabase():
    """Loads saved goals from Supabase into session state. Called on page load."""
    if st.session_state.get('user_goals'):
        return  # already loaded
    try:
        from supabase_client import get_supabase_client
        from auth_page import get_current_user_id
        uid = get_current_user_id()
        if not uid:
            return
        client = get_supabase_client()
        res = client.table('user_goals').select('*').eq('user_id', uid).limit(1).execute()
        if res.data:
            row = res.data[0]
            st.session_state['user_goals'] = {
                'primary_goal': row.get('primary_goal', 'General Fitness'),
                'experience': row.get('experience', 'Beginner'),
                'focus_area': row.get('focus_area', 'Full Body'),
                'weekly_workouts': int(row.get('weekly_workouts', 3)),
                'daily_steps_goal': int(row.get('daily_steps_goal', 8000)),
                'notes': row.get('notes', ''),
                'updated_at': row.get('updated_at', ''),
            }
    except Exception:
        pass  # Silently skip
