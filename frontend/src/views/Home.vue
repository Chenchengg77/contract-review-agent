<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { Search, ChatDotRound, Switch, Document, ArrowRight } from '@element-plus/icons-vue'
import { useUserStore } from '../stores/user'

const router = useRouter()
const store = useUserStore()
const evalSummary = ref<any>(null)

const greeting = computed(() => {
  const h = new Date().getHours()
  if (h < 6) return '夜深了'
  if (h < 12) return '早上好'
  if (h < 18) return '下午好'
  return '晚上好'
})

const stats = computed(() => {
  const e = evalSummary.value
  return [
    { label: '评估合同', value: e?.contracts ?? '31', suffix: '' },
    { label: '抽取准确率', value: e?.extraction ? (e.extraction.accuracy * 100).toFixed(1) : '95.5', suffix: '%' },
    { label: '核心条款', value: '13', suffix: ' 类' },
    { label: '金标条目', value: '403', suffix: ' 条' },
  ]
})

const entries = [
  { to: '/review', icon: Search, title: '合同审查', desc: '抽取 13 类条款、判定风险、生成修订建议' },
  { to: '/chat', icon: ChatDotRound, title: 'AI 对话', desc: '合同问答 / 法律问答，流式回答 + 引用' },
  { to: '/compare', icon: Switch, title: '合同对比', desc: '逐条比对两份合同的条款差异' },
  { to: '/templates', icon: Document, title: '合同模板', desc: '31 份示范文本，可预览、下载、上传' },
]

onMounted(async () => {
  try {
    const { data } = await import('../api').then((m) => m.default.get('/eval'))
    evalSummary.value = data.summary
  } catch {
    /* ignore */
  }
})
</script>

<template>
  <div class="page">
    <!-- Hero -->
    <section class="hero">
      <div class="hero-glow"></div>
      <div class="hero-content">
        <div class="hello">{{ greeting }}，{{ store.user?.username || '用户' }} 👋</div>
        <h1>合同审查工作台</h1>
        <p>上传合同，自动识别 13 类核心条款与风险点，生成可追溯的审查报告与修订建议。</p>
        <div class="hero-actions">
          <el-button type="primary" size="large" @click="router.push('/review')">开始审查</el-button>
          <el-button size="large" class="ghost-btn" @click="router.push('/chat')">AI 问答</el-button>
        </div>
      </div>
    </section>

    <!-- 指标 -->
    <section class="stats">
      <div v-for="s in stats" :key="s.label" class="stat">
        <div class="stat-value">{{ s.value }}<span class="suffix">{{ s.suffix }}</span></div>
        <div class="stat-label">{{ s.label }}</div>
      </div>
    </section>

    <!-- 快速入口 -->
    <section class="section">
      <div class="section-head">
        <h2>快速入口</h2>
      </div>
      <div class="entries">
        <button v-for="e in entries" :key="e.to" class="entry" @click="router.push(e.to)">
          <div class="entry-icon"><el-icon><component :is="e.icon" /></el-icon></div>
          <div class="entry-body">
            <div class="entry-title">{{ e.title }}</div>
            <div class="entry-desc">{{ e.desc }}</div>
          </div>
          <el-icon class="entry-arrow"><ArrowRight /></el-icon>
        </button>
      </div>
    </section>
  </div>
</template>

<style scoped>
.page {
  max-width: 1120px;
  margin: 0 auto;
  padding: 28px 32px 48px;
}

/* Hero */
.hero {
  position: relative;
  overflow: hidden;
  border-radius: 22px;
  padding: 40px;
  background: linear-gradient(130deg, #101c3a 0%, #1a2f66 55%, #243b8f 100%);
  color: #fff;
  margin-bottom: 22px;
  box-shadow: 0 30px 60px -30px rgba(16, 28, 58, 0.6);
}
.hero-glow {
  position: absolute;
  width: 460px;
  height: 460px;
  right: -140px;
  top: -180px;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(96, 165, 250, 0.55), transparent 65%);
  filter: blur(40px);
}
.hero-content {
  position: relative;
  z-index: 1;
  max-width: 620px;
}
.hello {
  font-size: 13px;
  color: #93c5fd;
  margin-bottom: 10px;
}
h1 {
  font-size: 30px;
  font-weight: 800;
  margin: 0 0 10px;
  letter-spacing: 0.5px;
}
.hero p {
  color: #cbd5e1;
  font-size: 14px;
  line-height: 1.8;
  margin: 0 0 24px;
}
.hero-actions {
  display: flex;
  gap: 12px;
}
.ghost-btn {
  background: rgba(255, 255, 255, 0.12);
  border: 1px solid rgba(255, 255, 255, 0.25);
  color: #fff;
}
.ghost-btn:hover {
  background: rgba(255, 255, 255, 0.2);
  border-color: rgba(255, 255, 255, 0.4);
  color: #fff;
}

/* 指标 */
.stats {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 14px;
  margin-bottom: 28px;
}
.stat {
  background: #fff;
  border: 1px solid #e8edf5;
  border-radius: 16px;
  padding: 20px;
  transition: all 0.2s;
}
.stat:hover {
  transform: translateY(-2px);
  box-shadow: 0 14px 30px -18px rgba(15, 23, 42, 0.25);
}
.stat-value {
  font-size: 26px;
  font-weight: 800;
  color: #0f172a;
}
.suffix {
  font-size: 13px;
  font-weight: 600;
  color: #64748b;
  margin-left: 2px;
}
.stat-label {
  font-size: 12px;
  color: #94a3b8;
  margin-top: 4px;
}

/* 入口 */
.section-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 14px;
}
h2 {
  font-size: 16px;
  margin: 0;
  color: #0f172a;
}
.entries {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px;
}
.entry {
  display: flex;
  align-items: center;
  gap: 16px;
  background: #fff;
  border: 1px solid #e8edf5;
  border-radius: 16px;
  padding: 20px;
  text-align: left;
  cursor: pointer;
  transition: all 0.2s;
  font-family: inherit;
}
.entry:hover {
  transform: translateY(-2px);
  border-color: #bfdbfe;
  box-shadow: 0 16px 32px -20px rgba(37, 99, 235, 0.4);
}
.entry-icon {
  width: 46px;
  height: 46px;
  border-radius: 14px;
  background: linear-gradient(135deg, #eff6ff, #e0e7ff);
  color: #2563eb;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  flex-shrink: 0;
}
.entry-body {
  flex: 1;
  min-width: 0;
}
.entry-title {
  font-size: 14px;
  font-weight: 600;
  color: #0f172a;
  margin-bottom: 3px;
}
.entry-desc {
  font-size: 12px;
  color: #94a3b8;
  line-height: 1.5;
}
.entry-arrow {
  color: #cbd5e1;
  transition: transform 0.2s, color 0.2s;
}
.entry:hover .entry-arrow {
  color: #2563eb;
  transform: translateX(3px);
}

@media (max-width: 860px) {
  .stats {
    grid-template-columns: 1fr 1fr;
  }
  .entries {
    grid-template-columns: 1fr;
  }
}
</style>
