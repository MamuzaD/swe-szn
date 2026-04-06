from openai import OpenAI

from swe_szn.config import settings

client = None


def get_client():
    if settings().ai_provider == "codex":
        raise RuntimeError(
            "OpenAI client is unavailable when SWE_SZN_AI_PROVIDER=codex"
        )
    global client
    if "client" not in globals() or client is None:
        client = OpenAI(api_key=settings().require_openai_key())
    return client
