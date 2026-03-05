"""
ETF管理系统 - 一键启动脚本
同时启动 FastAPI 后端 (端口8000) 和 Vue 前端 (端口5173)
"""
import subprocess
import sys
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
VENV_PYTHON = os.path.join(BASE_DIR, "venv", "Scripts", "python.exe")
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")


def main():
    procs = []

    # 启动 FastAPI 后端
    backend_cmd = [
        VENV_PYTHON, "-m", "uvicorn",
        "backend.main:app",
        "--host", "0.0.0.0", "--port", "8000", "--reload",
    ]
    print("[启动] FastAPI 后端: http://127.0.0.1:8000")
    print(f"  API文档: http://127.0.0.1:8000/docs")
    backend = subprocess.Popen(backend_cmd, cwd=BASE_DIR)
    procs.append(backend)

    # 启动 Vue 前端 (使用 node 直接调用本地 vite)
    vite_bin = os.path.join(FRONTEND_DIR, "node_modules", "vite", "bin", "vite.js")
    frontend_cmd = ["node", vite_bin, "--host", "0.0.0.0", "--port", "5173"]
    print(f"[启动] Vue 前端: http://127.0.0.1:5173")
    frontend = subprocess.Popen(frontend_cmd, cwd=FRONTEND_DIR)
    procs.append(frontend)

    print("\n按 Ctrl+C 停止所有服务\n")

    try:
        for p in procs:
            p.wait()
    except KeyboardInterrupt:
        print("\n[停止] 正在关闭所有服务...")
        for p in procs:
            p.terminate()
        for p in procs:
            p.wait()
        print("[完成] 所有服务已关闭")


if __name__ == "__main__":
    main()
