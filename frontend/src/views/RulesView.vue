<template>
  <div>
    <!-- 筛选 -->
    <div class="flex items-center gap-4 mb-4">
      <t-select v-model="filterCategory" placeholder="基金分类" clearable class="w-40" @change="loadRules">
        <t-option value="军工" label="军工" />
        <t-option value="芯片" label="芯片" />
        <t-option value="黄金" label="黄金" />
        <t-option value="军工/芯片" label="军工/芯片" />
        <t-option value="通用" label="通用" />
      </t-select>
      <t-select v-model="filterType" placeholder="规则类型" clearable class="w-40" @change="loadRules">
        <t-option value="止盈" label="止盈" />
        <t-option value="接回" label="接回" />
        <t-option value="加仓" label="加仓" />
        <t-option value="纪律" label="纪律" />
      </t-select>
      <div class="flex-1"></div>
      <t-button theme="primary" @click="showAdd = true">新增规则</t-button>
    </div>

    <!-- 规则表 -->
    <t-card :bordered="true">
      <t-table :data="rules" :columns="columns" row-key="rule_id" hover size="small" />
    </t-card>

    <!-- 新增/编辑弹窗 -->
    <t-dialog v-model:visible="showAdd" header="新增交易规则" :on-confirm="handleAdd" width="520px">
      <t-form :data="form" label-width="80px">
        <t-form-item label="分类">
          <t-input v-model="form.fund_category" placeholder="如：军工/芯片" />
        </t-form-item>
        <t-form-item label="类型">
          <t-select v-model="form.rule_type">
            <t-option value="止盈" label="止盈" />
            <t-option value="接回" label="接回" />
            <t-option value="加仓" label="加仓" />
            <t-option value="纪律" label="纪律" />
          </t-select>
        </t-form-item>
        <t-form-item label="条件">
          <t-textarea v-model="form.condition_desc" placeholder="触发条件描述" />
        </t-form-item>
        <t-form-item label="阈值">
          <t-input-number v-model="form.threshold" :decimal-places="2" theme="normal" />
        </t-form-item>
        <t-form-item label="操作">
          <t-input v-model="form.action_desc" placeholder="执行操作描述" />
        </t-form-item>
        <t-form-item label="优先级">
          <t-input-number v-model="form.priority" :min="0" theme="normal" />
        </t-form-item>
      </t-form>
    </t-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, h } from 'vue'
import { MessagePlugin, Switch as TSwitch, Tag as TTag } from 'tdesign-vue-next'
import { getRules, createRule, toggleRule } from '../api'

const rules = ref<any[]>([])
const showAdd = ref(false)
const filterCategory = ref('')
const filterType = ref('')
const form = ref({ fund_category: '', rule_type: '止盈', condition_desc: '', threshold: 0, action_desc: '', priority: 0 })

const typeTheme: Record<string, string> = { '止盈': 'danger', '接回': 'success', '加仓': 'warning', '纪律': 'primary' }

const handleToggle = async (row: any) => {
  await toggleRule(row.rule_id)
  await loadRules()
}

const columns = [
  { colKey: 'fund_category', title: '分类', width: 100 },
  {
    colKey: 'rule_type', title: '类型', width: 80,
    cell: (_hFn: any, { row }: any) => h(TTag, { theme: typeTheme[row.rule_type] || 'default', variant: 'light' }, () => row.rule_type),
  },
  { colKey: 'condition_desc', title: '触发条件', width: 250 },
  { colKey: 'threshold', title: '阈值', width: 80 },
  { colKey: 'action_desc', title: '执行操作', width: 200 },
  { colKey: 'priority', title: '优先级', width: 80 },
  {
    colKey: 'is_active', title: '启用', width: 80,
    cell: (_hFn: any, { row }: any) => h(TSwitch, { value: !!row.is_active, onChange: () => handleToggle(row), size: 'small' }),
  },
]

const loadRules = async () => {
  const params: any = {}
  if (filterCategory.value) params.category = filterCategory.value
  if (filterType.value) params.rule_type = filterType.value
  const res = await getRules(params)
  rules.value = res.data
}

const handleAdd = async () => {
  await createRule(form.value)
  MessagePlugin.success('规则创建成功')
  showAdd.value = false
  form.value = { fund_category: '', rule_type: '止盈', condition_desc: '', threshold: 0, action_desc: '', priority: 0 }
  await loadRules()
}

onMounted(() => loadRules())
</script>
