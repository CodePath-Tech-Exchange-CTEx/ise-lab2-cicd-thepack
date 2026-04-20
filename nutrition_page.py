#############################################################################
# nutrition_page.py
#
# AI-powered nutrition planner using Gemini.
#   - Daily macro targets based on user goals + weight (if logged)
#   - Gemini-generated full-day meal plan (breakfast, lunch, dinner, snacks)
#   - Meal plan regeneration and history
#   - Simple water intake tracker
#   - Calorie budget tracker vs workout burn
#############################################################################

import json
from datetime import date, datetime

import streamlit as st
import vertexai
from vertexai.generative_models import GenerativeModel

from data_fetcher import PROJECT_ID, get_user_workouts

# ── Macro calculator ──────────────────────────────────────────────────────────

GOAL_MACRO_RATIOS = {
    'Lose Weight':         {'protein_pct': 0.35, 'carb_pct': 0.35, 'fat_pct': 0.30, 'deficit': -300},
    'Build Muscle':        {'protein_pct': 0.35, 'carb_pct': 0.45, 'fat_pct': 0.20, 'deficit': 250},
    'Improve Endurance':   {'protein_pct': 0.20, 'carb_pct': 0.55, 'fat_pct': 0.25, 'deficit': 100},
    'Increase Flexibility':{'protein_pct': 0.25, 'carb_pct': 0.45, 'fat_pct': 0.30, 'deficit': 0},
    'General Fitness':     {'protein_pct': 0.30, 'carb_pct': 0.40, 'fat_pct': 0.30, 'deficit': 0},
    'Train for a Race':    {'protein_pct': 0.20, 'carb_pct': 0.60, 'fat_pct': 0.20, 'deficit': 150},
    'Reduce Stress':       {'protein_pct': 0.25, 'carb_pct': 0.45, 'fat_pct': 0.30, 'deficit': 0},
}

ACTIVITY_MULTIPLIER = {
    'Beginner':     1.375,
    'Intermediate': 1.55,
    'Advanced':     1.725,
}


def _estimate_tdee(weight_kg: float, age: int, is_male: bool, activity_level: str) -> int:
    """Harris-Benedict TDEE estimate."""
    if is_male:
        bmr = 88.362 + (13.397 * weight_kg) + (4.799 * 170) - (5.677 * age)
    else:
        bmr = 447.593 + (9.247 * weight_kg) + (3.098 * 160) - (4.330 * age)
    return int(bmr * ACTIVITY_MULTIPLIER.get(activity_level, 1.55))


# ── Main ──────────────────────────────────────────────────────────────────────

def display_nutrition_page(user_id: str):
    st.title('Nutrition')

    _inject_css()

    goals = st.session_state.get('user_goals', {})

    # ── Personal info for TDEE ────────────────────────────────────────────────
    with st.expander('Personal details (for accurate calorie targets)', expanded=not st.session_state.get('nutrition_profile')):
        with st.form('nutrition_profile_form'):
            c1, c2, c3, c4 = st.columns(4)
            weight_kg = c1.number_input('Weight (kg)', 40.0, 200.0, float(st.session_state.get('nutrition_profile', {}).get('weight_kg') or 70))
            age = c2.number_input('Age', 10, 100, int(st.session_state.get('nutrition_profile', {}).get('age') or 25))
            sex = c3.selectbox('Sex', ['Male', 'Female'], index=0 if st.session_state.get('nutrition_profile', {}).get('sex', 'Male') == 'Male' else 1)
            dietary_pref = c4.selectbox('Diet preference', ['No restriction', 'Vegetarian', 'Vegan', 'Gluten-free', 'Dairy-free', 'Keto', 'Paleo'])
            if st.form_submit_button('Save', type='primary'):
                st.session_state['nutrition_profile'] = {
                    'weight_kg': weight_kg, 'age': age, 'sex': sex,
                    'dietary_pref': dietary_pref,
                }
                st.rerun()

    profile = st.session_state.get('nutrition_profile', {'weight_kg': 70, 'age': 25, 'sex': 'Male', 'dietary_pref': 'No restriction'})
    activity = goals.get('experience', 'Intermediate')
    goal_name = goals.get('primary_goal', 'General Fitness')

    tdee = _estimate_tdee(profile['weight_kg'], profile['age'], profile['sex'] == 'Male', activity)
    ratios = GOAL_MACRO_RATIOS.get(goal_name, GOAL_MACRO_RATIOS['General Fitness'])
    target_cal = tdee + ratios['deficit']
    protein_g = int(target_cal * ratios['protein_pct'] / 4)
    carb_g = int(target_cal * ratios['carb_pct'] / 4)
    fat_g = int(target_cal * ratios['fat_pct'] / 9)

    # ── Calorie overview ──────────────────────────────────────────────────────
    st.subheader('Daily Targets')
    cal_burned = _estimate_today_burn(user_id)

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric('Target Calories', f'{target_cal:,}')
    c2.metric('Protein', f'{protein_g}g')
    c3.metric('Carbs', f'{carb_g}g')
    c4.metric('Fats', f'{fat_g}g')
    c5.metric('Workout Burn', f'~{cal_burned:,} cal')

    if cal_burned > 0:
        net = target_cal + cal_burned
        st.info(f'After your workout, your net calorie target is **{net:,} cal** (base + burn).')

    st.divider()

    # ── Meal plan ─────────────────────────────────────────────────────────────
    st.subheader("Today's Meal Plan")

    plan_key = f'meal_plan_{date.today().isoformat()}'
    cached_plan = st.session_state.get(plan_key)

    col1, col2 = st.columns([4, 1])
    with col2:
        if st.button('Regenerate', use_container_width=True):
            if plan_key in st.session_state:
                del st.session_state[plan_key]
            cached_plan = None
            st.rerun()

    if cached_plan is None:
        with st.spinner('Generating your personalised meal plan…'):
            cached_plan = _generate_meal_plan(
                goal_name, profile, target_cal, protein_g, carb_g, fat_g
            )
            st.session_state[plan_key] = cached_plan

    _render_meal_plan(cached_plan)

    st.divider()

    # ── Water tracker ─────────────────────────────────────────────────────────
    st.subheader('Water Intake')
    _render_water_tracker(profile['weight_kg'])

    st.divider()

    # ── Nutrition tips ────────────────────────────────────────────────────────
    st.subheader('Nutrition Tips')
    _render_nutrition_tips(goal_name)


# ── Meal plan generation ──────────────────────────────────────────────────────

def _generate_meal_plan(goal: str, profile: dict, target_cal: int, protein_g: int, carb_g: int, fat_g: int) -> dict:
    diet_pref = profile.get('dietary_pref', 'No restriction')
    diet_note = f'Diet preference: {diet_pref}.' if diet_pref != 'No restriction' else ''

    prompt = f"""You are a registered dietitian. Create a complete, realistic one-day meal plan.

Goal: {goal}
Daily targets: {target_cal} calories | {protein_g}g protein | {carb_g}g carbs | {fat_g}g fat
{diet_note}

Return ONLY valid JSON with this exact structure (no markdown):
{{
  "breakfast": {{"name": "...", "description": "...", "calories": 0, "protein_g": 0, "carb_g": 0, "fat_g": 0, "prep_time": "5 min"}},
  "morning_snack": {{"name": "...", "description": "...", "calories": 0, "protein_g": 0, "carb_g": 0, "fat_g": 0, "prep_time": "2 min"}},
  "lunch": {{"name": "...", "description": "...", "calories": 0, "protein_g": 0, "carb_g": 0, "fat_g": 0, "prep_time": "15 min"}},
  "afternoon_snack": {{"name": "...", "description": "...", "calories": 0, "protein_g": 0, "carb_g": 0, "fat_g": 0, "prep_time": "2 min"}},
  "dinner": {{"name": "...", "description": "...", "calories": 0, "protein_g": 0, "carb_g": 0, "fat_g": 0, "prep_time": "25 min"}},
  "tip": "One short practical nutrition tip for this goal (max 20 words)"
}}
"""

    try:
        vertexai.init(project=PROJECT_ID, location='us-central1')
        model = GenerativeModel('gemini-2.5-flash-lite')
        response = model.generate_content(prompt)
        raw = response.text.strip().removeprefix('```json').removeprefix('```').removesuffix('```').strip()
        return json.loads(raw)
    except Exception as e:
        return {'error': str(e)}


def _render_meal_plan(plan: dict):
    if 'error' in plan:
        st.error(f'Could not generate plan: {plan["error"]}')
        return

    MEAL_LABELS = {
        'breakfast': ('Breakfast',),
        'morning_snack': ('Morning Snack',),
        'lunch': ('Lunch',),
        'afternoon_snack': ('Afternoon Snack',),
        'dinner': ('Dinner',),
    }

    total_cal = 0
    total_prot = 0

    for key, (label,) in MEAL_LABELS.items():
        meal = plan.get(key)
        if not meal:
            continue
        total_cal += meal.get('calories', 0)
        total_prot += meal.get('protein_g', 0)

        with st.container(border=True):
            col1, col2 = st.columns([3, 1])
            with col1:
                st.markdown(f'**{label}: {meal["name"]}**')
                st.caption(meal.get('description', ''))
            with col2:
                st.markdown(
                    f'<div style="text-align:right">'
                    f'<span style="color:#111827;font-weight:700">{meal.get("calories",0)} cal</span><br>'
                    f'<span style="font-size:0.8rem;color:#6B7280">'
                    f'P:{meal.get("protein_g",0)}g C:{meal.get("carb_g",0)}g F:{meal.get("fat_g",0)}g</span><br>'
                    f'<span style="font-size:0.75rem;color:#9CA3AF">{meal.get("prep_time","")}</span>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

    if plan.get('tip'):
        st.success(f'💡 {plan["tip"]}')

    st.markdown(f'**Daily total: ~{total_cal:,} cal · ~{total_prot}g protein**')


# ── Water tracker ─────────────────────────────────────────────────────────────

def _render_water_tracker(weight_kg: float):
    """Simple 8-glass water tracker with session persistence."""
    recommended = max(8, int(weight_kg * 0.033))  # 33ml per kg, min 8 glasses

    if 'water_glasses' not in st.session_state:
        st.session_state.water_glasses = 0

    glasses = st.session_state.water_glasses
    pct = min(glasses / recommended, 1.0)

    st.progress(pct, text=f'{glasses} / {recommended} glasses today')

    c1, c2 = st.columns([1, 5])
    with c1:
        if st.button('+ Glass', type='primary'):
            st.session_state.water_glasses += 1
            st.rerun()
    with c2:
        if glasses > 0 and st.button('Undo last'):
            st.session_state.water_glasses -= 1
            st.rerun()

    if glasses >= recommended:
        st.success('Hydration goal reached!')
    elif glasses >= recommended * 0.75:
        st.info(f'Almost there — {recommended - glasses} more glass{"es" if recommended-glasses>1 else ""} to go!')


# ── Nutrition tips ────────────────────────────────────────────────────────────

TIPS = {
    'Lose Weight': [
        'Fill half your plate with vegetables at every meal.',
        'Eat protein first — it keeps you fuller longer.',
        'Swap sugary drinks for water or sparkling water.',
        'Plan meals ahead to avoid impulsive choices.',
    ],
    'Build Muscle': [
        'Aim for 0.7–1g of protein per lb of bodyweight.',
        'Eat a protein + carb meal within 30 min post-workout.',
        'Don\'t skip carbs — they fuel your lifts.',
        'Sleep 7–9 hours: most muscle repair happens at night.',
    ],
    'Improve Endurance': [
        'Carb-load the night before long sessions.',
        'Eat easily digestible carbs 1–2 hr before training.',
        'Replenish electrolytes during workouts > 60 min.',
        'Post-workout: 3:1 carb-to-protein ratio aids recovery.',
    ],
    'General Fitness': [
        'Choose whole foods over processed most of the time.',
        'Meal prep on Sunday to stay consistent all week.',
        'Include a variety of coloured vegetables every day.',
        'Stay hydrated — even mild dehydration hurts performance.',
    ],
}


def _render_nutrition_tips(goal: str):
    tips = TIPS.get(goal, TIPS['General Fitness'])
    for tip in tips:
        st.markdown(f'— {tip}')


# ── Helpers ───────────────────────────────────────────────────────────────────

def _estimate_today_burn(user_id: str) -> int:
    """Estimate today's calorie burn from workouts."""
    # Apple Health first
    ah = st.session_state.get('apple_health', {})
    today = date.today().isoformat()
    if ah.get('daily_calories', {}).get(today, 0):
        return int(ah['daily_calories'][today])

    # Session completed workouts
    sessions = st.session_state.get('completed_sessions', [])
    for s in sessions:
        if s.get('date') == today:
            return s.get('cal_estimate', 0)

    # BigQuery
    try:
        workouts = get_user_workouts(user_id)
        from datetime import datetime
        from progress_page import to_date
        today_date = date.today()
        return int(sum(
            w.get('calories_burned', 0) for w in workouts
            if to_date(w['start_timestamp']) == today_date
        ))
    except Exception:
        return 0


def _inject_css():
    st.markdown("""
        <style>
        [data-testid="stProgress"] > div > div { background-color: #27ae60 !important; }
        </style>
    """, unsafe_allow_html=True)
