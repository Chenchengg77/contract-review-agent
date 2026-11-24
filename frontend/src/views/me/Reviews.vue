<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import api from '../../api'

const reviews = ref<any[]>([])
const loading = ref(false)

onMounted(async () => {
  loading.value = true
  try {
    const { data } = await api.get('/reviews')
    reviews.value = data.reviews || []
  } catch {
    ElMessage.error('加载失败')
  } finally {
    loading.value = false
  }
})

function fmt(ts: number) {
  return ts ? new Date(ts * 1000).toLocaleString('zh-CN') : '-'
}
</script>

<template>
  <div class="page">
    <div class="page-head">
      <div class="page-icon" style="background: #ecfdf5; color: #059669">📋</div>
      <div>
        <h1 class="page-title">我的审查</h1>
        <p class="page-sub">共 {{ reviews.length }} 条审查记录</p>
      </div>
    </div>

    <div class="card">
      <el-table :data="reviews" v-loading="loading" style="width: 100%">
        <el-table-column prop="filename" label="合同" min-width="300" show-overflow-tooltip />
        <el-table-column label="高 / 中 / 低" width="150">
          <template #default="{ row }">
            <span style="color: #dc2626">{{ row.high }}</span> /
            <span style="color: #d97706">{{ row.mid }}</span> /
            <span style="color: #16a34a">{{ row.low }}</span>
          </template>
        </el-table-column>
        <el-table-column label="时间" width="200">
          <template #default="{ row }">{{ fmt(row.created_at) }}</template>
        </el-table-column>
      </el-table>
    </div>
  </div>
</template>

<style scoped>
.card {
  background: #fff;
  border: 1px solid #e8edf5;
  border-radius: 16px;
  padding: 16px;
}
</style>
