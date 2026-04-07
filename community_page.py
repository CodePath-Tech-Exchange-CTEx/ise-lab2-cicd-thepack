#############################################################################
# community_page.py
#
# This page displays posts from a user's friends and one piece of GenAI advice.
#############################################################################

import streamlit as st
from data_fetcher import get_user_profile, get_user_posts, get_genai_advice


def display_community_page(user_id):
    """Displays the community page with friends' posts and GenAI advice."""
    st.title('Community')

    # Get the user's friend list
    profile = get_user_profile(user_id)
    friends = profile['friends']

    # Collect posts from all friends, deduplicating by post_id
    seen_post_ids = set()
    all_posts = []
    for friend_id in friends:
        for post in get_user_posts(friend_id):
            if post['post_id'] not in seen_post_ids:
                seen_post_ids.add(post['post_id'])
                all_posts.append(post)

    # Sort by timestamp and take the first 10
    all_posts.sort(key=lambda x: x['timestamp'])
    top_posts = all_posts[:10]

    st.subheader('Friends Posts')
    if not top_posts:
        st.write('No posts from friends yet.')
    else:
        for post in top_posts:
            friend_profile = get_user_profile(post['user_id'])
            st.markdown(f"**{friend_profile['username']}**")
            st.caption(post['timestamp'])
            if post['content']:
                st.write(post['content'])
            if post['image'] and post['image'].startswith('http'):
                st.image(post['image'], use_container_width=True)
            st.divider()

    # Display one piece of GenAI advice
    st.subheader('AI Advice')
    advice = get_genai_advice(user_id)
    st.caption(advice['timestamp'])
    st.info(advice['content'])
    if advice['image']:
        st.image(advice['image'], use_container_width=True)