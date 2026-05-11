"""CUA Node Configuration — tüm env var'lar ve sabitler."""
import os
from dotenv import load_dotenv

load_dotenv()

# ── Orchestrator ────────────────────────────────────────────────────────────
ORCHESTRATOR_HOST = os.getenv("ORCHESTRATOR_HOST", "localhost")
ORCHESTRATOR_PORT = int(os.getenv("ORCHESTRATOR_PORT", "50051"))
CUA_GRPC_PORT     = int(os.getenv("CUA_GRPC_PORT", "50054"))

# ── RabbitMQ ────────────────────────────────────────────────────────────────
RABBITMQ_HOST     = os.getenv("RABBITMQ_HOST", "localhost")
RABBITMQ_PORT     = int(os.getenv("RABBITMQ_PORT", "5672"))
RABBITMQ_USER     = os.getenv("RABBITMQ_USER", "guest")
RABBITMQ_PASSWORD = os.getenv("RABBITMQ_PASSWORD", "guest")
QUEUE_AGENT_TASKS   = "agent_tasks"
QUEUE_AGENT_RESULTS = "agent_results"

# ── LLM Ayarları ────────────────────────────────────────────────────────────
# MODEL_MODE = "local"       → LM Studio (OpenAI-compat endpoint)
# MODEL_MODE = "production"  → Qwen3.5-9B via transformers + bitsandbytes
MODEL_MODE  = os.getenv("MODEL_MODE", "local")
MODEL_NAME  = os.getenv("MODEL_NAME", "Qwen/Qwen3.5-9B-Instruct")
CUA_LLM_MAX_COMPLETION_TOKENS = int(os.getenv("CUA_LLM_MAX_COMPLETION_TOKENS", "8192"))
CUA_PIPELINE_MAX_NEW_TOKENS   = int(os.getenv("CUA_PIPELINE_MAX_NEW_TOKENS", "4096"))
CUA_SYNTHESIS_MAX_TOKENS      = int(os.getenv("CUA_SYNTHESIS_MAX_TOKENS", "8192"))
CUA_MAX_IMAGES_PER_ARTICLE    = int(os.getenv("CUA_MAX_IMAGES_PER_ARTICLE", "3"))
CUA_MAX_QUERY_PLAN            = int(os.getenv("CUA_MAX_QUERY_PLAN", "10"))

# LM Studio / vLLM endpoint (Vast.ai'da: http://localhost:8000/v1)
LMSTUDIO_URL = os.getenv("LMSTUDIO_URL", "http://localhost:8000/v1")
LMSTUDIO_API_KEY = os.getenv("LMSTUDIO_API_KEY", os.getenv("VLLM_API_KEY", "lm-studio"))

# ── Browser Ayarları ────────────────────────────────────────────────────────
# "duckduckgo" | "bing" | "google"  — DDG varsayılan, CAPTCHA yok
DEFAULT_SEARCH_ENGINE = os.getenv("SEARCH_ENGINE", "duckduckgo")

# Headless mod (prod=True, debug=False)
BROWSER_HEADLESS  = os.getenv("BROWSER_HEADLESS", "true").lower() == "true"

# Surface/all-in-one mode should avoid sources already covered by crawler.
SURFACE_EXCLUDED_DOMAINS = [
    d.strip().lower()
    for d in os.getenv(
        "SURFACE_EXCLUDED_DOMAINS",
        "bbc.com,edition.cnn.com,aljazeera.com,ekathimerini.com,"
        "greekreporter.com,greekcitytimes.com,timesofisrael.com,haaretz.com,"
        "jpost.com,israelnationalnews.com,iranintl.com",
    ).split(",")
    if d.strip()
]

# Surface mode is for news articles, not encyclopedias or generic statistic pages.
SURFACE_BLOCKED_DOMAINS = [
    d.strip().lower()
    for d in os.getenv(
        "SURFACE_BLOCKED_DOMAINS",
        "britannica.com,wikipedia.org,wikimedia.org,statisticsoftheworld.com,"
        "worlddata.info,worldbank.org,imf.org,cia.gov",
    ).split(",")
    if d.strip()
]

# ── Agent Parametreleri ─────────────────────────────────────────────────────
MAX_ARTICLES_DEFAULT         = int(os.getenv("MAX_ARTICLES", "10"))
MAX_SEARCHES_DEFAULT         = int(os.getenv("MAX_SEARCHES", "5"))
RESEARCH_CONFIDENCE_THRESHOLD = float(os.getenv("CONFIDENCE_THRESHOLD", "0.80"))
MAX_RESEARCH_CYCLES          = int(os.getenv("MAX_RESEARCH_CYCLES", "15"))

# Arama döngüleri arası bekleme (saniye) — Google rate limit koruması
SEARCH_DELAY_SECONDS = float(os.getenv("SEARCH_DELAY", "1.5"))
