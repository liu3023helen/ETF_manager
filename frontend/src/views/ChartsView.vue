<template>
  <div>
    <!-- 筛选栏 -->
    <t-card class="mb-4" :bordered="true">
      <div class="flex items-center gap-4 flex-wrap">
        <t-select
          v-model="selectedFunds"
          placeholder="选择基金（可多选对比）"
          multiple
          clearable
          filterable
          class="w-96"
          :min-collapsed-num="3"
          @change="loadAllQuotes"
        >
          <t-option v-for="f in funds" :key="f.fund_code" :value="f.fund_code" :label="f.fund_name" />
        </t-select>
        <t-date-range-picker
          v-model="dateRange"
          class="w-72"
          @change="loadAllQuotes"
        />
        <t-checkbox v-model="normalizeMode">
          归一化对比
          <t-tooltip content="将所有基金的起始价格统一为100，便于比较不同价位基金的涨跌幅度">
            <t-icon name="help-circle" size="14px" class="ml-1 text-gray-400" />
          </t-tooltip>
        </t-checkbox>
      </div>
    </t-card>

    <!-- 净值走势 -->
    <t-card :title="normalizeMode ? '归一化走势对比（基准=100）' : '净值走势'" class="mb-4" :bordered="true">
      <div v-if="Object.keys(fundDataMap).length === 0" class="text-center text-gray-400 py-10">暂无净值数据，请选择基金</div>
      <v-chart v-else ref="navChartRef" :option="navChartOption" autoresize class="h-96" group="fundCharts" />
    </t-card>

    <!-- 每日涨跌幅 -->
    <t-card title="每日涨跌幅对比" class="mb-4" :bordered="true">
      <div v-if="Object.keys(fundDataMap).length === 0" class="text-center text-gray-400 py-10">暂无数据</div>
      <v-chart v-else ref="pnlChartRef" :option="pnlChartOption" autoresize class="h-72" group="fundCharts" />
    </t-card>

    <!-- 净值明细 -->
    <t-card title="净值明细" :bordered="true">
      <div v-if="flatQuotes.length === 0" class="text-center text-gray-400 py-10">暂无净值明细数据</div>
      <t-table
        v-else
        :data="flatQuotes"
        :columns="quoteColumns"
        :pagination="{ pageSize: 15 }"
        size="small"
        stripe
      />
    </t-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed, watch, nextTick } from 'vue'
import VChart from '@/utils/echarts'
import { getFunds, getQuotes } from '../api'
import * as echarts from 'echarts'

// 多选颜色调色板
const COLORS = [
  '#0052d9', '#e37318', '#00a870', '#d54941',
  '#8b5cf6', '#0594fa', '#ed7b2f', '#3b82f6',
  '#f59e0b', '#10b981', '#ef4444', '#6366f1',
]

const funds = ref<any[]>([])
const selectedFunds = ref<string[]>([])
const dateRange = ref<string[]>([])
const normalizeMode = ref(false)
const navChartRef = ref<any>(null)
const pnlChartRef = ref<any>(null)
const loading = ref(false)

// 获取默认日期范围（近1年）
const getDefaultDateRange = (): [string, string] => {
  const now = new Date()
  const to = now.toISOString().slice(0, 10)
  const from = new Date(now.getFullYear() - 1, now.getMonth(), now.getDate()).toISOString().slice(0, 10)
  return [from, to]
}

// 核心数据结构：每个基金独立存储，key 是 fund_code
const fundDataMap = ref<Record<string, { name: string; data: any[] }>>({})

// 每个基金独立请求，自动分页拉取数据
const loadAllQuotes = async () => {
  if (!selectedFunds.value || selectedFunds.value.length === 0) {
    fundDataMap.value = {}
    return
  }
  loading.value = true
  try {
    const results: Record<string, { name: string; data: any[] }> = {}
    // 确定日期范围：用户选了就用用户的，没选就默认近1年
    const [defaultFrom, defaultTo] = getDefaultDateRange()
    const dateFrom = dateRange.value?.length === 2 ? dateRange.value[0] : defaultFrom
    const dateTo = dateRange.value?.length === 2 ? dateRange.value[1] : defaultTo

    // 并行请求每个基金
    const requests = selectedFunds.value.map(async (code) => {
      const allRows: any[] = []
      let page = 1
      const pageSize = 1000
      while (true) {
        const params: any = {
          page_size: pageSize, page, fund_code: code,
          date_from: dateFrom, date_to: dateTo,
        }
        const res = await getQuotes(params)
        const rows = res.data.data || []
        allRows.push(...rows)
        if (rows.length < pageSize) break
        page++
      }
      // 按日期正序
      allRows.sort((a: any, b: any) => new Date(a.quote_date).getTime() - new Date(b.quote_date).getTime())
      const name = allRows.length > 0 ? (allRows[0].fund_name || code) : code
      results[code] = { name, data: allRows }
    })
    await Promise.all(requests)
    fundDataMap.value = results
  } finally {
    loading.value = false
  }
}

// 汇总所有数据用于明细表
const flatQuotes = computed(() => {
  const all: any[] = []
  for (const group of Object.values(fundDataMap.value)) {
    all.push(...group.data)
  }
  return all.sort((a, b) => new Date(b.quote_date).getTime() - new Date(a.quote_date).getTime())
})

// 所有日期的并集（用于对齐X轴）
const allDates = computed(() => {
  const dateSet = new Set<string>()
  for (const group of Object.values(fundDataMap.value)) {
    for (const q of group.data) {
      dateSet.add(q.quote_date)
    }
  }
  return [...dateSet].sort()
})

const fundCount = computed(() => Object.keys(fundDataMap.value).length)

const navChartOption = computed(() => {
  const dates = allDates.value
  const series: any[] = []
  let idx = 0

  for (const [code, group] of Object.entries(fundDataMap.value)) {
    const color = COLORS[idx % COLORS.length]
    // 构建日期 -> 价格的映射
    const dateMap = new Map<string, number>()
    for (const q of group.data) {
      dateMap.set(q.quote_date, q.close_price)
    }

    let basePrice: number | null = null
    const data = dates.map(d => {
      const price = dateMap.get(d) ?? null
      if (normalizeMode.value && price !== null) {
        if (basePrice === null) basePrice = price
        return basePrice > 0 ? parseFloat(((price / basePrice) * 100).toFixed(2)) : null
      }
      return price
    })

    series.push({
      name: group.name,
      type: 'line',
      smooth: true,
      showSymbol: false,
      connectNulls: true,
      data,
      lineStyle: { color, width: 2 },
      itemStyle: { color },
      emphasis: { lineStyle: { width: 3 } },
    })
    idx++
  }

  return {
    tooltip: {
      trigger: 'axis',
      formatter: (params: any) => {
        if (!Array.isArray(params)) return ''
        let html = `<div style="font-weight:600;margin-bottom:4px">${params[0].name}</div>`
        for (const p of params) {
          if (p.value !== null && p.value !== undefined) {
            html += `<div>${p.marker} ${p.seriesName}: <b>${p.value}</b></div>`
          }
        }
        return html
      },
    },
    legend: {
      show: true,
      top: 4,
      right: 10,
      type: 'scroll',
    },
    grid: { left: 80, right: 40, top: 40, bottom: 60 },
    xAxis: { type: 'category', data: dates, boundaryGap: false },
    yAxis: {
      type: 'value',
      name: normalizeMode.value ? '归一化值' : '净值/点位',
      scale: true,
      axisLabel: {
        formatter: (value: number) => {
          if (value >= 10000) return (value / 10000).toFixed(1) + 'w'
          return value.toFixed(2)
        },
      },
    },
    dataZoom: [{ type: 'inside' }, { type: 'slider' }],
    series,
  }
})

// 计算每日涨跌幅（每个基金单独计算）
const pnlChartOption = computed(() => {
  const dates = allDates.value
  const series: any[] = []
  let idx = 0

  for (const [code, group] of Object.entries(fundDataMap.value)) {
    const color = COLORS[idx % COLORS.length]

    // 计算涨跌幅
    const changePctMap = new Map<string, number>()
    for (let i = 0; i < group.data.length; i++) {
      const d = group.data[i]
      if (i === 0) {
        changePctMap.set(d.quote_date, 0)
      } else {
        const prev = group.data[i - 1].close_price
        const curr = d.close_price
        if (prev && curr && prev > 0) {
          changePctMap.set(d.quote_date, parseFloat((((curr - prev) / prev) * 100).toFixed(2)))
        } else {
          changePctMap.set(d.quote_date, 0)
        }
      }
    }

    const data = dates.map(d => changePctMap.get(d) ?? null)

    // 多基金用折线对比，单基金用红绿柱状图
    if (fundCount.value > 1) {
      series.push({
        name: group.name,
        type: 'line',
        smooth: true,
        showSymbol: false,
        connectNulls: true,
        data,
        lineStyle: { color, width: 1.5 },
        itemStyle: { color },
      })
    } else {
      series.push({
        name: group.name,
        type: 'bar',
        data: dates.map(d => {
          const val = changePctMap.get(d) ?? null
          return val !== null
            ? { value: val, itemStyle: { color: val >= 0 ? '#d54941' : '#2ba471' } }
            : null
        }),
      })
    }
    idx++
  }

  return {
    tooltip: {
      trigger: 'axis',
      formatter: (params: any) => {
        if (!Array.isArray(params)) return ''
        let html = `<div style="font-weight:600;margin-bottom:4px">${params[0].name}</div>`
        for (const p of params) {
          if (p.value !== null && p.value !== undefined) {
            const v = typeof p.value === 'object' ? p.value.value : p.value
            html += `<div>${p.marker} ${p.seriesName}: <b>${v}%</b></div>`
          }
        }
        return html
      },
    },
    legend: {
      show: true,
      top: 4,
      right: 10,
      type: 'scroll',
    },
    grid: { left: 70, right: 40, top: 40, bottom: 60 },
    xAxis: { type: 'category', data: dates },
    yAxis: {
      type: 'value',
      name: '涨跌幅(%)',
      axisLabel: { formatter: '{value}%' },
    },
    dataZoom: [
      { type: 'inside', xAxisIndex: 0 },
      { type: 'slider', xAxisIndex: 0, bottom: 10, height: 20 },
    ],
    series,
  }
})

// 净值明细表格列定义
const quoteColumns = computed(() => {
  const cols: any[] = [
    { colKey: 'quote_date', title: '日期', width: 120 },
  ]
  // 多选时始终显示基金信息列
  if (selectedFunds.value.length !== 1) {
    cols.push(
      { colKey: 'fund_code', title: '基金代码', width: 110 },
      { colKey: 'fund_name', title: '基金名称', width: 160 },
    )
  }
  cols.push(
    { colKey: 'open_price', title: '开盘价', width: 100, align: 'right' },
    { colKey: 'high_price', title: '最高价', width: 100, align: 'right' },
    { colKey: 'low_price', title: '最低价', width: 100, align: 'right' },
    { colKey: 'close_price', title: '收盘价/净值', width: 110, align: 'right' },
    { colKey: 'acc_nav', title: '累计净值', width: 100, align: 'right' },
  )
  return cols
})

// 监听图表实例，设置联动
watch([navChartRef, pnlChartRef], ([nav, pnl]) => {
  if (nav && pnl) {
    nextTick(() => {
      const navChart = navChartRef.value?.chart
      const pnlChart = pnlChartRef.value?.chart
      if (navChart && pnlChart) {
        connect('fundCharts')
      }
    })
  }
}, { immediate: true })

onMounted(async () => {
  const res = await getFunds()
  funds.value = res.data
  // 默认选中创业板指
  selectedFunds.value = ['399006.SZ']
  await loadAllQuotes()
})
</script>
