"""
批量获取所有持仓基金的历史净值数据
"""

import sys
import os
import sqlite3
import logging

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import DB_PATH
from fetch_daily_quotes import get_db_connection, fetch_history_quotes

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def get_all_tracked_funds():
    """获取所有需要跟踪的基金列表"""
    conn = get_db_connection()
    try:
        cursor = conn.execute("""
            SELECT DISTINCT f.fund_code, f.fund_name 
            FROM fund_info f
            INNER JOIN fund_holdings h ON f.fund_code = h.fund_code
            ORDER BY f.fund_code
        """)
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()


def fetch_all_history(days: int = 60):
    """
    获取所有持仓基金的历史净值数据
    """
    funds = get_all_tracked_funds()
    
    if not funds:
        logger.warning("没有找到持仓基金，请先添加持仓")
        return
    
    logger.info(f"共 {len(funds)} 只基金需要获取历史数据")
    logger.info(f"每只基金获取近 {days} 天数据")
    logger.info("=" * 50)
    
    success_count = 0
    fail_count = 0
    
    for i, fund in enumerate(funds, 1):
        fund_code = fund['fund_code']
        fund_name = fund['fund_name']
        
        logger.info(f"[{i}/{len(funds)}] 获取 {fund_code} {fund_name} 的历史数据...")
        
        try:
            fetch_history_quotes(fund_code, days)
            success_count += 1
        except Exception as e:
            logger.error(f"✗ [{fund_code}] 获取失败: {e}")
            fail_count += 1
    
    logger.info("=" * 50)
    logger.info(f"完成 - 成功: {success_count}, 失败: {fail_count}")


def fetch_all_history_by_date(start_date: str, end_date: str):
    """
    按日期范围获取所有持仓基金的历史净值数据
    """
    funds = get_all_tracked_funds()
    
    if not funds:
        logger.warning("没有找到持仓基金，请先添加持仓")
        return
    
    logger.info(f"共 {len(funds)} 只基金需要获取历史数据")
    logger.info(f"日期范围: {start_date} 至 {end_date}")
    logger.info("=" * 50)
    
    success_count = 0
    fail_count = 0
    
    for i, fund in enumerate(funds, 1):
        fund_code = fund['fund_code']
        fund_name = fund['fund_name']
        
        logger.info(f"[{i}/{len(funds)}] 获取 {fund_code} {fund_name} 的历史数据...")
        
        try:
            fetch_history_quotes(fund_code, start_date=start_date, end_date=end_date)
            success_count += 1
        except Exception as e:
            logger.error(f"✗ [{fund_code}] 获取失败: {e}")
            fail_count += 1
    
    logger.info("=" * 50)
    logger.info(f"完成 - 成功: {success_count}, 失败: {fail_count}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='批量获取所有持仓基金历史净值')
    parser.add_argument('--days', type=int, default=60, help='历史数据天数，默认60天')
    parser.add_argument('--start-date', type=str, help='开始日期，格式: 2025-01-01')
    parser.add_argument('--end-date', type=str, help='结束日期，格式: 2025-12-31')
    
    args = parser.parse_args()
    
    if args.start_date and args.end_date:
        fetch_all_history_by_date(args.start_date, args.end_date)
    else:
        fetch_all_history(args.days)
