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