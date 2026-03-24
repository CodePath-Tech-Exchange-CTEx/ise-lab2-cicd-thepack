#############################################################################
# activity_page.py
#
# This page displays a user's recent workouts and activity summary,
# with a share button to post a chosen statistic to the community.
#############################################################################

import streamlit as st
from google.cloud import bigquery
import uuid
from datetime import datetime
from data_fetcher import get_user_workouts
from modules import display_activity_summary, display_recent_workouts


def share_statistic(user_id, stat_name, stat_value):
    """Inserts a post into the Posts table sharing the user's chosen statistic."""
    client = bigquery.Client()
    post_id = str(uuid.uuid4())
    timestamp = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')

    # Build the post content based on which stat was chosen
    messages = {
        'Steps': f'Look at this, I walked {int(stat_value):,} steps today!',
        'Distance': f'I covered {stat_value:.1f} miles today!',
        'Calories': f'I burned {int(stat_value):,} calories today!',
        'Workouts': f'I completed {int(stat_value)} workout(s) this week!',
    }
    content = messages[stat_name]

    query = """
        INSERT INTO `tesfaye-kefene-fisk.ISE.Posts` (PostId, AuthorId, Timestamp, ImageUrl, Content)
        VALUES (@post_id, @user_id, @timestamp, NULL, @content)
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter('post_id', 'STRING', post_id),
            bigquery.ScalarQueryParameter('user_id', 'STRING', user_id),
            bigquery.ScalarQueryParameter('timestamp', 'DATETIME', timestamp),
            bigquery.ScalarQueryParameter('content', 'STRING', content),
        ]
    )
    client.query(query, job_config=job_config).result()


def display_activity_page(user_id):
    """Displays the activity page with recent workouts, summary, and share button."""
    st.title('My Activity')

    # Get workouts from the database
    workouts = get_user_workouts(user_id)

    # Show activity summary across all workouts
    display_activity_summary(workouts)

    # Show only the 3 most recent workouts
    recent_workouts = sorted(
        workouts,
        key=lambda x: x['start_timestamp'],
        reverse=True
    )[:3]
    display_recent_workouts(recent_workouts)

    # Calculate all statistics
    total_steps = sum(w.get('steps', 0) for w in workouts)
    total_distance = sum(w.get('distance', 0) for w in workouts)
    total_calories = sum(w.get('calories_burned', 0) for w in workouts)
    total_workouts = len(workouts)

    # Let the user choose which statistic to share
    st.subheader('Share Your Activity')
    stat_options = {
        'Steps': total_steps,
        'Distance': total_distance,
        'Calories': total_calories,
        'Workouts': total_workouts,
    }
    chosen_stat = st.selectbox('Choose a statistic to share', list(stat_options.keys()))
    chosen_value = stat_options[chosen_stat]

    # Preview what the post will say
    previews = {
        'Steps': f'Look at this, I walked {int(chosen_value):,} steps today!',
        'Distance': f'I covered {chosen_value:.1f} miles today!',
        'Calories': f'I burned {int(chosen_value):,} calories today!',
        'Workouts': f'I completed {int(chosen_value)} workout(s) this week!',
    }
    st.info(f'Preview: "{previews[chosen_stat]}"')

    if st.button('Share with Community'):
        try:
            share_statistic(user_id, chosen_stat, chosen_value)
            st.success('Posted to the community!')
            st.info('Go to the Community tab to see your post.')
        except Exception as e:
            st.error(f'Failed to share: {e}')