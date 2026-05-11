"""
PostgreSQL Manager Service
Handles database operations with asyncpg.
"""
import json
import hashlib
from datetime import datetime
from typing import Optional, List
from dataclasses import dataclass, asdict

# Note: asyncpg requires running in async context
# For sync operations, use psycopg2 as fallback
try:
    import asyncpg
    ASYNCPG_AVAILABLE = True
except ImportError:
    ASYNCPG_AVAILABLE = False

# Embedding support
try:
    from .embedding_manager import EmbeddingManager
    EMBEDDING_AVAILABLE = True
except ImportError:
    EMBEDDING_AVAILABLE = False

from ..config import (
    POSTGRES_HOST, POSTGRES_PORT, POSTGRES_DB,
    POSTGRES_USER, POSTGRES_PASSWORD
)


@dataclass
class NewsItem:
    """News item data structure."""
    news_id: str
    url: str
    source: str
    country: str
    keyword_found: str
    scraped_at: datetime
    content: str
    media: dict
    stored_at: Optional[datetime] = None
    vlm_processed: bool = False
    llm_processed: bool = False
    
    def to_dict(self) -> dict:
        d = asdict(self)
        d['scraped_at'] = self.scraped_at.isoformat() if self.scraped_at else None
        d['stored_at'] = self.stored_at.isoformat() if self.stored_at else None
        return d


class PostgresManager:
    """
    Manager for PostgreSQL database operations.
    Uses asyncpg for async operations.
    """
    
    def __init__(self, enable_embeddings: bool = True):
        self._pool = None
        self._conn_string = f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
        
        # Initialize embedding manager
        self._embedding_manager = None
        if enable_embeddings and EMBEDDING_AVAILABLE:
            self._embedding_manager = EmbeddingManager(mode='local')
            print("[PostgreSQL] Embedding support enabled")
    
    @staticmethod
    def generate_news_id(url: str) -> str:
        """Generate unique news ID from URL (16 char hash)."""
        return hashlib.sha256(url.encode()).hexdigest()[:16]
    
    async def connect(self) -> bool:
        """Connect to PostgreSQL and create pool."""
        if not ASYNCPG_AVAILABLE:
            print("[PostgreSQL] asyncpg not installed")
            return False
            
        try:
            self._pool = await asyncpg.create_pool(
                host=POSTGRES_HOST,
                port=POSTGRES_PORT,
                database=POSTGRES_DB,
                user=POSTGRES_USER,
                password=POSTGRES_PASSWORD,
                min_size=2,
                max_size=10
            )
            print(f"[PostgreSQL] Connected to {POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}")
            
            # Initialize tables
            await self._init_tables()
            
            return True
            
        except Exception as e:
            print(f"[PostgreSQL] Connection failed: {e}")
            return False
    
    async def _init_tables(self):
        """Create tables if they don't exist."""
        async with self._pool.acquire() as conn:
            # Enable pgvector extension
            await conn.execute("""
                CREATE EXTENSION IF NOT EXISTS vector;
            """)
            
            # News table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS news (
                    news_id VARCHAR(16) PRIMARY KEY,
                    url TEXT NOT NULL UNIQUE,
                    source VARCHAR(100),
                    country VARCHAR(50),
                    keyword_found VARCHAR(100),
                    scraped_at TIMESTAMP,
                    stored_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    content TEXT,
                    media JSONB,
                    vlm_processed BOOLEAN DEFAULT FALSE,
                    llm_processed BOOLEAN DEFAULT FALSE,
                    completed_at TIMESTAMP,
                    content_embedding vector(1024)
                );
                
                CREATE INDEX IF NOT EXISTS idx_news_url ON news(url);
                CREATE INDEX IF NOT EXISTS idx_news_vlm ON news(vlm_processed);
                CREATE INDEX IF NOT EXISTS idx_news_llm ON news(llm_processed);
            """)
            
            # Add CUA-related columns to news table
            await conn.execute("""
                ALTER TABLE news ADD COLUMN IF NOT EXISTS source_type VARCHAR(20) DEFAULT 'crawler';
                ALTER TABLE news ADD COLUMN IF NOT EXISTS mission_id VARCHAR(64);
            """)
            
            # VLM analysis table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS vlm_analysis (
                    id SERIAL PRIMARY KEY,
                    news_id VARCHAR(16) REFERENCES news(news_id) ON DELETE CASCADE,
                    image_minio_path TEXT,
                    description TEXT,
                    objects TEXT[],
                    sentiment VARCHAR(20),
                    relevance VARCHAR(20),
                    analyzed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                
                CREATE INDEX IF NOT EXISTS idx_vlm_news_id ON vlm_analysis(news_id);
            """)
            
            # LLM analysis table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS llm_analysis (
                    news_id VARCHAR(16) PRIMARY KEY REFERENCES news(news_id) ON DELETE CASCADE,
                    summary TEXT,
                    sentiment INTEGER CHECK (sentiment IN (-1, 0, 1)),
                    sentiment_label VARCHAR(20),
                    keywords TEXT[],
                    entities JSONB,
                    category VARCHAR(50),
                    relevance_to_topic VARCHAR(20),
                    analyzed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            
            # Research missions table (CUA)
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS research_missions (
                    mission_id VARCHAR(64) PRIMARY KEY,
                    topic TEXT NOT NULL,
                    status VARCHAR(20) DEFAULT 'in_progress',
                    final_report_json JSONB,
                    graph_state_json JSONB,
                    findings_count INTEGER DEFAULT 0,
                    confidence_score FLOAT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    completed_at TIMESTAMP
                );
                
                CREATE INDEX IF NOT EXISTS idx_research_status ON research_missions(status);
                CREATE INDEX IF NOT EXISTS idx_news_mission ON news(mission_id);
            """)
            
            print("[PostgreSQL] Tables initialized")
    
    async def insert_news(self, news_data: dict) -> tuple[str, bool]:
        """
        Insert news item into database.
        
        Returns:
            (news_id, is_duplicate)
        """
        url = news_data.get('url', '')
        news_id = self.generate_news_id(url)
        
        async with self._pool.acquire() as conn:
            # Check for duplicate
            existing = await conn.fetchval(
                "SELECT news_id FROM news WHERE url = $1",
                url
            )
            
            if existing:
                print(f"[PostgreSQL] Duplicate skipped: {news_id}")
                return existing, True
            
            # Parse datetime
            scraped_at = news_data.get('scraped_at')
            if isinstance(scraped_at, str):
                scraped_at = datetime.fromisoformat(scraped_at)
            
            # Insert
            await conn.execute("""
                INSERT INTO news (
                    news_id, url, source, country, keyword_found,
                    scraped_at, content, media, source_type, mission_id
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
            """,
                news_id,
                url,
                news_data.get('source'),
                news_data.get('country'),
                news_data.get('keyword_found'),
                scraped_at,
                news_data.get('content'),
                json.dumps(news_data.get('media', {})),
                news_data.get('source_type', 'crawler'),
                news_data.get('mission_id')
            )
            
            # Generate and store embedding (async in background)
            content = news_data.get('content', '')
            if content and self._embedding_manager:
                await self._store_embedding(news_id, content)
            
            print(f"[PostgreSQL] Inserted: {news_id}")
            return news_id, False
    
    async def get_unprocessed(self, limit: int = 10) -> List[dict]:
        """Get news items not yet processed by VLM."""
        async with self._pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT news_id, url, source, country, keyword_found,
                       scraped_at, content, media
                FROM news
                WHERE vlm_processed = FALSE
                ORDER BY stored_at
                LIMIT $1
            """, limit)
            
            return [dict(row) for row in rows]
    
    async def get_vlm_complete(self, limit: int = 10) -> List[dict]:
        """Get news items processed by VLM but not LLM."""
        async with self._pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT n.news_id, n.url, n.source, n.country,
                       n.content, n.media, 
                       json_agg(v.*) as vlm_results
                FROM news n
                LEFT JOIN vlm_analysis v ON n.news_id = v.news_id
                WHERE n.vlm_processed = TRUE AND n.llm_processed = FALSE
                GROUP BY n.news_id
                ORDER BY n.stored_at
                LIMIT $1
            """, limit)
            
            return [dict(row) for row in rows]
    
    async def mark_vlm_processed(self, news_id: str):
        """Mark news as processed by VLM."""
        async with self._pool.acquire() as conn:
            await conn.execute(
                "UPDATE news SET vlm_processed = TRUE WHERE news_id = $1",
                news_id
            )
    
    async def mark_llm_processed(self, news_id: str):
        """Mark news as processed by LLM."""
        async with self._pool.acquire() as conn:
            await conn.execute("""
                UPDATE news 
                SET llm_processed = TRUE, completed_at = CURRENT_TIMESTAMP 
                WHERE news_id = $1
            """, news_id)
    
    async def save_vlm_analysis(self, news_id: str, analysis: dict):
        """Save VLM analysis results."""
        async with self._pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO vlm_analysis (
                    news_id, image_minio_path, description, objects, sentiment, relevance
                ) VALUES ($1, $2, $3, $4, $5, $6)
            """,
                news_id,
                analysis.get('minio_path') or analysis.get('url') or analysis.get('original_url'),
                analysis.get('description'),
                analysis.get('objects', []),
                analysis.get('sentiment'),
                analysis.get('relevance')
            )
    
    async def save_llm_analysis(self, news_id: str, analysis: dict):
        """Save LLM analysis results."""
        async with self._pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO llm_analysis (
                    news_id, summary, sentiment, sentiment_label,
                    keywords, entities, category, relevance_to_topic
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                ON CONFLICT (news_id) DO UPDATE SET
                    summary = EXCLUDED.summary,
                    sentiment = EXCLUDED.sentiment,
                    sentiment_label = EXCLUDED.sentiment_label,
                    keywords = EXCLUDED.keywords,
                    entities = EXCLUDED.entities,
                    category = EXCLUDED.category,
                    relevance_to_topic = EXCLUDED.relevance_to_topic,
                    analyzed_at = CURRENT_TIMESTAMP
            """,
                news_id,
                analysis.get('summary'),
                analysis.get('sentiment'),
                analysis.get('sentiment_label'),
                analysis.get('keywords', []),
                json.dumps(analysis.get('entities', {})),
                analysis.get('category'),
                analysis.get('relevance_to_topic')
            )
    
    async def get_news_by_id(self, news_id: str) -> Optional[dict]:
        """Get complete news item with all analysis."""
        async with self._pool.acquire() as conn:
            news = await conn.fetchrow(
                "SELECT * FROM news WHERE news_id = $1",
                news_id
            )
            if not news:
                return None
            
            result = dict(news)
            
            # Get VLM analysis
            vlm = await conn.fetch(
                "SELECT * FROM vlm_analysis WHERE news_id = $1",
                news_id
            )
            result['vlm_analysis'] = [dict(v) for v in vlm]
            
            # Get LLM analysis
            llm = await conn.fetchrow(
                "SELECT * FROM llm_analysis WHERE news_id = $1",
                news_id
            )
            if llm:
                result['llm_analysis'] = dict(llm)
            
            return result
    
    async def _store_embedding(self, news_id: str, content: str):
        """Generate and store embedding for news content."""
        try:
            # Generate embedding (synchronous)
            embedding = self._embedding_manager.encode(content)
            
            if embedding:
                async with self._pool.acquire() as conn:
                    # Store as pgvector
                    await conn.execute(
                        "UPDATE news SET content_embedding = $1 WHERE news_id = $2",
                        str(embedding),  # pgvector accepts string format
                        news_id
                    )
                print(f"[PostgreSQL] Embedding stored for: {news_id}")
        except Exception as e:
            print(f"[PostgreSQL] Embedding error: {e}")
    
    async def search_similar(self, query: str, limit: int = 10) -> List[dict]:
        """
        Semantic search using vector similarity.
        
        Args:
            query: Search query text
            limit: Max results to return
            
        Returns:
            List of similar news items with similarity scores
        """
        if not self._embedding_manager:
            print("[PostgreSQL] Embeddings not enabled")
            return []
        
        # Generate query embedding
        query_embedding = self._embedding_manager.encode(query)
        if not query_embedding:
            return []
        
        async with self._pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT news_id, url, source, content,
                       1 - (content_embedding <=> $1::vector) AS similarity
                FROM news
                WHERE content_embedding IS NOT NULL
                ORDER BY content_embedding <=> $1::vector
                LIMIT $2
            """, str(query_embedding), limit)
            
            return [dict(row) for row in rows]
    
    async def get_embedding_stats(self) -> dict:
        """Get statistics about embeddings."""
        async with self._pool.acquire() as conn:
            total = await conn.fetchval("SELECT COUNT(*) FROM news")
            with_embedding = await conn.fetchval(
                "SELECT COUNT(*) FROM news WHERE content_embedding IS NOT NULL"
            )
            return {
                'total_news': total,
                'with_embedding': with_embedding,
                'embedding_coverage': f"{(with_embedding/total*100):.1f}%" if total > 0 else "0%"
            }
    
    async def insert_research_mission(self, mission_data: dict) -> str:
        """
        Create a new research mission record.
        
        Args:
            mission_data: Dictionary containing mission details
                - topic (str): Research topic
                - status (str, optional): Mission status (default: 'in_progress')
                - mission_id (str, optional): Mission ID (generated if not provided)
                
        Returns:
            mission_id: The ID of the created research mission
        """
        mission_id = mission_data.get('mission_id') or hashlib.sha256(
            mission_data.get('topic', '').encode()
        ).hexdigest()[:16]
        
        async with self._pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO research_missions (
                    mission_id, topic, status
                ) VALUES ($1, $2, $3)
                ON CONFLICT (mission_id) DO UPDATE SET
                    topic = EXCLUDED.topic,
                    status = EXCLUDED.status
            """,
                mission_id,
                mission_data.get('topic'),
                mission_data.get('status', 'in_progress')
            )
            
            print(f"[PostgreSQL] Research mission created: {mission_id}")
            return mission_id
    
    async def complete_research_mission(self, mission_id: str, report: dict, state: dict):
        """
        Finalize a research mission with report and graph state.
        
        Args:
            mission_id: The mission ID to complete
            report: Final research report as dictionary
            state: Final graph state as dictionary
        """
        async with self._pool.acquire() as conn:
            await conn.execute("""
                UPDATE research_missions
                SET 
                    final_report_json = $1,
                    graph_state_json = $2,
                    completed_at = CURRENT_TIMESTAMP,
                    status = 'completed',
                    findings_count = COALESCE($3, findings_count)
                WHERE mission_id = $4
            """,
                json.dumps(report),
                json.dumps(state),
                len(report.get('findings', [])) if isinstance(report.get('findings'), list) else None,
                mission_id
            )
            
            print(f"[PostgreSQL] Research mission completed: {mission_id}")

    async def close(self):
        """Close connection pool."""
        if self._pool:
            await self._pool.close()
            print("[PostgreSQL] Connection closed")

