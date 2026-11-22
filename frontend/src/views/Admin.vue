<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '../api'

const users = ref<any[]>([])
const reviews = ref<any[]>([])
const loading = ref(false)

async function load() {
  loading.value = true
  try {
    const [u, r] = await Promise.all([api.get('/admin/users'), api.get('/reviews')])
    users.value = u.data.users || []
    reviews.value = r.data.reviews || []
  } catch {
    ElMessage.error('加载失败')
  } finally {
    loading.value = false
  }
}

onMounted(load)

async function delUser(u: any) {
  try {
    await ElMessageBox.confirm(`确定删除用户「${u.username}」？其审查记录也会一并删除。`, '确认删除', {
      type: 'warning',
    })
  } catch {
    return
  }
  try {
    await api.delete('/admin/users/' + u.id)
    ElMessage.success('已删除')
    load()
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '删除失败')
  }
}

async function delReview(r: any) {
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
      <div class="page-icon" style="background: #fff7ed; color: #ea580c">👥</div>
      <div>
        <h1 class="page-title">管理后台</h1>
        <p class="page-sub">仅管理员可见 · 查看全部用户与审查记录</p>
      </div>
    </div>

    <el-card shadow="never" class="card">
      <div class="card-head">
        <span class="card-title">用户列表</span>
        <span class="count">{{ users.length }} 位用户</span>
      </div>
      <el-table :data="users" v-loading="loading" style="width: 100%">
        <el-table-column prop="id" label="ID" width="70" />
        <el-table-column prop="username" label="用户名" />
        <el-table-column label="角色" width="120">
          <template #default="{ row }">
            <el-tag :type="row.role === 'admin' ? 'warning' : 'info'" size="small">
              {{ row.role === 'admin' ? '管理员' : '普通用户' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="注册时间" width="200">
          <template #default="{ row }">{{ fmt(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="100">
          <template #default="{ row }">
            <el-button link type="danger" size="small" @click="delUser(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-card shadow="never" class="card">
      <div class="card-head">
        <span class="card-title">所有审查记录</span>
        <span class="count">{{ reviews.length }} 条记录</span>
      </div>
      <el-table :data="reviews" v-loading="loading" style="width: 100%">
        <el-table-column prop="username" label="用户" width="140" />
        <el-table-column prop="filename" label="合同" min-width="220" show-overflow-tooltip />
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
            <el-button link type="danger" size="small" @click="delReview(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<style scoped>
.page {
  max-width: 1120px;
  margin: 0 auto;
  padding: 32px;
}
h1 {
  margin: 0 0 6px;
  font-size: 24px;
}
.sub {
  color: #64748b;
  font-size: 14px;
  margin: 0 0 20px;
}
.card {
  margin-bottom: 16px;
  border-radius: 14px;
  border: 1px solid #e2e8f0;
}
.card-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 14px;
}
.card-title {
  font-weight: 600;
}
.count {
  font-size: 12px;
  color: #94a3b8;
}
</style>
