"""
将SQLite数据库中的所有表导出为Excel文件
包含中英文字段名
"""
import sqlite3
import pandas as pd
from pathlib import Path

# 字段中文名映射字典
FIELD_NAME_MAPPING = {
    'fund_info': {
        'fund_code': '基金代码',
        'fund_name': '基金名称',
        'fund_company': '基金公司',
        'fund_type': '基金类型',
        'tracking_index': '跟踪指数',
        'risk_level': '风险等级',
        'fund_category': '基金分类',
        'top_holdings': '前十大持仓',
        'risk_points': '风险提示',
        'return_1y': '近1年收益率',
        'return_3y': '近3年收益率',
        'return_since_inception': '成立以来收益率',
        'created_at': '创建时间',
        'updated_at': '更新时间'
    },
    'my_holdings': {
        'holding_id': '持仓记录ID',
        'fund_code': '基金代码',
        'fund_name': '基金名称',
        'platform': '持仓平台',
        'holding_shares': '持有份额',
        'avg_buy_price': '平均买入价',
        'base_shares': '底仓份额',
        'tradable_shares': '可交易份额',
        'current_price': '当前价格',
        'holding_value': '持仓总值',
        'invested_capital': '累计投入金额',
        'profit_loss_amount': '盈亏金额',
        'return_rate': '收益率',
        'first_buy_date': '首次买入日期',
        'last_update_date': '最后更新日期',
        'created_at': '创建时间',
        'updated_at': '更新时间'
    },
    'daily_quotes': {
        'quote_id': '记录ID',
        'fund_code': '基金代码',
        'fund_name': '基金名称',
        'quote_date': '净值日期',
        'nav': '单位净值',
        'acc_nav': '累计净值',
        'daily_change_pct': '当日涨跌幅',
        'daily_value': '当日持仓市值',
        'daily_pnl': '当日盈亏金额',
        'created_at': '创建时间'
    },
    'dca_plans': {
        'plan_id': '计划ID',
        'fund_code': '基金代码',
        'fund_name': '基金名称',
        'platform': '定投平台',
        'is_active': '是否启用',
        'frequency': '定投频率',
        'amount': '每期金额',
        'dca_type': '定投类型',
        'total_invested': '累计已投金额',
        'start_date': '开始日期',
        'next_execute_date': '下次执行日期',
        'created_at': '创建时间',
        'updated_at': '更新时间'
    },
    'transactions': {
        'tx_id': '交易ID',
        'fund_code': '基金代码',
        'fund_name': '基金名称',
        'platform': '交易平台',
        'tx_type': '交易类型',
        'tx_date': '交易日期',
        'amount': '交易金额',
        'shares': '交易份额',
        'nav_at_tx': '成交时净值',
        'fee': '手续费',
        'tx_status': '交易状态',
        'note': '备注',
        'created_at': '创建时间'
    },
    'trading_rules': {
        'rule_id': '规则ID',
        'fund_category': '基金分类',
        'rule_type': '规则类型',
        'condition_desc': '触发条件',
        'threshold': '阈值',
        'action_desc': '操作描述',
        'priority': '优先级',
        'is_active': '是否启用',
        'created_at': '创建时间',
        'updated_at': '更新时间'
    },
    'trade_signals': {
        'signal_id': '信号ID',
        'fund_code': '基金代码',
        'fund_name': '基金名称',
        'signal_date': '信号日期',
        'signal_type': '信号类型',
        'trigger_condition': '触发条件',
        'trigger_value': '触发数值',
        'suggested_action': '建议操作',
        'exec_status': '执行状态',
        'actual_action': '实际操作',
        'note': '备注',
        'created_at': '创建时间',
        'updated_at': '更新时间'
    }
}

def export_tables_to_excel():
    # 数据库路径
    db_path = Path(__file__).parent.parent / 'data' / 'etf_manager.db'
    
    # 输出目录
    output_dir = Path(__file__).parent.parent / 'data'
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 连接数据库
    conn = sqlite3.connect(db_path)
    
    try:
        # 获取所有表名
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = cursor.fetchall()
        
        print(f"找到 {len(tables)} 张表：")
        for table in tables:
            print(f"  - {table[0]}")
        
        # 将所有表导出到一个Excel文件的不同工作表
        output_file = output_dir / '数据库表导出.xlsx'
        
        with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
            for table_name in tables:
                table_name = table_name[0]
                
                # 跳过系统表
                if table_name == 'sqlite_sequence':
                    continue
                
                # 读取表数据
                df = pd.read_sql_query(f"SELECT * FROM {table_name}", conn)
                
                # 获取字段中文名映射
                field_mapping = FIELD_NAME_MAPPING.get(table_name, {})
                
                # 创建新的列名（英文 + 中文）
                new_columns = []
                for col in df.columns:
                    chinese_name = field_mapping.get(col, col)
                    if chinese_name != col:
                        new_columns.append(f"{col}\n{chinese_name}")
                    else:
                        new_columns.append(col)
                
                # 重命名列
                df.columns = new_columns
                
                # 导出到Excel工作表
                df.to_excel(writer, sheet_name=table_name, index=False)
                
                print(f"[OK] 已导出表: {table_name} ({len(df)} 行, {len(df.columns)} 列)")
        
        print(f"\n[成功] 所有表已导出到: {output_file}")
        print(f"   文件大小: {output_file.stat().st_size / 1024:.2f} KB")
        
    except Exception as e:
        print(f"[错误] 导出失败: {e}")
        raise
    finally:
        conn.close()

if __name__ == '__main__':
    export_tables_to_excel()

