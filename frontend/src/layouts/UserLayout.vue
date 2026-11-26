<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowDown } from '@element-plus/icons-vue'
import { useUserStore } from '../stores/user'

const route = useRoute()
const router = useRouter()
const store = useUserStore()
const scrolled = ref(false)

function onScroll() {
  scrolled.value = window.scrollY > 8
}

onBeforeUnmount(() => window.removeEventListener('scroll', onScroll))

const menus = [
  { path: '/home', label: '首页' },
  { path: '/review', label: '合同审查' },
  { path: '/chat', label: 'AI 对话' },
  { path: '/compare', label: '合同对比' },
  { path: '/templates', label: '合同模板' },
  { path: '/eval', label: '评估数据' },
]

const initial = computed(() => (store.user?.username || '?').slice(0, 1).toUpperCase())

function onCommand(cmd: string) {
  if (cmd === 'me') router.push('/me/overview')
  else if (cmd === 'admin') router.push('/admin/overview')
  else if (cmd === 'logout') {
    store.logout()
    router.push('/login')
  }
}

onMounted(() => {
  store.fetchMe()
  window.addEventListener('scroll', onScroll, { passive: true })
  onScroll()
})
</script>

<template>
  <div class="shell">
    <header class="topnav" :class="{ scrolled }">
      <div class="nav-inner">
        <div class="brand" @click="router.push('/home')">
          <div class="logo">
            <span class="mk">合</span>
            <i class="shine"></i>
          </div>
          <div class="brand-text">
            <div class="brand-name">合同审查</div>
            <div class="brand-sub">CONTRACT REVIEW</div>
          </div>
        </div>

        <nav class="menu">
          <RouterLink v-for="m in menus" :key="m.path" :to="m.path" class="menu-item">
            {{ m.label }}
          </RouterLink>
        </nav>

        <el-dropdown trigger="click" @command="onCommand">
          <div class="user-chip">
            <div class="avatar">{{ initial }}</div>
            <span class="uname">{{ store.user?.username || '...' }}</span>
            <el-icon class="caret"><ArrowDown /></el-icon>
          </div>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="me">个人中心</el-dropdown-item>
              <el-dropdown-item v-if="store.isAdmin" command="admin">管理后台</el-dropdown-item>
              <el-dropdown-item divided command="logout">退出登录</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
    </header>

    <main class="main">
      <router-view />
    </main>
  </div>
</template>

<style scoped>
.shell {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  background: #faf8f4;
}
.topnav {
  position: sticky;
  top: 0;
  z-index: 100;
  background: rgba(250, 248, 244, 0.92);
  backdrop-filter: blur(14px);
  border-bottom: 1px solid #e6e2da;
  transition: box-shadow 0.25s ease, background 0.25s ease;
}
.topnav.scrolled {
  background: rgba(250, 248, 244, 0.97);
  box-shadow: 0 12px 30px -24px rgba(20, 22, 26, 0.45);
}
.nav-inner {
  max-width: 1200px;
  margin: 0 auto;
  height: 72px;
  padding: 0 28px;
  display: flex;
  align-items: center;
  gap: 36px;
}
.brand {
  display: flex;
  align-items: center;
  gap: 10px;
  cursor: pointer;
  flex-shrink: 0;
}
.logo {
  width: 38px;
  height: 38px;
  border: 1px solid #14161a;
  background: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  overflow: hidden;
}
.mk {
  font-family: 'Noto Serif SC', 'Songti SC', 'SimSun', Georgia, serif;
  font-size: 19px;
  font-weight: 600;
  line-height: 1;
  background: linear-gradient(135deg, #1e3a8a 0%, #4f46e5 55%, #7c3aed 100%);
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
}
.shine {
  position: absolute;
  top: -60%;
  left: -80%;
  width: 60%;
  height: 220%;
  background: linear-gradient(
    100deg,
    transparent 0%,
    rgba(255, 255, 255, 0.75) 50%,
    transparent 100%
  );
  transform: rotate(18deg);
  animation: logo-shine 4.2s ease-in-out infinite;
  pointer-events: none;
}
@keyframes logo-shine {
  0%,
  58% {
    left: -80%;
  }
  82%,
  100% {
    left: 140%;
  }
}
.logo::after {
  content: '';
  position: absolute;
  right: 0;
  bottom: 0;
  width: 7px;
  height: 7px;
  background: #b4442f;
}
.brand:hover .logo::after {
  width: 11px;
  height: 11px;
  transition: all 0.2s ease;
}
@media (prefers-reduced-motion: reduce) {
  .shine {
    animation: none;
    display: none;
  }
}
.brand-name {
  font-family: 'Noto Serif SC', 'Songti SC', 'SimSun', Georgia, serif;
  font-size: 17px;
  font-weight: 600;
  color: #14161a;
  letter-spacing: 3px;
}
.brand-sub {
  font-size: 8px;
  letter-spacing: 3.2px;
  color: #b3b0a8;
  margin-top: 3px;
}
.menu {
  display: flex;
  align-items: center;
  gap: 30px;
  flex: 1;
  min-width: 0;
  overflow-x: auto;
  height: 100%;
}
.menu-item {
  position: relative;
  display: flex;
  align-items: center;
  height: 100%;
  font-size: 13.5px;
  color: #6b6f76;
  text-decoration: none;
  white-space: nowrap;
  letter-spacing: 0.5px;
  transition: color 0.15s;
}
.menu-item::after {
  content: '';
  position: absolute;
  left: 50%;
  bottom: 0;
  width: 68%;
  height: 2px;
  border-radius: 2px;
  background: linear-gradient(90deg, #60a5fa, #a78bfa);
  transform: translateX(-50%) scaleX(0);
  transition: transform 0.22s ease;
}
.menu-item:hover {
  color: #5b5bd6;
}
.menu-item.router-link-active {
  color: #14161a;
}
.menu-item.router-link-active::after {
  transform: translateX(-50%) scaleX(1);
}
.user-chip {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px 10px 4px 4px;
  border-radius: 999px;
  border: 1px solid #e6e2da;
  background: #fff;
  cursor: pointer;
  flex-shrink: 0;
}
.user-chip:hover {
  border-color: #c9c3b8;
}
.avatar {
  width: 26px;
  height: 26px;
  border-radius: 50%;
  background: #14161a;
  color: #f5f3ef;
  font-size: 11px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
}
.uname {
  font-size: 12.5px;
  color: #334155;
  letter-spacing: 0.3px;
  max-width: 100px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.caret {
  font-size: 12px;
  color: #b3b0a8;
}
.main {
  flex: 1;
  background: #faf8f4;
}
@media (max-width: 900px) {
  .brand-text {
    display: none;
  }
  .uname {
    display: none;
  }
}
</style>
