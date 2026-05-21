"""
Phase 2 Groq rate-limit and corpus configuration.

Model: llama-3.3-70b-versatile (Groq free tier limits as of planning doc).
"""
import os

# Groq limits — llama-3.3-70b-versatile
GROQ_RPM = 30
GROQ_RPD = 1000
GROQ_TPM = 12_000
GROQ_TPD = 100_000

DEFAULT_GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

# Max reviews stored in insights.total_reviews_analysed (stratified sample from DB)
PHASE2_MAX_REVIEWS = int(os.getenv("PHASE2_MAX_REVIEWS", "1000"))

# Subsets sent to LLM (keeps prompts under TPM / TPD)
PHASE2_THEME_SAMPLE_SIZE = int(os.getenv("PHASE2_THEME_SAMPLE_SIZE", "200"))
PHASE2_QUOTE_SAMPLE_SIZE = int(os.getenv("PHASE2_QUOTE_SAMPLE_SIZE", "30"))
PHASE2_LLM_SENTIMENT_MAX = int(os.getenv("PHASE2_LLM_SENTIMENT_MAX", "150"))

# Sentiment LLM batches (only when review count <= PHASE2_LLM_SENTIMENT_MAX)
SENTIMENT_BATCH_SIZE = int(os.getenv("PHASE2_SENTIMENT_BATCH_SIZE", "20"))

# Min seconds between Groq calls (30 RPM → ~2.1s)
GROQ_MIN_INTERVAL_SEC = 60.0 / GROQ_RPM
