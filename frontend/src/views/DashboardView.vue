<template>
  <div>
    <!-- 核心指标 -->
    <div class="grid grid-cols-4 gap-4 mb-6">
      <StatCard label="总资产" :value="'¥' + formatNum(summary.total_assets)" value-class="text-blue-700" />
      <StatCard label="总投入" :value="'¥' + formatNum(summary.total_invested)" value-class="text-gray-700" />
      <StatCard
        label="总收益"
        :value-class="summary.total_pnl >= 0 ? 'text-red-500' : 'text-green-600'"
      >
        {{ summary.total_pnl >= 0 ? '+' : '' }}¥{{ formatNum(summary.total_pnl) }}
        <span class="text-sm ml-1">({{ summary.pnl_rate >= 0 ? '+' : '' }}{{ summary.pnl_rate }}%)</span>
      </StatCard>
      <StatCard label="持仓基金数" :value="summary.fund_count" value-class="text-gray-700">
        <template #extra>
          <div v-if="summary.pending_signals > 0" class="text-xs text-orange-500 mt-1">
            {{ summary.pending_signals }} 条待处理信号
          </div>
        </template>
      </StatCard>
    </div>

    <!-- 图表区 -->
    <div class="grid grid-cols-2 gap-4 mb-6">
      <t-card title="资产分类分布" :bordered="true">
        <v-chart :option="categoryChartOption" autoresize class="h-72" />
      </t-card>
      <t-card title="平台资产分布" :bordered="true">
        <v-chart :option="platformChartOption" autoresize class="h-72" />
      </t-card>
    </div>

    <!-- 持仓明细 -->
    <t-card title="持仓明细" :bordered="true">
      <t-table :data="holdings" :columns="holdingColumns" row-key="holding_id" hover size="small" />
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
  total_assets: 0, total_invested: 0, total_pnl: 0, pnl_rate: 0,
  fund_count: 0, category_distribution: [], platform_distribution: [], pending_signals: 0,
})
const holdings = ref<any[]>([])

const categoryChartOption = computed(() => ({
  tooltip: { trigger: 'item', formatter: '{b}: ¥{c} ({d}%)' },
  legend: { bottom: 0 },
  color: ['#d54941', '#0052d9', '#e37318', '#2ba471', '#8eabff', '#a6a6a6'],
  series: [{
    type: 'pie', radius: ['40%', '70%'],
    label: { show: true, formatter: '{b}\n{d}%' },
    data: summary.value.category_distribution.map((d: any) => ({ name: d.category, value: d.value })),
  }],
}))

const platformChartOption = computed(() => ({
  tooltip: { trigger: 'axis' },
  grid: { left: 80, right: 30, top: 20, bottom: 30 },
  xAxis: { type: 'value', axisLabel: { formatter: '¥{value}' } },
  yAxis: { type: 'category', data: summary.value.platform_distribution.map((d: any) => d.platform) },
  series: [{
    type: 'bar', barWidth: 30,
    data: summary.value.platform_distribution.map((d: any) => d.value),
    itemStyle: { color: '#0052d9' },
  }],
}))

const holdingColumns = [
  { colKey: 'fund_name', title: '基金名称', width: 200 },
  { colKey: 'fund_code', title: '代码', width: 100 },
  { colKey: 'platform', title: '平台', width: 120 },
  { colKey: 'fund_category', title: '分类', width: 100 },
  { colKey: 'shares', title: '持仓份额', width: 110, cell: (_h: any, { row }: any) => formatNum(row.shares) },
  { colKey: 'cost_price', title: '成本价', width: 100, cell: (_h: any, { row }: any) => formatNum(row.cost_price) },
  { colKey: 'current_value', title: '当前市值', width: 110, cell: (_h: any, { row }: any) => '¥' + formatNum(row.current_value) },
  { colKey: 'base_shares', title: '底仓', width: 100, cell: (_h: any, { row }: any) => formatNum(row.base_shares) },
  { colKey: 'risk_level', title: '风险等级', width: 120 },
]

onMounted(async () => {
  const [sumRes, holdRes] = await Promise.all([getDashboardSummary(), getHoldings()])
  summary.value = sumRes.data
  holdings.value = holdRes.data
})
</script>
