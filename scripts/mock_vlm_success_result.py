#!/usr/bin/env python3
"""Publish controlled VLM SUCCESS messages for existing orchestrator tasks."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from orchestrator.config import QUEUE_VLM_RESULTS  # noqa: E402
from orchestrator.services.rabbitmq_manager import (  # noqa: E402
    QueueMessage,
    RabbitMQManager,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Publish mock VLM SUCCESS results so Orchestrator can exercise LLM -> DB."
    )
    parser.add_argument(
        "--task-id",
        action="append",
        required=True,
        help="Existing orchestrator task id to resume after VLM.",
    )
    parser.add_argument(
        "--description",
        default="Mock visual verification payload for downstream LLM and DB smoke testing.",
        help="Synthetic image description passed to the LLM.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    rabbitmq = RabbitMQManager()
    if not rabbitmq.connect():
        raise RuntimeError("RabbitMQ connection failed")

    try:
        for task_id in args.task_id:
            result_data = {
                "task_id": task_id,
                "status": "SUCCESS",
                "error": "",
                "results": [
                    {
                        "minio_path": None,
                        "original_url": "mock://vlm-smoke",
                        "description": args.description,
                        "objects": ["chart", "document"],
                        "sentiment": "neutral",
                        "relevance": "medium",
                    }
                ],
            }
            rabbitmq.publish(
                QUEUE_VLM_RESULTS,
                QueueMessage(
                    task_id=task_id,
                    json_data=json.dumps(result_data, ensure_ascii=False),
                ),
            )
            print(f"[MockVLM] Published SUCCESS result for {task_id}")
    finally:
        rabbitmq.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
