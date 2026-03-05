<template>
  <div>
    <!-- 统计 -->
    <div class="grid grid-cols-3 gap-4 mb-4">
      <t-card class="text-center" :bordered="true">
        <div class="text-sm text-gray-500">活跃计划</div>
        <div class="text-xl font-bold text-blue-700">{{ plans.filter(p => p.is_active).length }}</div>
      </t-card>
      <t-card class="text-center" :bordered="true">
        <div class="text-sm text-gray-500">计划总数</div>
        <div class="text-xl font-bold text-gray-700">{{ plans.length }}</div>
      </t-card>
      <t-card class="text-center" :bordered="true">
        <div class="text-sm text-gray-500">累计定投金额</div>
        <div class="text-xl font-bold text-orange-500">¥{{ totalDcaInvested.toFixed(2) }}</div>
      </t-card>
    </div>

    <!-- 操作栏 -->
    <div class="flex justify-end mb-4">
      <t-button theme="primary" @click="showAdd = true">新增定投计划</t-button>
    </div>

    <!-- 列表 -->
    <t-card :bordered="true">
      <t-table :data="plans" :columns="columns" row-key="plan_id" hover size="small" />
    </t-card>

    <!-- 新增弹窗 -->
    <t-dialog v-model:visible="showAdd" header="新增定投计划" :on-confirm="handleAdd" width="480px">
      <t-form :data="form" label-width="90px">
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
        <t-form-item label="频率">
          <t-input v-model="form.frequency" placeholder="如：每天/每周一" />
        </t-form-item>
        <t-form-item label="金额">
          <t-input-number v-model="form.amount" :min="1" theme="normal" />
        </t-form-item>
        <t-form-item label="类型">
          <t-select v-model="form.dca_type">
            <t-option value="固定金额" label="固定金额" />
            <t-option value="智能定投" label="智能定投" />
          </t-select>
        </t-form-item>
      </t-form>
    </t-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed, h } from 'vue'
import { MessagePlugin, Switch as TSwitch } from 'tdesign-vue-next'
import { getDcaPlans, createDcaPlan, toggleDcaPlan, getFunds } from '../api'

const plans = ref<any[]>([])
const funds = ref<any[]>([])
const showAdd = ref(false)
const form = ref({ fund_code: '', platform: '支付宝', frequency: '', amount: 100, dca_type: '固定金额' })

const totalDcaInvested = computed(() => plans.value.reduce((s, p) => s + (p.total_invested || 0), 0))

const handleToggle = async (row: any) => {
  await toggleDcaPlan(row.plan_id)
  await loadPlans()
}

const columns = [
  { colKey: 'fund_name', title: '基金名称', width: 200 },
  { colKey: 'platform', title: '平台', width: 120 },
  { colKey: 'frequency', title: '频率', width: 100 },
  { colKey: 'amount', title: '金额(元)', width: 100 },
  { colKey: 'dca_type', title: '类型', width: 100 },
  { colKey: 'total_invested', title: '累计投入', width: 120, cell: (_h: any, { row }: any) => '¥' + (row.total_invested ?? 0).toFixed(2) },
  {
    colKey: 'is_active', title: '状态', width: 80,
    cell: (_hFn: any, { row }: any) => h(TSwitch, { value: !!row.is_active, onChange: () => handleToggle(row), size: 'small' }),
  },
]

const loadPlans = async () => {
  const res = await getDcaPlans()
  plans.value = res.data
}

const handleAdd = async () => {
  await createDcaPlan(form.value)
  MessagePlugin.success('创建成功')
  showAdd.value = false
  form.value = { fund_code: '', platform: '支付宝', frequency: '', amount: 100, dca_type: '固定金额' }
  await loadPlans()
}

onMounted(async () => {
  const [, fRes] = await Promise.all([loadPlans(), getFunds()])
  funds.value = fRes.data
})
</script>
