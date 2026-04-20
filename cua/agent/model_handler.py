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
from cua.config import MODEL_MODE, MODEL_NAME, LMSTUDIO_URL, RESEARCH_CONFIDENCE_THRESHOLD


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

def _extract_json(text: str) -> Optional[Dict[str, Any]]:
    """Pull the first JSON object out of an LLM response."""
    text = text.strip()
    # Try direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # Try to find a JSON block
    match = re.search(r"\{[\s\S]*\}", text)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass
    return None


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
            # Bağlantı testi
            _raw_client = OpenAI(base_url=LMSTUDIO_URL, api_key="lm-studio")
            models = _raw_client.models.list()
            model_ids = [m.id for m in models.data]
            print(f"[ModelHandler] LM Studio connected. Models: {model_ids}")
            first_model = model_ids[0] if model_ids else "local-model"
            self._lmstudio_model = first_model

            # browser-use'un kendi dataclass ChatOpenAI'ı (provider+model native)
            self.llm = BrowserUseChatOpenAI(
                model=first_model,
                base_url=LMSTUDIO_URL,
                api_key="lm-studio",
                temperature=0.3,
            )
            print(f"[ModelHandler] browser-use ChatOpenAI hazır (model={first_model})")
        except Exception as e:
            print(f"[ModelHandler] LM Studio unavailable ({e}) — will retry at inference time")
            self.llm = None
            self._lmstudio_model = "local-model"


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
                max_new_tokens=1024,
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

    async def _call_llm(self, prompt: str, max_tokens: int = 512) -> str:
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
            raw    = await self._call_llm(prompt, max_tokens=1024)
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
