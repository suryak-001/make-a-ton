"""The daily jobs, run by the server itself so nobody has to remember to click.

Every day at `SCHEDULER_HOUR:SCHEDULER_MINUTE` (server time) the server bills everything that is due, then runs
the lifecycle job (close ended auto-close subscriptions, expire stale quotes). Billing goes first so a final
period is invoiced before its subscription closes. Both jobs are idempotent and catch up on missed days, so a
server that was down at the scheduled time simply does the work the next time it runs.

With several server processes only one runs the jobs: a PostgreSQL advisory lock keeps the others out.
"""

import asyncio
import logging
from datetime import date, datetime, timedelta

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import settings
from app.db import SessionLocal, engine
from app.services.billing import run_billing
from app.services.subscriptions import run_lifecycle_job

log = logging.getLogger("brightloop.scheduler")

ADVISORY_LOCK_KEY = 7_204_001  # any number, as long as nothing else in this database uses it
START_UP_DELAY_SECONDS = 15


def run_daily_jobs_in(db: Session, as_of: date | None = None) -> dict:
    """Billing, then the lifecycle job, each committed on its own. What the scheduler (and the tests) run."""
    as_of = as_of or date.today()
    billing = run_billing(db, as_of)
    db.commit()
    lifecycle = run_lifecycle_job(db, as_of)
    db.commit()
    return {
        "as_of": str(as_of),
        "billing": {
            "due": billing.due,
            "created": billing.created,
            "already_billed": billing.already_billed,
            "skipped": billing.skipped,
            "failed": billing.failed,
        },
        "lifecycle": lifecycle,
    }


def run_daily_jobs(as_of: date | None = None) -> dict | None:
    """Runs the daily jobs unless another process is already running them (then returns None)."""
    with engine.connect() as lock:
        if not lock.execute(text("select pg_try_advisory_lock(:key)"), {"key": ADVISORY_LOCK_KEY}).scalar():
            return None
        try:
            with SessionLocal() as db:
                return run_daily_jobs_in(db, as_of)
        finally:
            lock.execute(text("select pg_advisory_unlock(:key)"), {"key": ADVISORY_LOCK_KEY})
            lock.commit()


def seconds_until(now: datetime, hour: int, minute: int) -> float:
    """Seconds from `now` to the next `hour:minute` (today if it is still ahead, otherwise tomorrow)."""
    target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if target <= now:
        target += timedelta(days=1)
    return (target - now).total_seconds()


async def _run_once() -> None:
    try:
        summary = await asyncio.to_thread(run_daily_jobs)
    except Exception:  # a failed day must not stop the next one
        log.exception("Daily jobs failed")
        return
    log.info("Daily jobs: %s", summary if summary is not None else "skipped, another process has the lock")


async def scheduler_loop() -> None:
    if settings.scheduler_run_on_start:
        await asyncio.sleep(START_UP_DELAY_SECONDS)
        await _run_once()
    while True:
        await asyncio.sleep(seconds_until(datetime.now(), settings.scheduler_hour, settings.scheduler_minute))
        await _run_once()
