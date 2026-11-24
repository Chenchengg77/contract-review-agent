<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { DataAnalysis, List, User, Back, SwitchButton } from '@element-plus/icons-vue'
import { useUserStore } from '../stores/user'

const route = useRoute()
const router = useRouter()
const store = useUserStore()

const menus = [
  { path: '/me/overview', label: '概览', icon: DataAnalysis },
  { path: '/me/reviews', label: '我的审查', icon: List },
  { path: '/me/account', label: '账户', icon: User },
]

const currentTitle = computed(() => {
  const m = menus.find((x) => route.path.startsWith(x.path))
  return m ? m.label : ''
})

const initial = computed(() => (store.user?.username || '?').slice(0, 1).toUpperCase())

function logout() {
  store.logout()
  router.push('/login')
}

onMounted(() => {
  store.fetchMe()
})
</script>

<template>
  <div class="shell">
    <aside class="sidebar">
      <div class="brand">
        <div class="brand-logo">👤</div>
        <div class="brand-text">
          <div class="brand-name">个人中心</div>
          <div class="brand-sub">PERSONAL CENTER</div>
        </div>
      </div>

      <div class="nav-label">我的空间</div>
      <nav class="nav">
        <RouterLink v-for="m in menus" :key="m.path" :to="m.path" class="nav-item">
          <el-icon class="nav-icon"><component :is="m.icon" /></el-icon>
          <span>{{ m.label }}</span>
        </RouterLink>
      </nav>

      <div class="back-card" @click="router.push('/home')">
        <el-icon><Back /></el-icon>
        <span>返回用户端</span>
      </div>

      <div class="user-box">
        <div class="avatar">{{ initial }}</div>
        <div class="user-info">
          <div class="user-name">{{ store.user?.username || '...' }}</div>
          <div class="user-role">{{ store.isAdmin ? '管理员' : '普通用户' }}</div>
        </div>
        <el-tooltip content="退出登录" placement="top">
          <button class="icon-btn" @click="logout">
            <el-icon><SwitchButton /></el-icon>
          </button>
        </el-tooltip>
      </div>
    </aside>

    <div class="body">
      <header class="topbar">
        <div class="title-wrap">
          <span class="me-badge">个人</span>
          <span class="page-title">{{ currentTitle }}</span>
        </div>
        <div class="top-right">
          <span class="chip"><span class="dot"></span>数据自动汇总</span>
        </div>
      </header>
      <main class="main">
        <router-view />
      </main>
    </div>
  </div>
</template>

<style scoped>
.shell {
  display: flex;
  min-height: 100vh;
  background: #f6f8fb;
}
.sidebar {
  width: 236px;
  flex-shrink: 0;
  background: linear-gradient(180deg, #071a17 0%, #0c2420 100%);
  color: #94b8b1;
  display: flex;
  flex-direction: column;
  border-right: 1px solid rgba(255, 255, 255, 0.04);
}
.brand {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 22px 20px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
}
.brand-logo {
  width: 40px;
  height: 40px;
  border-radius: 12px;
  background: linear-gradient(135deg, #10b981, #14b8a6);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 19px;
  box-shadow: 0 8px 20px -8px rgba(16, 185, 129, 0.8);
}
.brand-name {
  font-size: 15px;
  font-weight: 700;
  color: #fff;
}
.brand-sub {
  font-size: 9px;
  letter-spacing: 1.5px;
  color: #3d5f58;
  margin-top: 2px;
}
.nav-label {
  font-size: 10px;
  letter-spacing: 1.5px;
  color: #3d5f58;
  padding: 18px 24px 8px;
}
.nav {
  padding: 0 12px;
  display: flex;
  flex-direction: column;
  gap: 3px;
}
.nav-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 12px;
  border-radius: 10px;
  color: #94b8b1;
  text-decoration: none;
  font-size: 13.5px;
  transition: all 0.15s;
  border: 1px solid transparent;
}
.nav-item:hover {
  background: rgba(255, 255, 255, 0.05);
  color: #d1fae5;
}
.nav-item.router-link-active {
  background: linear-gradient(90deg, rgba(16, 185, 129, 0.9), rgba(20, 184, 166, 0.85));
  color: #fff;
  font-weight: 500;
  border-color: rgba(110, 231, 183, 0.3);
  box-shadow: 0 8px 18px -10px rgba(16, 185, 129, 0.9);
}
.nav-icon {
  font-size: 16px;
}
.back-card {
  margin: auto 12px 10px;
  padding: 12px 14px;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.07);
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 12.5px;
  color: #6ee7b7;
  cursor: pointer;
  transition: all 0.15s;
}
.back-card:hover {
  background: rgba(16, 185, 129, 0.15);
  border-color: rgba(110, 231, 183, 0.4);
}
.user-box {
  margin: 12px;
  padding: 10px 12px;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.06);
  display: flex;
  align-items: center;
  gap: 10px;
}
.avatar {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: linear-gradient(135deg, #10b981, #14b8a6);
  color: #fff;
  font-size: 13px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.user-info {
  flex: 1;
  min-width: 0;
}
.user-name {
  font-size: 13px;
  color: #d1fae5;
  font-weight: 500;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.user-role {
  font-size: 10px;
  color: #5e827a;
  margin-top: 1px;
}
.icon-btn {
  background: none;
  border: none;
  color: #5e827a;
  cursor: pointer;
  font-size: 16px;
  display: flex;
  padding: 4px;
  border-radius: 6px;
}
.icon-btn:hover {
  color: #f87171;
  background: rgba(248, 113, 113, 0.1);
}
.body {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
}
.topbar {
  height: 60px;
  flex-shrink: 0;
  background: rgba(255, 255, 255, 0.85);
  backdrop-filter: blur(10px);
  border-bottom: 1px solid #e8edf5;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 28px;
  position: sticky;
  top: 0;
  z-index: 10;
}
.title-wrap {
  display: flex;
  align-items: center;
  gap: 10px;
}
.me-badge {
  font-size: 11px;
  color: #047857;
  background: #ecfdf5;
  border: 1px solid #a7f3d0;
  border-radius: 6px;
  padding: 2px 8px;
  font-weight: 600;
}
.page-title {
  font-size: 15px;
  font-weight: 600;
  color: #0f172a;
}
.chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: #64748b;
  background: #f1f5f9;
  border: 1px solid #e2e8f0;
  border-radius: 999px;
  padding: 4px 12px;
}
.dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #22c55e;
  box-shadow: 0 0 0 3px rgba(34, 197, 94, 0.15);
}
.main {
  flex: 1;
  overflow: auto;
  background:
    radial-gradient(1200px 400px at 100% -10%, rgba(16, 185, 129, 0.06), transparent 60%),
    #f6f8fb;
}
</style>
