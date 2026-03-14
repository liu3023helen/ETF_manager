from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import logging

from .routers import dashboard, funds, holdings, quotes, rules, trade_records, tables, snapshots

logger = logging.getLogger(__name__)

app = FastAPI(title="ETF管理系统", version="1.0.1")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    # 打印完整堆栈到控制台供调试
    logger.error(f"Unhandled exception on {request.method} {request.url.path}", exc_info=exc)
    
    return JSONResponse(
        status_code=500,
        content={"detail": "服务器内部错误"},
    )

app.include_router(dashboard.router)
app.include_router(funds.router)
app.include_router(holdings.router)
app.include_router(quotes.router)
app.include_router(rules.router)
app.include_router(trade_records.router)
app.include_router(tables.router)
app.include_router(snapshots.router)


@app.get("/")
def root():
    return {"message": "ETF管理系统 API", "docs": "/docs"}
