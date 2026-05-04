"""
CUA Standalone Test — Orchestrator/RabbitMQ olmadan direkt çalıştır.

Kullanım:
    python -m cua.test_local
    python -m cua.test_local --mode surface --query "Türkiye haberleri"
    python -m cua.test_local --mode research --topic "Türkiye ekonomisi 2026"
    python -m cua.test_local --mode surface --max-articles 3 --headless false

Gereksinimler:
    - LM Studio çalışıyor olmalı (localhost:1234)
    - `pip install browser-use playwright && playwright install chromium`
    - Orchestrator / RabbitMQ GEREKMEZ
"""
import asyncio
import argparse
import json
import sys
import os
from functools import wraps

# Proje kökünü path'e ekle (python -m cua.test_local ile çalıştırırken gerekebilir)
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from cua.agent.browser_tool import BrowserTool
from cua.agent.model_handler import CUAModelHandler
from cua.agent.graph import run_agent


def parse_args():
    p = argparse.ArgumentParser(description="CUA Standalone Test")
    p.add_argument("--mode",         default="surface",
                   choices=["surface", "research"],
                   help="surface = haber topla, research = derin araştırma")
    p.add_argument("--query",        default="Türkiye haberleri",
                   help="Surface mod arama terimi")
    p.add_argument("--topic",        default="",
                   help="Research mod konusu (boşsa query kullanılır)")
    p.add_argument("--max-articles", type=int, default=5,
                   help="Surface modda toplanacak max makale sayısı")
    p.add_argument("--max-cycles",   type=int, default=8,
                   help="Maksimum döngü sayısı")
    p.add_argument("--headless",     default="true",
                   help="true/false — tarayıcı görünür olsun mu?")
    p.add_argument("--engine",       default="duckduckgo",
                   choices=["google", "duckduckgo", "bing"],
                   help="Arama motoru (duckduckgo önerilen, CAPTCHA yok)")
    p.add_argument("--model-mode",   default="local",
                   choices=["local", "production"],
                   help="local = LM Studio, production = Qwen transformers")
    p.add_argument("--lmstudio-url", default="",
                   help="LM Studio URL (boşsa config.py'den gelir)")
    p.add_argument("--output",       default="",
                   help="Sonucu kaydet: output.json gibi")
    return p.parse_args()


async def main():
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
        
        # Kaba Kuvvet Çözümü: httpx / asyncio Proactor Event Loop Closed hatasını engeller.
        try:
            from asyncio.proactor_events import _ProactorBasePipeTransport
            def silence_event_loop_closed(func):
                @wraps(func)
                def wrapper(self, *args, **kwargs):
                    try:
                        return func(self, *args, **kwargs)
                    except RuntimeError as e:
                        if str(e) != 'Event loop is closed':
                            raise
                return wrapper
            _ProactorBasePipeTransport.__del__ = silence_event_loop_closed(_ProactorBasePipeTransport.__del__)
        except ImportError:
            pass

    args = parse_args()

    headless = args.headless.lower() != "false"
    mode     = args.mode
    query    = args.query
    topic    = args.topic or query

    if mode == "research":
        print("[Test] Research mode şimdilik askıda. TODO.md içindeki not tamamlanınca yeniden açılacak.")
        sys.exit(2)

    print("=" * 60)
    print("CUA STANDALONE TEST")
    print("=" * 60)
    print(f"  Mod:            {mode}")
    print(f"  Query/Topic:    {query if mode == 'surface' else topic}")
    print(f"  Max makale:     {args.max_articles}")
    print(f"  Max döngü:      {args.max_cycles}")
    print(f"  Tarayıcı:       {'headless' if headless else 'GÖRÜNÜR'}")
    print(f"  Arama motoru:   {args.engine}")
    print(f"  Model modu:     {args.model_mode}")
    print("=" * 60)

    # Env override (LM Studio URL)
    if args.lmstudio_url:
        import os
        os.environ["LMSTUDIO_URL"] = args.lmstudio_url

    # Config override
    import cua.config as cfg
    cfg.MAX_RESEARCH_CYCLES = args.max_cycles
    cfg.DEFAULT_SEARCH_ENGINE = args.engine

    # ── Model Handler başlat ─────────────────────────────────────────
    print("\n[Test] Model handler başlatılıyor...")
    try:
        model = CUAModelHandler(mode=args.model_mode)
    except Exception as e:
        print(f"[Test] [FAIL] Model handler başlatılamadı: {e}")
        print("       LM Studio'nun localhost:1234'te çalıştığından emin ol")
        sys.exit(1)

    # ── Browser başlat ───────────────────────────────────────────────
    print("[Test] Tarayıcı başlatılıyor...")
    # LLM'i browser-use Agent'a ver (LM Studio OpenAI-compat client)
    llm_for_browser = model.llm  # ChatOpenAI nesnesi
    
    try:
        async with BrowserTool(llm=llm_for_browser, headless=headless) as browser:
            print("[Test] [OK] Tarayıcı hazır")

            # ── Agent çalıştır ───────────────────────────────────────────────
            print(f"\n[Test] Agent başlatılıyor: mode={mode}")
            print("-" * 60)

            task_data = {
                "mode":  mode,
                "query": query,
                "topic": topic,
                "params": {
                    "max_articles": args.max_articles,
                    "max_searches": args.max_articles * 2,
                    "max_cycles": args.max_cycles,
                },
            }

            try:
                report = await run_agent(task_data, browser, model)
            except Exception as e:
                print(f"\n[Test] [FAIL] Agent hatası: {e}")
                import traceback
                traceback.print_exc()
                sys.exit(1)

            # ── Sonucu göster ────────────────────────────────────────────────
            print("\n" + "=" * 60)
            print("SONUÇ")
            print("=" * 60)
            print(f"Status: {report.get('status', '?')}")

            if mode == "surface":
                articles = report.get("articles", report.get("collected_articles", []))
                print(f"Toplanan makale: {len(articles)}")
                print(f"Özet: {report.get('summary', '-')}")
                print("\nMakaleler:")
                for i, a in enumerate(articles, 1):
                    print(f"  {i}. [{a.get('source','')}] {a.get('title','')[:80]}")
                    print(f"     URL: {a.get('url','')}")
                    print(f"     İçerik ({len(a.get('content',''))} karakter)")
            else:
                print(f"Konu:       {report.get('topic', topic)}")
                print(f"Confidence: {report.get('confidence_score', '?')}")
                print(f"\nYönetici özeti:\n{report.get('executive_summary', '-')}")
                print("\nTemel bulgular:")
                for f in report.get("key_findings", []):
                    print(f"  • {f}")

            # ── Dosyaya kaydet ───────────────────────────────────────────────
            output_file = args.output or f"cua_test_result_{mode}.json"
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
            print(f"\n[OK] Sonuç kaydedildi: {output_file}")

    except Exception as e:
        print(f"\n[Test] [FAIL] Beklenmeyen Hata: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
