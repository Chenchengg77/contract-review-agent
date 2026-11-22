<template>
  <div class="page">
    <div class="badge">Vue 迁移中</div>
    <h2>{{ title }}</h2>
    <p class="tip">该页面正在从原生 JS 迁移到 Vue，稍后完成。</p>
  </div>
</template>

<script setup lang="ts">
defineProps<{ title: string }>()
</script>

<style scoped>
.page {
  padding: 48px;
}
.badge {
  display: inline-block;
  background: #eff6ff;
  color: #1d4ed8;
  font-size: 12px;
  padding: 2px 10px;
  border-radius: 999px;
  margin-bottom: 12px;
}
h2 {
  margin: 0 0 8px;
}
.tip {
  color: #64748b;
}
</style>
