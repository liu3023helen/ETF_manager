<template>
  <div>
    <!-- 收益汇总指标 -->
    <div class="grid grid-cols-4 gap-4 mb-6" v-if="summary.latest">
      <StatCard
        label="总资产"
        :value="'¥' + formatNum(summary.latest.total_assets)"
        value-class="text-blue-700"
      />
      <StatCard
        label="总浮动盈亏"
        :value-class="summary.latest.total_pnl >= 0 ? 'text-red-500' : 'text-green-600'"
      >
        {{ summary.latest.total_pnl >= 0 ? '+' : '' }}¥{{ formatNum(summary.latest.total_pnl) }}
        <span class="text-sm ml-1">({{ summary.latest.pnl_rate >= 0 ? '+' : '' }}{{ summary.latest.pnl_rate }}%)</span>
      </StatCard>
      <StatCard
        label="已实现收益"
        :value-class="summary.latest.realized_pnl >= 0 ? 'text-red-500' : 'text-green-600'"
      >
        {{ summary.latest.realized_pnl >= 0 ? '+' : '' }}¥{{ formatNum(summary.latest.realized_pnl) }}
      </StatCard>
      <StatCard label="持仓基金数" :value="summary.latest.fund_count" value-class="text-gray-700" />
    </div>

    <!-- 时间段收益对比 -->
    <div class="flex gap-3 mb-6 flex-wrap" v-if="summary.periods.length > 0">
      <div
        v-for="p in summary.periods"
        :key="p.label"
        class="flex-1 min-w-[120px] bg-white rounded-lg border border-gray-200 p-3 text-center"
      >
        <div class="text-xs text-gray-400 mb-1">{{ p.label }}</div>
        <div
          :class="[
            'text-lg font-bold',
            p.pnl_rate_change >= 0 ? 'text-red-500' : 'text-green-600',
          ]"
        >
          {{ p.pnl_rate_change >= 0 ? '+' : '' }}{{ p.pnl_rate_change }}%
        </div>
        <div class="text-xs text-gray-400 mt-1">
          {{ p.pnl_change >= 0 ? '+' : '' }}¥{{ formatNum(p.pnl_change) }}
        </div>
      </div>
    </div>

    <!-- 各基金盈亏对比 -->
    <t-card title="各基金盈亏对比" class="mb-4" :bordered="true">
      <div v-if="holdings.length === 0" class="text-center text-gray-400 py-10">暂无持仓数据</div>
      <v-chart v-else :option="holdingsPnlChartOption" autoresize :style="{ height: holdingsChartHeight }" />
    </t-card>

    <!-- 持仓收益明细表 -->
    <t-card title="持仓收益明细" class="mb-4" :bordered="true">
      <div v-if="holdings.length === 0" class="text-center text-gray-400 py-10">暂无持仓数据</div>
      <t-table
        v-else
        :data="holdingsTableData"
        :columns="holdingsColumns"
        row-key="holding_id"
        stripe
        hover
        size="small"
        table-layout="auto"
      />
    </t-card>

    <!-- 筛选栏 -->
    <t-card class="mb-4" :bordered="true">
      <div class="flex items-center gap-4 flex-wrap">
        <t-date-range-picker
          v-model="dateRange"
          class="w-72"
          @change="loadData"
        />
        <div class="flex gap-2">
          <t-button
            v-for="shortcut in shortcuts"
            :key="shortcut.label"
            :variant="activeShortcut === shortcut.label ? 'base' : 'outline'"
            :theme="activeShortcut === shortcut.label ? 'primary' : 'default'"
            size="small"
            @click="applyShortcut(shortcut)"
          >
            {{ shortcut.label }}
          </t-button>
        </div>
      </div>
    </t-card>

    <!-- 收益率曲线 -->
    <t-card title="收益率走势" class="mb-4" :bordered="true">
      <div v-if="snapshots.length === 0" class="text-center text-gray-400 py-10">暂无收益数据</div>
      <v-chart v-else :option="pnlRateChartOption" autoresize class="h-80" />
    </t-card>

    <!-- 资产走势 -->
    <t-card title="总资产 vs 总投入" class="mb-4" :bordered="true">
      <div v-if="snapshots.length === 0" class="text-center text-gray-400 py-10">暂无数据</div>
      <v-chart v-else :option="assetsChartOption" autoresize class="h-72" />
    </t-card>

    <!-- 每日盈亏 -->
    <t-card title="每日盈亏变动" :bordered="true">
      <div v-if="snapshots.length === 0" class="text-center text-gray-400 py-10">暂无数据</div>
      <v-chart v-else :option="dailyPnlChartOption" autoresize class="h-60" />
    </t-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed, h } from 'vue'
import VChart from '@/utils/echarts'
import { formatNum } from '@/utils/format'
import StatCard from '@/components/StatCard.vue'
import { getSnapshots, getSnapshotSummary, getHoldings } from '../api'

interface Snapshot {
  date: string
  total_assets: number
  total_invested: number
  total_pnl: number
  pnl_rate: number
  realized_pnl: number
  fund_count: number
}

interface Holding {
  holding_id: number
  fund_code: string
  fund_name: string
  fund_category: string
  platform: string
  holding_value: number
  total_invested: number
  total_sold: number
  net_invested: number
  profit_loss_amount: number
  return_rate: number
  shares: number
  cost_price: number
  current_price: number
}

const snapshots = ref<Snapshot[]>([])
const summary = ref<any>({ latest: null, periods: [] })
const holdings = ref<Holding[]>([])
const dateRange = ref<string[]>([])
const activeShortcut = ref('全部')

const shortcuts = [
  { label: '近1月', days: 30 },
  { label: '近3月', days: 90 },
  { label: '近6月', days: 180 },
  { label: '近1年', days: 365 },
  { label: '全部', days: 0 },
]

function applyShortcut(s: { label: string; days: number }) {
  activeShortcut.value = s.label
  if (s.days === 0) {
    dateRange.value = []
  } else {
    const now = new Date()
    const to = now.toISOString().slice(0, 10)
    const from = new Date(now.getTime() - s.days * 86400000).toISOString().slice(0, 10)
    dateRange.value = [from, to]
  }
  loadData()
}

async function loadData() {
  const params: any = {}
  if (dateRange.value?.length === 2) {
    params.date_from = dateRange.value[0]
    params.date_to = dateRange.value[1]
  }
  const res = await getSnapshots(params)
  snapshots.value = res.data
}

async function loadHoldings() {
  const res = await getHoldings()
  holdings.value = res.data
}

// ============================
// 各基金盈亏对比柱状图
// ============================
const sortedHoldings = computed(() => {
  return [...holdings.value].sort((a, b) => a.profit_loss_amount - b.profit_loss_amount)
})

const holdingsChartHeight = computed(() => {
  return Math.max(300, holdings.value.length * 36 + 60) + 'px'
})

const holdingsPnlChartOption = computed(() => {
  const items = sortedHoldings.value
  const names = items.map(h => {
    const name = h.fund_name || h.fund_code
    return name.length > 10 ? name.slice(0, 10) + '…' : name
  })
  const pnlValues = items.map(h => h.profit_loss_amount)
  const rateValues = items.map(h => h.return_rate)

  return {
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      formatter: (params: any) => {
        if (!Array.isArray(params) || params.length === 0) return ''
        const idx = params[0].dataIndex
        const h = items[idx]
        const name = h.fund_name || h.fund_code
        const pnlColor = h.profit_loss_amount >= 0 ? '#d54941' : '#2ba471'
        const rateColor = h.return_rate >= 0 ? '#d54941' : '#2ba471'
        return `<div style="font-weight:600;margin-bottom:4px">${name}</div>
          <div>市值: ¥${h.holding_value.toFixed(2)}</div>
          <div>投入: ¥${h.total_invested.toFixed(2)}</div>
          <div>盈亏: <b style="color:${pnlColor}">${h.profit_loss_amount >= 0 ? '+' : ''}¥${h.profit_loss_amount.toFixed(2)}</b></div>
          <div>收益率: <b style="color:${rateColor}">${h.return_rate >= 0 ? '+' : ''}${h.return_rate.toFixed(2)}%</b></div>
          <div style="color:#999;font-size:11px">${h.platform}</div>`
      },
    },
    grid: { left: 140, right: 60, top: 10, bottom: 10 },
    xAxis: [
      {
        type: 'value',
        position: 'top',
        axisLabel: { formatter: (v: number) => v >= 1000 || v <= -1000 ? (v / 1000).toFixed(0) + 'k' : '¥' + v },
        splitLine: { lineStyle: { type: 'dashed' } },
      },
    ],
    yAxis: {
      type: 'category',
      data: names,
      axisLabel: { fontSize: 11, width: 130, overflow: 'truncate' },
    },
    series: [
      {
        name: '盈亏金额',
        type: 'bar',
        data: pnlValues.map((v, i) => ({
          value: v,
          itemStyle: { color: v >= 0 ? '#d54941' : '#2ba471' },
          label: {
            show: true,
            position: v >= 0 ? 'right' : 'left',
            formatter: `${v >= 0 ? '+' : ''}${v.toFixed(0)} (${rateValues[i] >= 0 ? '+' : ''}${rateValues[i].toFixed(1)}%)`,
            fontSize: 11,
            color: v >= 0 ? '#d54941' : '#2ba471',
          },
        })),
        barMaxWidth: 20,
      },
    ],
  }
})

// ============================
// 持仓收益明细表格
// ============================
const holdingsTableData = computed(() => {
  return [...holdings.value]
    .sort((a, b) => b.profit_loss_amount - a.profit_loss_amount)
    .map(h => ({
      ...h,
      _pnlClass: h.profit_loss_amount >= 0 ? 'color: #d54941' : 'color: #2ba471',
      _rateClass: h.return_rate >= 0 ? 'color: #d54941' : 'color: #2ba471',
    }))
})

const holdingsColumns = [
  { colKey: 'fund_name', title: '基金名称', width: 200, ellipsis: true,
    cell: (_h: any, { row }: any) => row.fund_name || row.fund_code },
  { colKey: 'platform', title: '平台', width: 100 },
  { colKey: 'fund_category', title: '分类', width: 80 },
  { colKey: 'holding_value', title: '市值(元)', width: 120, align: 'right',
    cell: (_h: any, { row }: any) => '¥' + row.holding_value.toFixed(2) },
  { colKey: 'total_invested', title: '累计买入', width: 120, align: 'right',
    cell: (_h: any, { row }: any) => '¥' + row.total_invested.toFixed(2) },
  { colKey: 'total_sold', title: '累计卖出', width: 120, align: 'right',
    cell: (_h: any, { row }: any) => '¥' + (row.total_sold || 0).toFixed(2) },
  { colKey: 'net_invested', title: '净投入', width: 120, align: 'right',
    cell: (_h: any, { row }: any) => '¥' + (row.net_invested || 0).toFixed(2) },
  { colKey: 'profit_loss_amount', title: '盈亏(元)', width: 120, align: 'right',
    cell: (_hFn: any, { row }: any) => {
      const v = row.profit_loss_amount
      const color = v >= 0 ? '#d54941' : '#2ba471'
      const sign = v >= 0 ? '+' : ''
      return h('span', { style: `color:${color};font-weight:600` }, `${sign}¥${v.toFixed(2)}`)
    }
  },
  { colKey: 'return_rate', title: '收益率', width: 100, align: 'right',
    cell: (_hFn: any, { row }: any) => {
      const v = row.return_rate
      const color = v >= 0 ? '#d54941' : '#2ba471'
      const sign = v >= 0 ? '+' : ''
      return h('span', { style: `color:${color};font-weight:600` }, `${sign}${v.toFixed(2)}%`)
    }
  },
  { colKey: 'current_price', title: '现价', width: 90, align: 'right',
    cell: (_h: any, { row }: any) => row.current_price?.toFixed(4) || '-' },
  { colKey: 'cost_price', title: '成本价', width: 90, align: 'right',
    cell: (_h: any, { row }: any) => row.cost_price?.toFixed(4) || '-' },
]

// ============================
// 收益率走势图（组合整体）
// ============================
const pnlRateChartOption = computed(() => {
  const dates = snapshots.value.map(s => s.date)
  const rates = snapshots.value.map(s => s.pnl_rate)

  return {
    tooltip: {
      trigger: 'axis',
      formatter: (params: any) => {
        const p = Array.isArray(params) ? params[0] : params
        const s = snapshots.value[p.dataIndex]
        return `<div style="font-weight:600;margin-bottom:4px">${s.date}</div>
          <div>收益率: <b style="color:${s.pnl_rate >= 0 ? '#d54941' : '#2ba471'}">${s.pnl_rate >= 0 ? '+' : ''}${s.pnl_rate}%</b></div>
          <div>盈亏: ${s.total_pnl >= 0 ? '+' : ''}¥${s.total_pnl.toFixed(2)}</div>
          <div>总资产: ¥${s.total_assets.toFixed(2)}</div>`
      },
    },
    grid: { left: 60, right: 30, top: 20, bottom: 60 },
    xAxis: { type: 'category', data: dates, boundaryGap: false },
    yAxis: {
      type: 'value',
      axisLabel: { formatter: '{value}%' },
      splitLine: { lineStyle: { type: 'dashed' } },
    },
    series: [{
      type: 'line',
      smooth: true,
      showSymbol: false,
      data: rates,
      areaStyle: {
        color: {
          type: 'linear', x: 0, y: 0, x2: 0, y2: 1,
          colorStops: [
            { offset: 0, color: 'rgba(0,82,217,0.25)' },
            { offset: 1, color: 'rgba(0,82,217,0.02)' },
          ],
        },
      },
      lineStyle: { color: '#0052d9', width: 2 },
      itemStyle: { color: '#0052d9' },
      markLine: {
        silent: true,
        symbol: 'none',
        data: [{ yAxis: 0, lineStyle: { color: '#999', type: 'dashed', width: 1 } }],
      },
    }],
    dataZoom: [{ type: 'inside' }, { type: 'slider', bottom: 10, height: 20 }],
  }
})

// 总资产 vs 总投入
const assetsChartOption = computed(() => {
  const dates = snapshots.value.map(s => s.date)
  const assets = snapshots.value.map(s => s.total_assets)
  const invested = snapshots.value.map(s => s.total_invested)

  return {
    tooltip: {
      trigger: 'axis',
      formatter: (params: any) => {
        if (!Array.isArray(params)) return ''
        let html = `<div style="font-weight:600;margin-bottom:4px">${params[0].name}</div>`
        for (const p of params) {
          html += `<div>${p.marker} ${p.seriesName}: <b>¥${Number(p.value).toFixed(2)}</b></div>`
        }
        return html
      },
    },
    legend: { top: 4, right: 10 },
    grid: { left: 70, right: 30, top: 40, bottom: 60 },
    xAxis: { type: 'category', data: dates, boundaryGap: false },
    yAxis: {
      type: 'value',
      axisLabel: {
        formatter: (v: number) => v >= 10000 ? (v / 10000).toFixed(1) + 'w' : '¥' + v.toFixed(0),
      },
    },
    series: [
      {
        name: '总资产',
        type: 'line', smooth: true, showSymbol: false,
        data: assets,
        lineStyle: { color: '#0052d9', width: 2 },
        itemStyle: { color: '#0052d9' },
        areaStyle: {
          color: {
            type: 'linear', x: 0, y: 0, x2: 0, y2: 1,
            colorStops: [
              { offset: 0, color: 'rgba(0,82,217,0.15)' },
              { offset: 1, color: 'rgba(0,82,217,0.01)' },
            ],
          },
        },
      },
      {
        name: '总投入',
        type: 'line', smooth: true, showSymbol: false,
        data: invested,
        lineStyle: { color: '#a6a6a6', width: 1.5, type: 'dashed' },
        itemStyle: { color: '#a6a6a6' },
      },
    ],
    dataZoom: [{ type: 'inside' }, { type: 'slider', bottom: 10, height: 20 }],
  }
})

// 每日盈亏变动柱状图
const dailyPnlChartOption = computed(() => {
  const dates = snapshots.value.map(s => s.date)
  const dailyChanges = snapshots.value.map((s, i) => {
    if (i === 0) return 0
    return parseFloat((s.total_pnl - snapshots.value[i - 1].total_pnl).toFixed(2))
  })

  return {
    tooltip: {
      trigger: 'axis',
      formatter: (params: any) => {
        const p = Array.isArray(params) ? params[0] : params
        const val = typeof p.value === 'object' ? p.value.value : p.value
        return `<div style="font-weight:600">${p.name}</div>
          <div>日盈亏变动: <b style="color:${val >= 0 ? '#d54941' : '#2ba471'}">${val >= 0 ? '+' : ''}¥${val.toFixed(2)}</b></div>`
      },
    },
    grid: { left: 60, right: 30, top: 10, bottom: 60 },
    xAxis: { type: 'category', data: dates },
    yAxis: {
      type: 'value',
      axisLabel: { formatter: '¥{value}' },
    },
    series: [{
      type: 'bar',
      data: dailyChanges.map(v => ({
        value: v,
        itemStyle: { color: v >= 0 ? '#d54941' : '#2ba471' },
      })),
    }],
    dataZoom: [
      { type: 'inside', xAxisIndex: 0 },
      { type: 'slider', xAxisIndex: 0, bottom: 10, height: 20 },
    ],
  }
})

onMounted(async () => {
  const [_, sumRes] = await Promise.all([loadData(), getSnapshotSummary(), loadHoldings()])
  summary.value = sumRes.data
})
</script>
