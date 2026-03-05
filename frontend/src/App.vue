<template>
  <t-layout class="min-h-screen">
    <t-aside width="220px" class="bg-white border-r border-gray-200">
      <div class="flex items-center justify-center h-16 border-b border-gray-200">
        <h1 class="text-lg font-bold text-blue-700">ETF 管理系统</h1>
      </div>
      <t-menu
        :value="currentRoute"
        @change="onMenuChange"
        theme="light"
        class="mt-2"
      >
        <t-menu-item value="/dashboard">
          <template #icon><DashboardIcon /></template>
          持仓总览
        </t-menu-item>
        <t-menu-item value="/charts">
          <template #icon><ChartLineIcon /></template>
          收益曲线
        </t-menu-item>
        <t-menu-item value="/dca-plans">
          <template #icon><CalendarIcon /></template>
          定投管理
        </t-menu-item>
        <t-menu-item value="/signals">
          <template #icon><NotificationIcon /></template>
          交易信号
        </t-menu-item>
        <t-menu-item value="/rules">
          <template #icon><SettingIcon /></template>
          交易规则
        </t-menu-item>
        <t-menu-item value="/transactions">
          <template #icon><ListIcon /></template>
          交易记录
        </t-menu-item>
        <t-menu-item value="/data-explorer">
          <template #icon><DataBaseIcon /></template>
          数据明细
        </t-menu-item>
      </t-menu>
    </t-aside>
    <t-layout>
      <t-header class="bg-white border-b border-gray-200 px-6 flex items-center h-16">
        <span class="text-base font-medium text-gray-700">{{ pageTitle }}</span>
      </t-header>
      <t-content class="p-6 bg-gray-50">
        <router-view />
      </t-content>
    </t-layout>
  </t-layout>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import {
  DashboardIcon,
  ChartLineIcon,
  CalendarIcon,
  NotificationIcon,
  SettingIcon,
  ListIcon,
  DataBaseIcon,
} from 'tdesign-icons-vue-next'

const router = useRouter()
const route = useRoute()

const currentRoute = computed(() => route.path)
const pageTitle = computed(() => (route.meta?.title as string) || '')

const onMenuChange = (value: string) => {
  router.push(value)
}
</script>
