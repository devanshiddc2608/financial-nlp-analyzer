import os
from dotenv import load_dotenv

load_dotenv()  # loads variables from a local .env file when running locally


class Config:
    GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
    MODEL = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")
    MAX_INPUT_CHARS = int(os.environ.get("MAX_INPUT_CHARS", 20000))
    # Groq's free tier caps requests at 12,000 tokens/minute for this model.
    # ~30,000 chars ≈ 7,500 tokens, leaving headroom for the system prompt + completion.
    # This is independent of MAX_INPUT_CHARS: MAX_INPUT_CHARS controls what the app accepts,
    # this controls what actually gets sent to Groq in a single call.
    SINGLE_REQUEST_CHAR_LIMIT = int(os.environ.get("SINGLE_REQUEST_CHAR_LIMIT", 30000))
    TEMPERATURE = float(os.environ.get("GROQ_TEMPERATURE", 0.2))
    MAX_TOKENS = int(os.environ.get("GROQ_MAX_TOKENS", 1500))
    PORT = int(os.environ.get("PORT", 5000))
    DEBUG = os.environ.get("FLASK_DEBUG", "True") == "True"
