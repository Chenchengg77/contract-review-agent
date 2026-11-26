<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElNotification } from 'element-plus'
import { DataBoard, User, Document, SwitchButton, Setting } from '@element-plus/icons-vue'
import { useUserStore } from '../stores/user'
import api from '../api'

const route = useRoute()
const router = useRouter()
const store = useUserStore()
const hasAlert = ref(false)

const menus = [
  { path: '/admin/overview', label: '概览', icon: DataBoard },
  { path: '/admin/users', label: '用户管理', icon: User },
  { path: '/admin/reviews', label: '审查记录', icon: Document },
  { path: '/admin/ops', label: '系统运维', icon: Setting },
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

onMounted(async () => {
  store.fetchMe()
  try {
    const { data } = await api.get('/admin/health')
    const rate = data.total ? data.failed / data.total : 0
    if (rate > 0.05) {
      hasAlert.value = true
      ElNotification({
        title: '系统告警',
        message: `近期失败率 ${(rate * 100).toFixed(1)}%，请到「系统运维」查看失败记录`,
        type: 'warning',
        duration: 8000,
      })
    }
  } catch {
    /* ignore */
  }
})
</script>

<template>
  <div class="shell">
    <aside class="sidebar">
      <div class="brand">
        <div class="logo">管</div>
        <div class="brand-text">
          <div class="brand-name">管理后台</div>
          <div class="brand-sub">ADMIN CONSOLE</div>
        </div>
      </div>

      <div class="nav-label">系统管理</div>
      <nav class="nav">
        <RouterLink v-for="m in menus" :key="m.path" :to="m.path" class="nav-item">
          <el-icon class="nav-icon"><component :is="m.icon" /></el-icon>
          <span>{{ m.label }}</span>
          <span v-if="m.path === '/admin/ops' && hasAlert" class="nav-dot"></span>
        </RouterLink>
      </nav>

      <div class="user-box">
        <div class="avatar">{{ initial }}</div>
        <div class="user-info">
          <div class="user-name">{{ store.user?.username || '...' }}</div>
          <div class="user-role">管理员</div>
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
          <span class="admin-badge">管理</span>
          <span class="page-title">{{ currentTitle }}</span>
        </div>
        <div class="top-right">
          <span class="chip"><span class="dot"></span>系统正常</span>
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
  background: #f8fafc;
  /* 主色：青碧（Element 组件跟随） */
  --el-color-primary: #14b8a6;
  --el-color-primary-light-3: #5eead4;
  --el-color-primary-light-5: #99f6e4;
  --el-color-primary-light-7: #ccfbf1;
  --el-color-primary-light-8: #e6fffa;
  --el-color-primary-light-9: #f0fdfa;
  --el-color-primary-dark-2: #0f766e;
}
.sidebar {
  width: 232px;
  flex-shrink: 0;
  background: #0f172a;
  color: #94a3b8;
  display: flex;
  flex-direction: column;
  border-right: 1px solid #1e293b;
}
.brand {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 24px 20px;
  border-bottom: 1px solid #1e293b;
}
.logo {
  width: 38px;
  height: 38px;
  border: 1px solid #334155;
  display: flex;
  align-items: center;
  justify-content: center;
  font-family: 'Noto Serif SC', 'Songti SC', 'SimSun', Georgia, serif;
  font-size: 19px;
  font-weight: 600;
  color: #5eead4;
  position: relative;
}
.logo::after {
  content: '';
  position: absolute;
  right: -1px;
  bottom: -1px;
  width: 7px;
  height: 7px;
  background: #14b8a6;
}
.brand-name {
  font-size: 15px;
  font-weight: 600;
  color: #f1f5f9;
  letter-spacing: 2px;
}
.brand-sub {
  font-size: 8px;
  letter-spacing: 3px;
  color: #475569;
  margin-top: 3px;
}
.nav-label {
  font-size: 10px;
  letter-spacing: 3px;
  color: #475569;
  padding: 20px 22px 10px;
}
.nav {
  padding: 0 12px;
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.nav-item {
  position: relative;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 12px;
  border-radius: 8px;
  color: #94a3b8;
  text-decoration: none;
  font-size: 13.5px;
  letter-spacing: 0.5px;
  transition:
    background 0.18s,
    color 0.18s;
}
.nav-item::before {
  content: '';
  position: absolute;
  left: 0;
  top: 8px;
  bottom: 8px;
  width: 3px;
  border-radius: 2px;
  background: transparent;
  transition: background 0.18s;
}
.nav-item:hover {
  background: rgba(255, 255, 255, 0.05);
  color: #e2e8f0;
}
.nav-item.router-link-active {
  background: rgba(20, 184, 166, 0.1);
  color: #f1f5f9;
}
.nav-item.router-link-active::before {
  background: #14b8a6;
  box-shadow: 0 0 12px rgba(20, 184, 166, 0.7);
}
.nav-icon {
  font-size: 16px;
}
.nav-dot {
  margin-left: auto;
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #ef4444;
}
.user-box {
  margin: auto 12px 14px;
  padding: 10px 12px;
  border: 1px solid #1e293b;
  border-radius: 10px;
  display: flex;
  align-items: center;
  gap: 10px;
  background: rgba(255, 255, 255, 0.02);
}
.avatar {
  width: 30px;
  height: 30px;
  border-radius: 50%;
  background: #14b8a6;
  color: #06231f;
  font-size: 12px;
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
  font-size: 12.5px;
  color: #e2e8f0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.user-role {
  font-size: 10px;
  color: #64748b;
  margin-top: 1px;
}
.icon-btn {
  background: none;
  border: none;
  color: #64748b;
  cursor: pointer;
  font-size: 15px;
  display: flex;
  padding: 4px;
  transition: color 0.18s;
}
.icon-btn:hover {
  color: #f87171;
}
.body {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
}
.topbar {
  height: 64px;
  flex-shrink: 0;
  background: #fff;
  border-bottom: 1px solid #e2e8f0;
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
  gap: 12px;
}
.admin-badge {
  font-size: 10px;
  letter-spacing: 2px;
  color: #0f766e;
  border: 1px solid #99f6e4;
  background: #f0fdfa;
  padding: 2px 8px;
  border-radius: 4px;
}
.page-title {
  font-size: 15px;
  font-weight: 600;
  color: #0f172a;
  letter-spacing: 0.5px;
}
.chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 11.5px;
  color: #475569;
  border: 1px solid #e2e8f0;
  border-radius: 999px;
  padding: 4px 12px;
  background: #f8fafc;
}
.dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #10b981;
  box-shadow: 0 0 8px rgba(16, 185, 129, 0.8);
}
.main {
  flex: 1;
  overflow: auto;
  background: #f8fafc;
}
/* 内容区加宽 */
.main :deep(.page) {
  max-width: 1440px;
}
</style>
