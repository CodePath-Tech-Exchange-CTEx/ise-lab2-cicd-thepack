#############################################################################
# supabase_client.py
#
# Singleton Supabase client initialised from Streamlit secrets.
# Required secrets (in .streamlit/secrets.toml):
#   [supabase]
#   url = "https://xxxx.supabase.co"
#   anon_key = "eyJ..."
#############################################################################

import streamlit as st
from supabase import create_client, Client


@st.cache_resource
def get_supabase_client() -> Client:
    """Returns a cached Supabase client instance."""
    url: str = st.secrets['supabase']['url']
    key: str = st.secrets['supabase']['anon_key']
    return create_client(url, key)


def get_supabase_admin_client() -> Client:
    """Returns a Supabase client using the service-role key (for server-side writes).
    Falls back to the anon key if service_role_key is not configured."""
    url: str = st.secrets['supabase']['url']
    service_key: str = st.secrets['supabase'].get(
        'service_role_key',
        st.secrets['supabase']['anon_key']
    )
    return create_client(url, service_key)
