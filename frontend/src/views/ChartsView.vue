<template>
  <div>
    <!-- 筛选栏 -->
    <t-card class="mb-4" :bordered="true">
      <div class="flex items-center gap-4">
        <t-select
          v-model="selectedFund"
          placeholder="选择基金"
          clearable
          class="w-64"
          @change="loadQuotes"
        >
          <t-option v-for="f in funds" :key="f.fund_code" :value="f.fund_code" :label="f.fund_name" />
        </t-select>
        <t-date-range-picker
          v-model="dateRange"
          class="w-72"
          @change="loadQuotes"
        />
      </div>
    </t-card>

    <!-- 净值走势 -->
    <t-card title="净值走势" class="mb-4" :bordered="true">
      <div v-if="quotes.length === 0" class="text-center text-gray-400 py-10">暂无净值数据</div>
      <v-chart v-else :option="navChartOption" autoresize class="h-80" />
    </t-card>

    <!-- 日盈亏 -->
    <t-card title="每日盈亏" class="mb-4" :bordered="true">
      <div v-if="quotes.length === 0" class="text-center text-gray-400 py-10">暂无数据</div>
      <v-chart v-else :option="pnlChartOption" autoresize class="h-64" />
    </t-card>

    <!-- 净值明细 -->
    <t-card title="净值明细" :bordered="true">
      <div v-if="quotes.length === 0" class="text-center text-gray-400 py-10">暂无净值明细数据</div>
      <t-table
        v-else
        :data="quotes"
        :columns="quoteColumns"
        :pagination="{ pageSize: 10 }"
        size="small"
        stripe
      />
    </t-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import VChart from '@/utils/echarts'
import { getFunds, getQuotes } from '../api'


const funds = ref<any[]>([])
const quotes = ref<any[]>([])
const selectedFund = ref('')
const dateRange = ref<string[]>([])

const loadQuotes = async () => {
  const params: any = { page_size: 1000 }
  if (selectedFund.value) params.fund_code = selectedFund.value
  if (dateRange.value?.length === 2) {
    params.date_from = dateRange.value[0]
    params.date_to = dateRange.value[1]
  }
  const res = await getQuotes(params)
  quotes.value = (res.data.data || []).reverse()
}

const navChartOption = computed(() => ({
  tooltip: { trigger: 'axis' },
  grid: { left: 60, right: 30, top: 20, bottom: 60 },
  xAxis: { type: 'category', data: quotes.value.map(q => q.quote_date) },
  yAxis: { type: 'value', name: '净值', scale: true },
  dataZoom: [{ type: 'inside' }, { type: 'slider' }],
  series: [{
    type: 'line', smooth: true, symbol: 'circle', symbolSize: 4,
    data: quotes.value.map(q => q.close_price),
    lineStyle: { color: '#0052d9' },
    itemStyle: { color: '#0052d9' },
    areaStyle: { color: 'rgba(0,82,217,0.08)' },
  }],
}))

const pnlChartOption = computed(() => ({
  tooltip: { trigger: 'axis', formatter: (p: any) => `${p[0].name}<br/>盈亏: ¥${p[0].value}` },
  grid: { left: 60, right: 30, top: 20, bottom: 30 },
  xAxis: { type: 'category', data: quotes.value.map(q => q.quote_date) },
  yAxis: { type: 'value', name: '盈亏(元)' },
  series: [{
    type: 'bar',
    data: quotes.value.map(q => ({
      value: q.daily_pnl ?? 0,
      itemStyle: { color: (q.daily_pnl ?? 0) >= 0 ? '#d54941' : '#2ba471' },
    })),
  }],
}))

// 净值明细表格列定义
const quoteColumns = [
  { colKey: 'quote_date', title: '日期', width: 120 },
  { colKey: 'open_price', title: '开盘价', width: 100, align: 'right' },
  { colKey: 'high_price', title: '最高价', width: 100, align: 'right' },
  { colKey: 'low_price', title: '最低价', width: 100, align: 'right' },
  { colKey: 'close_price', title: '收盘价', width: 100, align: 'right' },
  { colKey: 'acc_nav', title: '累计净值', width: 100, align: 'right' },
]

onMounted(async () => {
  const res = await getFunds()
  funds.value = res.data
  await loadQuotes()
})
</script>
