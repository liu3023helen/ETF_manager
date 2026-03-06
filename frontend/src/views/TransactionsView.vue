<template>
  <div>
    <!-- 筛选栏 -->
    <t-card class="mb-4" :bordered="true">
      <div class="flex items-center gap-4 flex-wrap">
        <t-select v-model="filter.fund_code" placeholder="选择基金" clearable class="w-56" @change="loadRecords">
          <t-option v-for="f in funds" :key="f.fund_code" :value="f.fund_code" :label="f.fund_name" />
        </t-select>
        <t-select v-model="filter.record_type" placeholder="记录类型" clearable class="w-32" @change="loadRecords">
          <t-option value="买入" label="买入" />
          <t-option value="卖出" label="卖出" />
          <t-option value="定投" label="定投" />
          <t-option value="信号" label="信号" />
        </t-select>
        <t-select v-model="filter.exec_status" placeholder="执行状态" clearable class="w-32" @change="loadRecords">
          <t-option value="待执行" label="待执行" />
          <t-option value="已执行" label="已执行" />
          <t-option value="已忽略" label="已忽略" />
        </t-select>
        <t-date-range-picker v-model="dateRange" class="w-72" @change="loadRecords" />
        <div class="flex-1"></div>
        <t-button theme="primary" @click="showAdd = true">新增记录</t-button>
      </div>
    </t-card>

    <!-- 列表 -->
    <t-card :bordered="true">
      <div class="flex items-center justify-between mb-3">
        <span class="text-sm text-gray-500">共 {{ total }} 条记录</span>
      </div>
      <div v-if="records.length === 0" class="text-center text-gray-400 py-10">暂无交易记录</div>
      <t-table v-else :data="records" :columns="columns" row-key="record_id" hover size="small" />
      <div class="flex justify-end mt-4" v-if="total > pageSize">
        <t-pagination
          v-model:current="currentPage"
          :total="total"
          :page-size="pageSize"
          @current-change="loadRecords"
          show-jumper
        />
      </div>
    </t-card>

    <!-- 新增弹窗 -->
    <t-dialog v-model:visible="showAdd" header="新增交易记录" :on-confirm="handleAdd" width="560px">
      <t-form :data="form" label-width="90px">
        <t-form-item label="基金">
          <t-select v-model="form.fund_code" placeholder="选择基金" filterable>
            <t-option v-for="f in funds" :key="f.fund_code" :value="f.fund_code" :label="`${f.fund_name} (${f.fund_code})`" />
          </t-select>
        </t-form-item>
        <t-form-item label="基金名称">
          <t-input v-model="form.fund_name" placeholder="自动填充或手动输入" />
        </t-form-item>
        <t-form-item label="记录类型">
          <t-select v-model="form.record_type">
            <t-option value="买入" label="买入" />
            <t-option value="卖出" label="卖出" />
            <t-option value="定投" label="定投" />
            <t-option value="信号" label="信号" />
          </t-select>
        </t-form-item>
        <t-form-item label="日期">
          <t-date-picker v-model="form.record_date" />
        </t-form-item>
        <t-form-item label="平台">
          <t-select v-model="form.platform" clearable>
            <t-option value="支付宝" label="支付宝" />
            <t-option value="涨乐财富通" label="涨乐财富通" />
          </t-select>
        </t-form-item>
        <t-form-item label="金额">
          <t-input-number v-model="form.amount" :min="0" theme="normal" />
        </t-form-item>
        <t-form-item label="份额">
          <t-input-number v-model="form.shares" :min="0" :decimal-places="2" theme="normal" />
        </t-form-item>
        <t-form-item label="成交净值">
          <t-input-number v-model="form.nav" :min="0" :decimal-places="4" theme="normal" />
        </t-form-item>
        <t-form-item label="手续费">
          <t-input-number v-model="form.fee" :min="0" :decimal-places="2" theme="normal" />
        </t-form-item>
        <t-form-item label="执行状态">
          <t-select v-model="form.exec_status">
            <t-option value="待执行" label="待执行" />
            <t-option value="已执行" label="已执行" />
            <t-option value="已忽略" label="已忽略" />
          </t-select>
        </t-form-item>
        <t-form-item label="备注">
          <t-input v-model="form.note" placeholder="可选" />
        </t-form-item>
      </t-form>
    </t-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, h, watch } from 'vue'
import { MessagePlugin, Tag as TTag } from 'tdesign-vue-next'
import { getTradeRecords, createTradeRecord, getFunds } from '../api'

const records = ref<any[]>([])
const funds = ref<any[]>([])
const showAdd = ref(false)
const dateRange = ref<string[]>([])
const total = ref(0)
const currentPage = ref(1)
const pageSize = 50
const filter = ref({ fund_code: '', record_type: '', exec_status: '' })

const defaultForm = () => ({
  fund_code: '',
  fund_name: '',
  record_type: '买入',
  record_date: '',
  platform: '支付宝',
  amount: 0,
  shares: 0,
  nav: 0,
  fee: 0,
  exec_status: '已执行',
  note: '',
})
const form = ref(defaultForm())

// 选中基金时自动填充名称
watch(() => form.value.fund_code, (code) => {
  const found = funds.value.find((f: any) => f.fund_code === code)
  if (found) form.value.fund_name = found.fund_name
})

const typeTheme: Record<string, 'danger' | 'success' | 'warning' | 'primary' | 'default'> = {
  '买入': 'danger', '卖出': 'success', '定投': 'warning', '信号': 'primary',
}
const statusTheme: Record<string, 'danger' | 'success' | 'warning' | 'primary' | 'default'> = {
  '待执行': 'warning', '已执行': 'success', '已忽略': 'default',
}

const columns = [
  { colKey: 'fund_name', title: '基金名称', width: 160, ellipsis: true },
  { colKey: 'platform', title: '平台', width: 110 },
  {
    colKey: 'record_type', title: '类型', width: 80,
    cell: (_hFn: any, { row }: any) =>
      h(TTag, { theme: typeTheme[row.record_type] || 'default', variant: 'light' }, () => row.record_type),
  },
  { colKey: 'record_date', title: '日期', width: 110 },
  { colKey: 'amount', title: '金额', width: 100, cell: (_h: any, { row }: any) => row.amount != null ? '¥' + Number(row.amount).toFixed(2) : '-' },
  { colKey: 'shares', title: '份额', width: 100, cell: (_h: any, { row }: any) => row.shares != null ? Number(row.shares).toFixed(2) : '-' },
  { colKey: 'nav', title: '成交净值', width: 100 },
  { colKey: 'fee', title: '手续费', width: 80, cell: (_h: any, { row }: any) => row.fee != null ? '¥' + Number(row.fee).toFixed(2) : '-' },
  {
    colKey: 'exec_status', title: '状态', width: 90,
    cell: (_hFn: any, { row }: any) =>
      h(TTag, { theme: statusTheme[row.exec_status] || 'default', variant: 'light' }, () => row.exec_status || '-'),
  },
  { colKey: 'note', title: '备注', width: 150, ellipsis: true },
]

const loadRecords = async () => {
  const params: any = { page: currentPage.value, page_size: pageSize }
  if (filter.value.fund_code) params.fund_code = filter.value.fund_code
  if (filter.value.record_type) params.record_type = filter.value.record_type
  if (filter.value.exec_status) params.exec_status = filter.value.exec_status
  if (dateRange.value?.length === 2) {
    params.date_from = dateRange.value[0]
    params.date_to = dateRange.value[1]
  }
  const res = await getTradeRecords(params)
  records.value = res.data.data
  total.value = res.data.total
}

const handleAdd = async () => {
  if (!form.value.fund_code) {
    MessagePlugin.warning('请选择基金')
    return
  }
  if (!form.value.record_date) {
    MessagePlugin.warning('请选择日期')
    return
  }
  await createTradeRecord(form.value)
  MessagePlugin.success('交易记录创建成功')
  showAdd.value = false
  form.value = defaultForm()
  await loadRecords()
}

onMounted(async () => {
  const [, fRes] = await Promise.all([loadRecords(), getFunds()])
  funds.value = fRes.data
})
</script>
