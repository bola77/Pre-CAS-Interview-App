# services/openai_client.py
import os
from openai import OpenAI  # modern SDK style[web:48][web:50]

def get_openai_client(api_key: str | None = None) -> OpenAI:
    """
    Returns an OpenAI client.
    Priority: explicit api_key argument > OPENAI_API_KEY env var.
    No dependency on Streamlit or Gradio.
    """
    key = api_key or os.getenv("OPENAI_API_KEY")
    if not key:
        raise RuntimeError("OPENAI_API_KEY not set; provide api_key or set env var.")
    return OpenAI(api_key=key)
