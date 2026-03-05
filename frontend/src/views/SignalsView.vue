<template>
  <div>
    <t-tabs v-model="activeTab" @change="loadSignals">
      <t-tab-panel value="" label="全部" />
      <t-tab-panel value="待执行" label="待执行" />
      <t-tab-panel value="已执行" label="已执行" />
      <t-tab-panel value="已忽略" label="已忽略" />
    </t-tabs>

    <t-card class="mt-4" :bordered="true">
      <div v-if="signals.length === 0" class="text-center text-gray-400 py-10">暂无交易信号</div>
      <t-table v-else :data="signals" :columns="columns" row-key="signal_id" hover size="small" />
    </t-card>

    <!-- 状态更新弹窗 -->
    <t-dialog v-model:visible="showUpdate" header="更新信号状态" :on-confirm="handleUpdate" width="400px">
      <t-form label-width="80px">
        <t-form-item label="状态">
          <t-select v-model="updateForm.exec_status">
            <t-option value="已执行" label="已执行" />
            <t-option value="已忽略" label="已忽略" />
          </t-select>
        </t-form-item>
        <t-form-item label="实际操作">
          <t-textarea v-model="updateForm.actual_action" placeholder="填写实际执行的操作" />
        </t-form-item>
      </t-form>
    </t-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, h } from 'vue'
import { Button as TButton, MessagePlugin, Tag as TTag } from 'tdesign-vue-next'
import { getSignals, updateSignalStatus } from '../api'

const signals = ref<any[]>([])
const activeTab = ref('')
const showUpdate = ref(false)
const currentSignalId = ref(0)
const updateForm = ref({ exec_status: '已执行', actual_action: '' })

const statusTheme: Record<string, string> = { '待执行': 'warning', '已执行': 'success', '已忽略': 'default' }

const columns = [
  { colKey: 'fund_name', title: '基金名称', width: 180 },
  { colKey: 'signal_date', title: '日期', width: 110 },
  { colKey: 'signal_type', title: '信号类型', width: 120 },
  { colKey: 'trigger_condition', title: '触发条件', width: 180 },
  { colKey: 'suggested_action', title: '建议操作', width: 150 },
  {
    colKey: 'exec_status', title: '状态', width: 100,
    cell: (_hFn: any, { row }: any) => h(TTag, { theme: statusTheme[row.exec_status] || 'default', variant: 'light' }, () => row.exec_status),
  },
  { colKey: 'actual_action', title: '实际操作', width: 150 },
  {
    colKey: 'op', title: '操作', width: 100,
    cell: (_hFn: any, { row }: any) => row.exec_status === '待执行'
      ? h(TButton, { theme: 'primary', variant: 'text', size: 'small', onClick: () => openUpdate(row) }, () => '处理')
      : null,
  },
]

const openUpdate = (row: any) => {
  currentSignalId.value = row.signal_id
  updateForm.value = { exec_status: '已执行', actual_action: '' }
  showUpdate.value = true
}

const handleUpdate = async () => {
  await updateSignalStatus(currentSignalId.value, updateForm.value)
  MessagePlugin.success('状态已更新')
  showUpdate.value = false
  await loadSignals()
}

const loadSignals = async () => {
  const res = await getSignals(activeTab.value || undefined)
  signals.value = res.data
}

onMounted(() => loadSignals())
</script>
