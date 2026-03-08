"""
ETF每日净值爬取脚本
使用新浪财经（场内ETF）和天天基金（场外基金）接口获取数据
写入 SQLite 数据库
支持增量更新、去重、日志记录
"""

import sys
import os
import sqlite3
import logging
import math
from datetime import datetime, timedelta
from typing import List, Optional

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import DB_PATH

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(os.path.dirname(__file__), '../log/fetch_quotes.log'), encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def get_db_connection() -> sqlite3.Connection:
    """获取数据库连接"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def get_tracked_funds(conn: sqlite3.Connection) -> List[dict]:
    """获取需要跟踪净值的基金列表（有持仓的基金）"""
    cursor = conn.execute("""
        SELECT DISTINCT f.fund_code, f.fund_name 
        FROM fund_info f
        INNER JOIN fund_holdings h ON f.fund_code = h.fund_code
        ORDER BY f.fund_code
    """)
    return [dict(row) for row in cursor.fetchall()]


def get_existing_quotes(conn: sqlite3.Connection, fund_code: str, date: str) -> bool:
    """检查某基金某日期是否已有数据"""
    cursor = conn.execute(
        "SELECT 1 FROM daily_quotes WHERE fund_code = ? AND quote_date = ? LIMIT 1",
        (fund_code, date)
    )
    return cursor.fetchone() is not None


def fetch_fund_nav_eastmoney(fund_code: str) -> Optional[dict]:
    """
    备用方案：使用天天基金接口获取场外基金净值
    适用于 00/01 开头的场外基金
    返回格式适配新表结构
    """
    import urllib.request
    import json
    import time
    import ssl
    
    try:
        # 天天基金接口
        url = f"http://fundgz.1234567.com.cn/js/{fund_code}.js?rt={int(time.time()*1000)}"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.0',
            'Referer': 'http://fund.eastmoney.com/'
        }
        
        req = urllib.request.Request(url, headers=headers)
        
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        
        with urllib.request.urlopen(req, timeout=10, context=ctx) as response:
            text = response.read().decode('utf-8')
            
            # 返回格式：jsonpgz({"fundcode":"001186","name":"...","jzrq":"2025-03-07","dwjz":"1.2345",...});
            if text.startswith("jsonpgz("):
                json_str = text[8:-2]  # 去掉 jsonpgz( 和 );
                data = json.loads(json_str)
                
                nav = float(data['dwjz'])
                
                # 场外基金只有一个净值，开盘=最高=最低=收盘
                return {
                    'quote_date': data['jzrq'],
                    'open_price': nav,
                    'high_price': nav,
                    'low_price': nav,
                    'close_price': nav,
                    'acc_nav': nav,  # 暂用单位净值代替
                    'daily_change_pct': float(data['gszzl']) # 涨跌幅（仅记录日志用）
                }
    
    except Exception as e:
        logger.debug(f"[{fund_code}] 天天基金接口失败: {e}")
    
    return None


def fetch_fund_nav_sina_single(fund_code: str, market: str) -> Optional[dict]:
    """
    使用新浪接口获取单市场ETF行情 (标准接口)
    market: 'sh' 或 'sz'
    返回: {date, open, high, low, close, acc_nav}
    """
    import urllib.request
    import ssl
    
    try:
        # 使用标准行情接口（无 s_ 前缀）
        url = f"https://hq.sinajs.cn/list={market}{fund_code}"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.0',
            'Referer': 'https://finance.sina.com.cn'
        }
        
        req = urllib.request.Request(url, headers=headers)
        
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        
        with urllib.request.urlopen(req, timeout=10, context=ctx) as response:
            data_str = response.read().decode('gbk')
        
        # 解析返回的数据
        # var hq_str_sh510300="华泰300,开盘,昨收,当前,最高,最低,买一,卖一,成交量,成交额,...";
        if f'var hq_str_{market}' not in data_str:
            return None
            
        # 提取数据部分
        start = data_str.find('"') + 1
        end = data_str.rfind('"')
        if start == 0 or end == -1:
            return None
        data = data_str[start:end].split(',')
        
        # 标准接口通常包含 30+ 个字段
        if len(data) >= 30 and float(data[3]) > 0:
            today = datetime.now().strftime('%Y-%m-%d')
            current_price = float(data[3])
            
            # 计算涨跌幅
            pre_close = float(data[2])
            change_pct = (current_price - pre_close) / pre_close * 100 if pre_close > 0 else 0
            
            return {
                'quote_date': data[30] if len(data) > 30 else today, # 日期
                'open_price': float(data[1]),
                'high_price': float(data[4]),
                'low_price': float(data[5]),
                'close_price': current_price,
                'acc_nav': current_price,  # 场内ETF暂用收盘价代替累计净值
                'daily_change_pct': change_pct
            }
        
        return None
        
    except Exception as e:
        logger.debug(f"[{fund_code}] 新浪{market}接口失败: {e}")
        return None


def fetch_fund_nav_sina(fund_code: str) -> Optional[dict]:
    """
    备用方案：使用新浪接口获取ETF净值
    同时尝试上海和深圳市场
    """
    # 上海市场
    data = fetch_fund_nav_sina_single(fund_code, 'sh')
    if data:
        return data
    
    # 深圳市场
    data = fetch_fund_nav_sina_single(fund_code, 'sz')
    if data:
        return data
    
    logger.debug(f"[{fund_code}] 新浪接口获取失败 (已尝试 sh 和 sz 市场)")
    return None


def save_quote(conn: sqlite3.Connection, fund_code: str, fund_name: str, data: dict):
    """保存净值数据到数据库 (新表结构)"""
    try:
        conn.execute("""
            INSERT OR REPLACE INTO daily_quotes 
            (fund_code, fund_name, quote_date, open_price, high_price, low_price, close_price, acc_nav)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            fund_code,
            fund_name,
            data['quote_date'],
            data['open_price'],
            data['high_price'],
            data['low_price'],
            data['close_price'],
            data['acc_nav']
        ))
        conn.commit()
        
        # 记录日志
        pct_str = f"{data['daily_change_pct']:.2f}%" if 'daily_change_pct' in data else "N/A"
        logger.info(f"✓ [{fund_code}] {fund_name} - {data['quote_date']} 收盘: {data['close_price']}, 涨跌: {pct_str}")
        return True
        
    except Exception as e:
        logger.error(f"[{fund_code}] 保存数据失败: {e}")
        conn.rollback()
        return False


def fetch_all_quotes(force_update: bool = False):
    """
    获取所有持仓基金的最新净值
    """
    logger.info("=" * 50)
    logger.info(f"开始获取ETF行情 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 50)
    
    conn = get_db_connection()
    
    try:
        # 获取需要跟踪的基金列表
        funds = get_tracked_funds(conn)
        
        if not funds:
            logger.warning("没有找到持仓基金，请先添加持仓")
            return
        
        logger.info(f"共 {len(funds)} 只基金需要更新")
        
        success_count = 0
        skip_count = 0
        fail_count = 0
        
        for fund in funds:
            fund_code = fund['fund_code']
            fund_name = fund['fund_name']
            
            data = None
            
            # 场内基金 (15/51/56/58 开头) 优先尝试新浪 (实时价格)
            if fund_code.startswith(('15', '51', '56', '58')):
                data = fetch_fund_nav_sina(fund_code)
                # 备选天天基金
                if data is None:
                    data = fetch_fund_nav_eastmoney(fund_code)
            else:
                # 场外基金 (00/01/20 等开头) 优先尝试天天基金
                data = fetch_fund_nav_eastmoney(fund_code)
                # 备选新浪 (虽通常不支持场外)
                if data is None:
                    data = fetch_fund_nav_sina(fund_code)
            
            if data is None:
                logger.error(f"✗ [{fund_code}] {fund_name} - 获取数据失败")
                fail_count += 1
                continue
            
            # 检查是否已存在
            if not force_update and get_existing_quotes(conn, fund_code, data['quote_date']):
                logger.info(f"○ [{fund_code}] {fund_name} - {data['quote_date']} 数据已存在，跳过")
                skip_count += 1
                continue
            
            # 保存数据
            if save_quote(conn, fund_code, fund_name, data):
                success_count += 1
            else:
                fail_count += 1
        
        logger.info("=" * 50)
        logger.info(f"完成 - 成功: {success_count}, 跳过: {skip_count}, 失败: {fail_count}")
        logger.info("=" * 50)
        
    finally:
        conn.close()


def fetch_history_quotes(fund_code: str, days: int = 60):
    """
    获取某只基金的历史净值（使用天天基金接口）
    """
    logger.info(f"获取 [{fund_code}] 近 {days} 天历史数据...")
    import urllib.request
    import json
    
    try:
        # 天天基金历史净值接口
        url = f"http://api.fund.eastmoney.com/f10/lsjz?fundCode={fund_code}&pageIndex=1&pageSize={days}&startDate=&endDate="
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.0',
            'Referer': 'http://fundf10.eastmoney.com/'
        }
        
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode('utf-8'))
            
        if data['ErrCode'] != 0 or not data['Data']['LSJZList']:
            logger.warning(f"[{fund_code}] 历史数据获取为空")
            return

        conn = get_db_connection()
        try:
            # 获取基金名称
            cursor = conn.execute("SELECT fund_name FROM fund_info WHERE fund_code = ?", (fund_code,))
            row = cursor.fetchone()
            fund_name = row['fund_name'] if row else ''

            inserted = 0
            for item in data['Data']['LSJZList']:
                date_str = item['FSRQ'] # 净值日期
                nav = float(item['DWJZ']) if item['DWJZ'] else 0 # 单位净值
                acc_nav = float(item['LJJZ']) if item['LJJZ'] else nav # 累计净值
                change_pct = float(item['JZZZL']) if item['JZZZL'] else 0 # 日增长率
                
                if get_existing_quotes(conn, fund_code, date_str):
                    continue
                
                # 历史数据只有单一净值，没有 OHLC
                conn.execute("""
                    INSERT INTO daily_quotes (fund_code, fund_name, quote_date, open_price, high_price, low_price, close_price, acc_nav)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (fund_code, fund_name, date_str, nav, nav, nav, nav, acc_nav))
                inserted += 1
            
            conn.commit()
            logger.info(f"✓ [{fund_code}] 插入 {inserted} 条历史数据")
            
        finally:
            conn.close()

    except Exception as e:
        logger.error(f"[{fund_code}] 获取历史数据失败: {e}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='ETF净值爬取工具')
    parser.add_argument('--history', type=str, help='获取某基金历史数据，如: 159770')
    parser.add_argument('--days', type=int, default=60, help='历史数据天数，默认60天')
    parser.add_argument('--force', action='store_true', help='强制更新已有数据')
    
    args = parser.parse_args()
    
    if args.history:
        fetch_history_quotes(args.history, args.days)
    else:
        fetch_all_quotes(force_update=args.force)
