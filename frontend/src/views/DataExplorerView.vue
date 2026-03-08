<template>
  <div class="space-y-5">
    <!-- 表选择卡片 -->
    <div class="flex gap-3 h-28">
      <div
        v-for="table in tables"
        :key="table.name"
        @click="selectTable(table.name)"
        :class="[
          'w-40 rounded-lg p-4 cursor-pointer transition-all duration-200 border-2 flex-shrink-0',
          activeTable === table.name
            ? 'border-blue-500 bg-blue-50 shadow-md'
            : 'border-gray-200 bg-white hover:border-blue-300 hover:shadow-sm',
        ]"
      >
        <div class="text-xs text-gray-500 mb-1">{{ table.label }}</div>
        <div class="text-lg font-bold text-gray-800">{{ table.count }}</div>
        <div class="text-xs text-gray-400 mt-1 truncate">{{ table.name }}</div>
      </div>
    </div>

    <!-- 数据表格 -->
    <div v-if="activeTable" class="bg-white rounded-lg shadow-sm border border-gray-200">
      <div class="flex items-center justify-between px-5 py-3 border-b border-gray-100">
        <div class="flex items-center gap-3">
          <span class="font-semibold text-gray-700">{{ activeLabel }}</span>
          <t-tag theme="primary" variant="light" size="small">
            {{ tableData.total }} 条记录
          </t-tag>
        </div>
        <div class="flex items-center gap-2">
          <t-select
            v-model="pageSize"
            :options="pageSizeOptions"
            size="small"
            style="width: 120px"
            @change="onPageSizeChange"
          />
        </div>
      </div>

      <div class="overflow-x-auto">
        <t-table
          :data="tableData.data"
          :columns="tableColumns"
          :loading="loading"
          row-key="quote_id"
          :sort="currentSort"
          @sort-change="onSortChange"
          stripe
          hover
          size="small"
          table-layout="auto"
          :max-height="520"
        />
      </div>

      <div class="flex justify-center py-3 border-t border-gray-100">
        <t-pagination
          v-model="currentPage"
          :total="tableData.total"
          :page-size="pageSize"
          :page-size-options="[20, 50, 100, 200]"
          show-jumper
          @change="onPageChange"
          size="small"
        />
      </div>
    </div>

    <!-- 空状态 -->
    <div v-else class="bg-white rounded-lg shadow-sm border border-gray-200 p-16 text-center">
      <div class="text-gray-400 text-lg mb-2">请选择一个表查看数据</div>
      <div class="text-gray-300 text-sm">点击上方的表卡片即可查看对应数据明细</div>
    </div>

    <!-- SQL 执行区域 -->
    <div class="bg-white rounded-lg shadow-sm border border-gray-200 p-5 space-y-4">
      <div class="flex items-center gap-4">
        <t-button theme="primary" :loading="sqlLoading" @click="runSql">执行 SQL</t-button>
        <div>
          <div class="font-semibold text-gray-700">SQL 查询</div>
          <div class="text-xs text-gray-400 mt-1">仅支持只读查询（SELECT / DESC），每次执行一条语句</div>
        </div>
      </div>

      <textarea
        v-model="sqlText"
        class="w-full min-h-[120px] rounded-md border border-gray-200 p-3 font-mono text-sm focus:outline-none focus:ring-2 focus:ring-blue-200"
      />
      <div class="text-xs text-gray-400">
        常用示例：<code>select * from fund_info;</code>、<code>desc fund_info;</code>
      </div>


      <div v-if="sqlResult" class="space-y-3">
        <div class="flex items-center gap-2 text-sm text-gray-500">
          <span>返回 {{ sqlResult.row_count }} 条</span>
          <t-tag v-if="sqlResult.truncated" theme="warning" variant="light" size="small">
            已自动限制最多 500 条
          </t-tag>
        </div>

        <div class="overflow-x-auto border border-gray-100 rounded">
          <t-table
            :data="sqlResult.rows"
            :columns="sqlColumns"
            size="small"
            stripe
            hover
            :max-height="360"
          />
        </div>
      </div>
    </div>
  </div>
</template>


<script setup lang="ts">
import { ref, reactive, onMounted, computed } from 'vue'
import { MessagePlugin } from 'tdesign-vue-next'
import { getTableList, getTableData, executeTableSql } from '../api'


interface TableInfo {
  name: string
  label: string
  count: number
  columns: { name: string; type: string }[]
}

interface SqlResult {
  columns: string[]
  rows: any[]
  row_count: number
  truncated: boolean
}


// 字段单位格式化映射
const FIELD_UNIT_MAP: Record<string, string> = {
  shares: '份',
  holding_shares: '份',
  base_shares: '份',
  avg_buy_price: '元',
  current_price: '元',
  holding_value: '元',
  invested_capital: '元',
  profit_loss_amount: '元',
  dca_amount: '元',
  dca_total_invested: '元',
  amount: '元',
  fee: '元',
}


// 格式化数值：保留2位小数 + 单位
function formatWithUnit(value: any, unit: string): string {
  const num = parseFloat(value)
  if (isNaN(num)) return value ?? ''
  return num.toFixed(2) + ' ' + unit
}

// 英文列名 → 中文标题映射（基于当前 5 张核心表）
const COLUMN_LABEL_MAP: Record<string, string> = {
  // 通用字段
  id: 'ID',
  created_at: '创建时间',
  updated_at: '更新时间',
  fund_code: '基金代码',
  fund_name: '基金名称',
  platform: '平台',
  note: '备注',

  // fund_info
  fund_company: '基金公司',
  fund_type: '基金类型',
  tracking_index: '跟踪指数',
  risk_level: '风险等级',
  fund_category: '基金分类',
  top_holdings: '重仓持股',
  risk_points: '风险要点',
  return_1y: '近1年收益',
  return_3y: '近3年收益',
  return_since_inception: '成立以来收益',
  inception_date: '成立日期',

  // fund_holdings
  holding_id: '持仓ID',
  holding_shares: '持有份额',
  avg_buy_price: '平均买入价',
  base_shares: '底仓份额',
  current_price: '当前净值/价格',
  holding_value: '持仓市值',
  invested_capital: '累计投入金额',
  profit_loss_amount: '持仓盈亏金额',
  return_rate: '收益率(%)',
  dca_is_active: '定投启用',
  dca_frequency: '定投频率',
  dca_amount: '每期定投金额',
  dca_type: '定投类型',
  dca_total_invested: '定投累计金额',
  first_buy_date: '首次买入日期',
  last_update_date: '最后更新日期',

  // daily_quotes
  quote_id: '记录ID',
  quote_date: '净值日期',
  open_price: '开盘净值',
  high_price: '最高净值',
  low_price: '最低净值',
  close_price: '收盘净值',
  acc_nav: '累计净值',
  daily_change_pct: '日涨跌幅', // 保留，尽管新表没存，但如果是计算字段可能用到
  daily_value: '日市值',
  daily_pnl: '日盈亏',

  // trading_rules
  rule_id: '规则ID',
  rule_type: '规则类型',
  condition_desc: '触发条件',
  threshold: '阈值',
  action_desc: '执行操作',
  priority: '优先级',
  is_active: '启用状态',

  // trade_records
  record_id: '记录ID',
  record_type: '记录类型',
  record_date: '记录日期',
  signal_type: '信号类型',
  trigger_condition: '触发条件',
  trigger_value: '触发值',
  suggested_action: '建议操作',
  exec_status: '执行状态',
  exec_date: '执行日期',
  actual_action: '实际操作',
  amount: '金额',
  shares: '份额',
  fee: '手续费',
}

// 每个表的默认排序配置（与后端 DEFAULT_SORT 对应）
const DEFAULT_SORT_MAP: Record<string, { sortBy: string; descending: boolean }> = {
  fund_info: { sortBy: 'fund_code', descending: false },
  fund_holdings: { sortBy: 'fund_code', descending: false },
  daily_quotes: { sortBy: 'quote_date', descending: true },
  trading_rules: { sortBy: 'fund_category', descending: false },
  trade_records: { sortBy: 'record_date', descending: true },
}



const tables = ref<TableInfo[]>([])
const activeTable = ref('')
const activeLabel = ref('')
const loading = ref(false)
const currentPage = ref(1)
const pageSize = ref(50)
const currentSort = ref<any>(null)

const pageSizeOptions = [
  { label: '每页 20 条', value: 20 },
  { label: '每页 50 条', value: 50 },
  { label: '每页 100 条', value: 100 },
  { label: '每页 200 条', value: 200 },
]

const tableData = reactive<{
  total: number
  columns: string[]
  data: any[]
}>({
  total: 0,
  columns: [],
  data: [],
})

const tableColumns = ref<any[]>([])

const sqlLoading = ref(false)
const sqlText = ref(`select * from fund_info;`)

const sqlResult = ref<SqlResult | null>(null)
const sqlColumns = computed(() => {
  if (!sqlResult.value) return []
  return sqlResult.value.columns.map((col) => ({
    colKey: col,
    title: getBilingualColumnTitle(col),
    ellipsis: true,
    width: getColumnWidth(col),
  }))
})



onMounted(async () => {
  const res = await getTableList()
  tables.value = res.data
  // 默认选中第一个表
  if (tables.value.length > 0) {
    selectTable(tables.value[0].name)
  }
})

async function selectTable(tableName: string) {
  activeTable.value = tableName
  const t = tables.value.find((t) => t.name === tableName)
  activeLabel.value = t?.label || tableName
  currentPage.value = 1
  // 设置该表的默认排序
  currentSort.value = DEFAULT_SORT_MAP[tableName] || null
  await fetchData()
}

async function fetchData() {
  loading.value = true
  const params: any = {
    page: currentPage.value,
    page_size: pageSize.value,
  }
  if (currentSort.value?.sortBy) {
    params.sort_by = currentSort.value.sortBy
    params.sort_order = currentSort.value.descending ? 'desc' : 'asc'
  }
  const res = await getTableData(activeTable.value, params)
  tableData.total = res.data.total
  tableData.columns = res.data.columns
  tableData.data = res.data.data

  // 动态生成列配置，排除不需要显示的列
  const HIDDEN_COLUMNS = ['quote_id'] // 隐藏主键列
  tableColumns.value = res.data.columns
    .filter((col: string) => !HIDDEN_COLUMNS.includes(col))
    .map((col: string) => {
      const config: any = {
        colKey: col,
        title: getBilingualColumnTitle(col),
        sortable: true,
        ellipsis: true,
        width: getColumnWidth(col),
      }

      // 为有单位映射的字段添加格式化
      if (FIELD_UNIT_MAP[col]) {
        const unit = FIELD_UNIT_MAP[col]
        config.cell = (_h: any, { row }: any) => formatWithUnit(row[col], unit)
      }
      return config
    })

  loading.value = false
}

function getBilingualColumnTitle(col: string): string {
  const cnTitle = COLUMN_LABEL_MAP[col]
  return cnTitle ? `${col} / ${cnTitle}` : col
}

function getColumnWidth(col: string): number | undefined {

  // 针对常见字段设置合理宽度
  if (col.includes('id') && col.length <= 10) return 80
  if (col.includes('code')) return 110
  if (col.includes('name')) return 180
  if (col.includes('date') || col.includes('at')) return 160
  if (col.includes('desc') || col.includes('condition') || col.includes('action')) return 220
  if (col.includes('note') || col.includes('holdings')) return 200
  return 130
}

async function runSql() {
  const sql = sqlText.value.trim()
  if (!sql) {
    MessagePlugin.warning('请先输入 SQL')
    return
  }

  sqlLoading.value = true
  try {
    const res = await executeTableSql(sql)
    sqlResult.value = {
      columns: res.data.columns || [],
      rows: res.data.rows || [],
      row_count: res.data.row_count || 0,
      truncated: !!res.data.truncated,
    }
  } finally {
    sqlLoading.value = false
  }
}

function onPageChange(info: any) {
  currentPage.value = typeof info === 'object' ? info.current : info
  fetchData()
}

function onPageSizeChange() {
  currentPage.value = 1
  fetchData()
}

function onSortChange(sort: any) {
  currentSort.value = sort
  currentPage.value = 1
  fetchData()
}
</script>

