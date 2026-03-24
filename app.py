#############################################################################
# app.py
#############################################################################

import streamlit as st
from modules import display_post, display_genai_advice, display_activity_summary, display_recent_workouts
from data_fetcher import get_user_posts, get_genai_advice, get_user_profile, get_user_workouts
from community_page import display_community_page
from activity_page import display_activity_page


def display_app_page():
    """Displays the home page of the app."""

    st.markdown("""
        <style>
            .stat-card {
                background: #ffffff;
                border: 2px solid #e8e0f7;
                border-radius: 16px;
                padding: 20px;
                text-align: center;
                color: #1a1a1a;
                margin-bottom: 10px;
                box-shadow: 0 2px 8px rgba(103, 58, 183, 0.08);
            }
            .stat-value {
                font-size: 2rem;
                font-weight: 800;
                color: #6c3fc5;
            }
            .stat-label {
                font-size: 0.85rem;
                color: #888;
                text-transform: uppercase;
                letter-spacing: 1px;
            }
            .profile-banner {
                background: linear-gradient(135deg, #6c3fc5, #9b59b6);
                border-radius: 20px;
                padding: 30px;
                color: white;
                margin-bottom: 20px;
            }
            .profile-name {
                font-size: 2rem;
                font-weight: 800;
                margin: 0;
            }
            .profile-username {
                font-size: 1rem;
                color: #e8d5ff;
                margin: 0;
            }
        </style>
    """, unsafe_allow_html=True)

    st.title('🏃 SDS Fitness')

    # User ID input
    userId = st.text_input('Enter your User ID', placeholder='e.g. user1, user2, user3')

    if not userId:
        st.info('Enter your User ID to get started.')
        return

    # Validate user exists in database
    try:
        profile = get_user_profile(userId)
    except ValueError:
        st.error(f'User "{userId}" not found.')
        return

    # Tabs
    home_tab, community_tab, activity_tab = st.tabs(['🏠 Home', '👥 Community', '💪 Activity'])

    with home_tab:
        # Get workouts for stats
        workouts = get_user_workouts(userId)
        total_steps = sum(w.get('steps', 0) for w in workouts)
        total_calories = sum(w.get('calories_burned', 0) for w in workouts)
        total_distance = sum(w.get('distance', 0) for w in workouts)

        # Profile banner
        st.markdown(f"""
            <div class="profile-banner">
                <p class="profile-name">👋 {profile['full_name']}</p>
                <p class="profile-username">@{profile['username']} · {len(profile['friends'])} friends</p>
            </div>
        """, unsafe_allow_html=True)

        # Quick stats
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.markdown(f"""
                <div class="stat-card">
                    <div class="stat-value">{len(workouts)}</div>
                    <div class="stat-label">🏋️ Workouts</div>
                </div>
            """, unsafe_allow_html=True)
        with col2:
            st.markdown(f"""
                <div class="stat-card">
                    <div class="stat-value">{total_steps:,}</div>
                    <div class="stat-label">👟 Steps</div>
                </div>
            """, unsafe_allow_html=True)
        with col3:
            st.markdown(f"""
                <div class="stat-card">
                    <div class="stat-value">{total_distance:.1f}</div>
                    <div class="stat-label">📏 Miles</div>
                </div>
            """, unsafe_allow_html=True)
        with col4:
            st.markdown(f"""
                <div class="stat-card">
                    <div class="stat-value">{total_calories:,.0f}</div>
                    <div class="stat-label">🔥 Calories</div>
                </div>
            """, unsafe_allow_html=True)

        st.divider()

        # AI advice teaser
        advice = get_genai_advice(userId)
        st.markdown("### 🤖 Today's Tip")
        st.info(advice['content'])

        st.caption('Go to **Community** to see friends\' posts · Go to **Activity** for your workouts')

    with community_tab:
        display_community_page(userId)

    with activity_tab:
        display_activity_page(userId)


if __name__ == '__main__':
    display_app_page()