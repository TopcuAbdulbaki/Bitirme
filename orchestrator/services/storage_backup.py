"""Local PostgreSQL/MinIO backup helper for the admin panel."""
from __future__ import annotations

import asyncio
import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

from orchestrator.config import (
    ADMIN_DB_NAME,
    ADMIN_DB_PASSWORD,
    ADMIN_DB_USER,
    BACKUP_COMMAND_TIMEOUT,
    BACKUP_DIR,
    BACKUP_MINIO_CONTAINER,
    BACKUP_POSTGRES_CONTAINER,
)


class StorageBackupManager:
    """Runs one local storage backup job at a time."""

    def __init__(self):
        self.root = Path(BACKUP_DIR).resolve()
        self._task: asyncio.Task | None = None
        self._status: dict[str, Any] = {
            "state": "idle",
            "message": "Hazir",
            "backup_id": "",
            "archive_name": "",
            "archive_size": 0,
            "started_at": "",
            "completed_at": "",
            "error": "",
        }

    def status(self) -> dict[str, Any]:
        data = dict(self._status)
        data["running"] = bool(self._task and not self._task.done())
        data["backup_dir"] = str(self.root)
        data["archives"] = self._list_archives()
        return data

    def start(self, *, include_postgres: bool = True, include_minio: bool = True) -> dict[str, Any]:
        if self._task and not self._task.done():
            return {"started": False, "status": self.status(), "error": "backup already running"}
        if not include_postgres and not include_minio:
            return {"started": False, "status": self.status(), "error": "nothing selected"}
        self._task = asyncio.create_task(
            self._run(include_postgres=include_postgres, include_minio=include_minio)
        )
        return {"started": True, "status": self.status()}

    def archive_path(self, archive_name: str) -> Path | None:
        if not archive_name.endswith(".zip") or "/" in archive_name or "\\" in archive_name:
            return None
        path = (self.root / archive_name).resolve()
        if path.parent != self.root or not path.exists():
            return None
        return path

    def _list_archives(self) -> list[dict[str, Any]]:
        if not self.root.exists():
            return []
        archives = []
        for path in sorted(self.root.glob("*.zip"), key=lambda item: item.stat().st_mtime, reverse=True)[:12]:
            stat = path.stat()
            archives.append(
                {
                    "name": path.name,
                    "size": stat.st_size,
                    "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat(timespec="seconds"),
                }
            )
        return archives

    async def _run(self, *, include_postgres: bool, include_minio: bool):
        backup_id = datetime.now().strftime("storage_%Y%m%d_%H%M%S")
        work_dir = self.root / backup_id
        archive_path = self.root / f"{backup_id}.zip"
        self._status.update(
            {
                "state": "running",
                "message": "Backup basladi",
                "backup_id": backup_id,
                "archive_name": "",
                "archive_size": 0,
                "started_at": datetime.now().isoformat(timespec="seconds"),
                "completed_at": "",
                "error": "",
            }
        )

        try:
            self.root.mkdir(parents=True, exist_ok=True)
            work_dir.mkdir(parents=True, exist_ok=False)

            manifest = {
                "backup_id": backup_id,
                "created_at": datetime.now().isoformat(timespec="seconds"),
                "postgres": include_postgres,
                "minio": include_minio,
                "postgres_container": BACKUP_POSTGRES_CONTAINER,
                "minio_container": BACKUP_MINIO_CONTAINER,
                "database": ADMIN_DB_NAME,
            }

            if include_postgres:
                await self._backup_postgres(work_dir, backup_id)
            if include_minio:
                await self._backup_minio(work_dir)

            (work_dir / "manifest.json").write_text(
                json.dumps(manifest, indent=2),
                encoding="utf-8",
            )

            self._status["message"] = "Zip arsivi olusturuluyor"
            made_archive = shutil.make_archive(str(work_dir), "zip", root_dir=work_dir)
            size = Path(made_archive).stat().st_size
            if Path(made_archive) != archive_path:
                archive_path = Path(made_archive)

            self._status.update(
                {
                    "state": "completed",
                    "message": "Backup hazir",
                    "archive_name": archive_path.name,
                    "archive_size": size,
                    "completed_at": datetime.now().isoformat(timespec="seconds"),
                    "error": "",
                }
            )
        except Exception as exc:
            self._status.update(
                {
                    "state": "failed",
                    "message": "Backup basarisiz",
                    "completed_at": datetime.now().isoformat(timespec="seconds"),
                    "error": str(exc),
                }
            )

    async def _backup_postgres(self, work_dir: Path, backup_id: str):
        self._status["message"] = "PostgreSQL dump aliniyor"
        container_dump = f"/tmp/{backup_id}.dump"
        await self._run_command(
            [
                "docker",
                "exec",
                "-e",
                f"PGPASSWORD={ADMIN_DB_PASSWORD}",
                BACKUP_POSTGRES_CONTAINER,
                "pg_dump",
                "-U",
                ADMIN_DB_USER,
                "-d",
                ADMIN_DB_NAME,
                "-Fc",
                "-f",
                container_dump,
            ]
        )
        try:
            await self._run_command(
                [
                    "docker",
                    "cp",
                    f"{BACKUP_POSTGRES_CONTAINER}:{container_dump}",
                    str(work_dir / "postgres_news_db.dump"),
                ]
            )
        finally:
            await self._run_command(
                ["docker", "exec", BACKUP_POSTGRES_CONTAINER, "rm", "-f", container_dump],
                allow_failure=True,
            )

    async def _backup_minio(self, work_dir: Path):
        self._status["message"] = "MinIO data kopyalaniyor"
        await self._run_command(
            [
                "docker",
                "cp",
                f"{BACKUP_MINIO_CONTAINER}:/data",
                str(work_dir / "minio_data"),
            ]
        )

    async def _run_command(self, args: list[str], *, allow_failure: bool = False):
        proc = await asyncio.create_subprocess_exec(
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(),
                timeout=BACKUP_COMMAND_TIMEOUT,
            )
        except asyncio.TimeoutError:
            proc.kill()
            await proc.communicate()
            raise RuntimeError(f"command timed out: {' '.join(args[:3])}")

        if proc.returncode != 0 and not allow_failure:
            details = (stderr or stdout).decode(errors="replace").strip()
            raise RuntimeError(details or f"command failed: {' '.join(args[:3])}")
