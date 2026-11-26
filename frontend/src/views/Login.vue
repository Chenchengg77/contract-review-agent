<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useUserStore } from '../stores/user'
import DocParticles from '../components/DocParticles.vue'

const router = useRouter()
const store = useUserStore()
const mode = ref<'login' | 'register'>('login')
const username = ref('')
const password = ref('')
const loading = ref(false)

const cards = [
  { title: '风险标注', desc: '合规 / 偏离 / 缺失 / 冲突', icon: 'shield' },
  { title: '条款定位', desc: '引用条款号，可点开原文', icon: 'pin' },
  { title: '审查报告', desc: '结构化输出，逐条可追溯', icon: 'doc' },
]

// 按钮粒子爆发
const burst = ref<{ id: number; dx: number; dy: number; c: string }[]>([])

function fireBurst() {
  const base = Date.now()
  burst.value = Array.from({ length: 16 }, (_, i) => {
    const ang = (Math.PI * 2 * i) / 16 + Math.random() * 0.35
    const dist = 42 + Math.random() * 58
    return {
      id: base + i,
      dx: Math.cos(ang) * dist,
      dy: Math.sin(ang) * dist,
      c: i % 2 ? '#67e8f9' : '#a78bfa',
    }
  })
  setTimeout(() => {
    burst.value = []
  }, 820)
}

async function submit() {
  if (!username.value || !password.value) {
    ElMessage.warning('请填写用户名和密码')
    return
  }
  fireBurst()
  loading.value = true
  try {
    if (mode.value === 'login') {
      await store.login(username.value, password.value)
      ElMessage.success('登录成功')
      router.push(store.isAdmin ? '/admin/overview' : '/home')
      return
    }

    await store.register(username.value, password.value)
    store.logout()
    mode.value = 'login'
    password.value = ''
    ElMessage.success('注册成功，请用新账号登录')
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '操作失败')
  } finally {
    loading.value = false
  }
}

async function demoLogin() {
  fireBurst()
  loading.value = true
  try {
    await store.login('demo01', 'demo123456')
    ElMessage.success('已进入演示账号')
    router.push('/home')
  } catch {
    ElMessage.error('演示账号不存在，请用 admin / admin123')
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="auth">
    <div class="glow glow-cyan" aria-hidden="true"></div>
    <div class="glow glow-violet" aria-hidden="true"></div>
    <div class="scan" aria-hidden="true"></div>
    <DocParticles :count="18" />

    <div class="auth-inner">
      <!-- 左侧品牌区 -->
      <section class="brand-side">
        <div class="brand">
          <div class="logo">合</div>
          <div>
            <div class="brand-name">合同智能审查</div>
            <div class="brand-sub">CONTRACT REVIEW AGENT</div>
          </div>
        </div>

        <div class="headline-panel">
          <h1 class="headline">
            合同风险，<br />
            <em>一眼看清</em>
          </h1>
        </div>

        <p class="lead">上传合同，自动识别 13 类核心条款与风险点，给出原文定位与改写建议。</p>

        <div class="cards">
          <div v-for="c in cards" :key="c.title" class="fcard">
            <div class="ficon" :class="c.icon">
              <svg v-if="c.icon === 'shield'" viewBox="0 0 24 24" class="ico-shield">
                <path d="M12 3.2 19 6v5.6c0 4.6-3 7.6-7 9.2-4-1.6-7-4.6-7-9.2V6l7-2.8Z" />
              </svg>
              <template v-else-if="c.icon === 'pin'">
                <span class="pin-dot"></span>
                <span class="pin-ring"></span>
              </template>
              <template v-else>
                <span class="doc-sheet"></span>
                <span class="doc-sheet back"></span>
              </template>
            </div>
            <div class="fcard-title">{{ c.title }}</div>
            <div class="fcard-desc">{{ c.desc }}</div>
          </div>
        </div>

        <button class="demo-btn" :disabled="loading" @click="demoLogin">
          <span class="demo-ico">
            <svg viewBox="0 0 24 24" class="ico-up">
              <path d="M12 16V5m0 0-4 4m4-4 4 4" />
              <path d="M5 17h14" />
            </svg>
          </span>
          <span>一键体验 Demo</span>
        </button>
      </section>

      <!-- 右侧玻璃登录卡 -->
      <section class="form-side">
        <div class="glass-card">
          <h2 class="card-title">欢迎回来</h2>
          <p class="card-sub">登录后开始审查合同</p>

          <!-- 液体 Tab -->
          <div class="tabs">
            <button class="tab" :class="{ active: mode === 'login' }" @click="mode = 'login'">登录</button>
            <button class="tab" :class="{ active: mode === 'register' }" @click="mode = 'register'">注册</button>
            <span class="tab-ink" :class="{ right: mode === 'register' }"></span>
          </div>

          <div class="field">
            <label>用户名</label>
            <div class="input-shell">
              <el-input v-model="username" placeholder="请输入用户名" size="large" @keyup.enter="submit" />
              <span class="streak"></span>
            </div>
          </div>
          <div class="field">
            <label>密码</label>
            <div class="input-shell">
              <el-input
                v-model="password"
                type="password"
                placeholder="至少 6 位"
                size="large"
                show-password
                @keyup.enter="submit"
              />
              <span class="streak"></span>
            </div>
          </div>

          <button class="submit" :disabled="loading" @click="submit">
            <span class="submit-label">{{ loading ? '处理中…' : mode === 'login' ? '登录' : '注册' }}</span>
            <span
              v-for="p in burst"
              :key="p.id"
              class="spark"
              :style="{ '--dx': p.dx + 'px', '--dy': p.dy + 'px', background: p.c }"
            ></span>
          </button>

          <!-- 演示账号气泡 -->
          <div class="demo-bubble">
            <button class="bubble-trigger">查看演示账号</button>
            <div class="bubble">
              <div class="bubble-arrow"></div>
              <div class="bubble-row"><span>管理员</span>admin / admin123</div>
              <div class="bubble-row"><span>演示用户</span>demo01 / demo123456</div>
            </div>
          </div>
        </div>
      </section>
    </div>
  </div>
</template>

<style scoped>
.auth {
  min-height: 100vh;
  position: relative;
  overflow: hidden;
  background-color: #0f141c;
  background-image:
    linear-gradient(rgba(148, 163, 184, 0.05) 1px, transparent 1px),
    linear-gradient(90deg, rgba(148, 163, 184, 0.05) 1px, transparent 1px),
    linear-gradient(rgba(148, 163, 184, 0.028) 1px, transparent 1px),
    linear-gradient(90deg, rgba(148, 163, 184, 0.028) 1px, transparent 1px);
  background-size:
    96px 96px,
    96px 96px,
    24px 24px,
    24px 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 48px 24px;
}
.glow {
  position: absolute;
  border-radius: 50%;
  pointer-events: none;
  filter: blur(10px);
  z-index: 0;
}
.glow-cyan {
  width: 720px;
  height: 720px;
  left: -14%;
  top: -22%;
  background: radial-gradient(circle, rgba(34, 211, 238, 0.17) 0%, transparent 68%);
}
.glow-violet {
  width: 680px;
  height: 680px;
  right: -10%;
  bottom: -24%;
  background: radial-gradient(circle, rgba(139, 92, 246, 0.15) 0%, transparent 68%);
}
.scan {
  position: absolute;
  top: 10%;
  height: 80%;
  left: 4%;
  width: 1px;
  background: linear-gradient(180deg, transparent, rgba(103, 232, 249, 0.85), transparent);
  box-shadow: 0 0 26px 5px rgba(34, 211, 238, 0.22);
  pointer-events: none;
  z-index: 2;
  animation: scan-move 9s ease-in-out infinite;
}
.scan::after {
  content: '';
  position: absolute;
  top: 0;
  bottom: 0;
  right: 0;
  width: 200px;
  background: linear-gradient(90deg, transparent, rgba(34, 211, 238, 0.09), transparent);
  filter: blur(8px);
  transform: translateX(-100%);
}
@keyframes scan-move {
  0% {
    left: 4%;
    opacity: 0;
  }
  10% {
    opacity: 1;
  }
  86% {
    opacity: 1;
  }
  100% {
    left: 50%;
    opacity: 0;
  }
}
.auth-inner {
  position: relative;
  z-index: 3;
  width: 100%;
  max-width: 1120px;
  display: grid;
  grid-template-columns: 1.15fr 0.85fr;
  gap: 72px;
  align-items: center;
}
/* 左侧 */
.brand {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 40px;
}
.logo {
  width: 40px;
  height: 40px;
  border: 1px solid rgba(148, 163, 184, 0.35);
  display: flex;
  align-items: center;
  justify-content: center;
  font-family: 'Noto Serif SC', 'Songti SC', 'SimSun', Georgia, serif;
  font-size: 20px;
  font-weight: 600;
  color: #7dd3fc;
  position: relative;
}
.logo::after {
  content: '';
  position: absolute;
  right: -1px;
  bottom: -1px;
  width: 8px;
  height: 8px;
  background: #22d3ee;
}
.brand-name {
  font-size: 16px;
  font-weight: 600;
  color: #e9eef6;
  letter-spacing: 2px;
}
.brand-sub {
  font-size: 8px;
  letter-spacing: 3px;
  color: #64748b;
  margin-top: 3px;
}
.headline-panel {
  display: inline-block;
  padding: 28px 38px 32px;
  margin: 0 0 22px;
  border-radius: 20px;
  background: linear-gradient(
    135deg,
    rgba(255, 255, 255, 0.07) 0%,
    rgba(255, 255, 255, 0.03) 45%,
    rgba(255, 255, 255, 0.055) 100%
  );
  -webkit-backdrop-filter: blur(24px) saturate(140%);
  backdrop-filter: blur(24px) saturate(140%);
  border: 1px solid rgba(148, 163, 184, 0.22);
  box-shadow:
    0 40px 90px -60px rgba(0, 0, 0, 0.9),
    inset 0 1px 0 rgba(255, 255, 255, 0.12);
}
.headline {
  font-family: 'HarmonyOS Sans SC', 'MiSans', 'PingFang SC', 'Microsoft YaHei', system-ui, sans-serif;
  font-size: 54px;
  line-height: 1.26;
  font-weight: 800;
  letter-spacing: 1px;
  margin: 0;
  background: linear-gradient(100deg, #f1f5fb 0%, #a5e8fb 35%, #c4b5fd 65%, #f1f5fb 100%);
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
  -webkit-text-stroke: 0.6px rgba(226, 232, 240, 0.25);
  animation: title-breathe 5.5s ease-in-out infinite;
}
@keyframes title-breathe {
  0%,
  100% {
    filter: brightness(1) drop-shadow(0 0 0 rgba(103, 232, 249, 0));
  }
  50% {
    filter: brightness(1.16) drop-shadow(0 0 18px rgba(103, 232, 249, 0.22));
  }
}
.lead {
  font-size: 14px;
  line-height: 2;
  margin: 0 0 30px;
  max-width: 460px;
  background: linear-gradient(90deg, #7c8798 0%, #cfd8e6 45%, #7c8798 100%);
  background-size: 220% 100%;
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
  animation: lead-flow 7s linear infinite;
}
@keyframes lead-flow {
  0% {
    background-position: 200% 0;
  }
  100% {
    background-position: -100% 0;
  }
}
/* 能力卡 */
.cards {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
  margin-bottom: 22px;
}
.fcard {
  position: relative;
  padding: 16px 15px 15px;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.045);
  -webkit-backdrop-filter: blur(16px) saturate(140%);
  backdrop-filter: blur(16px) saturate(140%);
  border: 1px solid rgba(148, 163, 184, 0.18);
  transition:
    transform 0.25s ease,
    box-shadow 0.25s ease,
    background 0.25s ease;
  overflow: hidden;
}
.fcard::before {
  content: '';
  position: absolute;
  inset: 0;
  border-radius: inherit;
  padding: 1px;
  background: linear-gradient(
    120deg,
    transparent 10%,
    rgba(103, 232, 249, 0.95) 35%,
    rgba(167, 139, 250, 0.95) 60%,
    transparent 90%
  );
  background-size: 240% 100%;
  -webkit-mask:
    linear-gradient(#000 0 0) content-box,
    linear-gradient(#000 0 0);
  -webkit-mask-composite: xor;
  mask-composite: exclude;
  opacity: 0;
  transition: opacity 0.3s;
  animation: border-flow 2.8s linear infinite;
  pointer-events: none;
}
.fcard:hover {
  transform: translateY(-4px);
  background: rgba(255, 255, 255, 0.07);
  box-shadow: 0 20px 40px -28px rgba(34, 211, 238, 0.55);
}
.fcard:hover::before {
  opacity: 1;
}
@keyframes border-flow {
  0% {
    background-position: 0% 0;
  }
  100% {
    background-position: 240% 0;
  }
}
.ficon {
  height: 26px;
  margin-bottom: 10px;
  position: relative;
  transition: transform 0.25s ease;
}
.fcard:hover .ficon {
  transform: scale(1.12);
}
.ico-shield {
  width: 22px;
  height: 22px;
  fill: none;
  stroke: #7dd3fc;
  stroke-width: 1.4;
  animation: shield-blink 2.8s ease-in-out infinite;
}
@keyframes shield-blink {
  0%,
  100% {
    opacity: 0.55;
    filter: drop-shadow(0 0 0 rgba(103, 232, 249, 0));
  }
  50% {
    opacity: 1;
    filter: drop-shadow(0 0 6px rgba(103, 232, 249, 0.65));
  }
}
.pin-dot {
  position: absolute;
  left: 6px;
  top: 8px;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #22d3ee;
}
.pin-ring {
  position: absolute;
  left: 2px;
  top: 4px;
  width: 16px;
  height: 16px;
  border-radius: 50%;
  border: 1px solid rgba(34, 211, 238, 0.7);
  animation: pin-pulse 2.2s ease-out infinite;
}
@keyframes pin-pulse {
  0% {
    transform: scale(0.5);
    opacity: 0.9;
  }
  100% {
    transform: scale(1.9);
    opacity: 0;
  }
}
.doc-sheet {
  position: absolute;
  left: 2px;
  top: 3px;
  width: 15px;
  height: 19px;
  border: 1px solid rgba(167, 139, 250, 0.85);
  border-radius: 1px;
  transform-origin: left center;
  animation: doc-flip 3.4s ease-in-out infinite;
}
.doc-sheet.back {
  left: 7px;
  opacity: 0.45;
  animation-delay: -0.6s;
}
@keyframes doc-flip {
  0%,
  60%,
  100% {
    transform: rotateY(0deg);
  }
  80% {
    transform: rotateY(-38deg);
  }
}
.fcard-title {
  font-size: 13px;
  font-weight: 600;
  color: #e2e8f0;
  letter-spacing: 0.5px;
  margin-bottom: 5px;
}
.fcard-desc {
  font-size: 11px;
  color: #7c8798;
  line-height: 1.6;
}
/* Demo 按钮 */
.demo-btn {
  position: relative;
  margin-top: 30px;
  display: inline-flex;
  align-items: center;
  gap: 9px;
  padding: 11px 24px;
  border: none;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.04);
  color: #dbe4f0;
  font-size: 12.5px;
  letter-spacing: 1.5px;
  cursor: pointer;
  overflow: hidden;
  transition: background 0.25s;
}
.demo-btn::before {
  content: '';
  position: absolute;
  inset: 0;
  border-radius: inherit;
  padding: 1px;
  background: linear-gradient(90deg, #22d3ee, #a78bfa, #22d3ee);
  background-size: 220% 100%;
  -webkit-mask:
    linear-gradient(#000 0 0) content-box,
    linear-gradient(#000 0 0);
  -webkit-mask-composite: xor;
  mask-composite: exclude;
  animation: border-flow 3s linear infinite;
  pointer-events: none;
}
.demo-btn:hover {
  background: rgba(255, 255, 255, 0.08);
}
.demo-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
.demo-ico {
  display: inline-flex;
  width: 16px;
  height: 16px;
}
.ico-up {
  width: 16px;
  height: 16px;
  fill: none;
  stroke: #67e8f9;
  stroke-width: 1.5;
  stroke-linecap: round;
  stroke-linejoin: round;
  transition: transform 0.3s ease;
}
.demo-btn:hover .ico-up {
  transform: translateY(-5px);
}
/* ===== 右侧玻璃登录卡 ===== */
.form-side {
  display: flex;
  justify-content: center;
}
.glass-card {
  position: relative;
  width: 100%;
  max-width: 404px;
  padding: 38px 34px 28px;
  border-radius: 18px;
  background: linear-gradient(
    160deg,
    rgba(255, 255, 255, 0.09) 0%,
    rgba(255, 255, 255, 0.03) 52%,
    rgba(255, 255, 255, 0.065) 100%
  );
  -webkit-backdrop-filter: blur(26px) saturate(160%);
  backdrop-filter: blur(26px) saturate(160%);
  border: 1px solid rgba(103, 232, 249, 0.22);
  box-shadow:
    0 50px 100px -60px rgba(0, 0, 0, 0.95),
    0 0 44px -14px rgba(34, 211, 238, 0.28),
    inset 0 1px 0 rgba(255, 255, 255, 0.14);
}
.card-title {
  font-family: 'HarmonyOS Sans SC', 'MiSans', 'PingFang SC', 'Microsoft YaHei', system-ui, sans-serif;
  font-size: 23px;
  font-weight: 700;
  color: #eef2f8;
  margin: 0 0 6px;
  letter-spacing: 1px;
}
.card-sub {
  font-size: 12.5px;
  color: #8b95a6;
  margin: 0 0 24px;
  letter-spacing: 0.5px;
}
/* 液体 Tab */
.tabs {
  position: relative;
  display: grid;
  grid-template-columns: 1fr 1fr;
  border-bottom: 1px solid rgba(148, 163, 184, 0.16);
  margin-bottom: 24px;
}
.tab {
  background: none;
  border: none;
  padding: 0 0 13px;
  font-size: 13.5px;
  color: #7c8798;
  cursor: pointer;
  letter-spacing: 1px;
  transition: color 0.3s;
}
.tab.active {
  color: #e9eef6;
}
.tab-ink {
  position: absolute;
  bottom: -1px;
  left: 0;
  width: 50%;
  height: 2px;
  border-radius: 2px;
  background: linear-gradient(90deg, #22d3ee, #a78bfa);
  box-shadow: 0 0 12px rgba(34, 211, 238, 0.7);
  transition:
    left 0.5s cubic-bezier(0.34, 1.56, 0.64, 1),
    width 0.5s cubic-bezier(0.34, 1.56, 0.64, 1);
}
.tab-ink.right {
  left: 50%;
}
/* 输入框 + 流光 */
.field {
  margin-bottom: 16px;
}
.field label {
  display: block;
  font-size: 11.5px;
  color: #94a3b8;
  margin-bottom: 7px;
  letter-spacing: 0.5px;
}
.input-shell {
  position: relative;
  border-radius: 8px;
}
.input-shell :deep(.el-input__wrapper) {
  border-radius: 8px;
  box-shadow: none;
  border: 1px solid rgba(148, 163, 184, 0.22);
  background: rgba(255, 255, 255, 0.04);
  padding: 2px 12px;
  transition: border-color 0.25s, background 0.25s;
}
.input-shell :deep(.el-input__inner) {
  color: #e6ebf3;
}
.input-shell :deep(.el-input__inner::placeholder) {
  color: #5b6675;
}
.input-shell :deep(.el-input__wrapper.is-focus) {
  border-color: rgba(103, 232, 249, 0.55);
  background: rgba(255, 255, 255, 0.06);
}
.streak {
  position: absolute;
  inset: 0;
  border-radius: 8px;
  padding: 1px;
  background: linear-gradient(
    90deg,
    transparent 0%,
    #22d3ee 42%,
    #a78bfa 58%,
    transparent 100%
  );
  background-size: 200% 100%;
  -webkit-mask:
    linear-gradient(#000 0 0) content-box,
    linear-gradient(#000 0 0);
  -webkit-mask-composite: xor;
  mask-composite: exclude;
  opacity: 0;
  transition: opacity 0.2s;
  pointer-events: none;
}
.input-shell:focus-within .streak {
  opacity: 1;
  animation: streak-run 1.5s linear infinite;
}
@keyframes streak-run {
  0% {
    background-position: 200% 0;
  }
  100% {
    background-position: -200% 0;
  }
}
/* 渐变按钮 + 粒子爆发 */
.submit {
  position: relative;
  width: 100%;
  margin-top: 8px;
  padding: 13px 0;
  border: none;
  border-radius: 9px;
  background: linear-gradient(100deg, #22d3ee, #6366f1 55%, #a78bfa);
  background-size: 200% 100%;
  color: #06121c;
  font-size: 14px;
  font-weight: 700;
  letter-spacing: 3px;
  cursor: pointer;
  animation: btn-flow 6s linear infinite;
  transition: filter 0.2s;
  overflow: visible;
}
.submit:hover {
  filter: brightness(1.08);
}
.submit:disabled {
  opacity: 0.75;
  cursor: not-allowed;
}
@keyframes btn-flow {
  0% {
    background-position: 0% 50%;
  }
  100% {
    background-position: 200% 50%;
  }
}
.spark {
  position: absolute;
  left: 50%;
  top: 50%;
  width: 4px;
  height: 4px;
  border-radius: 50%;
  pointer-events: none;
  animation: spark-out 0.8s ease-out forwards;
  box-shadow: 0 0 8px currentColor;
}
@keyframes spark-out {
  0% {
    transform: translate(-50%, -50%) scale(1);
    opacity: 1;
  }
  100% {
    transform: translate(calc(-50% + var(--dx)), calc(-50% + var(--dy))) scale(0.2);
    opacity: 0;
  }
}
/* 演示账号气泡 */
.demo-bubble {
  position: relative;
  margin-top: 18px;
  text-align: center;
}
.bubble-trigger {
  background: none;
  border: none;
  color: #7c8798;
  font-size: 11.5px;
  letter-spacing: 0.5px;
  cursor: pointer;
  border-bottom: 1px dashed rgba(148, 163, 184, 0.35);
  padding-bottom: 2px;
  transition: color 0.2s;
}
.demo-bubble:hover .bubble-trigger {
  color: #a5e8fb;
}
.bubble {
  position: absolute;
  left: 50%;
  bottom: 30px;
  transform: translateX(-50%) translateY(10px) scale(0.85);
  opacity: 0;
  pointer-events: none;
  background: rgba(13, 20, 30, 0.94);
  border: 1px solid rgba(103, 232, 249, 0.3);
  border-radius: 10px;
  padding: 10px 14px;
  font-size: 11.5px;
  color: #cbd5e1;
  white-space: nowrap;
  box-shadow:
    0 24px 50px -24px rgba(0, 0, 0, 1),
    0 0 26px -10px rgba(34, 211, 238, 0.5);
  transition:
    opacity 0.35s ease,
    transform 0.45s cubic-bezier(0.34, 1.56, 0.64, 1);
}
.demo-bubble:hover .bubble {
  opacity: 1;
  pointer-events: auto;
  transform: translateX(-50%) translateY(0) scale(1);
}
.bubble-arrow {
  position: absolute;
  bottom: -5px;
  left: 50%;
  width: 8px;
  height: 8px;
  transform: translateX(-50%) rotate(45deg);
  background: rgba(13, 20, 30, 0.94);
  border-right: 1px solid rgba(103, 232, 249, 0.3);
  border-bottom: 1px solid rgba(103, 232, 249, 0.3);
}
.bubble-row {
  display: flex;
  gap: 10px;
  line-height: 2;
}
.bubble-row span {
  color: #64748b;
}
@media (prefers-reduced-motion: reduce) {
  .headline,
  .lead,
  .fcard::before,
  .demo-btn::before,
  .stat::before,
  .ico-shield,
  .pin-ring,
  .doc-sheet,
  .submit,
  .scan,
  .tab-ink,
  .spark {
    animation: none;
  }
}
@media (max-width: 1000px) {
  .auth-inner {
    grid-template-columns: 1fr;
    gap: 44px;
  }
  .brand {
    margin-bottom: 28px;
  }
  .headline {
    font-size: 40px;
  }
  .cards {
    grid-template-columns: 1fr;
  }
  .glass-card {
    max-width: none;
  }
}
</style>
