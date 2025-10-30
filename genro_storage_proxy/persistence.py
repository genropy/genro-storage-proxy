"""SQLite backed persistence for storage volumes."""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

import aiosqlite

from genro_storage_proxy.logger import get_logger

logger = get_logger("Persistence")


class Persistence:
    """Helper class responsible for reading and writing storage volumes configuration."""

    def __init__(self, db_path: str = "/tmp/storage_proxy.db"):
        """Persist data to the given database path (``:memory:`` allowed)."""
        self.db_path = db_path or ":memory:"

    async def init_db(self) -> None:
        """Create (or migrate) the database schema."""
        async with aiosqlite.connect(self.db_path) as db:
            # Create volumes table
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS volumes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    backend TEXT NOT NULL,
                    config TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

            # Create indices
            await db.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS idx_volumes_name ON volumes(name)"
            )

            await db.commit()
            logger.info(f"Database initialized at {self.db_path}")

    # Volumes ------------------------------------------------------------------

    async def add_volumes(self, volumes: List[Dict[str, Any]]) -> None:
        """Insert or replace storage volumes."""
        if not volumes:
            return
        async with aiosqlite.connect(self.db_path) as db:
            for vol in volumes:
                await db.execute(
                    """
                    INSERT OR REPLACE INTO volumes (name, backend, config, updated_at)
                    VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                    """,
                    (vol["name"], vol["backend"], json.dumps(vol["config"]))
                )
            await db.commit()
        logger.info(f"Added/updated {len(volumes)} volumes")

    async def add_volume(self, volume: Dict[str, Any]) -> None:
        """Insert or replace a single storage volume."""
        await self.add_volumes([volume])

    async def list_volumes(self) -> List[Dict[str, Any]]:
        """Return all configured volumes."""
        async with aiosqlite.connect(self.db_path) as db:
            query = "SELECT id, name, backend, config, created_at, updated_at FROM volumes ORDER BY name"
            async with db.execute(query) as cur:
                rows = await cur.fetchall()
                cols = [c[0] for c in cur.description]

        result = []
        for row in rows:
            vol = dict(zip(cols, row))
            vol["config"] = json.loads(vol["config"])
            result.append(vol)
        return result

    async def get_volume(self, volume_name: str) -> Optional[Dict[str, Any]]:
        """Get volume configuration by name.

        Returns None if no volume found.
        """
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT id, name, backend, config, created_at, updated_at FROM volumes WHERE name=?",
                (volume_name,)
            ) as cur:
                row = await cur.fetchone()
                if not row:
                    return None
                cols = [c[0] for c in cur.description]
                vol = dict(zip(cols, row))
                vol["config"] = json.loads(vol["config"])
                return vol

    async def delete_volume(self, volume_name: str) -> bool:
        """Delete a volume by name. Returns True if deleted."""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "DELETE FROM volumes WHERE name=?",
                (volume_name,)
            )
            await db.commit()
            deleted = cursor.rowcount > 0
            if deleted:
                logger.info(f"Deleted volume: {volume_name}")
            return deleted

    async def update_volume(self, volume_name: str, backend: str, config: Dict[str, Any]) -> bool:
        """Update an existing volume. Returns True if updated."""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                """
                UPDATE volumes
                SET backend = ?, config = ?, updated_at = CURRENT_TIMESTAMP
                WHERE name = ?
                """,
                (backend, json.dumps(config), volume_name)
            )
            await db.commit()
            updated = cursor.rowcount > 0
            if updated:
                logger.info(f"Updated volume: {volume_name}")
            return updated
