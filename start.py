"""
ETF管理系统 - 一键启动脚本
同时启动 FastAPI 后端 (端口8000) 和 Vue 前端 (端口5173)
启动前检查端口，避免重复拉起多实例
"""
import subprocess
import os
import socket
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
VENV_PYTHON = os.path.join(BASE_DIR, "venv", "Scripts", "python.exe")
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")
BACKEND_PORT = 8000
FRONTEND_PORT = 5173


def is_port_in_use(port: int, host: str = "127.0.0.1") -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.3)
        return s.connect_ex((host, port)) == 0


def ensure_single_instance_or_exit():
    conflicts = []
    if is_port_in_use(BACKEND_PORT):
        conflicts.append(f"{BACKEND_PORT}(后端)")
    if is_port_in_use(FRONTEND_PORT):
        conflicts.append(f"{FRONTEND_PORT}(前端)")

    if conflicts:
        print("[错误] 检测到已有实例正在运行：" + "、".join(conflicts))
        print("请先关闭旧的 start.py/uvicorn/vite 进程，再重新启动。")
        input("按回车键退出...")
        sys.exit(1)


def main():
    ensure_single_instance_or_exit()

    procs = []

    # 启动 FastAPI 后端
    backend_cmd = [
        VENV_PYTHON,
        "-m",
        "uvicorn",
        "backend.main:app",
        "--host",
        "0.0.0.0",
        "--port",
        str(BACKEND_PORT),
        "--reload",
    ]
    print(f"[启动] FastAPI 后端: http://127.0.0.1:{BACKEND_PORT}")
    print(f"  API文档: http://127.0.0.1:{BACKEND_PORT}/docs")
    backend = subprocess.Popen(backend_cmd, cwd=BASE_DIR)
    procs.append(backend)

    # 启动 Vue 前端
    vite_bin = os.path.join(FRONTEND_DIR, "node_modules", "vite", "bin", "vite.js")
    frontend_cmd = ["node", vite_bin, "--host", "0.0.0.0", "--port", str(FRONTEND_PORT)]
    print(f"[启动] Vue 前端: http://127.0.0.1:{FRONTEND_PORT}")
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
