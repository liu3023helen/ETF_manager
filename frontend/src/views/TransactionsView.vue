<template>
  <div>
    <!-- 筛选栏 -->
    <t-card class="mb-4" :bordered="true">
      <div class="flex items-center gap-4 flex-wrap">
        <t-select v-model="filter.fund_code" placeholder="选择基金" clearable class="w-56" @change="loadTx">
          <t-option v-for="f in funds" :key="f.fund_code" :value="f.fund_code" :label="f.fund_name" />
        </t-select>
        <t-select v-model="filter.platform" placeholder="平台" clearable class="w-36" @change="loadTx">
          <t-option value="支付宝" label="支付宝" />
          <t-option value="涨乐财富通" label="涨乐财富通" />
        </t-select>
        <t-select v-model="filter.tx_type" placeholder="交易类型" clearable class="w-32" @change="loadTx">
          <t-option value="买入" label="买入" />
          <t-option value="卖出" label="卖出" />
          <t-option value="定投" label="定投" />
        </t-select>
        <t-date-range-picker v-model="dateRange" class="w-72" @change="loadTx" />
        <div class="flex-1"></div>
        <t-button theme="primary" @click="showAdd = true">新增交易</t-button>
      </div>
    </t-card>

    <!-- 列表 -->
    <t-card :bordered="true">
      <div v-if="transactions.length === 0" class="text-center text-gray-400 py-10">暂无交易记录</div>
      <t-table v-else :data="transactions" :columns="columns" row-key="tx_id" hover size="small" />
    </t-card>

    <!-- 新增弹窗 -->
    <t-dialog v-model:visible="showAdd" header="新增交易记录" :on-confirm="handleAdd" width="520px">
      <t-form :data="form" label-width="80px">
        <t-form-item label="基金">
          <t-select v-model="form.fund_code" placeholder="选择基金">
            <t-option v-for="f in funds" :key="f.fund_code" :value="f.fund_code" :label="f.fund_name" />
          </t-select>
        </t-form-item>
        <t-form-item label="平台">
          <t-select v-model="form.platform">
            <t-option value="支付宝" label="支付宝" />
            <t-option value="涨乐财富通" label="涨乐财富通" />
          </t-select>
        </t-form-item>
        <t-form-item label="类型">
          <t-select v-model="form.tx_type">
            <t-option value="买入" label="买入" />
            <t-option value="卖出" label="卖出" />
            <t-option value="定投" label="定投" />
          </t-select>
        </t-form-item>
        <t-form-item label="日期">
          <t-date-picker v-model="form.tx_date" />
        </t-form-item>
        <t-form-item label="金额">
          <t-input-number v-model="form.amount" :min="0" theme="normal" />
        </t-form-item>
        <t-form-item label="份额">
          <t-input-number v-model="form.shares" :min="0" :decimal-places="2" theme="normal" />
        </t-form-item>
        <t-form-item label="成交净值">
          <t-input-number v-model="form.nav_at_tx" :min="0" :decimal-places="4" theme="normal" />
        </t-form-item>
        <t-form-item label="手续费">
          <t-input-number v-model="form.fee" :min="0" :decimal-places="2" theme="normal" />
        </t-form-item>
        <t-form-item label="备注">
          <t-input v-model="form.note" placeholder="可选" />
        </t-form-item>
      </t-form>
    </t-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, h } from 'vue'
import { MessagePlugin, Tag as TTag } from 'tdesign-vue-next'
import { getTransactions, createTransaction, getFunds } from '../api'

const transactions = ref<any[]>([])
const funds = ref<any[]>([])
const showAdd = ref(false)
const dateRange = ref<string[]>([])
const filter = ref({ fund_code: '', platform: '', tx_type: '' })
const form = ref({
  fund_code: '', platform: '支付宝', tx_type: '买入', tx_date: '',
  amount: 0, shares: 0, nav_at_tx: 0, fee: 0, note: '',
})

const txTypeTheme: Record<string, string> = { '买入': 'danger', '卖出': 'success', '定投': 'warning' }

const columns = [
  { colKey: 'fund_name', title: '基金名称', width: 180 },
  { colKey: 'platform', title: '平台', width: 110 },
  {
    colKey: 'tx_type', title: '类型', width: 80,
    cell: (_hFn: any, { row }: any) => h(TTag, { theme: txTypeTheme[row.tx_type] || 'default', variant: 'light' }, () => row.tx_type),
  },
  { colKey: 'tx_date', title: '日期', width: 110 },
  { colKey: 'amount', title: '金额', width: 100, cell: (_h: any, { row }: any) => '¥' + (row.amount ?? 0).toFixed(2) },
  { colKey: 'shares', title: '份额', width: 100, cell: (_h: any, { row }: any) => (row.shares ?? 0).toFixed(2) },
  { colKey: 'nav_at_tx', title: '成交净值', width: 100 },
  { colKey: 'fee', title: '手续费', width: 80 },
  { colKey: 'note', title: '备注', width: 150 },
]

const loadTx = async () => {
  const params: any = {}
  if (filter.value.fund_code) params.fund_code = filter.value.fund_code
  if (filter.value.platform) params.platform = filter.value.platform
  if (filter.value.tx_type) params.tx_type = filter.value.tx_type
  if (dateRange.value?.length === 2) {
    params.date_from = dateRange.value[0]
    params.date_to = dateRange.value[1]
  }
  const res = await getTransactions(params)
  transactions.value = res.data
}

const handleAdd = async () => {
  await createTransaction(form.value)
  MessagePlugin.success('交易记录创建成功')
  showAdd.value = false
  form.value = { fund_code: '', platform: '支付宝', tx_type: '买入', tx_date: '', amount: 0, shares: 0, nav_at_tx: 0, fee: 0, note: '' }
  await loadTx()
}

onMounted(async () => {
  const [, fRes] = await Promise.all([loadTx(), getFunds()])
  funds.value = fRes.data
})
</script>
