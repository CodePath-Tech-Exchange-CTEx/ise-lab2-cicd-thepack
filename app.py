#############################################################################
# app.py
#
# This file contains the entrypoint for the app.
#
#############################################################################

import streamlit as st
from modules import display_my_custom_component, display_post, display_genai_advice, display_activity_summary, display_recent_workouts
from data_fetcher import get_user_posts, get_genai_advice, get_user_profile, get_user_sensor_data, get_user_workouts
from community_page import display_community_page
from activity_page import display_activity_page




def display_app_page():
    """Displays the home page of the app."""
    st.title('Welcome to SDS!')

    # Let the user type in a user ID to look up
    userId = st.text_input('Enter User ID (e.g. user1, user2, user3)')

    if not userId:
        st.info('Enter a user ID to get started.')
        return
    
    # Check if the user exists in the database
    try:
        profile = get_user_profile(userId)
    except ValueError:
        st.error(f'User "{userId}" not found in the database.')
        return

    st.success(f'Welcome, {profile["full_name"]}!')

       # Create tabs for the three pages
    home_tab, community_tab, activity_tab = st.tabs(['Home', 'Community', 'Activity'])

    with home_tab:
        value = st.text_input('Enter your name')
        display_my_custom_component(value)

        posts = get_user_posts(userId)
        for post in posts:
            post_profile = get_user_profile(post['user_id'])
            display_post(
                username=post_profile['username'],
                user_image=post_profile['profile_image'],
                timestamp=post['timestamp'],
                content=post['content'],
                post_image=post['image'],
            )

        workouts = get_user_workouts(userId)
        display_activity_summary(workouts)
        display_recent_workouts(workouts)

        advice = get_genai_advice(userId)
        display_genai_advice(
            timestamp=advice['timestamp'],
            content=advice['content'],
            image=advice['image'],
        )

    with community_tab:
        display_community_page(userId)

    with activity_tab:
        display_activity_page(userId)

# This is the starting point for your app. You do not need to change these lines
if __name__ == '__main__':
    display_app_page()
