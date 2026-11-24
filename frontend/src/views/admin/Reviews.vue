<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '../../api'

const reviews = ref<any[]>([])
const loading = ref(false)

async function load() {
  loading.value = true
  try {
    const { data } = await api.get('/reviews')
    reviews.value = data.reviews || []
  } catch {
    ElMessage.error('加载失败')
  } finally {
    loading.value = false
  }
}

onMounted(load)

async function del(r: any) {
  try {
    await ElMessageBox.confirm('确定删除这条审查记录？', '确认删除', { type: 'warning' })
  } catch {
    return
  }
  try {
    await api.delete('/reviews/' + r.id)
    ElMessage.success('已删除')
    load()
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '删除失败')
  }
}

function fmt(ts: number) {
  return ts ? new Date(ts * 1000).toLocaleString('zh-CN') : '-'
}
</script>

<template>
  <div class="page">
    <div class="page-head">
      <div class="page-icon" style="background: #f5f3ff; color: #7c3aed">📋</div>
      <div>
        <h1 class="page-title">审查记录</h1>
        <p class="page-sub">共 {{ reviews.length }} 条记录 · 全部用户的审查历史</p>
      </div>
    </div>

    <el-card shadow="never">
      <el-table :data="reviews" v-loading="loading" style="width: 100%">
        <el-table-column prop="username" label="用户" width="140" />
        <el-table-column prop="filename" label="合同" min-width="240" show-overflow-tooltip />
        <el-table-column label="高 / 中 / 低" width="140">
          <template #default="{ row }">
            <span style="color: #dc2626">{{ row.high }}</span> /
            <span style="color: #d97706">{{ row.mid }}</span> /
            <span style="color: #16a34a">{{ row.low }}</span>
          </template>
        </el-table-column>
        <el-table-column label="时间" width="200">
          <template #default="{ row }">{{ fmt(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="100">
          <template #default="{ row }">
            <el-button link type="danger" size="small" @click="del(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>
