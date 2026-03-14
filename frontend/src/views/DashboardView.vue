<template>
  <div>
    <!-- 核心指标 -->
    <div class="grid grid-cols-3 lg:grid-cols-6 gap-4 mb-6">
      <StatCard label="总资产" :value="'¥' + formatNum(summary.total_assets)" value-class="text-blue-700" />
      <StatCard label="累计买入" :value="'¥' + formatNum(summary.total_invested)" value-class="text-gray-700" />
      <StatCard label="累计卖出" :value="'¥' + formatNum(summary.total_sold)" value-class="text-gray-700" />
      <StatCard label="净投入" :value="'¥' + formatNum(summary.net_invested)" value-class="text-gray-700" />
      <StatCard
        label="总收益"
        :value-class="summary.total_pnl >= 0 ? 'text-red-500' : 'text-green-600'"
      >
        {{ summary.total_pnl >= 0 ? '+' : '' }}¥{{ formatNum(summary.total_pnl) }}
        <span class="text-sm ml-1">({{ summary.pnl_rate >= 0 ? '+' : '' }}{{ summary.pnl_rate }}%)</span>
      </StatCard>
      <StatCard label="持仓基金数" :value="summary.fund_count" value-class="text-gray-700">
        <template #extra>
          <div v-if="pendingCount > 0" class="text-xs text-orange-500 mt-1">
            {{ pendingCount }} 条待处理记录
          </div>
        </template>
      </StatCard>
    </div>

    <!-- 图表区 -->
    <div class="grid grid-cols-2 gap-4 mb-6">
      <t-card title="资产分类分布" :bordered="true">
        <v-chart
          ref="categoryChartRef"
          :option="categoryChartOption"
          autoresize
          class="h-72"
          @click="onCategoryChartClick"
        />
      </t-card>
      <t-card title="平台资产分布" :bordered="true">
        <v-chart
          ref="platformChartRef"
          :option="platformChartOption"
          autoresize
          class="h-72"
          @click="onPlatformChartClick"
        />
      </t-card>
    </div>

    <!-- 持仓明细 -->
    <t-card :bordered="true">
      <template #title>
        <div class="flex items-center gap-2">
          <span>持仓明细</span>
          <t-tag
            v-if="activeFilter"
            theme="primary"
            variant="light"
            size="small"
            closable
            @close="clearFilter"
          >
            {{ activeFilter.type === 'category' ? '分类' : '平台' }}：{{ activeFilter.value }}
          </t-tag>
        </div>
      </template>
      <t-table :data="filteredHoldings" :columns="holdingColumns" row-key="holding_id" hover size="small" />
    </t-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import VChart from '@/utils/echarts'
import { formatNum } from '@/utils/format'
import StatCard from '@/components/StatCard.vue'
import { getDashboardSummary, getHoldings } from '../api'

const summary = ref<any>({
  total_assets: 0, total_invested: 0, total_sold: 0, net_invested: 0,
  total_pnl: 0, pnl_rate: 0,
  fund_count: 0, category_distribution: [], platform_distribution: [], pending_records: 0,
})
const holdings = ref<any[]>([])
const pendingCount = computed(() => summary.value.pending_records ?? 0)

// 筛选状态
const activeFilter = ref<{ type: 'category' | 'platform'; value: string } | null>(null)
const categoryChartRef = ref<any>(null)
const platformChartRef = ref<any>(null)

// 根据筛选条件过滤持仓
const filteredHoldings = computed(() => {
  if (!activeFilter.value) return holdings.value
  const { type, value } = activeFilter.value
  if (type === 'category') {
    return holdings.value.filter((h: any) => h.fund_category === value)
  }
  return holdings.value.filter((h: any) => h.platform === value)
})

// 清除筛选
function clearFilter() {
  activeFilter.value = null
  // 取消图表高亮
  clearChartSelection(categoryChartRef.value)
  clearChartSelection(platformChartRef.value)
}

function clearChartSelection(chartRef: any) {
  const chart = chartRef?.chart
  if (!chart) return
  chart.dispatchAction({ type: 'downplay', seriesIndex: 0 })
}

// 点击资产分类饼图
function onCategoryChartClick(params: any) {
  const clickedName = params.name
  if (activeFilter.value?.type === 'category' && activeFilter.value.value === clickedName) {
    // 再次点击同一项 → 取消筛选
    clearFilter()
  } else {
    // 清除平台图的高亮
    clearChartSelection(platformChartRef.value)
    activeFilter.value = { type: 'category', value: clickedName }
  }
}

// 点击平台分布条形图
function onPlatformChartClick(params: any) {
  const clickedName = params.name
  if (activeFilter.value?.type === 'platform' && activeFilter.value.value === clickedName) {
    clearFilter()
  } else {
    clearChartSelection(categoryChartRef.value)
    activeFilter.value = { type: 'platform', value: clickedName }
  }
}

const categoryChartOption = computed(() => {
  const selected = activeFilter.value?.type === 'category' ? activeFilter.value.value : null
  return {
    tooltip: { trigger: 'item', formatter: '{b}: ¥{c} ({d}%)' },
    legend: { bottom: 0 },
    color: ['#d54941', '#0052d9', '#e37318', '#2ba471', '#8eabff', '#a6a6a6'],
    series: [{
      type: 'pie', radius: ['40%', '70%'],
      selectedMode: 'single',
      label: { show: true, formatter: '{b}\n{d}%' },
      data: summary.value.category_distribution.map((d: any) => ({
        name: d.category,
        value: d.value,
        selected: d.category === selected,
        itemStyle: selected && d.category !== selected ? { opacity: 0.35 } : {},
      })),
    }],
  }
})

const platformChartOption = computed(() => {
  const selected = activeFilter.value?.type === 'platform' ? activeFilter.value.value : null
  const platforms = summary.value.platform_distribution.map((d: any) => d.platform)
  const values = summary.value.platform_distribution.map((d: any) => d.value)
  return {
    tooltip: { trigger: 'axis' },
    grid: { left: 80, right: 30, top: 20, bottom: 30 },
    xAxis: { type: 'value', axisLabel: { formatter: '¥{value}' } },
    yAxis: { type: 'category', data: platforms },
    series: [{
      type: 'bar', barWidth: 30,
      data: values.map((v: number, i: number) => ({
        value: v,
        itemStyle: {
          color: selected && platforms[i] !== selected ? 'rgba(0,82,217,0.25)' : '#0052d9',
        },
      })),
    }],
  }
})

const holdingColumns = [
  { colKey: 'fund_name', title: '基金名称', width: 200 },
  { colKey: 'fund_code', title: '代码', width: 100 },
  { colKey: 'platform', title: '平台', width: 120 },
  { colKey: 'fund_category', title: '分类', width: 100 },
  { colKey: 'shares', title: '持有份额', width: 110, cell: (_h: any, { row }: any) => formatNum(row.shares) + ' 份' },
  { colKey: 'cost_price', title: '成本价', width: 100, cell: (_h: any, { row }: any) => formatNum(row.cost_price) + ' 元' },
  { colKey: 'base_shares', title: '底仓份额', width: 100, cell: (_h: any, { row }: any) => formatNum(row.base_shares) + ' 份' },
  { colKey: 'tradable_shares', title: '可交易份额', width: 110, cell: (_h: any, { row }: any) => formatNum(row.tradable_shares) + ' 份' },
  { colKey: 'total_invested', title: '累计投入', width: 110, cell: (_h: any, { row }: any) => formatNum(row.total_invested) + ' 元' },
  { colKey: 'current_value', title: '当前市值', width: 110, cell: (_h: any, { row }: any) => '¥' + formatNum(row.current_value) },
  { colKey: 'risk_level', title: '风险等级', width: 120 },
]

onMounted(async () => {
  const [sumRes, holdRes] = await Promise.all([getDashboardSummary(), getHoldings()])
  summary.value = sumRes.data
  holdings.value = holdRes.data
})
</script>
