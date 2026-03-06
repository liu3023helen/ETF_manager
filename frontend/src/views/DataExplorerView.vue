<template>
  <div class="space-y-5">
    <!-- 表选择卡片 -->
    <div class="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-3">
      <div
        v-for="table in tables"
        :key="table.name"
        @click="selectTable(table.name)"
        :class="[
          'rounded-lg p-4 cursor-pointer transition-all duration-200 border-2',
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
          row-key="index"
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
      <div class="flex items-center justify-between">
        <div>
          <div class="font-semibold text-gray-700">SQL 查询</div>
          <div class="text-xs text-gray-400 mt-1">仅支持只读查询（SELECT / DESC），每次执行一条语句</div>
        </div>
        <t-button theme="primary" :loading="sqlLoading" @click="runSql">执行 SQL</t-button>
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
  cost_price: '元',
  base_shares: '份',
  tradable_shares: '份',
  total_invested: '元',
}

// 格式化数值：保留2位小数 + 单位
function formatWithUnit(value: any, unit: string): string {
  const num = parseFloat(value)
  if (isNaN(num)) return value ?? ''
  return num.toFixed(2) + ' ' + unit
}

// 英文列名 → 中文标题映射（基于数据库实际字段）
const COLUMN_LABEL_MAP: Record<string, string> = {
  // 通用字段
  id: 'ID',
  holding_id: '持仓ID',
  fund_code: '基金代码',
  fund_name: '基金名称',
  platform: '平台',
  shares: '持有份额',
  cost_price: '成本价',
  base_shares: '底仓份额',
  tradable_shares: '可交易份额',
  total_invested: '累计投入',
  first_buy_date: '首次买入日期',
  updated_at: '更新时间',
  created_at: '创建时间',
  is_active: '是否启用',
  amount: '金额',
  note: '备注',
  // fund_info 表
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
  // daily_quotes 表
  date: '日期',
  nav: '净值',
  acc_nav: '累计净值',
  daily_change_pct: '日涨跌幅',
  daily_value: '日市值',
  daily_pnl: '日盈亏',
  // dca_plans 表
  plan_id: '计划ID',
  frequency: '频率',
  dca_type: '定投类型',
  start_date: '开始日期',
  end_date: '结束日期',
  // transactions 表
  tx_id: '交易ID',
  tx_type: '交易类型',
  tx_date: '交易日期',
  nav_at_tx: '成交净值',
  fee: '手续费',
  // trading_rules 表
  rule_id: '规则ID',
  rule_type: '规则类型',
  condition_desc: '触发条件',
  threshold: '阈值',
  action_desc: '执行操作',
  priority: '优先级',
  // trade_signals 表
  signal_id: '信号ID',
  signal_date: '信号日期',
  signal_type: '信号类型',
  trigger_condition: '触发条件',
  suggested_action: '建议操作',
  exec_status: '执行状态',
  actual_action: '实际操作',
}

// 每个表的默认排序配置（与后端 DEFAULT_SORT 对应）
const DEFAULT_SORT_MAP: Record<string, { sortBy: string; descending: boolean }> = {
  fund_info: { sortBy: 'fund_code', descending: false },
  fund_holdings: { sortBy: 'fund_code', descending: false },
  daily_quotes: { sortBy: 'date', descending: false },
  trading_rules: { sortBy: 'rule_id', descending: false },
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

  // 动态生成列配置
  tableColumns.value = res.data.columns.map((col: string) => {
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

