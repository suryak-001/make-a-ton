import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI

from app.config import settings
from app.core.errors import register_error_handlers
from app.routers import (
    auth,
    customers,
    demo_gateway,
    discounts,
    invoices,
    payments,
    plans,
    portal_invoices,
    portal_subscriptions,
    pricing,
    products,
    quotation_templates,
    reconciliation,
    reports,
    subscriptions,
    taxes,
    users,
)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """Starts the daily billing and lifecycle jobs with the server (SCHEDULER_ENABLED=false turns them off)."""
    from app.services.scheduler import scheduler_loop

    task = asyncio.create_task(scheduler_loop()) if settings.scheduler_enabled else None
    yield
    if task is not None:
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task


app = FastAPI(title="Brightloop Subscriptions API", lifespan=lifespan)
register_error_handlers(app)

for module in (
    auth,
    users,
    customers,
    products,
    plans,
    quotation_templates,
    subscriptions,
    portal_subscriptions,
    taxes,
    discounts,
    invoices,
    payments,
    reconciliation,
    pricing,
    reports,
    portal_invoices,
    demo_gateway,
):
    app.include_router(module.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}
