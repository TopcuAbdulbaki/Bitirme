"""
Local Pipeline Runner
Runs Orchestrator + Crawler for basic testing without external dependencies.
"""
import asyncio
import subprocess
import sys
import os
import time
import signal
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent


def run_orchestrator():
    """Start the orchestrator in a subprocess."""
    print("🚀 Starting Orchestrator...")
    env = os.environ.copy()
    return subprocess.Popen(
        [sys.executable, "-m", "orchestrator.main"],
        cwd=str(PROJECT_ROOT),
        env=env,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == 'nt' else 0
    )


def run_crawler():
    """Start the crawler in distributed mode."""
    print("🕷️ Starting Crawler in distributed mode...")
    env = os.environ.copy()
    env['CRAWLER_MODE'] = 'distributed'
    
    return subprocess.Popen(
        [sys.executable, "FilteredCrawler.py"],
        cwd=str(PROJECT_ROOT / "crawler"),
        env=env,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == 'nt' else 0
    )


def main():
    print("=" * 60)
    print("LOCAL PIPELINE RUNNER")
    print("=" * 60)
    print("\nThis will start:")
    print("  1. Orchestrator (gRPC server)")
    print("  2. Crawler (sends news to Orchestrator)")
    print("\nPress Ctrl+C to stop all processes.\n")
    
    processes = []
    
    try:
        # Start Orchestrator
        orch_proc = run_orchestrator()
        processes.append(orch_proc)
        
        # Wait for Orchestrator to start
        time.sleep(3)
        
        # Check if Orchestrator is running
        if orch_proc.poll() is not None:
            print("❌ Orchestrator failed to start!")
            return
        
        print("✅ Orchestrator is running on port 50051\n")
        
        # Ask user if they want to start crawler
        print("Options:")
        print("  1. Start Crawler (will crawl news and send to Orchestrator)")
        print("  2. Keep Orchestrator running only (for manual testing)")
        print()
        
        choice = input("Enter choice (1/2): ").strip()
        
        if choice == "1":
            crawler_proc = run_crawler()
            processes.append(crawler_proc)
            print("\n✅ Crawler started! Monitoring...\n")
            
            # Wait for crawler to complete
            crawler_proc.wait()
            print("\n✅ Crawler finished!")
        else:
            print("\n📡 Orchestrator running. Use another terminal to test.")
            print("   Example: python test_system.py")
            print("\nPress Ctrl+C to stop.\n")
        
        # Keep running until interrupted
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n\n🛑 Stopping all processes...")
    finally:
        for proc in processes:
            if proc.poll() is None:
                if os.name == 'nt':
                    proc.send_signal(signal.CTRL_BREAK_EVENT)
                else:
                    proc.terminate()
                proc.wait(timeout=5)
        
        print("✅ All processes stopped.")


if __name__ == "__main__":
    main()
