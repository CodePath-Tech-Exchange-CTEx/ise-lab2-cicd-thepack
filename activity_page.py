#############################################################################
# activity_page.py
#
# This page displays a user's recent workouts and activity summary,
# with a button to create a new post with optional workout stats and image.
#############################################################################

import streamlit as st
from data_fetcher import get_user_workouts, get_user_posts, upload_image_to_gcs, create_post, delete_post
from modules import display_activity_summary, display_recent_workouts


def display_activity_page(user_id):
    """Displays the activity page with recent workouts, summary, and post creation."""
    st.title('My Activity')

    workouts = get_user_workouts(user_id)

    display_activity_summary(workouts)

    recent_workouts = sorted(
        workouts,
        key=lambda x: x['start_timestamp'],
        reverse=True
    )[:3]
    display_recent_workouts(recent_workouts)

    # ── New Post ──────────────────────────────────────────────────────────────
    if 'show_post_form' not in st.session_state:
        st.session_state.show_post_form = False
    if 'post_submitted' not in st.session_state:
        st.session_state.post_submitted = False
    if st.session_state.pop('post_success', False):
        st.success('Posted to the community!')

    if st.button('＋ New Post', use_container_width=True, type='primary'):
        st.session_state.show_post_form = not st.session_state.show_post_form

    if st.session_state.show_post_form:
        st.subheader('Create a Post')

        with st.form('new_post_form', clear_on_submit=True):
            content = st.text_area(
                'What\'s on your mind?',
                placeholder='Share how your workout went...',
                max_chars=500,
            )

            # Optionally attach a workout's stats
            workout_options = {
                f"Workout {i+1} — {w['start_timestamp']} ({w['steps']:,} steps, {w['distance']:.1f} mi)": w
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
                            f"\n\n🏃 Workout stats: "
                            f"{selected_workout['steps']:,} steps · "
                            f"{selected_workout['distance']:.1f} mi · "
                            f"{selected_workout['calories_burned']:,} cal"
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

    # ── My Posts ──────────────────────────────────────────────────────────────
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
