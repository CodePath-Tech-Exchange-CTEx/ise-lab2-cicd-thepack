#############################################################################
# workout_session_page.py
#
# Live workout session tracker.
#   - Pick a plan (from AI Coach / Workout Planner) or build ad-hoc
#   - Live JavaScript stopwatch timer embedded in an HTML component
#   - Check off sets as you complete them
#   - Session summary with calories estimate on completion
#   - Completed sessions saved to st.session_state['completed_sessions']
#############################################################################

import time
from datetime import datetime

import streamlit as st

from data_fetcher import get_workout_plan, get_user_workouts

# ── CSS + JS timer component ──────────────────────────────────────────────────

TIMER_HTML = """
<style>
  body { margin:0; font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif; background:transparent; }
  .timer-wrap {
    background: #111827;
    border-radius: 16px;
    padding: 28px 20px;
    text-align: center;
    color: white;
  }
  .timer-digits {
    font-size: 3.2rem;
    font-weight: 700;
    letter-spacing: 2px;
    font-variant-numeric: tabular-nums;
  }
  .timer-label { font-size: 0.72rem; opacity: 0.5; margin-bottom: 16px; text-transform:uppercase; letter-spacing:1.5px; }
  .btn-row { display:flex; gap:10px; justify-content:center; margin-top:18px; }
  button {
    padding: 9px 26px;
    border-radius: 8px;
    border: none;
    font-size: 0.88rem;
    font-weight: 600;
    cursor: pointer;
    transition: opacity .15s;
  }
  button:active { opacity: 0.7; }
  .btn-start  { background:#fff; color:#111827; }
  .btn-pause  { background:rgba(255,255,255,.15); color:#fff; border:1px solid rgba(255,255,255,.3); }
  .btn-reset  { background:transparent; color:rgba(255,255,255,.5); border:1px solid rgba(255,255,255,.2); }
</style>
<div class="timer-wrap">
  <div class="timer-label">Workout Timer</div>
  <div class="timer-digits" id="display">00:00:00</div>
  <div class="btn-row">
    <button class="btn-start" onclick="startStop()">Start</button>
    <button class="btn-pause" onclick="startStop()">Pause</button>
    <button class="btn-reset" onclick="resetTimer()">Reset</button>
  </div>
</div>
<script>
  let sec = 0, running = false, iv = null;
  const disp = document.getElementById('display');
  const [startBtn, pauseBtn] = document.querySelectorAll('button');
  function fmt(s) {
    const h = String(Math.floor(s/3600)).padStart(2,'0');
    const m = String(Math.floor((s%3600)/60)).padStart(2,'0');
    const ss = String(s%60).padStart(2,'0');
    return h+':'+m+':'+ss;
  }
  function startStop() {
    if (!running) {
      running = true;
      startBtn.style.display='none';
      pauseBtn.style.display='inline-block';
      iv = setInterval(()=>{ sec++; disp.textContent=fmt(sec); }, 1000);
    } else {
      running = false;
      pauseBtn.style.display='none';
      startBtn.style.display='inline-block';
      clearInterval(iv);
    }
  }
  function resetTimer() {
    clearInterval(iv); running=false; sec=0;
    disp.textContent='00:00:00';
    startBtn.style.display='inline-block';
    pauseBtn.style.display='none';
  }
  pauseBtn.style.display='none';
</script>
"""

# ── Public entry point ────────────────────────────────────────────────────────

def display_workout_session_page(user_id: str):
    st.title('Session')

    _inject_css()

    # State flags
    if 'session_active' not in st.session_state:
        st.session_state.session_active = False
    if 'session_exercises' not in st.session_state:
        st.session_state.session_exercises = []
    if 'set_log' not in st.session_state:
        st.session_state.set_log = {}  # {ex_name: sets_done}
    if 'session_start_time' not in st.session_state:
        st.session_state.session_start_time = None
    if 'completed_sessions' not in st.session_state:
        st.session_state.completed_sessions = []

    if not st.session_state.session_active:
        _show_session_setup(user_id)
    else:
        _show_active_session()


# ── Setup screen ──────────────────────────────────────────────────────────────

def _show_session_setup(user_id: str):
    st.markdown('### Choose your workout')

    source = st.radio(
        'Start from',
        ['AI Coach plan', 'Workout Planner', 'Quick custom'],
        horizontal=True,
    )

    exercises = []

    if source == 'AI Coach plan':
        goals = st.session_state.get('user_goals', {})
        if not goals:
            st.info('Set your goals on the **AI Coach** tab first to use your personalised plan.')
        else:
            st.caption(f'Goal: **{goals["primary_goal"]}** · Focus: **{goals["focus_area"]}**')
            cached_plan = st.session_state.get('_coach_plan_cache')
            if cached_plan is None:
                with st.spinner('Loading your AI plan…'):
                    try:
                        from ai_coach_page import _get_ai_exercise_plan, _build_progress_context
                        progress = _build_progress_context(user_id)
                        focus = goals.get('focus_area', 'Core')
                        if focus == 'Full Body':
                            focus = 'Core'
                        cached_plan = _get_ai_exercise_plan(user_id, goals, progress, focus)
                        st.session_state['_coach_plan_cache'] = cached_plan
                    except Exception:
                        cached_plan = []
            exercises = cached_plan

    elif source == 'Workout Planner':
        focus = st.session_state.get('workout_focus')
        if not focus:
            st.info('Select a focus area on the **Workout Plan** tab first.')
        else:
            with st.spinner(f'Loading {focus} plan…'):
                try:
                    exercises = get_workout_plan(user_id, focus)
                except Exception:
                    exercises = []

    else:  # Quick custom
        exercises = _build_custom_exercise_list()

    if exercises:
        st.markdown('---')
        st.markdown('**Preview:**')
        for i, ex in enumerate(exercises):
            st.markdown(f'  **{i+1}.** {ex["name"]} — {ex.get("sets", 3)} × {ex.get("reps", "10")}')

    col1, col2 = st.columns([3, 1])
    with col1:
        if st.button('Start Session', type='primary', use_container_width=True, disabled=not exercises):
            st.session_state.session_active = True
            st.session_state.session_exercises = exercises
            st.session_state.set_log = {ex['name']: 0 for ex in exercises}
            st.session_state.session_start_time = datetime.now()
            st.rerun()

    # Recent sessions
    _show_recent_sessions()


def _build_custom_exercise_list() -> list:
    """Lets the user add ad-hoc exercises."""
    st.markdown('**Add exercises:**')
    if 'custom_exercises' not in st.session_state:
        st.session_state.custom_exercises = []

    with st.form('add_exercise_form', clear_on_submit=True):
        c1, c2, c3 = st.columns([3, 1, 1])
        name = c1.text_input('Exercise name', placeholder='e.g. Push-ups')
        sets = c2.number_input('Sets', min_value=1, max_value=10, value=3)
        reps = c3.text_input('Reps', value='10-12')
        if st.form_submit_button('Add'):
            if name.strip():
                st.session_state.custom_exercises.append({
                    'name': name.strip(),
                    'sets': int(sets),
                    'reps': reps,
                    'tip': '',
                    'instructions': [],
                    'primaryMuscles': [],
                    'equipment': 'body only',
                    'level': '',
                })
                st.rerun()

    for i, ex in enumerate(st.session_state.custom_exercises):
        col1, col2 = st.columns([5, 1])
        col1.markdown(f'**{ex["name"]}** — {ex["sets"]} × {ex["reps"]}')
        if col2.button('Remove', key=f'rm_{i}'):
            st.session_state.custom_exercises.pop(i)
            st.rerun()

    return st.session_state.custom_exercises


# ── Active session ────────────────────────────────────────────────────────────

def _show_active_session():
    exercises = st.session_state.session_exercises

    # Timer
    import streamlit.components.v1 as components
    components.html(TIMER_HTML, height=200)

    st.markdown('---')

    # Exercise cards
    total_sets_possible = sum(ex.get('sets', 3) for ex in exercises)
    total_sets_done = sum(st.session_state.set_log.values())
    completion_pct = total_sets_done / total_sets_possible if total_sets_possible else 0

    col_prog, col_end = st.columns([4, 1])
    with col_prog:
        st.progress(completion_pct, text=f'{total_sets_done} / {total_sets_possible} sets complete')
    with col_end:
        if st.button('Finish Session', type='primary', use_container_width=True):
            _finish_session()
            st.rerun()

    st.markdown('---')

    for ex in exercises:
        name = ex['name']
        target_sets = ex.get('sets', 3)
        reps = ex.get('reps', '10')
        done = st.session_state.set_log.get(name, 0)

        # Colour card based on completion
        if done >= target_sets:
            border = '#27ae60'
            bg = '#f0faf4'
        elif done > 0:
            border = '#f39c12'
            bg = '#fffbf0'
        else:
            border = '#e0e0e0'
            bg = '#fff'

        st.markdown(
            f'<div style="border-left:4px solid {border};background:{bg};'
            f'border-radius:0 12px 12px 0;padding:14px 16px;margin-bottom:12px">'
            f'<span style="font-weight:700;font-size:1.05rem">{name}</span>'
            f'<span style="color:#888;font-size:0.85rem;margin-left:12px">'
            f'{done}/{target_sets} sets · {reps} reps</span>'
            f'{"  ✓" if done >= target_sets else ""}'
            f'</div>',
            unsafe_allow_html=True,
        )

        c1, c2, c3 = st.columns([1, 1, 4])
        with c1:
            if st.button('+ Set', key=f'add_{name}', disabled=done >= target_sets):
                st.session_state.set_log[name] = done + 1
                st.rerun()
        with c2:
            if st.button('Undo', key=f'undo_{name}', disabled=done == 0):
                st.session_state.set_log[name] = done - 1
                st.rerun()
        if ex.get('tip'):
            c3.caption(ex['tip'])

    st.markdown('---')
    if st.button('Cancel Session', use_container_width=True):
        _reset_session()
        st.rerun()


# ── Finish / reset ────────────────────────────────────────────────────────────

def _finish_session():
    exercises = st.session_state.session_exercises
    log = st.session_state.set_log
    start = st.session_state.session_start_time
    duration = (datetime.now() - start).seconds // 60 if start else 0

    # Estimate calories: ~5 cal/min moderate workout
    cal_estimate = duration * 5

    total_sets = sum(log.values())
    session_record = {
        'date': datetime.now().strftime('%Y-%m-%d'),
        'time': datetime.now().strftime('%H:%M'),
        'duration_min': duration,
        'exercises': [
            {'name': ex['name'], 'sets_done': log.get(ex['name'], 0),
             'sets_target': ex.get('sets', 3), 'reps': ex.get('reps', '10')}
            for ex in exercises
        ],
        'total_sets': total_sets,
        'cal_estimate': cal_estimate,
    }

    if 'completed_sessions' not in st.session_state:
        st.session_state.completed_sessions = []
    st.session_state.completed_sessions.insert(0, session_record)

    # Save to Supabase (non-blocking)
    _save_session_to_supabase(session_record)

    st.success(f'Session complete — {duration} min · ~{cal_estimate} cal · {total_sets} sets')
    _reset_session()


def _reset_session():
    st.session_state.session_active = False
    st.session_state.session_exercises = []
    st.session_state.set_log = {}
    st.session_state.session_start_time = None
    if 'custom_exercises' in st.session_state:
        del st.session_state['custom_exercises']


# ── Recent sessions list ──────────────────────────────────────────────────────

def _show_recent_sessions():
    sessions = st.session_state.get('completed_sessions', [])
    if not sessions:
        return

    st.markdown('---')
    st.subheader('Completed Sessions')
    for s in sessions[:5]:
        with st.expander(f"{s['date']} at {s['time']} — {s['duration_min']} min"):
            c1, c2, c3 = st.columns(3)
            c1.metric('Duration', f'{s["duration_min"]} min')
            c2.metric('Sets Done', s['total_sets'])
            c3.metric('~Calories', s['cal_estimate'])

            for ex in s['exercises']:
                done = ex['sets_done']
                target = ex['sets_target']
                status = '✓' if done >= target else '·'
                st.markdown(f'{status} **{ex["name"]}** — {done}/{target} sets × {ex["reps"]}')


# ── Supabase persistence ──────────────────────────────────────────────────────

def _save_session_to_supabase(session: dict):
    """Persist completed session to Supabase workout_sessions table (if it exists)."""
    try:
        import json
        from supabase_client import get_supabase_client
        from auth_page import get_current_user_id
        uid = get_current_user_id()
        if not uid:
            return
        client = get_supabase_client()
        client.table('workout_sessions').insert({
            'user_id': uid,
            'date': session['date'],
            'duration_min': session['duration_min'],
            'total_sets': session['total_sets'],
            'cal_estimate': session['cal_estimate'],
            'exercises': json.dumps(session['exercises']),
        }).execute()
    except Exception:
        pass


# ── CSS ───────────────────────────────────────────────────────────────────────

def _inject_css():
    st.markdown("""
        <style>
        [data-testid="stProgress"] > div > div { background-color: #111827 !important; }
        </style>
    """, unsafe_allow_html=True)
