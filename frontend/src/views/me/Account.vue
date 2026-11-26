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
      <div class="page-icon" style="background: #f1ede6; color: #14161a">👤</div>
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

      <button class="logout" @click="logout">退出登录</button>
    </div>
  </div>
</template>

<style scoped>
.card {
  background: #fff;
  border: 1px solid #e9e4da;
  border-radius: 4px;
  padding: 36px;
  max-width: 680px;
  box-shadow:
    0 30px 70px -55px rgba(20, 22, 26, 0.6),
    0 2px 6px -4px rgba(20, 22, 26, 0.12);
}
.profile {
  display: flex;
  align-items: center;
  gap: 18px;
  padding-bottom: 24px;
  border-bottom: 1px solid #e6e2da;
}
.avatar {
  width: 56px;
  height: 56px;
  border-radius: 50%;
  background: #14161a;
  color: #f5f3ef;
  font-size: 20px;
  font-weight: 600;
  display: flex;
  align-items: center;
  justify-content: center;
  font-family: 'Noto Serif SC', 'Songti SC', Georgia, serif;
}
.name {
  font-family: 'Noto Serif SC', 'Songti SC', 'SimSun', Georgia, serif;
  font-size: 22px;
  font-weight: 600;
  color: #14161a;
  letter-spacing: 1px;
}
.role {
  font-size: 11.5px;
  color: #8a867d;
  margin-top: 6px;
  letter-spacing: 1px;
}
.rows {
  margin: 8px 0 30px;
}
.row {
  display: flex;
  justify-content: space-between;
  padding: 16px 0;
  border-bottom: 1px solid #f4f1ea;
  font-size: 13px;
}
.k {
  color: #8a867d;
  letter-spacing: 0.5px;
}
.v {
  color: #14161a;
  font-weight: 500;
}
.logout {
  background: none;
  border: 1px solid #e6e2da;
  color: #b4442f;
  font-size: 12.5px;
  letter-spacing: 1px;
  padding: 9px 22px;
  border-radius: 2px;
  cursor: pointer;
}
.logout:hover {
  background: #fdf6f4;
  border-color: #e8cfc8;
}
</style>
