<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useUserStore } from '../stores/user'

const router = useRouter()
const store = useUserStore()
const mode = ref<'login' | 'register'>('login')
const username = ref('')
const password = ref('')
const loading = ref(false)

const stats = ref([
  { label: '评估合同', value: 0, target: 31, suffix: '' },
  { label: '抽取准确率', value: 0, target: 95.5, suffix: '%' },
  { label: '类条款', value: 0, target: 13, suffix: '' },
])

const features = [
  { icon: '🎯', title: '风险分级标注', desc: '合规 / 偏离 / 缺失 / 冲突' },
  { icon: '📍', title: '条款定位引用', desc: '原文可追溯' },
  { icon: '✍️', title: '修订建议', desc: '可直接替换' },
  { icon: '📊', title: '审查报告', desc: '一键查看' },
]

onMounted(() => {
  stats.value.forEach((s) => {
    const start = performance.now()
    const dur = 900
    const step = (now: number) => {
      const p = Math.min((now - start) / dur, 1)
      const eased = 1 - Math.pow(1 - p, 3)
      s.value = s.target * eased
      if (p < 1) requestAnimationFrame(step)
    }
    requestAnimationFrame(step)
  })
})

function fmt(v: number) {
  return Number.isInteger(v) ? Math.round(v) : v.toFixed(1)
}

async function submit() {
  if (!username.value || !password.value) {
    ElMessage.warning('请填写用户名和密码')
    return
  }
  loading.value = true
  try {
    if (mode.value === 'login') {
      await store.login(username.value, password.value)
    } else {
      await store.register(username.value, password.value)
    }
    ElMessage.success(mode.value === 'login' ? '登录成功' : '注册成功')
    router.push(store.isAdmin ? '/admin/overview' : '/home')
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '操作失败')
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="auth-page">
    <!-- 整页背景光斑 -->
    <div class="blob blob-1"></div>
    <div class="blob blob-2"></div>
    <div class="blob blob-3"></div>
    <div class="grid-fade"></div>

    <div class="content">
      <!-- 左：品牌内容（直接在背景上） -->
      <section class="brand">
        <div class="logo">
          <span class="logo-icon">⚖️</span>
          <div>
            <div class="logo-name">合同智能审查</div>
            <div class="logo-sub">CONTRACT REVIEW AGENT</div>
          </div>
        </div>

        <h1>
          合同风险，<br />
          <span class="gradient-text">一眼看清</span>
        </h1>
        <p class="lead">上传合同，自动识别 13 类核心条款与风险点，给出原文定位与可直接使用的修订建议。</p>

        <div class="features">
          <div v-for="f in features" :key="f.title" class="feature">
            <span class="f-icon">{{ f.icon }}</span>
            <div>
              <div class="f-title">{{ f.title }}</div>
              <div class="f-desc">{{ f.desc }}</div>
            </div>
          </div>
        </div>

        <div class="stats">
          <div v-for="s in stats" :key="s.label" class="stat">
            <div class="stat-value">{{ fmt(s.value) }}{{ s.suffix }}</div>
            <div class="stat-label">{{ s.label }}</div>
          </div>
        </div>
      </section>

      <!-- 右：悬浮登录卡片 -->
      <section class="form-wrap">
        <div class="form-card">
          <h2>欢迎回来</h2>
          <p class="sub">登录后开始审查合同</p>

          <div class="tabs">
            <button :class="{ active: mode === 'login' }" @click="mode = 'login'">登录</button>
            <button :class="{ active: mode === 'register' }" @click="mode = 'register'">注册</button>
          </div>

          <label>用户名</label>
          <input v-model="username" placeholder="请输入用户名" autocomplete="username" />

          <label>密码</label>
          <input
            v-model="password"
            type="password"
            placeholder="至少 6 位"
            autocomplete="current-password"
            @keyup.enter="submit"
          />

          <button class="submit" :disabled="loading" @click="submit">
            {{ loading ? '处理中…' : mode === 'login' ? '登录' : '注册' }}
          </button>

          <div class="footer">默认管理员：admin / admin123</div>
        </div>
      </section>
    </div>
  </div>
</template>

<style scoped>
.auth-page {
  position: relative;
  min-height: 100vh;
  overflow: hidden;
  background: linear-gradient(140deg, #070d1a 0%, #0e1a33 45%, #13234f 100%);
  display: flex;
  align-items: center;
  justify-content: center;
}

/* 背景光斑（整页） */
.blob {
  position: absolute;
  border-radius: 50%;
  filter: blur(90px);
  pointer-events: none;
  animation: float 18s ease-in-out infinite;
}
.blob-1 {
  width: 520px;
  height: 520px;
  top: -160px;
  left: -120px;
  background: rgba(37, 99, 235, 0.55);
}
.blob-2 {
  width: 560px;
  height: 560px;
  bottom: -220px;
  right: -140px;
  background: rgba(124, 58, 237, 0.45);
  animation-delay: -6s;
}
.blob-3 {
  width: 360px;
  height: 360px;
  top: 45%;
  right: 26%;
  background: rgba(14, 165, 233, 0.32);
  animation-delay: -11s;
}
@keyframes float {
  0%,
  100% {
    transform: translate(0, 0) scale(1);
  }
  33% {
    transform: translate(30px, -34px) scale(1.08);
  }
  66% {
    transform: translate(-24px, 22px) scale(0.95);
  }
}
.grid-fade {
  position: absolute;
  inset: 0;
  background-image: radial-gradient(circle, rgba(255, 255, 255, 0.05) 1px, transparent 1px);
  background-size: 28px 28px;
  mask-image: radial-gradient(ellipse at 30% 40%, rgba(0, 0, 0, 0.9), transparent 75%);
  -webkit-mask-image: radial-gradient(ellipse at 30% 40%, rgba(0, 0, 0, 0.9), transparent 75%);
  pointer-events: none;
}

.content {
  position: relative;
  z-index: 1;
  display: flex;
  align-items: center;
  gap: 72px;
  width: 100%;
  max-width: 1240px;
  padding: 56px;
}

/* 左侧品牌 */
.brand {
  flex: 1;
  min-width: 0;
  color: #e2e8f0;
}
.logo {
  display: flex;
  align-items: center;
  gap: 14px;
  margin-bottom: 44px;
}
.logo-icon {
  width: 52px;
  height: 52px;
  border-radius: 16px;
  background: linear-gradient(135deg, #3b82f6, #6366f1);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 26px;
  box-shadow: 0 10px 30px -8px rgba(59, 130, 246, 0.7);
}
.logo-name {
  font-size: 19px;
  font-weight: 700;
  color: #fff;
}
.logo-sub {
  font-size: 11px;
  letter-spacing: 2px;
  color: #64748b;
  margin-top: 2px;
}
h1 {
  font-size: 46px;
  line-height: 1.18;
  font-weight: 800;
  margin: 0 0 18px;
  color: #fff;
}
.gradient-text {
  background: linear-gradient(95deg, #60a5fa, #a78bfa, #f472b6, #60a5fa);
  background-size: 250% auto;
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
  animation: shift 7s ease infinite;
}
@keyframes shift {
  0%,
  100% {
    background-position: 0% 50%;
  }
  50% {
    background-position: 100% 50%;
  }
}
.lead {
  color: #94a3b8;
  font-size: 15px;
  line-height: 1.8;
  margin: 0 0 32px;
  max-width: 460px;
}
.features {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  margin-bottom: 36px;
  max-width: 520px;
}
.feature {
  display: flex;
  gap: 12px;
  align-items: flex-start;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.09);
  border-radius: 14px;
  padding: 14px;
  backdrop-filter: blur(6px);
  transition: all 0.2s;
}
.feature:hover {
  background: rgba(255, 255, 255, 0.08);
  border-color: rgba(96, 165, 250, 0.45);
  transform: translateY(-2px);
}
.f-icon {
  font-size: 20px;
}
.f-title {
  font-size: 13px;
  font-weight: 600;
  color: #e2e8f0;
}
.f-desc {
  font-size: 11px;
  color: #64748b;
  margin-top: 2px;
}
.stats {
  display: flex;
  gap: 48px;
}
.stat-value {
  font-size: 30px;
  font-weight: 800;
  color: #fff;
}
.stat-label {
  font-size: 12px;
  color: #64748b;
  margin-top: 2px;
}

/* 右侧悬浮卡片 */
.form-wrap {
  flex-shrink: 0;
}
.form-card {
  width: 400px;
  background: #fff;
  border-radius: 24px;
  padding: 40px 36px;
  box-shadow:
    0 40px 80px -30px rgba(0, 0, 0, 0.55),
    0 0 0 1px rgba(255, 255, 255, 0.06);
  animation: rise 0.5s ease both;
}
@keyframes rise {
  from {
    opacity: 0;
    transform: translateY(16px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
h2 {
  margin: 0 0 6px;
  font-size: 24px;
  color: #0f172a;
}
.sub {
  margin: 0 0 26px;
  font-size: 13px;
  color: #94a3b8;
}
.tabs {
  display: flex;
  gap: 24px;
  border-bottom: 1px solid #e2e8f0;
  margin-bottom: 22px;
}
.tabs button {
  background: none;
  border: none;
  padding: 0 0 12px;
  font-size: 14px;
  color: #94a3b8;
  cursor: pointer;
  border-bottom: 2px solid transparent;
  margin-bottom: -1px;
}
.tabs button.active {
  color: #1d4ed8;
  font-weight: 600;
  border-bottom-color: #1d4ed8;
}
label {
  display: block;
  font-size: 12px;
  font-weight: 500;
  color: #475569;
  margin: 14px 0 6px;
}
input {
  width: 100%;
  border: 1px solid #dbe3ee;
  border-radius: 10px;
  padding: 11px 14px;
  font-size: 14px;
  outline: none;
  transition: all 0.15s;
}
input:focus {
  border-color: #1d4ed8;
  box-shadow: 0 0 0 4px rgba(29, 78, 216, 0.1);
}
.submit {
  width: 100%;
  margin-top: 24px;
  background: linear-gradient(135deg, #2563eb, #4f46e5);
  color: #fff;
  border: none;
  border-radius: 10px;
  padding: 12px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
  box-shadow: 0 10px 24px -10px rgba(37, 99, 235, 0.7);
}
.submit:hover {
  transform: translateY(-1px);
  box-shadow: 0 14px 28px -10px rgba(37, 99, 235, 0.8);
}
.submit:disabled {
  opacity: 0.6;
  cursor: default;
  transform: none;
}
.footer {
  margin-top: 22px;
  text-align: center;
  font-size: 12px;
  color: #94a3b8;
}

@media (max-width: 1080px) {
  .content {
    justify-content: center;
  }
  .brand {
    display: none;
  }
}
@media (max-width: 520px) {
  .form-card {
    width: 92vw;
    padding: 32px 24px;
  }
}
</style>
