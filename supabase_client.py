#############################################################################
# supabase_client.py
#
# Singleton Supabase client.
# Reads credentials from (in priority order):
#   1. .streamlit/secrets.toml  [supabase] section  (local dev)
#   2. Environment variables SUPABASE_URL / SUPABASE_ANON_KEY  (Cloud Run)
#############################################################################

import os
import streamlit as st
from supabase import create_client, Client


def _get_supabase_url() -> str:
    try:
        return st.secrets['supabase']['url']
    except Exception:
        return os.environ.get('SUPABASE_URL', '')


def _get_supabase_key() -> str:
    try:
        return st.secrets['supabase']['anon_key']
    except Exception:
        return os.environ.get('SUPABASE_ANON_KEY', '')


@st.cache_resource
def get_supabase_client() -> Client:
    """Returns a cached Supabase client instance."""
    url = _get_supabase_url()
    key = _get_supabase_key()
    if not url or not key:
        raise RuntimeError(
            'Supabase credentials not found. Set SUPABASE_URL and '
            'SUPABASE_ANON_KEY environment variables on Cloud Run, or '
            'add them to .streamlit/secrets.toml for local dev.'
        )
    return create_client(url, key)


def get_supabase_admin_client() -> Client:
    """Returns a Supabase client using the service-role key (for server-side writes).
    Falls back to the anon key if service_role_key is not configured."""
    url = _get_supabase_url()
    try:
        service_key = st.secrets['supabase'].get('service_role_key', _get_supabase_key())
    except Exception:
        service_key = os.environ.get('SUPABASE_SERVICE_ROLE_KEY', _get_supabase_key())
    return create_client(url, service_key)
