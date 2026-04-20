"""
browser-use minimal test — LangGraph olmadan sadece Agent.run() test eder.

Çalıştır:
    python cua/test_browser_only.py
"""
import asyncio
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))


async def main():
    print("=== browser-use minimal test ===")

    # 1. browser-use'un kendi OpenAI wrapper'ını kullan — langchain değil!
    print("[1] LLM oluşturuluyor (browser-use.ChatOpenAI)...")
    try:
        from browser_use.llm.openai.chat import ChatOpenAI
        llm = ChatOpenAI(
            model="local-model",
            base_url="http://localhost:1234/v1",
            api_key="lm-studio",
            temperature=0.1,
            timeout=300,
            dont_force_structured_output=True,
            max_completion_tokens=1024,
        )
        print(f"    ✅ LLM hazır: provider={llm.provider}, model={llm.model}")
    except Exception as e:
        print(f"    ❌ LLM hatası: {e}")
        import traceback; traceback.print_exc()
        return

    # 2. browser-use import
    print("[2] browser-use Agent import ediliyor...")
    try:
        from browser_use import Agent
        print("    ✅ OK")
    except ImportError as e:
        print(f"    ❌ Import hatası: {e}")
        return

    # 3. Agent çalıştır
    print("[3] Agent oluşturuluyor ve çalıştırılıyor...")
    print("    (Tarayıcı penceresi açılmalı!)")
    try:
        agent = Agent(
            task=(
                "Go to google.com and search for 'Türkiye haberleri'.\n"
                "Return the first 3 result URLs as a simple list."
            ),
            llm=llm,
            max_steps=8,
        )
        print("    Agent oluşturuldu, agent.run() çağrılıyor...")
        result = await agent.run()
        output = result.final_result()
        print(f"\n=== SONUÇ ===\n{output}")
    except Exception as e:
        print(f"    ❌ Agent hatası: {type(e).__name__}: {e}")
        import traceback; traceback.print_exc()


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    asyncio.run(main())
