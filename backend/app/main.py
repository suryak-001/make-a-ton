from fastapi import FastAPI

from app.core.errors import register_error_handlers
from app.routers import (
    auth,
    customers,
    discounts,
    invoices,
    payments,
    plans,
    portal_invoices,
    portal_subscriptions,
    pricing,
    products,
    quotation_templates,
    reports,
    subscriptions,
    taxes,
    users,
)

app = FastAPI(title="Brightloop Subscriptions API")
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
    pricing,
    reports,
    portal_invoices,
):
    app.include_router(module.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}
