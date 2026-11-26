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
      <div class="page-icon" style="background: #f1ede6; color: #14161a">📋</div>
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
            <span class="hi">{{ row.high }}</span> /
            <span class="mi">{{ row.mid }}</span> /
            <span class="lo">{{ row.low }}</span>
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
  border: 1px solid #e9e4da;
  border-radius: 4px;
  padding: 12px;
  box-shadow:
    0 30px 70px -55px rgba(20, 22, 26, 0.6),
    0 2px 6px -4px rgba(20, 22, 26, 0.12);
}
.hi {
  color: #b4442f;
}
.mi {
  color: #b98a3c;
}
.lo {
  color: #6b7d6e;
}
</style>
