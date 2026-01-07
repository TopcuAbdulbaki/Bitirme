import asyncio
import os
import sys
import json
from datetime import datetime

try:
    import asyncpg
except ImportError:
    print("Error: 'asyncpg' is required. Run: pip install asyncpg")
    sys.exit(1)

# Configuration from env or defaults
HOST = os.getenv("POSTGRES_HOST", "localhost")
PORT = os.getenv("POSTGRES_PORT", "5432")
USER = os.getenv("POSTGRES_USER", "postgres")
PASSWORD = os.getenv("POSTGRES_PASSWORD", "postgres")
DB_NAME = os.getenv("POSTGRES_DB", "bitirme_db")

async def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python check_db.py list [limit]")
        print("  python check_db.py get <news_id>")
        print("  python check_db.py stats")
        return

    command = sys.argv[1]
    
    try:
        conn = await asyncpg.connect(
            host=HOST, port=PORT, user=USER, password=PASSWORD, database=DB_NAME
        )
    except Exception as e:
        print(f"Connection failed: {e}")
        print(f"Ensure DB is running at {HOST}:{PORT}")
        return

    try:
        if command == "list":
            limit = int(sys.argv[2]) if len(sys.argv) > 2 else 5
            rows = await conn.fetch("""
                SELECT n.news_id, n.url, n.source, n.scraped_at, 
                       n.vlm_processed, n.llm_processed,
                       l.summary
                FROM news n
                LEFT JOIN llm_analysis l ON n.news_id = l.news_id
                ORDER BY n.stored_at DESC
                LIMIT $1
            """, limit)
            
            print(f"\nLast {limit} News Items:")
            print("-" * 80)
            print(f"{'ID':<10} | {'Source':<15} | {'VLM':<4} | {'LLM':<4} | {'Summary'}")
            print("-" * 80)
            for row in rows:
                summary = (row['summary'] or "")[:40] + "..." if row['summary'] else "-"
                print(f"{row['news_id'][:8]:<10} | {row['source'][:15]:<15} | {str(row['vlm_processed']):<4} | {str(row['llm_processed']):<4} | {summary}")
            print("-" * 80)

        elif command == "get":
            if len(sys.argv) < 3:
                print("Error: Missing news_id")
                return
            news_id = sys.argv[2]
            
            # Fetch full details
            row = await conn.fetchrow("SELECT * FROM news WHERE news_id = $1", news_id)
            if not row:
                print("News item not found.")
                return
                
            print(f"\n=== NEWS: {news_id} ===")
            print(f"URL: {row['url']}")
            print(f"Source: {row['source']}")
            print(f"Date: {row['scraped_at']}")
            print(f"\n[Content Preview]:\n{row['content'][:200]}...\n")
            
            # VLM
            vlm_rows = await conn.fetch("SELECT * FROM vlm_analysis WHERE news_id = $1", news_id)
            if vlm_rows:
                print("\n--- VLM Analysis (Images) ---")
                for v in vlm_rows:
                    print(f"- Image: {v['description']}")
                    print(f"  Objects: {v['objects']}")
                    print(f"  Sentiment: {v['sentiment']}")
            
            # LLM
            llm_row = await conn.fetchrow("SELECT * FROM llm_analysis WHERE news_id = $1", news_id)
            if llm_row:
                print("\n--- LLM Analysis (Text) ---")
                print(f"Summary: {llm_row['summary']}")
                print(f"Sentiment: {llm_row['sentiment']} ({llm_row['sentiment_label']})")
                print(f"Keywords: {llm_row['keywords']}")
                print(f"Category: {llm_row['category']}")

        elif command == "stats":
            total = await conn.fetchval("SELECT COUNT(*) FROM news")
            vlm_count = await conn.fetchval("SELECT COUNT(*) FROM news WHERE vlm_processed = TRUE")
            llm_count = await conn.fetchval("SELECT COUNT(*) FROM news WHERE llm_processed = TRUE")
            
            print(f"\n=== System Statistics ===")
            print(f"Total News: {total}")
            print(f"VLM Processed: {vlm_count}")
            print(f"LLM Processed: {llm_count}")
            
    finally:
        await conn.close()

if __name__ == "__main__":
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
