"""
根据数据库表结构创建新的Excel文件，并迁移现有数据
表名和字段名包含中英文对照
"""
import pandas as pd
from pathlib import Path
import sys

# 表名中英文映射
TABLE_NAME_MAPPING = {
    'fund_info': 'fund_info(基金基本信息表)',
    'fund_holdings': 'fund_holdings(持仓管理表)',
    'daily_quotes': 'daily_quotes(每日净值表)',
    'dca_plans': 'dca_plans(定投计划表)',
    'transactions': 'transactions(交易记录表)',
    'trading_rules': 'trading_rules(交易规则配置表)',
    'trade_signals': 'trade_signals(交易信号表)'
}

# 字段中英文映射字典（根据数据库表结构.md）
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
        'risk_points': '风险提示要点',
        'return_1y': '近1年收益率',
        'return_3y': '近3年收益率',
        'return_since_inception': '成立以来收益率',
        'created_at': '创建时间',
        'updated_at': '更新时间'
    },
    'fund_holdings': {
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

def migrate_excel():
    """迁移Excel数据到新格式"""
    # 文件路径
    data_dir = Path(__file__).parent.parent / 'data'
    input_file = data_dir / '数据库表导出.xlsx'
    output_file = data_dir / '数据库表导出_新版.xlsx'
    
    print(f"读取文件: {input_file}")
    print(f"输出文件: {output_file}")
    print("-" * 60)
    
    try:
        # 读取原始Excel文件
        excel_file = pd.ExcelFile(input_file)
        
        # 创建新的Excel文件
        with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
            # 表映射关系：旧表名 -> 新表名
            table_mapping = {
                'daily_quotes': 'daily_quotes',
                'dca_plans': 'dca_plans',
                'fund_info': 'fund_info',
                'my_holdings': 'fund_holdings',  # 旧表名是my_holdings
                'trade_signals': 'trade_signals',
                'trading_rules': 'trading_rules',
                'transactions': 'transactions'
            }
            
            for old_sheet_name, new_table_name in table_mapping.items():
                if old_sheet_name not in excel_file.sheet_names:
                    print(f"[跳过] 工作表不存在: {old_sheet_name}")
                    continue
                
                # 读取原表数据
                df = pd.read_excel(excel_file, sheet_name=old_sheet_name)
                
                # 处理列名：提取英文部分（去掉中文）
                new_columns = []
                for col in df.columns:
                    if '\n' in str(col):
                        # 提取英文部分（\n之前的部分）
                        english_name = str(col).split('\n')[0]
                        new_columns.append(english_name)
                    else:
                        new_columns.append(col)
                df.columns = new_columns
                
                # 根据表名进行字段映射和数据转换
                if old_sheet_name == 'daily_quotes':
                    # daily_quotes字段映射
                    df = migrate_daily_quotes(df)
                elif old_sheet_name == 'dca_plans':
                    # dca_plans字段映射
                    df = migrate_dca_plans(df)
                elif old_sheet_name == 'fund_info':
                    # fund_info字段映射
                    df = migrate_fund_info(df)
                elif old_sheet_name == 'my_holdings':
                    # my_holdings字段映射 -> fund_holdings
                    df = migrate_fund_holdings(df)
                elif old_sheet_name == 'trade_signals':
                    # trade_signals字段映射
                    df = migrate_trade_signals(df)
                elif old_sheet_name == 'trading_rules':
                    # trading_rules字段映射
                    df = migrate_trading_rules(df)
                elif old_sheet_name == 'transactions':
                    # transactions字段映射
                    df = migrate_transactions(df)
                
                # 获取字段中文名映射
                field_mapping = FIELD_NAME_MAPPING.get(new_table_name, {})
                
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
                
                # 使用新的工作表名（包含中文）
                sheet_name = TABLE_NAME_MAPPING.get(new_table_name, new_table_name)
                
                # 写入Excel
                df.to_excel(writer, sheet_name=sheet_name, index=False)
                
                print(f"[OK] 已迁移表: {old_sheet_name} -> {sheet_name} ({len(df)} 行, {len(df.columns)} 列)")
        
        print("\n" + "=" * 60)
        print(f"[成功] 新Excel文件已创建: {output_file}")
        print(f"文件大小: {output_file.stat().st_size / 1024:.2f} KB")
        
    except Exception as e:
        print(f"[错误] 迁移失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

def migrate_daily_quotes(df):
    """迁移daily_quotes表"""
    # 字段映射：id -> quote_id, date -> quote_date
    column_mapping = {
        'id': 'quote_id',
        'date': 'quote_date'
    }
    
    # 重命名列
    df = df.rename(columns=column_mapping)
    
    # 添加缺失字段
    if 'fund_name' not in df.columns:
        df['fund_name'] = ''
    if 'created_at' not in df.columns:
        df['created_at'] = ''
    
    # 按目标字段顺序重新排列
    target_columns = ['quote_id', 'fund_code', 'fund_name', 'quote_date', 
                      'nav', 'acc_nav', 'daily_change_pct', 'daily_value', 
                      'daily_pnl', 'created_at']
    
    # 只保留目标字段中存在的列
    existing_columns = [col for col in target_columns if col in df.columns]
    df = df[existing_columns]
    
    return df

def migrate_dca_plans(df):
    """迁移dca_plans表"""
    # 字段映射：end_date -> next_execute_date
    column_mapping = {
        'end_date': 'next_execute_date'
    }
    
    # 重命名列
    df = df.rename(columns=column_mapping)
    
    # 添加缺失字段
    if 'fund_name' not in df.columns:
        df['fund_name'] = ''
    if 'created_at' not in df.columns:
        df['created_at'] = ''
    if 'updated_at' not in df.columns:
        df['updated_at'] = ''
    
    # 按目标字段顺序重新排列
    target_columns = ['plan_id', 'fund_code', 'fund_name', 'platform',
                      'is_active', 'frequency', 'amount', 'dca_type',
                      'total_invested', 'start_date', 'next_execute_date',
                      'created_at', 'updated_at']
    
    # 只保留目标字段中存在的列
    existing_columns = [col for col in target_columns if col in df.columns]
    df = df[existing_columns]
    
    return df

def migrate_fund_info(df):
    """迁移fund_info表"""
    # fund_info表字段基本匹配，保持不变
    # 按目标字段顺序重新排列
    target_columns = ['fund_code', 'fund_name', 'fund_company', 'fund_type',
                      'tracking_index', 'risk_level', 'fund_category',
                      'top_holdings', 'risk_points', 'return_1y',
                      'return_3y', 'return_since_inception',
                      'created_at', 'updated_at']
    
    # 只保留目标字段中存在的列
    existing_columns = [col for col in target_columns if col in df.columns]
    df = df[existing_columns]
    
    return df

def migrate_fund_holdings(df):
    """迁移fund_holdings表"""
    # 字段映射：my_holdings -> fund_holdings
    column_mapping = {
        'shares': 'holding_shares',
        'cost_price': 'avg_buy_price',
        'total_invested': 'invested_capital'
    }
    
    # 重命名列
    df = df.rename(columns=column_mapping)
    
    # 添加缺失字段
    if 'current_price' not in df.columns:
        df['current_price'] = None
    if 'holding_value' not in df.columns:
        df['holding_value'] = None
    if 'profit_loss_amount' not in df.columns:
        df['profit_loss_amount'] = None
    if 'return_rate' not in df.columns:
        df['return_rate'] = None
    if 'last_update_date' not in df.columns:
        df['last_update_date'] = ''
    if 'created_at' not in df.columns:
        df['created_at'] = ''
    
    # 按目标字段顺序重新排列
    target_columns = ['holding_id', 'fund_code', 'fund_name', 'platform',
                      'holding_shares', 'avg_buy_price', 'base_shares',
                      'tradable_shares', 'current_price', 'holding_value',
                      'invested_capital', 'profit_loss_amount', 'return_rate',
                      'first_buy_date', 'last_update_date',
                      'created_at', 'updated_at']
    
    # 只保留目标字段中存在的列
    existing_columns = [col for col in target_columns if col in df.columns]
    df = df[existing_columns]
    
    return df

def migrate_trade_signals(df):
    """迁移trade_signals表"""
    # 添加缺失字段
    if 'trigger_value' not in df.columns:
        df['trigger_value'] = None
    if 'note' not in df.columns:
        df['note'] = ''
    if 'updated_at' not in df.columns:
        df['updated_at'] = ''
    
    # 按目标字段顺序重新排列
    target_columns = ['signal_id', 'fund_code', 'fund_name', 'signal_date',
                      'signal_type', 'trigger_condition', 'trigger_value',
                      'suggested_action', 'exec_status', 'actual_action',
                      'note', 'created_at', 'updated_at']
    
    # 只保留目标字段中存在的列
    existing_columns = [col for col in target_columns if col in df.columns]
    df = df[existing_columns]
    
    return df

def migrate_trading_rules(df):
    """迁移trading_rules表"""
    # 添加缺失字段
    if 'created_at' not in df.columns:
        df['created_at'] = ''
    if 'updated_at' not in df.columns:
        df['updated_at'] = ''
    
    # 按目标字段顺序重新排列
    target_columns = ['rule_id', 'fund_category', 'rule_type',
                      'condition_desc', 'threshold', 'action_desc',
                      'priority', 'is_active', 'created_at', 'updated_at']
    
    # 只保留目标字段中存在的列
    existing_columns = [col for col in target_columns if col in df.columns]
    df = df[existing_columns]
    
    return df

def migrate_transactions(df):
    """迁移transactions表"""
    # 添加缺失字段
    if 'tx_status' not in df.columns:
        df['tx_status'] = '已成交'
    if 'note' not in df.columns:
        df['note'] = ''
    if 'created_at' not in df.columns:
        df['created_at'] = ''
    
    # 按目标字段顺序重新排列
    target_columns = ['tx_id', 'fund_code', 'fund_name', 'platform',
                      'tx_type', 'tx_date', 'amount', 'shares',
                      'nav_at_tx', 'fee', 'tx_status', 'note', 'created_at']
    
    # 只保留目标字段中存在的列
    existing_columns = [col for col in target_columns if col in df.columns]
    df = df[existing_columns]
    
    return df

if __name__ == '__main__':
    migrate_excel()
