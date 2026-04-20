#############################################################################
# activity_page.py
#
# Enhanced activity page:
#   - Activity summary with today's step goal progress
#   - Workout cards with sensor data charts (heart rate, speed, etc.)
#   - GPS start/end map visualisation
#   - Post creation with workout attachment
#############################################################################

import pandas as pd
import streamlit as st
from collections import defaultdict
from datetime import datetime, date

from data_fetcher import (
    get_user_workouts, get_user_posts, get_user_sensor_data,
    upload_image_to_gcs, create_post, delete_post,
)


def display_activity_page(user_id):
    """Displays the enhanced activity page."""
    st.title('Activity')

    workouts = get_user_workouts(user_id)

    _display_enhanced_summary(workouts)
    _display_workout_history(workouts, user_id)

    st.divider()
    _render_post_creator(user_id, workouts)

    st.subheader('My Posts')
    my_posts = get_user_posts(user_id)
    if not my_posts:
        st.caption('You have no posts yet.')
    else:
        for i, post in enumerate(my_posts):
            with st.container(border=True):
                st.caption(post['timestamp'])
                st.write(post['content'])
                if post['image'] and post['image'].startswith('http'):
                    st.image(post['image'], use_container_width=True)
                if st.button('Delete', key=f"del_{i}_{post['post_id']}", type='secondary'):
                    try:
                        delete_post(post['post_id'], user_id)
                        st.rerun()
                    except Exception as e:
                        st.error(f'Failed to delete: {e}')


# ── Enhanced summary ──────────────────────────────────────────────────────────

def _display_enhanced_summary(workouts: list):
    st.subheader('Summary')

    total_distance = sum(w.get('distance', 0) for w in workouts)
    total_steps = sum(w.get('steps', 0) for w in workouts)
    total_calories = sum(w.get('calories_burned', 0) for w in workouts)

    ah = st.session_state.get('apple_health', {})
    if ah.get('total_steps', 0) > total_steps:
        total_steps = ah['total_steps']
    if ah.get('total_calories', 0) > total_calories:
        total_calories = ah['total_calories']

    col1, col2, col3, col4 = st.columns(4)
    col1.metric('Workouts', len(workouts))
    col2.metric('Distance (mi)', f'{total_distance:.1f}')
    col3.metric('Steps', f'{total_steps:,.0f}')
    col4.metric('Calories', f'{total_calories:,.0f}')

    goals = st.session_state.get('user_goals', {})
    if goals and goals.get('daily_steps_goal'):
        today = date.today().isoformat()
        today_steps = ah.get('daily_steps', {}).get(today, 0)
        if not today_steps:
            today_date = date.today()
            today_steps = sum(
                w.get('steps', 0) for w in workouts
                if _to_date(w['start_timestamp']) == today_date
            )
        daily_goal = goals['daily_steps_goal']
        pct = min(today_steps / daily_goal, 1.0) if daily_goal else 0
        st.markdown(f"**Today's step goal:** {today_steps:,.0f} / {daily_goal:,}")
        st.progress(pct)

    st.divider()


# ── Workout history ───────────────────────────────────────────────────────────

def _display_workout_history(workouts: list, user_id: str):
    st.subheader('Workout History')

    if not workouts:
        st.info('No workouts found. Complete a session to see your history here.')
        return

    recent = sorted(workouts, key=lambda x: x['start_timestamp'], reverse=True)

    for i, workout in enumerate(recent[:10]):
        _render_workout_card(workout, i, user_id)


def _render_workout_card(workout: dict, index: int, user_id: str):
    workout_id = workout.get('workout_id', '')
    start_ts = str(workout.get('start_timestamp', 'N/A'))
    steps = workout.get('steps', 0)
    distance = workout.get('distance', 0)
    calories = workout.get('calories_burned', 0)

    try:
        start_dt = datetime.fromisoformat(start_ts[:19])
        end_dt = datetime.fromisoformat(str(workout['end_timestamp'])[:19])
        duration_min = int((end_dt - start_dt).seconds / 60)
        duration_str = f'{duration_min} min'
    except Exception:
        duration_str = '—'

    label = f'Workout {index + 1} — {start_ts[:10]}  ·  {steps:,} steps  ·  {distance:.1f} mi  ·  {calories:,.0f} cal'

    with st.expander(label):
        col1, col2, col3, col4 = st.columns(4)
        col1.metric('Duration', duration_str)
        col2.metric('Steps', f'{steps:,}')
        col3.metric('Distance', f'{distance:.2f} mi')
        col4.metric('Calories', f'{calories:,.0f}')

        # Map
        start_loc = workout.get('start_lat_lng')
        end_loc = workout.get('end_lat_lng')
        if (start_loc and end_loc
                and len(start_loc) == 2 and len(end_loc) == 2
                and all(v is not None for v in list(start_loc) + list(end_loc))):
            try:
                map_df = pd.DataFrame([
                    {'lat': float(start_loc[0]), 'lon': float(start_loc[1])},
                    {'lat': float(end_loc[0]), 'lon': float(end_loc[1])},
                ])
                st.caption('Start → Finish')
                st.map(map_df, zoom=12)
            except Exception:
                st.caption(f'Start: {start_loc}  →  End: {end_loc}')

        if workout_id:
            _render_sensor_charts(user_id, workout_id)


def _render_sensor_charts(user_id: str, workout_id: str):
    try:
        sensor_data = get_user_sensor_data(user_id, workout_id)
    except Exception:
        return

    if not sensor_data:
        return

    by_type = defaultdict(list)
    for reading in sensor_data:
        by_type[reading['sensor_type']].append(reading)

    if not by_type:
        return

    st.markdown('**Sensor Data**')

    COLORS = {
        'Heart Rate': '#e74c3c',
        'Steps': '#111827',
        'Speed': '#2980b9',
        'Distance': '#27ae60',
        'Calories': '#f39c12',
    }

    for sensor_type, readings in by_type.items():
        if len(readings) < 2:
            continue
        try:
            df = pd.DataFrame([
                {'Time': r['timestamp'][:19], sensor_type: float(r['data'])}
                for r in readings
            ])
            df['Time'] = pd.to_datetime(df['Time'])
            df = df.sort_values('Time').set_index('Time')
            color = COLORS.get(sensor_type, '#111827')
            st.caption(f'{sensor_type} ({readings[0].get("units", "")})')
            st.line_chart(df, color=color, height=160)
        except Exception:
            pass


# ── Post creator ──────────────────────────────────────────────────────────────

def _render_post_creator(user_id: str, workouts: list):
    if 'show_post_form' not in st.session_state:
        st.session_state.show_post_form = False
    if 'post_submitted' not in st.session_state:
        st.session_state.post_submitted = False
    if st.session_state.pop('post_success', False):
        st.success('Posted to the community!')

    if st.button('New Post', use_container_width=True, type='primary'):
        st.session_state.show_post_form = not st.session_state.show_post_form

    if st.session_state.show_post_form:
        st.subheader('Create a Post')

        with st.form('new_post_form', clear_on_submit=True):
            content = st.text_area(
                "What's on your mind?",
                placeholder='Share how your workout went...',
                max_chars=500,
            )

            workout_options = {
                f"Workout {i+1} — {w['start_timestamp'][:10]} ({w['steps']:,} steps, {w['distance']:.1f} mi)": w
                for i, w in enumerate(
                    sorted(workouts, key=lambda x: x['start_timestamp'], reverse=True)
                )
            }
            attach_workout = st.checkbox('Attach a workout')
            selected_workout = None
            if attach_workout and workout_options:
                label = st.selectbox('Select workout', list(workout_options.keys()))
                selected_workout = workout_options[label]
            elif attach_workout:
                st.caption('No workouts found.')

            uploaded_file = st.file_uploader(
                'Add a photo (optional)',
                type=['jpg', 'jpeg', 'png', 'webp'],
            )

            submitted = st.form_submit_button('Post', type='primary')

        if submitted and not st.session_state.post_submitted:
            st.session_state.post_submitted = True
            if not content.strip() and selected_workout is None:
                st.warning('Write something or attach a workout before posting.')
                st.session_state.post_submitted = False
            else:
                try:
                    post_content = content.strip()
                    if selected_workout:
                        post_content += (
                            f'\n\n🏃 Workout stats: '
                            f'{selected_workout["steps"]:,} steps · '
                            f'{selected_workout["distance"]:.1f} mi · '
                            f'{selected_workout["calories_burned"]:,} cal'
                        )
                    image_url = None
                    if uploaded_file is not None:
                        with st.spinner('Uploading image...'):
                            image_url = upload_image_to_gcs(
                                uploaded_file.read(),
                                uploaded_file.name,
                                uploaded_file.type,
                            )
                    with st.spinner('Posting...'):
                        create_post(user_id, post_content, image_url)
                    st.session_state.show_post_form = False
                    st.session_state.post_success = True
                    st.rerun()
                except Exception as e:
                    st.session_state.post_submitted = False
                    st.error(f'Failed to post: {e}')
        elif not submitted:
            st.session_state.post_submitted = False


# ── Helpers ───────────────────────────────────────────────────────────────────

def _to_date(s):
    if not s:
        return None
    try:
        return datetime.fromisoformat(str(s)[:19]).date()
    except Exception:
        return None
