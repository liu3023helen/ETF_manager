<template>
  <t-card class="text-center" :bordered="true">
    <div class="text-sm text-gray-500 mb-1">{{ label }}</div>
    <div class="text-2xl font-bold" :class="valueClass">
      <slot>{{ value }}</slot>
    </div>
    <slot name="extra"></slot>
  </t-card>
</template>

<script setup lang="ts">
defineProps<{
  label: string
  value?: string | number
  valueClass?: string
}>()
</script>
