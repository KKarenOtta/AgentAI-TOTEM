from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

from app.services.aws_db_service import AWSDBService, init_db_pool
from core.persistence.sync_queue import list_pending, mark_failed, mark_synced

logger = logging.getLogger("sync_worker")


async def process_sync_item(item: dict[str, Any], service: AWSDBService) -> None:
    entity = item.get("entity")
    operation = item.get("operation")
    payload = item.get("payload") or {}

    if entity == "metrics" and operation == "insert":
        await service.insert_metric(payload)

    elif entity == "leads" and operation in {"insert", "upsert"}:
        await service.upsert_lead(payload)

    elif entity == "consents" and operation == "insert":
        await service.insert_consent(payload)

    else:
        raise ValueError(f"Tipo de sync não suportado: {entity}:{operation}")

    try:
        await service.record_sync_audit(item, status="synced")
    except Exception:
        pass


async def run_once(limit: int = 100) -> dict[str, int]:
    await init_db_pool()

    service = AWSDBService()
    items = list_pending(limit=limit)

    result = {
        "total": len(items),
        "synced": 0,
        "failed": 0,
    }

    for item in items:
        sync_id = item.get("sync_id")

        if not sync_id:
            continue

        try:
            await process_sync_item(item, service)
            mark_synced(sync_id)
            result["synced"] += 1
        except Exception as exc:
            mark_failed(sync_id, f"{type(exc).__name__}: {exc}")
            result["failed"] += 1

            try:
                await service.record_sync_audit(item, status="failed", error=str(exc))
            except Exception:
                pass

    return result


async def run_forever(interval_seconds: int = 15, limit: int = 100) -> None:
    while True:
        started = time.time()

        try:
            result = await run_once(limit=limit)
            logger.info("sync result: %s", result)
        except Exception as exc:
            logger.warning("sync loop error: %s", exc)

        elapsed = time.time() - started
        sleep_for = max(1, interval_seconds - int(elapsed))
        await asyncio.sleep(sleep_for)


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="TOTEM persistence sync worker")
    parser.add_argument("--once", action="store_true", help="Executa uma rodada e encerra.")
    parser.add_argument("--interval", type=int, default=15, help="Intervalo do loop contínuo.")
    parser.add_argument("--limit", type=int, default=100, help="Máximo de itens por rodada.")

    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")

    if args.once:
        result = asyncio.run(run_once(limit=args.limit))
        print(result)
        return

    asyncio.run(run_forever(interval_seconds=args.interval, limit=args.limit))


if __name__ == "__main__":
    main()
