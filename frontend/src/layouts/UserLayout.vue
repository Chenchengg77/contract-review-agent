<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  HomeFilled,
  Search,
  ChatDotRound,
  Switch,
  Document,
  DataAnalysis,
  InfoFilled,
  SwitchButton,
  Setting,
} from '@element-plus/icons-vue'
import { useUserStore } from '../stores/user'

const route = useRoute()
const router = useRouter()
const store = useUserStore()

const menus = [
  { path: '/home', label: '首页', icon: HomeFilled },
  { path: '/review', label: '合同审查', icon: Search },
  { path: '/chat', label: 'AI 对话', icon: ChatDotRound },
  { path: '/compare', label: '合同对比', icon: Switch },
  { path: '/templates', label: '合同模板', icon: Document },
  { path: '/eval', label: '评估数据', icon: DataAnalysis },
  { path: '/about', label: '关于', icon: InfoFilled },
]

const TITLES: Record<string, string> = {
  '/home': '首页',
  '/review': '合同审查',
  '/chat': 'AI 对话',
  '/compare': '合同对比',
  '/templates': '合同模板',
  '/eval': '评估数据',
  '/me': '个人中心',
  '/about': '关于',
}

const currentTitle = computed(() => TITLES[route.path] || '')

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
        <div class="brand-logo">⚖️</div>
        <div class="brand-text">
          <div class="brand-name">合同审查</div>
          <div class="brand-sub">CONTRACT REVIEW</div>
        </div>
      </div>

      <div class="nav-label">导航</div>
      <nav class="nav">
        <RouterLink v-for="m in menus" :key="m.path" :to="m.path" class="nav-item">
          <el-icon class="nav-icon"><component :is="m.icon" /></el-icon>
          <span>{{ m.label }}</span>
        </RouterLink>
      </nav>

      <div class="tips">
        <div class="tips-title">三步上手</div>
        <div class="tip-row"><span>1</span> 上传 .docx 合同</div>
        <div class="tip-row"><span>2</span> AI 抽取 13 类条款</div>
        <div class="tip-row"><span>3</span> 输出风险报告</div>
      </div>

      <div class="status-card">
        <div class="status-row"><i class="dot"></i> 模型：DeepSeek-Chat</div>
        <div class="status-row"><span class="ic">⏱</span> 单份约 2 秒</div>
        <div class="status-row"><span class="ic">💰</span> 成本约 1 分钱</div>
      </div>

      <div class="user-box clickable" @click="router.push('/me/overview')">
        <div class="avatar">{{ initial }}</div>
        <div class="user-info">
          <div class="user-name">{{ store.user?.username || '...' }}</div>
          <div class="user-role">{{ store.isAdmin ? '管理员' : '普通用户' }} · 个人中心</div>
        </div>
        <el-tooltip v-if="store.isAdmin" content="进入管理后台" placement="top">
          <button class="icon-btn" @click.stop="router.push('/admin')">
            <el-icon><Setting /></el-icon>
          </button>
        </el-tooltip>
        <el-tooltip content="退出登录" placement="top">
          <button class="icon-btn" @click.stop="logout">
            <el-icon><SwitchButton /></el-icon>
          </button>
        </el-tooltip>
      </div>
    </aside>

    <div class="body">
      <header class="topbar">
        <div class="page-title">{{ currentTitle }}</div>
        <div class="top-right">
          <span class="chip"><span class="dot"></span>DeepSeek-Chat</span>
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
  background: linear-gradient(180deg, #0a1120 0%, #101c33 100%);
  color: #94a3b8;
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
  background: linear-gradient(135deg, #3b82f6, #6366f1);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  box-shadow: 0 8px 20px -8px rgba(59, 130, 246, 0.8);
}
.brand-name {
  font-size: 15px;
  font-weight: 700;
  color: #fff;
  letter-spacing: 0.5px;
}
.brand-sub {
  font-size: 9px;
  letter-spacing: 1.5px;
  color: #475569;
  margin-top: 2px;
}
.nav-label {
  font-size: 10px;
  letter-spacing: 1.5px;
  color: #475569;
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
  color: #94a3b8;
  text-decoration: none;
  font-size: 13.5px;
  transition: all 0.15s;
  border: 1px solid transparent;
}
.nav-item:hover {
  background: rgba(255, 255, 255, 0.05);
  color: #e2e8f0;
}
.nav-item.router-link-active {
  background: linear-gradient(90deg, rgba(37, 99, 235, 0.9), rgba(79, 70, 229, 0.85));
  color: #fff;
  font-weight: 500;
  border-color: rgba(96, 165, 250, 0.3);
  box-shadow: 0 8px 18px -10px rgba(37, 99, 235, 0.9);
}
.nav-icon {
  font-size: 16px;
}
.tips {
  margin: 18px 12px 0;
  padding: 14px;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.06);
}
.tips-title {
  font-size: 10px;
  letter-spacing: 1.5px;
  color: #475569;
  margin-bottom: 10px;
}
.tip-row {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: #94a3b8;
  margin-bottom: 8px;
}
.tip-row:last-child {
  margin-bottom: 0;
}
.tip-row span {
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: rgba(37, 99, 235, 0.22);
  color: #93c5fd;
  font-size: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.status-card {
  margin: auto 12px 10px;
  padding: 12px 14px;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.06);
}
.status-row {
  display: flex;
  align-items: center;
  gap: 7px;
  font-size: 11.5px;
  color: #64748b;
  margin-bottom: 6px;
}
.status-row:last-child {
  margin-bottom: 0;
}
.dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #22c55e;
  box-shadow: 0 0 0 3px rgba(34, 197, 94, 0.15);
  display: inline-block;
}
.ic {
  font-size: 11px;
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
.user-box.clickable {
  cursor: pointer;
  transition: all 0.15s;
}
.user-box.clickable:hover {
  background: rgba(255, 255, 255, 0.07);
  border-color: rgba(147, 197, 253, 0.35);
}
.avatar {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: linear-gradient(135deg, #3b82f6, #8b5cf6);
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
  color: #e2e8f0;
  font-weight: 500;
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
  font-size: 16px;
  display: flex;
  padding: 4px;
  border-radius: 6px;
}
.icon-btn:hover {
  color: #93c5fd;
  background: rgba(147, 197, 253, 0.1);
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
.main {
  flex: 1;
  overflow: auto;
  background:
    radial-gradient(1200px 400px at 100% -10%, rgba(37, 99, 235, 0.05), transparent 60%),
    #f6f8fb;
}
</style>
