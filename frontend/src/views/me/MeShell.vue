<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()

const tabs = [
  { path: '/me/overview', label: '概览' },
  { path: '/me/reviews', label: '我的审查' },
  { path: '/me/account', label: '账户' },
]

const active = computed(() => route.path)
</script>

<template>
  <div class="me-shell">
    <!-- 第一层：个人中心条 -->
    <div class="me-bar">
      <div class="me-bar-inner">
        <div class="me-head">
          <span class="me-eyebrow">PERSONAL CENTER</span>
          <span class="me-title">个人中心</span>
        </div>
        <nav class="me-tabs">
          <RouterLink
            v-for="t in tabs"
            :key="t.path"
            :to="t.path"
            class="me-tab"
            :class="{ active: active.startsWith(t.path) }"
          >
            {{ t.label }}
          </RouterLink>
        </nav>
      </div>
    </div>

    <!-- 第二层：白色纸面 -->
    <div class="me-sheet">
      <router-view v-slot="{ Component }">
        <transition name="me-fade" mode="out-in">
          <component :is="Component" />
        </transition>
      </router-view>
    </div>
  </div>
</template>

<style scoped>
.me-shell {
  background: #f1ece4;
  min-height: calc(100vh - 72px);
  display: flex;
  flex-direction: column;
}
.me-bar {
  background: #f1ece4;
}
.me-bar-inner {
  max-width: 1120px;
  margin: 0 auto;
  padding: 22px 32px 0;
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 24px;
  flex-wrap: wrap;
}
.me-head {
  display: flex;
  align-items: baseline;
  gap: 12px;
  padding-bottom: 16px;
}
.me-eyebrow {
  font-size: 10px;
  letter-spacing: 3px;
  color: #a8a29a;
}
.me-title {
  font-family: 'Noto Serif SC', 'Songti SC', 'SimSun', Georgia, serif;
  font-size: 22px;
  font-weight: 600;
  color: #14161a;
  letter-spacing: 1.5px;
}
.me-tabs {
  display: flex;
  gap: 26px;
}
.me-tab {
  position: relative;
  padding: 0 0 16px;
  font-size: 13.5px;
  color: #7a746a;
  text-decoration: none;
  letter-spacing: 0.5px;
  border-bottom: 2px solid transparent;
  transition: color 0.15s;
}
.me-tab:hover {
  color: #14161a;
}
.me-tab.active {
  color: #14161a;
  border-bottom-color: #14161a;
}
/* 白色纸面：压在个人中心条下面 */
.me-sheet {
  flex: 1;
  background: #fff;
  border-radius: 16px 16px 0 0;
  box-shadow: 0 -22px 50px -45px rgba(20, 22, 26, 0.65);
  padding-top: 8px;
  animation: sheet-in 0.55s cubic-bezier(0.2, 0.7, 0.2, 1) both;
}
@keyframes sheet-in {
  from {
    opacity: 0;
    transform: translateY(18px);
  }
  to {
    opacity: 1;
    transform: none;
  }
}
/* 页面切换过渡 */
.me-fade-enter-active,
.me-fade-leave-active {
  transition:
    opacity 0.26s ease,
    transform 0.26s cubic-bezier(0.2, 0.7, 0.2, 1);
}
.me-fade-enter-from {
  opacity: 0;
  transform: translateY(12px);
}
.me-fade-leave-to {
  opacity: 0;
  transform: translateY(-8px);
}
@media (prefers-reduced-motion: reduce) {
  .me-sheet {
    animation: none;
  }
  .me-fade-enter-active,
  .me-fade-leave-active {
    transition: none;
  }
}
</style>
