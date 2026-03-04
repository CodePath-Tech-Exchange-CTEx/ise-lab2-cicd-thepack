#############################################################################
# modules.py
#
# This file contains modules that may be used throughout the app.
#
# You will write these in Unit 2. Do not change the names or inputs of any
# function other than the example.
#############################################################################

import streamlit as st
from internals import create_component


# This one has been written for you as an example. You may change it as wanted.
def display_my_custom_component(value):
    """Displays a 'my custom component' which showcases an example of how custom
    components work.

    value: the name you'd like to be called by within the app
    """
    # Define any templated data from your HTML file. The contents of
    # 'value' will be inserted to the templated HTML file wherever '{{NAME}}'
    # occurs. You can add as many variables as you want.
    data = {
        'NAME': value,
    }
    # Register and display the component by providing the data and name
    # of the HTML file. HTML must be placed inside the "custom_components" folder.
    html_file_name = "my_custom_component"
    create_component(data, html_file_name)


def display_post(username, user_image, timestamp, content, post_image):
    """Displays a single post with the author's profile image, username,
    timestamp, text content, and an optional post image.

    username: the post author's username
    user_image: URL of the user's profile picture
    timestamp: when the post was made
    content: the text content of the post
    post_image: URL of an image attached to the post
    """
    col1, col2 = st.columns([1, 8])
    with col1:
        if user_image:
            st.image(user_image, width=50)
    with col2:
        st.markdown(f"**{username}**")
        st.caption(str(timestamp))
    st.write(content)
    if post_image and post_image.startswith('http'):
        st.image(post_image, use_container_width=True)
    st.divider()
    


def display_activity_summary(workouts_list):
    """Displays a summary of total activity across all workouts, including
    total number of workouts, distance, steps, and calories burned.

    workouts_list: a list of workout dicts with start/end timestamps,
                   distance, steps, calories_burned, and start/end coordinates
    """
    st.subheader("📊 Activity Summary")
    total_distance = sum(w.get('distance', 0) for w in workouts_list)
    total_steps = sum(w.get('steps', 0) for w in workouts_list)
    total_calories = sum(w.get('calories_burned', 0) for w in workouts_list)

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("🏃 Workouts", len(workouts_list))
    col2.metric("📏 Distance (mi)", f"{total_distance:.1f}")
    col3.metric("👟 Steps", f"{total_steps:,}")
    col4.metric("🔥 Calories", f"{total_calories:,}")
    st.divider()

def display_recent_workouts(workouts_list):
    """Displays each workout in the list with its start/end timestamps,
    distance, steps, calories burned, and start/end coordinates.

    workouts_list: a list of workout dicts with start/end timestamps,
                   distance, steps, calories_burned, and start/end coordinates
    """
    st.subheader("🏋️ Recent Workouts")
    for i, workout in enumerate(workouts_list):
        with st.expander(f"Workout {i + 1} — {workout.get('start_timestamp', 'N/A')}"):
            col1, col2 = st.columns(2)
            with col1:
                st.write(f"**Start:** {workout.get('start_timestamp', 'N/A')}")
                st.write(f"**End:** {workout.get('end_timestamp', 'N/A')}")
                st.write(f"**Distance:** {workout.get('distance', 0):.1f} mi")
            with col2:
                st.write(f"**Steps:** {workout.get('steps', 0):,}")
                st.write(f"**Calories:** {workout.get('calories_burned', 0):,}")
                st.write(f"**Start coords:** {workout.get('start_lat_lng', 'N/A')}")
                st.write(f"**End coords:** {workout.get('end_lat_lng', 'N/A')}")
    st.divider()

def display_genai_advice(timestamp, content, image):
    """Displays AI-generated fitness advice with a timestamp and an optional
    motivational image.

    timestamp: when the advice was generated
    content: the advice text from the AI
    image: URL of a motivational image (can be None)
    """
    st.subheader("🤖 AI Fitness Advice")
    st.caption(str(timestamp))
    st.info(content)
    if image:
        st.image(image, use_container_width=True)
    st.divider()
