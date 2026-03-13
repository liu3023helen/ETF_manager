"""
ETF管理系统 - 指数数据管理脚本
功能：
  1. 删除广发天天红货币B在daily_quotes中的所有数据
  2. 插入五大指数基本信息到fund_info
  3. 抓取五大指数历史K线数据写入daily_quotes
幂等设计，可重复执行
"""

import sys
import os
import sqlite3
import json
import logging
import time
import urllib.request
import ssl
from datetime import datetime

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import DB_PATH

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)


# ===== 五大指数基本信息 =====
INDEX_LIST = [
    {
        "fund_code": "000300.SH",
        "fund_name": "沪深300指数",
        "fund_company": "中证指数公司",
        "fund_type": "股票指数",
        "tracking_index": None,
        "risk_level": "中高",
        "fund_category": "宽基指数",
        "top_holdings": "由沪深市场中规模大、流动性好的300只证券组成，反映A股市场整体表现",
        "risk_points": "大盘波动风险",
        "inception_date": "2005-04-08",
        "secid": "1.000300",  # 东方财富API参数：沪市用1前缀
    },
    {
        "fund_code": "000905.SH",
        "fund_name": "中证500指数",
        "fund_company": "中证指数公司",
        "fund_type": "股票指数",
        "tracking_index": None,
        "risk_level": "中高",
        "fund_category": "宽基指数",
        "top_holdings": "由全部A股中剔除沪深300指数成份股后总市值排名靠前的500只股票组成，反映中小市值公司表现",
        "risk_points": "中小盘波动风险",
        "inception_date": "2007-01-15",
        "secid": "1.000905",
    },
    {
        "fund_code": "000001.SH",
        "fund_name": "上证指数",
        "fund_company": "上海证券交易所",
        "fund_type": "股票指数",
        "tracking_index": None,
        "risk_level": "中",
        "fund_category": "综合指数",
        "top_holdings": "上海证券交易所全部上市股票的加权平均指数，是中国资本市场最具代表性的指数之一",
        "risk_points": "全市场系统性风险",
        "inception_date": "1991-07-15",
        "secid": "1.000001",
    },
    {
        "fund_code": "399006.SZ",
        "fund_name": "创业板指",
        "fund_company": "深圳证券交易所",
        "fund_type": "股票指数",
        "tracking_index": None,
        "risk_level": "高",
        "fund_category": "成长指数",
        "top_holdings": "由创业板市场中市值大、流动性好的100只股票组成，反映创新型、成长型企业整体表现",
        "risk_points": "成长股高波动风险",
        "inception_date": "2010-06-01",
        "secid": "0.399006",  # 深市用0前缀
    },
    {
        "fund_code": "000688.SH",
        "fund_name": "科创50指数",
        "fund_company": "上海证券交易所",
        "fund_type": "股票指数",
        "tracking_index": None,
        "risk_level": "高",
        "fund_category": "科创指数",
        "top_holdings": "由科创板中市值大、流动性好的50只股票组成，反映科创板核心上市公司整体表现",
        "risk_points": "科创板高波动风险",
        "inception_date": "2020-07-23",
        "secid": "1.000688",
    },
]


def get_db_connection() -> sqlite3.Connection:
    """获取数据库连接"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn


def step1_delete_currency_fund_quotes(conn: sqlite3.Connection):
    """
    步骤1：删除广发天天红货币B在daily_quotes中的所有数据
    fund_code = 002183
    """
    fund_code = "002183"
    logger.info("=" * 60)
    logger.info(f"步骤1: 删除 {fund_code}(广发天天红货币B) 的 daily_quotes 数据")
    logger.info("=" * 60)

    # 先统计数量
    cursor = conn.execute(
        "SELECT COUNT(*) FROM daily_quotes WHERE fund_code = ?", (fund_code,)
    )
    count = cursor.fetchone()[0]
    logger.info(f"  当前共有 {count} 条记录")

    if count == 0:
        logger.info("  无数据需要删除，跳过")
        return

    # 执行删除
    conn.execute("DELETE FROM daily_quotes WHERE fund_code = ?", (fund_code,))
    conn.commit()
    logger.info(f"  ✓ 已删除 {count} 条记录")


def step2_insert_index_info(conn: sqlite3.Connection):
    """
    步骤2：插入五大指数基本信息到fund_info
    使用 INSERT OR REPLACE 实现幂等
    """
    logger.info("=" * 60)
    logger.info("步骤2: 插入五大指数信息到 fund_info")
    logger.info("=" * 60)

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    for idx in INDEX_LIST:
        conn.execute("""
            INSERT OR REPLACE INTO fund_info 
            (fund_code, fund_name, fund_company, fund_type, tracking_index, 
             risk_level, fund_category, top_holdings, risk_points, inception_date,
             created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            idx["fund_code"], idx["fund_name"], idx["fund_company"],
            idx["fund_type"], idx["tracking_index"], idx["risk_level"],
            idx["fund_category"], idx["top_holdings"], idx["risk_points"],
            idx["inception_date"], now, now,
        ))
        logger.info(f"  ✓ {idx['fund_code']} {idx['fund_name']}")

    conn.commit()
    logger.info(f"  共插入/更新 {len(INDEX_LIST)} 条指数信息")


def fetch_index_history_eastmoney(secid: str, start_date: str = "19900101", end_date: str = None):
    """
    使用东方财富API获取指数历史日K线数据
    
    参数:
        secid: 东方财富格式的代码，如 "1.000300"（1=沪市, 0=深市）
        start_date: 开始日期 YYYYMMDD 格式
        end_date: 结束日期 YYYYMMDD 格式，默认到今天
    
    返回: list of dict，每条包含 date, open, high, low, close, volume, amount
    """
    if end_date is None:
        end_date = datetime.now().strftime("%Y%m%d")

    url = (
        f"http://push2his.eastmoney.com/api/qt/stock/kline/get?"
        f"secid={secid}&fields1=f1,f2,f3,f4,f5,f6"
        f"&fields2=f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61"
        f"&klt=101&fqt=1"
        f"&beg={start_date}&end={end_date}"
        f"&lmt=50000"  # 最多拉取50000条
    )

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": "http://quote.eastmoney.com/",
    }

    try:
        req = urllib.request.Request(url, headers=headers)
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

        with urllib.request.urlopen(req, timeout=30, context=ctx) as response:
            data = json.loads(response.read().decode("utf-8"))

        if data.get("data") is None or data["data"].get("klines") is None:
            logger.warning(f"  [{secid}] API返回无数据")
            return []

        klines = data["data"]["klines"]
        result = []
        for line in klines:
            # 格式: "2005-04-08,1003.28,1012.58,993.02,998.23,4001308,38990760000.00,..."
            fields = line.split(",")
            if len(fields) >= 7:
                result.append({
                    "date": fields[0],          # 日期
                    "open": float(fields[1]),    # 开盘
                    "close": float(fields[2]),   # 收盘
                    "high": float(fields[3]),    # 最高
                    "low": float(fields[4]),     # 最低
                    "volume": float(fields[5]),  # 成交量
                    "amount": float(fields[6]),  # 成交额
                })

        return result

    except Exception as e:
        logger.error(f"  [{secid}] 东方财富API请求失败: {e}")
        return []


def step3_fetch_and_save_index_history(conn: sqlite3.Connection):
    """
    步骤3：抓取五大指数的所有历史K线数据并写入daily_quotes
    """
    logger.info("=" * 60)
    logger.info("步骤3: 抓取五大指数历史行情数据")
    logger.info("=" * 60)

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    for idx in INDEX_LIST:
        fund_code = idx["fund_code"]
        secid = idx["secid"]
        fund_name = idx["fund_name"]

        logger.info(f"\n  --- {fund_code} {fund_name} (secid={secid}) ---")

        # 抓取历史数据
        klines = fetch_index_history_eastmoney(secid)

        if not klines:
            logger.error(f"  ✗ {fund_code} 未获取到数据")
            continue

        logger.info(f"  获取到 {len(klines)} 条K线数据 ({klines[0]['date']} ~ {klines[-1]['date']})")

        # 批量插入（每500条提交一次）
        inserted = 0
        skipped = 0
        batch_size = 500
        batch = []

        for kline in klines:
            batch.append((
                fund_code,
                kline["date"],
                kline["open"],
                kline["high"],
                kline["low"],
                kline["close"],
                kline["close"],  # acc_nav 用收盘价填充（指数没有累计净值概念）
                now,
            ))

            if len(batch) >= batch_size:
                ins, skip = _batch_insert(conn, batch)
                inserted += ins
                skipped += skip
                batch = []

        # 剩余数据
        if batch:
            ins, skip = _batch_insert(conn, batch)
            inserted += ins
            skipped += skip

        logger.info(f"  ✓ {fund_code} 插入 {inserted} 条, 跳过(已存在) {skipped} 条")

        # 请求间隔，避免被封IP
        time.sleep(0.5)

    logger.info("\n所有指数历史数据抓取完成!")


def _batch_insert(conn: sqlite3.Connection, batch: list) -> tuple:
    """批量插入数据，返回 (inserted_count, skipped_count)"""
    inserted = 0
    skipped = 0

    for row in batch:
        try:
            conn.execute("""
                INSERT OR IGNORE INTO daily_quotes 
                (fund_code, quote_date, open_price, high_price, low_price, close_price, acc_nav, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, row)
            if conn.total_changes:
                inserted += 1
        except sqlite3.IntegrityError:
            skipped += 1

    conn.commit()
    # 简化：用总数减去跳过数来估算
    return len(batch) - skipped, skipped


def main():
    logger.info("=" * 60)
    logger.info("ETF管理系统 - 指数数据管理脚本")
    logger.info(f"数据库路径: {DB_PATH}")
    logger.info(f"执行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 60)

    conn = get_db_connection()

    try:
        # 步骤1: 删除广发天天红货币B的daily_quotes数据
        step1_delete_currency_fund_quotes(conn)

        # 步骤2: 插入五大指数信息
        step2_insert_index_info(conn)

        # 步骤3: 抓取并保存历史行情数据
        step3_fetch_and_save_index_history(conn)

        # 最终验证
        logger.info("\n" + "=" * 60)
        logger.info("最终验证")
        logger.info("=" * 60)

        cursor = conn.execute("""
            SELECT fund_code, fund_name FROM fund_info 
            WHERE fund_type = '股票指数'
            ORDER BY fund_code
        """)
        indices = cursor.fetchall()
        logger.info(f"fund_info 中的指数: {len(indices)} 条")
        for row in indices:
            count_cur = conn.execute(
                "SELECT COUNT(*) FROM daily_quotes WHERE fund_code = ?",
                (row["fund_code"],)
            )
            count = count_cur.fetchone()[0]
            logger.info(f"  {row['fund_code']:12s}  {row['fund_name']:12s}  {count} 条行情数据")

        # 确认货币B已删除
        count_cur = conn.execute(
            "SELECT COUNT(*) FROM daily_quotes WHERE fund_code = '002183'"
        )
        count = count_cur.fetchone()[0]
        logger.info(f"\n  广发天天红货币B(002183) daily_quotes: {count} 条 {'(已清理)' if count == 0 else '(未清理!)'}")

    finally:
        conn.close()

    logger.info("\n脚本执行完毕!")


if __name__ == "__main__":
    main()
