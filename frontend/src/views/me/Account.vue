<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '../../stores/user'

const store = useUserStore()
const router = useRouter()

onMounted(() => {
  if (!store.user) store.fetchMe()
})

const initial = computed(() => (store.user?.username || '?').slice(0, 1).toUpperCase())

function logout() {
  store.logout()
  router.push('/login')
}
</script>

<template>
  <div class="page">
    <div class="page-head">
      <div class="page-icon" style="background: #ecfdf5; color: #059669">👤</div>
      <div>
        <h1 class="page-title">账户</h1>
        <p class="page-sub">账号信息与登录状态</p>
      </div>
    </div>

    <div class="card">
      <div class="profile">
        <div class="avatar">{{ initial }}</div>
        <div>
          <div class="name">{{ store.user?.username || '-' }}</div>
          <div class="role">{{ store.isAdmin ? '管理员' : '普通用户' }}</div>
        </div>
      </div>

      <div class="rows">
        <div class="row">
          <span class="k">用户名</span>
          <span class="v">{{ store.user?.username || '-' }}</span>
        </div>
        <div class="row">
          <span class="k">角色</span>
          <span class="v">{{ store.isAdmin ? '管理员' : '普通用户' }}</span>
        </div>
        <div class="row">
          <span class="k">账号 ID</span>
          <span class="v">{{ store.user?.id ?? '-' }}</span>
        </div>
      </div>

      <el-button type="danger" plain @click="logout">退出登录</el-button>
    </div>
  </div>
</template>

<style scoped>
.card {
  background: #fff;
  border: 1px solid #e8edf5;
  border-radius: 16px;
  padding: 24px;
  max-width: 640px;
}
.profile {
  display: flex;
  align-items: center;
  gap: 16px;
  padding-bottom: 20px;
  border-bottom: 1px solid #f1f5f9;
  margin-bottom: 8px;
}
.avatar {
  width: 52px;
  height: 52px;
  border-radius: 50%;
  background: linear-gradient(135deg, #10b981, #14b8a6);
  color: #fff;
  font-size: 20px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
}
.name {
  font-size: 16px;
  font-weight: 700;
  color: #0f172a;
}
.role {
  font-size: 12px;
  color: #94a3b8;
  margin-top: 2px;
}
.rows {
  margin: 10px 0 20px;
}
.row {
  display: flex;
  justify-content: space-between;
  padding: 12px 0;
  border-bottom: 1px solid #f8fafc;
  font-size: 13px;
}
.k {
  color: #94a3b8;
}
.v {
  color: #0f172a;
  font-weight: 500;
}
</style>
