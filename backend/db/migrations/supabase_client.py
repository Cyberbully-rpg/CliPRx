"""
Supabase Connection Initialization
Establishes a secure connection to the PostgreSQL database using environment variables.
"""
import os
from supabase import create_client, Client

def get_supabase_client() -> Client:
    """
    Retrieves the Supabase URL and Anon Key from the environment and returns an active client.
    """
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")

    if not supabase_url or not supabase_key:
        raise ValueError(
            "Supabase credentials missing. Ensure SUPABASE_URL and SUPABASE_KEY are in your .env file."
        )

    return create_client(supabase_url, supabase_key)


def get_supabase_admin_client() -> Client:
    """
    Same as get_supabase_client(), but authenticated with the service role key,
    which bypasses Row Level Security. Backend-only -- for writing rows on a
    user's behalf (e.g. reports/prescriptions) after the request's own JWT has
    already been verified and ownership established. Never expose this key to
    a frontend/browser context.
    """
    supabase_url = os.getenv("SUPABASE_URL")
    service_role_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

    if not supabase_url or not service_role_key:
        raise ValueError(
            "Supabase admin credentials missing. Ensure SUPABASE_URL and "
            "SUPABASE_SERVICE_ROLE_KEY are in your .env file."
        )

    return create_client(supabase_url, service_role_key)