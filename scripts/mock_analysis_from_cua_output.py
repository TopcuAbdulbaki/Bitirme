#!/usr/bin/env python3
"""
Feed articles from a saved CUA surface-output markdown file into the normal
crawler-result ingress so Orchestrator drives VLM -> LLM -> DB unchanged.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import grpc

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from crawler.generated import orchestrator_pb2 as pb2  # noqa: E402
from crawler.generated import orchestrator_pb2_grpc as pb2_grpc  # noqa: E402


def load_surface_report(path: Path) -> dict:
    text = path.read_text(encoding="utf-8", errors="replace")
    decoder = json.JSONDecoder()
    candidates: list[dict] = []

    for index, char in enumerate(text):
        if char != "{":
            continue
        try:
            value, _ = decoder.raw_decode(text[index:])
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict) and isinstance(value.get("articles"), list):
            candidates.append(value)

    if not candidates:
        raise ValueError(f"No JSON report with an articles list found in {path}")

    return candidates[-1]


def build_mock_crawler_payload(article: dict) -> dict:
    media = article.get("media") if isinstance(article.get("media"), dict) else {}
    payload = {
        "source": article.get("source") or "mock_surface",
        "country": article.get("country") or "unknown",
        "url": article.get("url") or "",
        "keyword_found": article.get("keyword_found") or "mock surface replay",
        "scraped_at": article.get("scraped_at")
        or datetime.now(timezone.utc).isoformat(),
        "title": article.get("title") or "",
        "content": article.get("content") or "",
        "description": article.get("description") or "",
        "media": {
            "main_image": media.get("main_image"),
            "content_images": media.get("content_images") or [],
            "videos": media.get("videos") or [],
        },
    }

    if not payload["url"]:
        raise ValueError("Article is missing url")
    if not payload["content"]:
        raise ValueError(f"Article is missing content: {payload['url']}")

    return payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Replay saved CUA surface articles through Orchestrator crawler ingress."
    )
    parser.add_argument(
        "--input",
        default=str(REPO_ROOT / "cua" / "outputs5.md"),
        help="Markdown/text file containing a JSON object with articles.",
    )
    parser.add_argument(
        "--host",
        default=os.getenv("ORCHESTRATOR_HOST", "127.0.0.1"),
        help="Orchestrator gRPC host.",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.getenv("ORCHESTRATOR_PORT", "50051")),
        help="Orchestrator gRPC port.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Maximum number of articles to send. 0 means all.",
    )
    parser.add_argument(
        "--task-prefix",
        default="mock_outputs5",
        help="Task id prefix reported to Orchestrator.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse and print the payload summary without sending RPCs.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    input_path = Path(args.input).expanduser().resolve()
    report = load_surface_report(input_path)
    articles = [
        build_mock_crawler_payload(article)
        for article in report.get("articles", [])
        if isinstance(article, dict)
    ]

    if args.limit > 0:
        articles = articles[: args.limit]

    if not articles:
        raise ValueError("No usable articles found")

    print(f"[MockAnalysis] Loaded {len(articles)} article(s) from {input_path}")
    for index, article in enumerate(articles, start=1):
        print(
            f"[MockAnalysis] #{index}: "
            f"{article['source']} | {article['url']}"
        )

    if args.dry_run:
        print("[MockAnalysis] Dry run complete; no RPC sent.")
        return 0

    target = f"{args.host}:{args.port}"
    print(f"[MockAnalysis] Connecting to Orchestrator gRPC at {target}")
    channel = grpc.insecure_channel(target)
    try:
        grpc.channel_ready_future(channel).result(timeout=10)
        stub = pb2_grpc.OrchestratorServiceStub(channel)

        for index, article in enumerate(articles, start=1):
            task_id = f"{args.task_prefix}_{index}"
            request = pb2.CrawlTaskResponse(
                task_id=task_id,
                status=pb2.SUCCESS,
                json_data=json.dumps(article, ensure_ascii=False),
                error_message="",
            )
            stub.ReportCrawlResult(request, timeout=15)
            print(f"[MockAnalysis] Sent {task_id}: {article['url']}")
    finally:
        channel.close()

    print("[MockAnalysis] Replay submitted.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
