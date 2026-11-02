"""Cliente único de Google GenAI (Gemini API) a partir de GOOGLE_API_KEY del .env."""
from __future__ import annotations

import os
from functools import lru_cache

from dotenv import load_dotenv

try:  # usa el almacén de certificados del sistema (evita CERTIFICATE_VERIFY_FAILED en Windows)
    import truststore

    truststore.inject_into_ssl()
except ImportError:
    pass

from google import genai

load_dotenv()


@lru_cache(maxsize=1)
def get_client() -> genai.Client:
    api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("Falta GOOGLE_API_KEY en .env (copia .env.example a .env y rellénala)")
    return genai.Client(api_key=api_key)
