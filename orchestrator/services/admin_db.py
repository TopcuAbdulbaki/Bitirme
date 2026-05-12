"""Read-only PostgreSQL access for the local orchestrator admin panel."""
from __future__ import annotations

import asyncio
import os
import re
from collections import defaultdict
from typing import Any

try:
    import asyncpg
except ImportError:  # pragma: no cover - handled at runtime
    asyncpg = None

from orchestrator.config import (
    ADMIN_DB_HOST,
    ADMIN_DB_PORT,
    ADMIN_DB_NAME,
    ADMIN_DB_USER,
    ADMIN_DB_PASSWORD,
)

try:
    from db.services.embedding_manager import EmbeddingManager
except ImportError:  # pragma: no cover - optional runtime path
    EmbeddingManager = None


def _safe_excerpt(value: str | None, limit: int = 280) -> str:
    text = re.sub(r"\s+", " ", value or "").strip()
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."


class AdminDatabase:
    """Small, failure-tolerant read-only DB client for the ops panel."""

    def __init__(self):
        self._pool = None
        self._last_error = ""
        self._embedding_mode = os.getenv("ORCHESTRATOR_SEARCH_EMBEDDING_MODE", "disabled").lower()
        self._embedding_api_base = os.getenv("EMBEDDING_API_URL")
        self._embedder = None
        self._embedding_error = ""
        if self._embedding_mode in {"local", "api"} and EmbeddingManager is not None:
            try:
                self._embedder = EmbeddingManager(
                    mode=self._embedding_mode,
                    api_base=self._embedding_api_base,
                )
            except Exception as exc:
                self._embedding_error = str(exc)
        elif self._embedding_mode in {"local", "api"}:
            self._embedding_error = "db embedding manager dependencies are unavailable"

    @property
    def configured(self) -> bool:
        return bool(ADMIN_DB_HOST)

    @property
    def connected(self) -> bool:
        return self._pool is not None

    @property
    def last_error(self) -> str:
        return self._last_error

    async def connect(self) -> bool:
        if self._pool:
            return True
        if not self.configured:
            self._last_error = "panel DB host is not configured"
            return False
        if asyncpg is None:
            self._last_error = "asyncpg is not installed"
            return False
        try:
            self._pool = await asyncpg.create_pool(
                host=ADMIN_DB_HOST,
                port=ADMIN_DB_PORT,
                database=ADMIN_DB_NAME,
                user=ADMIN_DB_USER,
                password=ADMIN_DB_PASSWORD,
                min_size=1,
                max_size=3,
                command_timeout=15,
            )
            self._last_error = ""
            return True
        except Exception as exc:
            self._last_error = str(exc)
            self._pool = None
            return False

    async def close(self):
        if self._pool:
            await self._pool.close()
            self._pool = None

    async def ensure_connected(self) -> bool:
        return self.connected or await self.connect()

    async def health(self) -> dict[str, Any]:
        available = await self.ensure_connected()
        if not available:
            return {
                "configured": self.configured,
                "connected": False,
                "error": self._last_error,
            }
        try:
            async with self._pool.acquire() as conn:
                await conn.fetchval("SELECT 1")
            return {
                "configured": True,
                "connected": True,
                "error": "",
                "vector_search": self._vector_status(),
            }
        except Exception as exc:
            self._last_error = str(exc)
            return {
                "configured": True,
                "connected": False,
                "error": self._last_error,
                "vector_search": self._vector_status(),
            }

    def _vector_status(self) -> dict[str, Any]:
        return {
            "enabled": self._embedder is not None,
            "mode": self._embedding_mode,
            "error": self._embedding_error,
        }

    async def _query_embedding(self, query: str) -> list[float] | None:
        if not self._embedder:
            return None
        try:
            if self._embedding_mode == "api":
                return await self._embedder.encode_async(query)
            return await asyncio.to_thread(self._embedder.encode, query)
        except Exception as exc:
            self._embedding_error = str(exc)
            return None

    async def stats(self) -> dict[str, Any]:
        if not await self.ensure_connected():
            return {"available": False, "error": self._last_error}
        try:
            async with self._pool.acquire() as conn:
                row = await conn.fetchrow(
                    """
                    SELECT
                        COUNT(*)::int AS total_news,
                        COUNT(*) FILTER (WHERE content_embedding IS NOT NULL)::int AS with_embedding,
                        COUNT(*) FILTER (WHERE vlm_processed = FALSE)::int AS pending_vlm,
                        COUNT(*) FILTER (
                            WHERE vlm_processed = TRUE AND llm_processed = FALSE
                        )::int AS pending_llm
                    FROM news
                    """
                )
                missions = await conn.fetch(
                    """
                    SELECT status, COUNT(*)::int AS count
                    FROM research_missions
                    GROUP BY status
                    ORDER BY status
                    """
                )
            total_news = row["total_news"] or 0
            with_embedding = row["with_embedding"] or 0
            coverage = round((with_embedding / total_news) * 100, 1) if total_news else 0.0
            return {
                "available": True,
                "total_news": total_news,
                "with_embedding": with_embedding,
                "embedding_coverage": coverage,
                "pending_vlm": row["pending_vlm"] or 0,
                "pending_llm": row["pending_llm"] or 0,
                "missions_by_status": {m["status"]: m["count"] for m in missions},
            }
        except Exception as exc:
            self._last_error = str(exc)
            return {"available": False, "error": self._last_error}

    async def search_news(self, query: str, limit: int = 12) -> dict[str, Any]:
        query = (query or "").strip()
        if not query:
            return {"available": True, "query": "", "results": []}
        if not await self.ensure_connected():
            return {"available": False, "query": query, "error": self._last_error, "results": []}

        try:
            async with self._pool.acquire() as conn:
                text_rows = await conn.fetch(
                    """
                    SELECT
                        n.news_id,
                        n.url,
                        n.source,
                        n.country,
                        n.keyword_found,
                        n.content,
                        l.summary,
                        ts_rank_cd(
                            to_tsvector('simple', coalesce(n.content, '') || ' ' || coalesce(l.summary, '')),
                            plainto_tsquery('simple', $1)
                        ) AS text_rank
                    FROM news n
                    LEFT JOIN llm_analysis l ON l.news_id = n.news_id
                    WHERE to_tsvector('simple', coalesce(n.content, '') || ' ' || coalesce(l.summary, ''))
                          @@ plainto_tsquery('simple', $1)
                       OR n.source ILIKE '%' || $1 || '%'
                       OR n.keyword_found ILIKE '%' || $1 || '%'
                    ORDER BY text_rank DESC NULLS LAST, n.stored_at DESC
                    LIMIT $2
                    """,
                    query,
                    limit,
                )

                vector_rows = []
                query_embedding = await self._query_embedding(query)
                if query_embedding:
                    vector_rows = await conn.fetch(
                        """
                        SELECT
                            n.news_id,
                            n.url,
                            n.source,
                            n.country,
                            n.keyword_found,
                            n.content,
                            l.summary,
                            1 - (n.content_embedding <=> $1::vector) AS vector_rank
                        FROM news n
                        LEFT JOIN llm_analysis l ON l.news_id = n.news_id
                        WHERE n.content_embedding IS NOT NULL
                        ORDER BY n.content_embedding <=> $1::vector
                        LIMIT $2
                        """,
                        str(query_embedding),
                        limit,
                    )

            merged = defaultdict(lambda: {"text_rank": 0.0, "vector_rank": 0.0})
            for row in text_rows:
                item = merged[row["news_id"]]
                item.update(dict(row))
                item["text_rank"] = float(row["text_rank"] or 0.0)
            for row in vector_rows:
                item = merged[row["news_id"]]
                item.update(dict(row))
                item["vector_rank"] = float(row["vector_rank"] or 0.0)

            results = []
            for news_id, item in merged.items():
                text_rank = float(item.get("text_rank") or 0.0)
                vector_rank = float(item.get("vector_rank") or 0.0)
                combined_score = text_rank + max(vector_rank, 0.0)
                results.append(
                    {
                        "news_id": news_id,
                        "url": item.get("url"),
                        "source": item.get("source"),
                        "country": item.get("country"),
                        "keyword_found": item.get("keyword_found"),
                        "excerpt": _safe_excerpt(item.get("content")),
                        "summary": _safe_excerpt(item.get("summary"), 220),
                        "text_score": round(text_rank, 4),
                        "vector_score": round(vector_rank, 4),
                        "combined_score": round(combined_score, 4),
                    }
                )
            results.sort(key=lambda row: row["combined_score"], reverse=True)
            return {
                "available": True,
                "query": query,
                "results": results[:limit],
                "vector_search": self._vector_status(),
            }
        except Exception as exc:
            self._last_error = str(exc)
            return {"available": False, "query": query, "error": self._last_error, "results": []}

    async def list_missions(self, limit: int = 20) -> dict[str, Any]:
        if not await self.ensure_connected():
            return {"available": False, "error": self._last_error, "missions": []}
        try:
            async with self._pool.acquire() as conn:
                rows = await conn.fetch(
                    """
                    SELECT mission_id, topic, status, findings_count, confidence_score,
                           created_at, completed_at
                    FROM research_missions
                    ORDER BY created_at DESC
                    LIMIT $1
                    """,
                    limit,
                )
            return {
                "available": True,
                "missions": [
                    {
                        **dict(row),
                        "created_at": row["created_at"].isoformat() if row["created_at"] else None,
                        "completed_at": row["completed_at"].isoformat() if row["completed_at"] else None,
                    }
                    for row in rows
                ],
            }
        except Exception as exc:
            self._last_error = str(exc)
            return {"available": False, "error": self._last_error, "missions": []}

    async def mission_detail(self, mission_id: str) -> dict[str, Any]:
        if not await self.ensure_connected():
            return {"available": False, "error": self._last_error}
        try:
            async with self._pool.acquire() as conn:
                row = await conn.fetchrow(
                    """
                    SELECT mission_id, topic, status, final_report_json, graph_state_json,
                           findings_count, confidence_score, created_at, completed_at
                    FROM research_missions
                    WHERE mission_id = $1
                    """,
                    mission_id,
                )
            if not row:
                return {"available": True, "mission": None}
            data = dict(row)
            data["created_at"] = row["created_at"].isoformat() if row["created_at"] else None
            data["completed_at"] = row["completed_at"].isoformat() if row["completed_at"] else None
            return {"available": True, "mission": data}
        except Exception as exc:
            self._last_error = str(exc)
            return {"available": False, "error": self._last_error}
