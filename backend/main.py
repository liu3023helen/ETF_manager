from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import traceback
import sys

from .routers import dashboard, funds, holdings, quotes, rules, trade_records, tables

app = FastAPI(title="ETF管理系统", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    exc_type, exc_value, exc_traceback = sys.exc_info()
    error_msg = str(exc)
    
    # 打印完整堆栈到控制台供调试
    traceback.print_exception(exc_type, exc_value, exc_traceback)
    
    return JSONResponse(
        status_code=500,
        content={"detail": "服务器内部错误", "message": error_msg},
    )

app.include_router(dashboard.router)
app.include_router(funds.router)
app.include_router(holdings.router)
app.include_router(quotes.router)
app.include_router(rules.router)
app.include_router(trade_records.router)
app.include_router(tables.router)


@app.get("/")
def root():
    return {"message": "ETF管理系统 API", "docs": "/docs"}
