#############################################################################
# community_page.py
#
# Enhanced community page:
#   - Friends' posts with profile avatars and timestamps
#   - Reaction buttons (stored locally in session state)
#   - AI daily tip card
#   - Leaderboard: friends ranked by total steps this week
#############################################################################

from collections import defaultdict
from datetime import date, timedelta, datetime

import streamlit as st

from data_fetcher import get_user_profile, get_user_posts, get_genai_advice, get_user_workouts


def display_community_page(user_id):
    """Displays the enhanced community page."""
    st.title('Community')

    tab_feed, tab_leaderboard, tab_ai = st.tabs(['Friends Feed', 'Leaderboard', 'Daily Tip'])

    with tab_feed:
        _render_friends_feed(user_id)

    with tab_leaderboard:
        _render_leaderboard(user_id)

    with tab_ai:
        _render_ai_tip(user_id)


# ── Friends feed ──────────────────────────────────────────────────────────────

def _render_friends_feed(user_id: str):
    profile = get_user_profile(user_id)
    friends = profile.get('friends', [])

    if not friends:
        st.info("You haven't added any friends yet.")
        return

    seen_post_ids = set()
    all_posts = []
    friend_profiles = {}

    for fid in friends:
        try:
            fp = get_user_profile(fid)
            friend_profiles[fid] = fp
            for post in get_user_posts(fid):
                if post['post_id'] not in seen_post_ids:
                    seen_post_ids.add(post['post_id'])
                    post['_author_profile'] = fp
                    all_posts.append(post)
        except Exception:
            pass

    if not all_posts:
        st.info("No posts from friends yet. Be the first to post!")
        return

    all_posts.sort(key=lambda x: x['timestamp'], reverse=True)
    top_posts = all_posts[:15]

    # Reactions state
    if 'reactions' not in st.session_state:
        st.session_state.reactions = {}

    for post in top_posts:
        _render_post_card(post)


def _render_post_card(post: dict):
    """Render a single post with reactions."""
    author = post.get('_author_profile', {})
    username = author.get('username', 'unknown')
    full_name = author.get('full_name', username)
    avatar = author.get('profile_image')
    post_id = post['post_id']

    with st.container(border=True):
        # Header row
        c1, c2 = st.columns([1, 8])
        with c1:
            if avatar and avatar.startswith('http'):
                try:
                    st.image(avatar, width=44)
                except Exception:
                    st.markdown(f'<div style="width:44px;height:44px;border-radius:50%;background:#E8E8ED;display:flex;align-items:center;justify-content:center;font-size:1.1rem;color:#6B7280">{full_name[0].upper()}</div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div style="width:44px;height:44px;border-radius:50%;background:#E8E8ED;display:flex;align-items:center;justify-content:center;font-size:1.1rem;color:#6B7280">{full_name[0].upper()}</div>', unsafe_allow_html=True)
        with c2:
            st.markdown(f'**{full_name}** `@{username}`')
            try:
                ts = datetime.fromisoformat(str(post['timestamp'])[:19])
                delta = datetime.utcnow() - ts
                if delta.days > 0:
                    time_str = f'{delta.days}d ago'
                elif delta.seconds > 3600:
                    time_str = f'{delta.seconds // 3600}h ago'
                else:
                    time_str = f'{delta.seconds // 60}m ago'
                st.caption(time_str)
            except Exception:
                st.caption(str(post['timestamp'])[:19])

        # Content
        if post.get('content'):
            st.write(post['content'])
        if post.get('image') and post['image'].startswith('http'):
            st.image(post['image'], use_container_width=True)

        # Reaction bar — keep emoji here as they're user-facing reactions, not UI chrome
        reactions = st.session_state.reactions.get(post_id, {'🔥': 0, '💪': 0, '❤️': 0, '👏': 0})
        r1, r2, r3, r4, _ = st.columns([1, 1, 1, 1, 4])
        for col, emoji in zip([r1, r2, r3, r4], ['🔥', '💪', '❤️', '👏']):
            count = reactions.get(emoji, 0)
            label = f'{emoji} {count}' if count else emoji
            if col.button(label, key=f'react_{post_id}_{emoji}'):
                if post_id not in st.session_state.reactions:
                    st.session_state.reactions[post_id] = {'🔥': 0, '💪': 0, '❤️': 0, '👏': 0}
                st.session_state.reactions[post_id][emoji] += 1
                st.rerun()


# ── Leaderboard ───────────────────────────────────────────────────────────────

def _render_leaderboard(user_id: str):
    st.subheader('Weekly Steps')

    try:
        profile = get_user_profile(user_id)
        friends = profile.get('friends', [])
    except Exception:
        friends = []

    participants = [user_id] + friends
    today = date.today()
    week_start = today - timedelta(days=today.weekday())

    rows = []
    for uid in participants:
        try:
            p = get_user_profile(uid)
            workouts = get_user_workouts(uid)
            week_steps = sum(
                w.get('steps', 0) for w in workouts
                if _to_date(w['start_timestamp']) and _to_date(w['start_timestamp']) >= week_start
            )
            # Add Apple Health steps for current user
            if uid == user_id:
                ah = st.session_state.get('apple_health', {})
                for d_str, s in ah.get('daily_steps', {}).items():
                    try:
                        d = date.fromisoformat(d_str)
                        if d >= week_start:
                            week_steps += s
                    except Exception:
                        pass
            rows.append({
                'name': p.get('full_name', uid),
                'username': p.get('username', uid),
                'steps': int(week_steps),
                'is_me': uid == user_id,
            })
        except Exception:
            pass

    if not rows:
        st.info('No data available.')
        return

    rows.sort(key=lambda x: x['steps'], reverse=True)

    RANK_LABELS = ['1st', '2nd', '3rd']

    for rank, row in enumerate(rows):
        rank_label = RANK_LABELS[rank] if rank < 3 else f'#{rank+1}'
        is_me = row['is_me']
        bg = '#F9FAFB' if is_me else '#ffffff'
        border = '#111827' if is_me else '#E8E8ED'
        border_width = '2px' if is_me else '1px'

        st.markdown(
            f'<div style="background:{bg};border:{border_width} solid {border};border-radius:12px;'
            f'padding:14px 20px;margin-bottom:8px;display:flex;justify-content:space-between;align-items:center">'
            f'<span style="font-size:0.8rem;font-weight:600;color:#6B7280;min-width:32px">{rank_label}</span>'
            f'<span style="flex:1;margin-left:12px;font-weight:{"700" if is_me else "500"};color:#111827">'
            f'{row["name"]} <span style="color:#9CA3AF;font-size:0.83rem">@{row["username"]}</span></span>'
            f'<span style="font-weight:700;color:#111827">{row["steps"]:,} steps</span>'
            f'</div>',
            unsafe_allow_html=True,
        )
        if is_me:
            st.caption('Your ranking this week')


# ── AI tip ────────────────────────────────────────────────────────────────────

def _render_ai_tip(user_id: str):
    st.subheader('Daily Tip')
    try:
        advice = get_genai_advice(user_id)
        st.caption(advice['timestamp'][:19])
        st.info(advice['content'])
        if advice['image'] and advice['image'].startswith('http'):
            st.image(advice['image'], use_container_width=True)
    except Exception as e:
        st.warning(f'Could not load tip: {e}')

    if st.button('Refresh tip'):
        get_genai_advice.clear()
        st.rerun()


# ── Helpers ───────────────────────────────────────────────────────────────────

def _to_date(s):
    if not s:
        return None
    try:
        return datetime.fromisoformat(str(s)[:19]).date()
    except Exception:
        return None
