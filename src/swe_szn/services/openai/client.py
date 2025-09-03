from openai import OpenAI

from swe_szn.config import settings


def get_client():
    global client
    if "client" not in globals() or client is None:
        client = OpenAI(api_key=settings().require_openai_key())
    return client
