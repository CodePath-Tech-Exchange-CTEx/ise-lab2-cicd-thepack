#############################################################################
# app.py
#
# This file contains the entrypoint for the app.
#
#############################################################################

import streamlit as st
from modules import display_my_custom_component, display_post, display_genai_advice, display_activity_summary, display_recent_workouts
from data_fetcher import get_user_posts, get_genai_advice, get_user_profile, get_user_sensor_data, get_user_workouts

userId = 'user2'


def display_app_page():
    """Displays the home page of the app."""
    st.title('Welcome to SDS!')

    # An example of displaying a custom component called "my_custom_component"
    value = st.text_input('Enter your name')
    display_my_custom_component(value)

    # Display posts
    posts = get_user_posts(userId)
    for post in posts:
        profile = get_user_profile(post['user_id'])
        display_post(
            username=profile['username'],
            user_image=profile['profile_image'],
            timestamp=post['timestamp'],
            content=post['content'],
            post_image=post['image'],
        )
    # Display activity summary and recent workouts
    workouts = get_user_workouts(userId)
    display_activity_summary(workouts)
    display_recent_workouts(workouts)

    # Display genai advice
    advice = get_genai_advice(userId)
    display_genai_advice(
        timestamp=advice['timestamp'],
        content=advice['content'],
        image=advice['image'],
    )


# This is the starting point for your app. You do not need to change these lines
if __name__ == '__main__':
    display_app_page()
