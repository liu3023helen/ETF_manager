"""
ETF管理系统 - 全局配置
"""
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
DB_PATH = os.path.join(DATA_DIR, "etf_manager.db")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
