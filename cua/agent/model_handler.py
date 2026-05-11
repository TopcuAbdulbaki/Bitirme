"""
CUA LLM Model Handler — real inference via LM Studio (local) or Qwen (production).

Local mode:  browser-use'un kendi ChatOpenAI wrapper'ı (browser_use.llm.openai.chat)
             LM Studio OpenAI-compat endpoint → localhost:1234
Production:  Qwen3.5-9B-Instruct via transformers + bitsandbytes (4/8-bit)

NEDEN browser-use.ChatOpenAI?
  browser-use 0.12.x kendi llm interface'ini kullanır (langchain değil).
  BaseChatModel Protocol'ü: .provider, .model, .ainvoke() gerektirir.
  browser_use.llm.openai.chat.ChatOpenAI bunların hepsini native sağlar.
"""
import json
import re
import os
import base64
from typing import Dict, Any, Optional

# ---------------------------------------------------------------------------
# browser-use 0.12.x native LLM — langchain değil
# ---------------------------------------------------------------------------
try:
    from browser_use.llm.openai.chat import ChatOpenAI as BrowserUseChatOpenAI
    _BROWSER_USE_LLM_AVAILABLE = True
except ImportError:
    BrowserUseChatOpenAI = None  # type: ignore
    _BROWSER_USE_LLM_AVAILABLE = False

from cua.agent.state import AgentState
from cua.config import (
    CUA_LLM_MAX_COMPLETION_TOKENS,
    CUA_MAX_IMAGES_PER_ARTICLE,
    CUA_MAX_QUERY_PLAN,
    CUA_PIPELINE_MAX_NEW_TOKENS,
    CUA_SYNTHESIS_MAX_TOKENS,
    LMSTUDIO_API_KEY,
    MODEL_MODE,
    MODEL_NAME,
    LMSTUDIO_URL,
    RESEARCH_CONFIDENCE_THRESHOLD,
)


# ---------------------------------------------------------------------------
# Shared prompt builders
# ---------------------------------------------------------------------------

def _build_surface_plan_prompt(state: AgentState) -> str:
    articles_count = len(state.get("collected_articles", []))
    visited_count  = len(state.get("visited_urls", []))
    max_articles   = state.get("params", {}).get("max_articles", 10)
    query          = state.get("query", "")
    return f"""You are a news discovery agent. Your task is to collect news articles.

Current status:
- Search topic: {query}
- Articles found: {articles_count} / {max_articles}
- URLs already visited: {visited_count}

Choose ONE of the following actions and respond with VALID JSON only:

Option A — search for more articles:
{{"action": "search", "query": "<your_search_query>"}}

Option B — visit a specific URL you found:
{{"action": "visit", "url": "<url_to_visit>"}}

Option C — you have enough articles, stop:
{{"action": "complete"}}

Rules:
- Use "complete" only when articles_found >= {max_articles}
- Vary your search queries each cycle to discover new sources
- Prefer authoritative news sources (Reuters, AP, BBC, Al Jazeera, etc.)
- Do NOT revisit already-visited URLs

Respond with ONLY valid JSON, no explanation."""


def _build_research_plan_prompt(state: AgentState) -> str:
    topic          = state.get("topic", state.get("query", ""))
    hypothesis     = state.get("current_hypothesis", "No hypothesis yet")
    findings_count = len(state.get("findings", []))
    cycle          = state.get("cycle_count", 0)
    confidence     = state.get("confidence", 0.0)
    visited_count  = len(state.get("visited_urls", []))
    findings_summary = ""
    for i, f in enumerate(state.get("findings", [])[-3:], 1):
        findings_summary += f"  {i}. {f.get('title', '')} — {f.get('content', '')[:200]}\n"

    return f"""You are a deep intelligence research agent investigating a topic.

Topic: {topic}
Current hypothesis: {hypothesis}
Findings collected: {findings_count}
Confidence: {confidence:.1%}
Cycle: {cycle}
URLs visited: {visited_count}

Recent findings:
{findings_summary or "  (none yet)"}

Choose ONE action and respond with VALID JSON only:

Option A — search for new evidence:
{{"action": "search", "query": "<targeted_search_query>", "reason": "<why this query helps>"}}

Option B — visit a promising URL:
{{"action": "visit", "url": "<url>", "reason": "<why this source is valuable>"}}

Option C — you have sufficient evidence, generate report:
{{"action": "complete"}}

Use "complete" only when confidence >= {RESEARCH_CONFIDENCE_THRESHOLD:.0%}.
Respond with ONLY valid JSON, no explanation."""


def _build_evaluate_prompt(state: AgentState) -> str:
    topic    = state.get("topic", state.get("query", ""))
    findings = state.get("findings", [])
    summary  = "\n".join(
        f"- {f.get('title','')}: {f.get('content','')[:300]}"
        for f in findings[-5:]
    )
    return f"""Rate your research confidence on topic: "{topic}"

Evidence gathered so far ({len(findings)} findings):
{summary or "(none yet)"}

Reply with ONLY a JSON object:
{{"confidence": <float 0.0-1.0>, "reasoning": "<one sentence>"}}"""


def _build_synthesize_prompt(state: AgentState) -> str:
    mode = state.get("mode", "surface")
    if mode == "surface":
        articles = state.get("collected_articles", [])
        articles_text = "\n".join(
            f"- [{a.get('source','')}] {a.get('title','')}: {a.get('content','')[:500]}"
            for a in articles
        )
        return f"""Summarize the following news articles into a structured JSON report.

Articles:
{articles_text}

Respond ONLY with valid JSON:
{{
  "mode": "surface",
  "summary": "<2-3 sentence overview>",
  "article_count": {len(articles)},
  "sources": ["<source1>", "..."],
  "top_keywords": ["<kw1>", "..."],
  "key_findings": ["<finding1>", "..."]
}}"""
    else:
        topic    = state.get("topic", "")
        findings = state.get("findings", [])
        findings_text = "\n".join(
            f"- {f.get('title','')}: {f.get('content','')[:600]}"
            for f in findings
        )
        return f"""Write a comprehensive intelligence report on: "{topic}"

Research findings:
{findings_text}

Respond ONLY with valid JSON:
{{
  "mode": "research",
  "topic": "{topic}",
  "executive_summary": "<2-3 sentence overview>",
  "key_findings": ["<finding1>", "..."],
  "hypothesis": "<refined hypothesis>",
  "supporting_evidence": ["{{"source": "...", "quote": "..."}}"],
  "confidence_score": <0.0-1.0>,
  "recommendations": ["<next step1>", "..."]
}}"""


# ---------------------------------------------------------------------------
# JSON extraction helper
# ---------------------------------------------------------------------------

def _strip_llm_wrappers(text: str) -> str:
    """Remove common model wrappers without trying to reinterpret content."""
    text = (text or "").strip()
    text = re.sub(r"<think>[\s\S]*?</think>", "", text, flags=re.IGNORECASE)
    text = re.sub(r"```(?:json)?", "", text, flags=re.IGNORECASE)
    return text.replace("```", "").strip()


def _first_json_value(text: str, openers: str = "{["):
    """Parse the first valid JSON object/array without greedy regex matching."""
    text = _strip_llm_wrappers(text)
    decoder = json.JSONDecoder()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    for idx, char in enumerate(text):
        if char not in openers:
            continue
        try:
            value, _ = decoder.raw_decode(text[idx:])
        except json.JSONDecodeError:
            continue
        return value
    return None


def _extract_json(text: str) -> Optional[Dict[str, Any]]:
    """Pull the first valid JSON object out of an LLM response."""
    value = _first_json_value(text, "{")
    return value if isinstance(value, dict) else None


def _extract_json_array(text: str) -> Optional[list]:
    """Pull the first valid JSON array out of an LLM response."""
    value = _first_json_value(text, "[")
    return value if isinstance(value, list) else None


def _clean_model_text(text: str, max_chars: int = 1200) -> str:
    """Best-effort cleanup for useful free-text model output."""
    text = _strip_llm_wrappers(text)
    text = re.split(
        r"\b[23]\.\s*(?:analyze|contextualize|synthesize|article context|context)\b",
        text,
        maxsplit=1,
        flags=re.I,
    )[0]
    text = re.sub(r"\bthe user wants me to [^.]+\.\s*", "", text, flags=re.I)
    text = re.sub(r"\b(?:i need to|i should) [^.]+\.\s*", "", text, flags=re.I)
    text = re.sub(r"^\s*(Thinking Process|Reasoning|Analysis)\s*:\s*", "", text, flags=re.I)
    text = re.sub(r"[*_`#]+", "", text)
    text = re.sub(r"\b\d+\.\s*Analyze the Image\s*:?", "", text, flags=re.I)
    text = re.sub(r"\b(?:Visuals?|Content|Specific Items|Text|Title)\s*:\s*", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:max_chars]


# ---------------------------------------------------------------------------
# Main handler
# ---------------------------------------------------------------------------

class CUAModelHandler:
    """
    CUA's LLM decision engine.

    Supports:
      - local:      LM Studio (OpenAI-compat, e.g. Qwen3-8B-q4)
      - production: Qwen3.5-9B-Instruct via transformers + bitsandbytes
    """

    def __init__(self, mode: str = None):
        self.mode = mode or MODEL_MODE
        self.llm  = None
        self._tokenizer = None
        self._pipeline  = None
        self._lmstudio_client = None
        self._initialize_model()

    # ------------------------------------------------------------------
    # Initialization
    # ------------------------------------------------------------------

    def _initialize_model(self):
        if self.mode == "local":
            self._init_lmstudio()
        else:
            self._init_transformers()

    def _init_lmstudio(self):
        """Connect to LM Studio OpenAI-compatible endpoint via browser-use native ChatOpenAI."""
        if not _BROWSER_USE_LLM_AVAILABLE:
            print("[ModelHandler] browser-use yüklü değil")
            return
        try:
            from openai import OpenAI
            import os
            # Ensure LMSTUDIO_URL is dynamically read just in case
            current_url = os.environ.get("LMSTUDIO_URL", LMSTUDIO_URL)
            self._openai_base_url = current_url
            print(f"[ModelHandler] Test connection to: {current_url}")
            
            _raw_client = OpenAI(base_url=current_url, api_key=LMSTUDIO_API_KEY)
            models = _raw_client.models.list()
            model_ids = [m.id for m in models.data]
            print(f"[ModelHandler] LM Studio connected. Models: {model_ids}")
            first_model = model_ids[0] if model_ids else MODEL_NAME
            self._lmstudio_model = first_model

            # browser-use'un kendi dataclass ChatOpenAI'ı (provider+model native)
            self.llm = BrowserUseChatOpenAI(
                model=first_model,
                base_url=current_url,
                api_key=LMSTUDIO_API_KEY,
                temperature=0.3,
                max_completion_tokens=CUA_LLM_MAX_COMPLETION_TOKENS,
            )
            print(f"[ModelHandler] browser-use ChatOpenAI hazır (model={first_model})")
        except Exception as e:
            import traceback
            print(f"[ModelHandler] LM Studio unavailable: {e}")
            traceback.print_exc()
            self.llm = None
            self._lmstudio_model = MODEL_NAME
            self._openai_base_url = os.environ.get("LMSTUDIO_URL", LMSTUDIO_URL)


    def _init_transformers(self):
        """Load Qwen model locally via transformers."""
        try:
            import torch
            from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline, BitsAndBytesConfig

            print(f"[ModelHandler] Loading {MODEL_NAME} (4-bit quantized)...")
            bnb_config = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_quant_type="nf4",
                bnb_4bit_compute_dtype=torch.float16,
                bnb_4bit_use_double_quant=True,
            )
            self._tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, trust_remote_code=True)
            model = AutoModelForCausalLM.from_pretrained(
                MODEL_NAME,
                quantization_config=bnb_config,
                device_map="auto",
                trust_remote_code=True,
            )
            self._pipeline = pipeline(
                "text-generation",
                model=model,
                tokenizer=self._tokenizer,
                max_new_tokens=CUA_PIPELINE_MAX_NEW_TOKENS,
                temperature=0.3,
                do_sample=True,
                repetition_penalty=1.1,
            )
            print(f"[ModelHandler] {MODEL_NAME} loaded successfully")
        except ImportError as e:
            print(f"[ModelHandler] transformers/bitsandbytes not installed: {e}")
            # Graceful fallback: try LM Studio
            print("[ModelHandler] Falling back to LM Studio...")
            self._init_lmstudio()
        except Exception as e:
            print(f"[ModelHandler] Model load error: {e}")
            self._init_lmstudio()

    # ------------------------------------------------------------------
    # Core inference
    # ------------------------------------------------------------------

    async def _call_llm(self, prompt: str, max_tokens: int = CUA_LLM_MAX_COMPLETION_TOKENS) -> str:
        """Send prompt to whichever backend is active and return raw text."""
        if self.llm is not None:
            return await self._call_lmstudio(prompt, max_tokens)
        elif self._pipeline is not None:
            return self._call_pipeline(prompt, max_tokens)
        else:
            # Last resort: attempt LM Studio reconnect
            self._init_lmstudio()
            if self.llm:
                return await self._call_lmstudio(prompt, max_tokens)
            raise RuntimeError("[ModelHandler] No LLM backend available")

    async def _call_lmstudio(self, prompt: str, max_tokens: int) -> str:
        """browser-use ChatOpenAI.ainvoke() üzerinden LM Studio'ya istek at."""
        from browser_use.llm.messages import UserMessage

        try:
            result = await self.llm.ainvoke(
                [UserMessage(content=prompt)]
            )
            return result.completion or ""
        except Exception as e:
            print(f"[ModelHandler] _call_lmstudio error: {e}")
            return ""

    async def generate_query_plan(self, state: AgentState, count: int = CUA_MAX_QUERY_PLAN) -> list[str]:
        """Generate a bounded list of search queries for the task."""
        base_query = state.get("query", state.get("topic", ""))
        collected = state.get("collected_articles", [])
        recent = "\n".join(
            f"- {a.get('title', '')}: {a.get('content', '')[:180]}"
            for a in collected[-3:]
        )
        prompt = f"""Generate {count} diverse web search queries for collecting news articles.

Topic: {base_query}
Already collected:
{recent or "(none)"}

Rules:
- Keep every query directly related to the topic.
- Vary wording, sources, and subtopics.
- Do not include generic one-word queries.
- Return ONLY a JSON array of strings."""
        try:
            raw = await self._call_llm(prompt, max_tokens=512)
            items = _extract_json_array(raw) or []
            queries = self._complete_query_plan(items, base_query, collected, count)
            if len(queries) > 1 or not items:
                print(f"[ModelHandler] Query plan: {queries}")
                return queries
            print(f"[ModelHandler] Query plan parse failed, raw='{raw[:200]}'")
        except Exception as e:
            print(f"[ModelHandler] generate_query_plan error: {e}")

        from cua.agent.search_strategy import SearchStrategy
        fallback = []
        for cycle in range(max(count, 3)):
            fallback.extend(SearchStrategy.generate_queries(base_query, "surface", collected, cycle, ""))
        return self._normalize_query_list(fallback, base_query, count)

    def _complete_query_plan(
        self,
        items: list,
        base_query: str,
        collected: list,
        count: int,
    ) -> list[str]:
        from cua.agent.search_strategy import SearchStrategy

        candidates = list(items or [])
        if len(candidates) < count:
            for cycle in range(max(count, 3)):
                candidates.extend(SearchStrategy.generate_queries(base_query, "surface", collected, cycle, ""))
                if len(candidates) >= count * 2:
                    break
        return self._normalize_query_list(candidates, base_query, count)

    def _normalize_query_list(self, items: list, base_query: str, count: int) -> list[str]:
        queries = [base_query]
        queries.extend(str(item).strip() for item in items if str(item).strip())
        unique = []
        seen = set()
        for query in queries:
            normalized = re.sub(r"\s+", " ", query.lower()).strip()
            if len(normalized) < 4 or normalized in seen:
                continue
            if base_query and not any(part in normalized for part in base_query.lower().split()[:2]):
                continue
            seen.add(normalized)
            unique.append(query)
            if len(unique) >= count:
                break
        return unique

    async def analyze_article(self, article: Dict[str, Any]) -> Dict[str, Any]:
        """Attach CUA inline LLM/VLM analysis in existing pipeline shapes."""
        article["llm_analysis"] = {
            "result": await self.analyze_article_text(article)
        }

        images = []
        media = article.get("media", {}) or {}
        if media.get("main_image"):
            images.append(media["main_image"])
        images.extend(media.get("content_images", []))

        vlm_results = []
        for image_url in images[:CUA_MAX_IMAGES_PER_ARTICLE]:
            vlm_results.append(await self.analyze_image_url(image_url, article))
        article["vlm_analysis"] = {"results": vlm_results}
        return article

    async def assess_article_quality(self, article: Dict[str, Any], topic: str = "") -> Dict[str, Any]:
        """Return a small accept/reject gate for candidate surface articles."""
        heuristic = self._heuristic_article_quality(article, topic)
        if heuristic["accept"] == 0:
            return heuristic

        prompt = f"""You are a strict news article quality gate.

Decide if this candidate should be accepted into a news dataset for the topic.

Accept only if:
- It is an actual news article, analysis article, or institutional/economic report page.
- The main text is meaningfully about the requested topic.
- The page is not an anti-bot/security wall, error page, product page, marketplace page, SEO spam page, generic scraped page, index/category page, or unrelated page.

Return ONLY valid JSON:
{{
  "accept": 1,
  "reason": "short reason",
  "page_type": "news_article/report/product/security_wall/error/category/seo_spam/unrelated/other",
  "relevance": "high/medium/low"
}}

Use accept=0 for low relevance or invalid page types.

Topic: {topic or article.get('keyword_found', '')}
URL: {article.get('url', '')}
Source: {article.get('source', '')}
Title: {article.get('title', '')}
Description: {article.get('description', '')}
Content:
{article.get('content', '')[:2500]}"""
        try:
            raw = await self._call_llm(prompt, max_tokens=350)
            parsed = _extract_json(raw)
            if parsed:
                return self._normalize_quality_gate(parsed, article, topic)
            print(f"[ModelHandler] Article quality parse failed, raw='{raw[:200]}'")
        except Exception as e:
            print(f"[ModelHandler] assess_article_quality error: {e}")
        return heuristic

    def _normalize_quality_gate(
        self,
        parsed: Dict[str, Any],
        article: Dict[str, Any],
        topic: str,
    ) -> Dict[str, Any]:
        page_type = str(parsed.get("page_type", "other")).lower().strip()
        relevance = self._normalize_label(parsed.get("relevance"), {"high", "medium", "low"}, "low")
        accept_raw = parsed.get("accept", 0)
        accept = 1 if accept_raw in (1, "1", True, "true", "yes", "accept") else 0

        invalid_types = {
            "product", "security_wall", "error", "category",
            "seo_spam", "unrelated", "marketplace",
        }
        if page_type in invalid_types or relevance == "low":
            accept = 0

        heuristic = self._heuristic_article_quality(article, topic)
        if heuristic["accept"] == 0:
            return heuristic

        return {
            "accept": accept,
            "reason": str(parsed.get("reason", ""))[:240],
            "page_type": page_type or "other",
            "relevance": relevance,
        }

    def _heuristic_article_quality(self, article: Dict[str, Any], topic: str = "") -> Dict[str, Any]:
        title = str(article.get("title", ""))
        content = str(article.get("content", ""))
        description = str(article.get("description", ""))
        source = str(article.get("source", "")).lower()
        url = str(article.get("url", "")).lower()
        text = f"{title}\n{description}\n{content}".lower()

        bad_markers = [
            "automated behavior",
            "programmatic access",
            "security tools has flagged",
            "unauthorized commercial tools",
            "please contact helpdesk",
            "error code:",
            "cloudflare ray id",
            "origin is unreachable",
            "web server is returning an unknown error",
            "verify you are human",
            "human verification",
            "complete the captcha",
        ]
        if any(marker in text for marker in bad_markers):
            return {
                "accept": 0,
                "reason": "security/error wall",
                "page_type": "security_wall",
                "relevance": "low",
            }

        marketplace_markers = [
            "add to cart", "shopping cart", "commercial license",
            "download this product", "source files", "creative fabrica",
            "licença comercial", "carrinho", "inscreva-se gratuitamente",
        ]
        if any(marker in text for marker in marketplace_markers):
            return {
                "accept": 0,
                "reason": "marketplace/product page",
                "page_type": "product",
                "relevance": "low",
            }

        bad_sources = {"creativefabrica.com", "googleapis.com"}
        if source in bad_sources or "storage.googleapis.com" in url:
            return {
                "accept": 0,
                "reason": "non-news hosting/source",
                "page_type": "seo_spam",
                "relevance": "low",
            }

        return {
            "accept": 1,
            "reason": "passed heuristic checks",
            "page_type": "candidate",
            "relevance": "medium",
        }

    async def analyze_article_text(self, article: Dict[str, Any]) -> Dict[str, Any]:
        prompt = f"""You are a news analysis assistant specialized in sentiment classification.

Analyze this news article and respond ONLY with valid JSON:
{{
  "summary": "2-3 sentence summary of the article",
  "sentiment": -1,
  "sentiment_label": "negative",
  "keywords": ["keyword1", "keyword2", "keyword3"],
  "entities": {{
    "countries": ["Country1"],
    "organizations": ["Org1"],
    "people": ["Person1"]
  }},
  "category": "politics/economy/sports/technology/other",
  "relevance_to_topic": "high/medium/low"
}}

Sentiment scoring:
- 1 = Positive
- 0 = Neutral
- -1 = Negative

Title: {article.get('title', '')}
Topic/query: {article.get('keyword_found', '')}
Content:
{article.get('content', '')[:5000]}"""
        try:
            raw = await self._call_llm(prompt, max_tokens=900)
            parsed = _extract_json(raw)
            if parsed:
                return self._normalize_llm_analysis(parsed)
            print(f"[ModelHandler] Article analysis parse failed, raw='{raw[:200]}'")
        except Exception as e:
            print(f"[ModelHandler] analyze_article_text error: {e}")
        return self._fallback_llm_analysis(article)

    async def analyze_image_url(self, image_url: str, article: Dict[str, Any]) -> Dict[str, Any]:
        result_base = {
            "minio_path": None,
            "original_url": image_url,
            "description": "",
            "objects": [],
            "sentiment": "neutral",
            "relevance": "low",
        }
        try:
            from openai import AsyncOpenAI

            data_url = await self._image_url_to_data_url(image_url)
            client = AsyncOpenAI(
                base_url=getattr(self, "_openai_base_url", os.environ.get("LMSTUDIO_URL", LMSTUDIO_URL)),
                api_key=LMSTUDIO_API_KEY,
            )
            prompt = f"""Analyze this news image in the context of the article.

Return ONLY valid JSON:
{{
  "description": "Brief factual description",
  "objects": ["detected", "objects"],
  "sentiment": "positive/negative/neutral",
  "relevance": "high/medium/low"
}}

Article title: {article.get('title', '')}
Article context: {article.get('content', '')[:800]}"""
            response = await client.chat.completions.create(
                model=getattr(self, "_lmstudio_model", MODEL_NAME),
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {"type": "image_url", "image_url": {"url": data_url}},
                        ],
                    }
                ],
                max_tokens=500,
                temperature=0.2,
            )
            content = response.choices[0].message.content or ""
            parsed = _extract_json(content)
            if parsed:
                result_base.update({
                    "description": str(parsed.get("description", ""))[:1000],
                    "objects": parsed.get("objects", []) if isinstance(parsed.get("objects", []), list) else [],
                    "sentiment": self._normalize_label(parsed.get("sentiment"), {"positive", "negative", "neutral"}, "neutral"),
                    "relevance": self._normalize_label(parsed.get("relevance"), {"high", "medium", "low"}, "medium"),
                })
                return result_base
            description = _clean_model_text(content)
            if len(description) >= 20:
                result_base.update({
                    "description": description,
                    "relevance": "medium",
                })
                return result_base
            result_base["error"] = f"image analysis parse failed: {content[:160]}"
            return result_base
        except Exception as e:
            result_base["error"] = str(e)
            return result_base

    async def _image_url_to_data_url(self, image_url: str) -> str:
        import aiohttp

        headers = {"User-Agent": "Mozilla/5.0"}
        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.get(image_url, timeout=aiohttp.ClientTimeout(total=30)) as response:
                response.raise_for_status()
                content_type = response.headers.get("content-type", "image/jpeg").split(";", 1)[0]
                image_bytes = await response.read()
        encoded = base64.b64encode(image_bytes).decode("ascii")
        return f"data:{content_type};base64,{encoded}"

    def _normalize_llm_analysis(self, data: Dict[str, Any]) -> Dict[str, Any]:
        try:
            sentiment = int(data.get("sentiment", 0))
        except (TypeError, ValueError):
            sentiment = 0
        sentiment = max(-1, min(1, sentiment))
        label = data.get("sentiment_label")
        if label not in {"positive", "negative", "neutral"}:
            label = {1: "positive", 0: "neutral", -1: "negative"}[sentiment]
        return {
            "summary": str(data.get("summary", ""))[:1000],
            "sentiment": sentiment,
            "sentiment_label": label,
            "keywords": data.get("keywords", []) if isinstance(data.get("keywords", []), list) else [],
            "entities": data.get("entities", {}) if isinstance(data.get("entities", {}), dict) else {},
            "category": str(data.get("category", "other")),
            "relevance_to_topic": self._normalize_label(data.get("relevance_to_topic"), {"high", "medium", "low"}, "medium"),
        }

    def _fallback_llm_analysis(self, article: Dict[str, Any]) -> Dict[str, Any]:
        words = re.findall(r"[A-Za-z][A-Za-z0-9-]{4,}", article.get("content", ""))
        keywords = []
        seen = set()
        for word in words:
            lowered = word.lower()
            if lowered not in seen:
                seen.add(lowered)
                keywords.append(word)
            if len(keywords) >= 5:
                break
        return {
            "summary": (article.get("description") or article.get("content", ""))[:500],
            "sentiment": 0,
            "sentiment_label": "neutral",
            "keywords": keywords,
            "entities": {"countries": [], "organizations": [], "people": []},
            "category": "other",
            "relevance_to_topic": "medium",
        }

    def _normalize_label(self, value: Any, allowed: set[str], default: str) -> str:
        value = str(value or "").lower().strip()
        return value if value in allowed else default


    def _call_pipeline(self, prompt: str, max_tokens: int) -> str:
        outputs = self._pipeline(prompt, max_new_tokens=max_tokens)
        generated = outputs[0]["generated_text"]
        # Strip echo of the input prompt
        if generated.startswith(prompt):
            generated = generated[len(prompt):]
        return generated.strip()

    # ------------------------------------------------------------------
    # Agent decision methods
    # ------------------------------------------------------------------

    async def plan_next_action(self, state: AgentState) -> Dict[str, Any]:
        """
        Decide the next step: search, visit a URL, or mark complete.

        Returns:
            {"action": "search"|"visit"|"complete", "query"?: str, "url"?: str}
        """
        mode = state.get("mode", "surface")
        prompt = (
            _build_surface_plan_prompt(state)
            if mode == "surface"
            else _build_research_plan_prompt(state)
        )

        try:
            raw = await self._call_llm(prompt, max_tokens=256)
            result = _extract_json(raw)
            if result and "action" in result:
                print(f"[ModelHandler] Plan: {result}")
                return result
            print(f"[ModelHandler] Plan parse failed, raw='{raw[:200]}'")
        except Exception as e:
            print(f"[ModelHandler] plan_next_action error: {e}")

        # Safe fallback
        return {"action": "search", "query": state.get("query", state.get("topic", ""))}

    async def evaluate_confidence(self, state: AgentState) -> float:
        """
        Ask LLM to self-rate confidence on how complete the research is.

        Returns float [0.0, 1.0]
        """
        prompt = _build_evaluate_prompt(state)
        try:
            raw    = await self._call_llm(prompt, max_tokens=128)
            result = _extract_json(raw)
            if result and "confidence" in result:
                confidence = float(result["confidence"])
                confidence = max(0.0, min(1.0, confidence))
                print(f"[ModelHandler] Self-eval confidence: {confidence:.2f} — {result.get('reasoning','')}")
                return confidence
        except Exception as e:
            print(f"[ModelHandler] evaluate_confidence error: {e}")

        # Fallback: increase by 0.15/cycle
        return min(0.15 * state.get("cycle_count", 1), 0.95)

    async def synthesize_report(self, state: AgentState) -> Dict[str, Any]:
        """
        Create a structured final report from all collected data.

        Returns dict matching the pipeline's expected output format.
        """
        prompt = _build_synthesize_prompt(state)
        try:
            raw    = await self._call_llm(prompt, max_tokens=CUA_SYNTHESIS_MAX_TOKENS)
            result = _extract_json(raw)
            if result:
                print(f"[ModelHandler] Report synthesized ({len(str(result))} chars)")
                return result
            print(f"[ModelHandler] Synthesize parse failed, building fallback report")
        except Exception as e:
            print(f"[ModelHandler] synthesize_report error: {e}")

        # Fallback: raw collection dump
        mode = state.get("mode", "surface")
        if mode == "surface":
            return {
                "mode": "surface",
                "summary": "Agent surface search completed.",
                "article_count": len(state.get("collected_articles", [])),
                "articles": state.get("collected_articles", []),
            }
        else:
            return {
                "mode": "research",
                "topic": state.get("topic", ""),
                "executive_summary": "Research mission completed.",
                "findings": state.get("findings", []),
                "confidence_score": state.get("confidence", 0.0),
            }

    async def update_hypothesis(self, state: AgentState) -> str:
        """
        For research mode: refine the current hypothesis based on findings.

        Returns updated hypothesis string.
        """
        topic    = state.get("topic", "")
        findings = state.get("findings", [])
        old_hypo = state.get("current_hypothesis", "No hypothesis yet")

        findings_text = "\n".join(
            f"- {f.get('title','')}: {f.get('content','')[:400]}"
            for f in findings[-4:]
        )
        prompt = f"""You are a research analyst. Refine the working hypothesis.

Topic: {topic}
Current hypothesis: {old_hypo}
New evidence:
{findings_text}

Respond with ONE sentence that is the refined hypothesis. No JSON, no lists."""

        try:
            new_hypo = (await self._call_llm(prompt, max_tokens=80)).strip()
            if len(new_hypo) > 20:
                return new_hypo
        except Exception as e:
            print(f"[ModelHandler] hypothesis update error: {e}")

        return old_hypo
