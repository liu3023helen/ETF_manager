from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routers import dashboard, funds, holdings, quotes, dca_plans, rules, signals, transactions, tables

app = FastAPI(title="ETF管理系统", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(dashboard.router)
app.include_router(funds.router)
app.include_router(holdings.router)
app.include_router(quotes.router)
app.include_router(dca_plans.router)
app.include_router(rules.router)
app.include_router(signals.router)
app.include_router(transactions.router)
app.include_router(tables.router)


@app.get("/")
def root():
    return {"message": "ETF管理系统 API", "docs": "/docs"}
