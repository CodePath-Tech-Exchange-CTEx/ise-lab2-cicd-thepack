#############################################################################
# auth_page.py
#
# Supabase authentication page — sign up, sign in, and sign out.
# Session state keys used:
#   st.session_state['supabase_user']   – dict with id, email, user_metadata
#   st.session_state['supabase_session'] – raw Supabase session object
#############################################################################

import streamlit as st
from supabase_client import get_supabase_client


def _supabase():
    return get_supabase_client()


def display_auth_page():
    """Renders the sign-in / sign-up form. Returns True if user is authenticated."""

    # Already logged in — nothing to show
    if st.session_state.get('supabase_user'):
        return True

    st.markdown("""
        <style>
            .auth-header {
                background: #111827;
                border-radius: 16px;
                padding: 40px 30px;
                text-align: center;
                color: white;
                margin-bottom: 30px;
            }
            .auth-header h1 { margin: 0; font-size: 2.2rem; font-weight: 700; letter-spacing: -0.5px; }
            .auth-header p  { margin: 6px 0 0; color: rgba(255,255,255,.5); font-size: 0.95rem; }
        </style>
        <div class="auth-header">
            <h1>SDS Fitness</h1>
            <p>Your personal fitness companion</p>
        </div>
    """, unsafe_allow_html=True)

    tab_login, tab_signup = st.tabs(['Sign In', 'Create Account'])

    # ── Sign In ───────────────────────────────────────────────────────────────
    with tab_login:
        with st.form('login_form'):
            st.subheader('Welcome back!')
            email = st.text_input('Email address', placeholder='you@example.com')
            password = st.text_input('Password', type='password')
            submitted = st.form_submit_button('Sign In', use_container_width=True, type='primary')

        if submitted:
            if not email or not password:
                st.error('Please enter both email and password.')
            else:
                with st.spinner('Signing in…'):
                    try:
                        client = _supabase()
                        res = client.auth.sign_in_with_password({'email': email, 'password': password})
                        _store_session(res)
                        st.success('Signed in!')
                        st.rerun()
                    except Exception as e:
                        st.error(f'Sign-in failed: {_friendly_error(e)}')

    # ── Sign Up ───────────────────────────────────────────────────────────────
    with tab_signup:
        with st.form('signup_form'):
            st.subheader('Create your account')
            display_name = st.text_input('Display name', placeholder='e.g. Alex Johnson')
            new_email = st.text_input('Email address', placeholder='you@example.com')
            new_pw = st.text_input('Password', type='password',
                                   help='At least 6 characters')
            new_pw2 = st.text_input('Confirm password', type='password')
            submitted2 = st.form_submit_button('Create Account', use_container_width=True, type='primary')

        if submitted2:
            if not display_name or not new_email or not new_pw:
                st.error('Please fill in all fields.')
            elif new_pw != new_pw2:
                st.error('Passwords do not match.')
            elif len(new_pw) < 6:
                st.error('Password must be at least 6 characters.')
            else:
                with st.spinner('Creating account…'):
                    try:
                        client = _supabase()
                        res = client.auth.sign_up({
                            'email': new_email,
                            'password': new_pw,
                            'options': {
                                'data': {'display_name': display_name}
                            }
                        })
                        if res.user:
                            _store_session(res)
                            st.success('Account created! Welcome to SDS Fitness.')
                            st.rerun()
                        else:
                            st.info('Check your email to confirm your account, then sign in.')
                    except Exception as e:
                        st.error(f'Sign-up failed: {_friendly_error(e)}')

    return False


def display_user_sidebar():
    """Renders logged-in user info + sign-out button in the sidebar."""
    user = st.session_state.get('supabase_user')
    if not user:
        return

    with st.sidebar:
        st.markdown('---')
        name = user.get('user_metadata', {}).get('display_name') or user.get('email', 'User')
        st.markdown(f'**{name}**')
        st.caption(user.get('email', ''))
        if st.button('Sign Out', use_container_width=True):
            sign_out()
            st.rerun()


def get_current_user_id():
    """Returns the Supabase user UUID for the currently signed-in user, or None."""
    user = st.session_state.get('supabase_user')
    return user['id'] if user else None


def get_current_display_name():
    """Returns display name or email of the current user."""
    user = st.session_state.get('supabase_user')
    if not user:
        return 'User'
    return (user.get('user_metadata', {}).get('display_name')
            or user.get('email', 'User'))


# ── Helpers ───────────────────────────────────────────────────────────────────

def _store_session(res):
    """Persist auth result into session state."""
    user_obj = res.user
    if user_obj is None:
        return
    st.session_state['supabase_user'] = {
        'id': user_obj.id,
        'email': user_obj.email,
        'user_metadata': user_obj.user_metadata or {},
    }
    st.session_state['supabase_session'] = res.session


def sign_out():
    """Clear session state on sign-out."""
    try:
        _supabase().auth.sign_out()
    except Exception:
        pass
    for key in ('supabase_user', 'supabase_session', 'user_goals'):
        st.session_state.pop(key, None)


def _friendly_error(exc):
    msg = str(exc).lower()
    if 'invalid login credentials' in msg or 'invalid email or password' in msg:
        return 'Invalid email or password.'
    if 'email already registered' in msg or 'user already registered' in msg:
        return 'An account with that email already exists.'
    if 'rate limit' in msg:
        return 'Too many attempts — please wait a moment and try again.'
    return str(exc)
