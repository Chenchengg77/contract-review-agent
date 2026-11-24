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
  // 主动告警：失败率 > 5% 时提示管理员
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
        <div class="brand-logo">🛡️</div>
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
  background: #f6f8fb;
}
.sidebar {
  width: 236px;
  flex-shrink: 0;
  background: linear-gradient(180deg, #140f26 0%, #1a1333 100%);
  color: #a5a1bd;
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
  background: linear-gradient(135deg, #8b5cf6, #d946ef);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 19px;
  box-shadow: 0 8px 20px -8px rgba(139, 92, 246, 0.8);
}
.brand-name {
  font-size: 15px;
  font-weight: 700;
  color: #fff;
}
.brand-sub {
  font-size: 9px;
  letter-spacing: 1.5px;
  color: #4c4670;
  margin-top: 2px;
}
.nav-label {
  font-size: 10px;
  letter-spacing: 1.5px;
  color: #4c4670;
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
  color: #a5a1bd;
  text-decoration: none;
  font-size: 13.5px;
  transition: all 0.15s;
  border: 1px solid transparent;
}
.nav-item:hover {
  background: rgba(255, 255, 255, 0.05);
  color: #ede9fe;
}
.nav-item.router-link-active {
  background: linear-gradient(90deg, rgba(139, 92, 246, 0.9), rgba(217, 70, 239, 0.8));
  color: #fff;
  font-weight: 500;
  border-color: rgba(196, 181, 253, 0.3);
  box-shadow: 0 8px 18px -10px rgba(139, 92, 246, 0.9);
}
.nav-icon {
  font-size: 16px;
}
.nav-dot {
  margin-left: auto;
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #ef4444;
  box-shadow: 0 0 0 3px rgba(239, 68, 68, 0.18);
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
  color: #c4b5fd;
  cursor: pointer;
  transition: all 0.15s;
}
.back-card:hover {
  background: rgba(139, 92, 246, 0.15);
  border-color: rgba(196, 181, 253, 0.4);
}
.user-box {
  margin: auto 12px 12px;
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
  background: linear-gradient(135deg, #8b5cf6, #d946ef);
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
  color: #ede9fe;
  font-weight: 500;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.user-role {
  font-size: 10px;
  color: #7c7899;
  margin-top: 1px;
}
.icon-btn {
  background: none;
  border: none;
  color: #7c7899;
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
.admin-badge {
  font-size: 11px;
  color: #7c3aed;
  background: #f5f3ff;
  border: 1px solid #ddd6fe;
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
    radial-gradient(1200px 400px at 100% -10%, rgba(139, 92, 246, 0.06), transparent 60%),
    #f6f8fb;
}
</style>
