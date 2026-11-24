<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '../../api'

const users = ref<any[]>([])
const loading = ref(false)

async function load() {
  loading.value = true
  try {
    const { data } = await api.get('/admin/users')
    users.value = data.users || []
  } catch {
    ElMessage.error('加载失败')
  } finally {
    loading.value = false
  }
}

onMounted(load)

async function del(u: any) {
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

function fmt(ts: number) {
  return ts ? new Date(ts * 1000).toLocaleString('zh-CN') : '-'
}
</script>

<template>
  <div class="page">
    <div class="page-head">
      <div class="page-icon" style="background: #eff6ff; color: #2563eb">👥</div>
      <div>
        <h1 class="page-title">用户管理</h1>
        <p class="page-sub">共 {{ users.length }} 位用户 · 删除用户会级联删除其审查记录</p>
      </div>
    </div>

    <el-card shadow="never">
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
        <el-table-column label="注册时间" width="190">
          <template #default="{ row }">{{ fmt(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="审查次数" width="100">
          <template #default="{ row }">{{ row.review_count ?? 0 }}</template>
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

