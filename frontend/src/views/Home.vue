<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '../stores/user'
import api from '../api'
import SiteFooter from '../components/SiteFooter.vue'
import FallingLeaves from '../components/FallingLeaves.vue'

// —— 滚动入场动画 ——
let io: IntersectionObserver | null = null

/** 观察当前 DOM 里所有还没出现过的 .reveal（异步渲染出来的也要观察） */
function observeReveals() {
  if (!io) return
  document.querySelectorAll('.reveal:not(.in)').forEach((el) => io!.observe(el))
}

onMounted(async () => {
  io = new IntersectionObserver(
    (entries) => {
      entries.forEach((e) => {
        if (e.isIntersecting) {
          e.target.classList.add('in')
          io?.unobserve(e.target)
        }
      })
    },
    { threshold: 0.12, rootMargin: '0px 0px -60px 0px' }
  )
  observeReveals()

  try {
    const { data } = await api.get('/eval')
    summary.value = data.summary
    before.value = data.before
    cases.value = data.cases || []
    qaCases.value = data.qa_cases || []
  } catch {
    /* ignore */
  }
  // 数据回来后新渲染的区块，重新挂观察
  await nextTick()
  observeReveals()
})

onBeforeUnmount(() => io?.disconnect())

const router = useRouter()
const store = useUserStore()
const summary = ref<any>(null)
const before = ref<any>(null)
const cases = ref<any[]>([])
const qaCases = ref<any[]>([])

const greeting = computed(() => {
  const h = new Date().getHours()
  return h < 6 ? '夜深了' : h < 12 ? '早上好' : h < 18 ? '下午好' : '晚上好'
})

function pct(v: number | undefined | null, digits = 1) {
  return v == null ? '—' : (v * 100).toFixed(digits) + '%'
}

function delta(a: number | undefined | null, b: number | undefined | null) {
  if (a == null || b == null) return '—'
  const d = (b - a) * 100
  return (d >= 0 ? '+' : '') + d.toFixed(2) + '%'
}

const stats = computed(() => [
  { value: '13', label: '核心条款', en: 'Clauses' },
  { value: String(summary.value?.contracts ?? 31), label: '评估合同', en: 'Contracts' },
  { value: pct(summary.value?.extraction?.accuracy), label: '抽取准确率', en: 'Extraction' },
  { value: pct(summary.value?.judgment?.verdict_accuracy), label: '判定准确率', en: 'Judgment' },
])

const pains = [
  { n: '01', title: '人工审太慢', desc: '一份几十页的合同，逐条读完要 1~2 小时，还容易看漏。' },
  { n: '02', title: '条款缺了不知道', desc: '保密、责任上限、知识产权——缺了也不一定有人提醒你。' },
  { n: '03', title: '看出问题不会改', desc: '知道「这条有风险」，但不知道该改成什么样才合规。' },
]

const abilities = [
  { n: '01', title: '13 类条款识别', desc: '付款、违约金、交付、保密、知识产权等，逐条定位到原文。' },
  { n: '02', title: '判定可追溯', desc: '合规/偏离/缺失/冲突，每条引用条款号，可点开看原文。' },
  { n: '03', title: '质量可量化', desc: '自建 31 份合同 / 403 条金标评测，数字可复现。' },
  { n: '04', title: '可运维', desc: '健康检查、失败重试、运行时配置，出问题能定位能修。' },
]

const assistantAbilities = [
  { name: '前置拦截', how: '检索阈值 + 意图分类（Guardrails）', effect: '越界问题拒答；阈值命中零成本' },
  { name: '审查上下文', how: '注入最近一次审查摘要', effect: '能回答「哪条高风险」' },
  { name: '人设语气', how: 'system prompt 人设 + 语气规则', effect: '更像法务顾问，避免机器人腔' },
  { name: '主动追问', how: '审查完成后模板文案', effect: '引导用户继续提问' },
  { name: '记住用户', how: '/me/stats 最近记录', effect: '默认上次审查的合同' },
]

const advantages = [
  {
    n: '01',
    title: '只依据原文，找不到就拒答',
    desc: '检索不到相关条款时直接说「没找到」，不调用模型硬编——回答有边界。',
    proof: '机制 · BM25 检索 + 阈值 + 前置护栏',
  },
  {
    n: '02',
    title: '每条判定都指到条款号',
    desc: '不是一句结论，而是「结论 + 条款位置 + 原文」，点开即可核对。',
    proof: '机制 · 抽取记录 clause_no 与原文片段',
  },
  {
    n: '03',
    title: '准确率是测出来的',
    desc: '31 份合同、403 条人工金标：抽取 95.53%、判定 91.07%，数据可现场复现。',
    proof: '机制 · 自建评测集，/api/eval 可查',
  },
]

const steps = [
  { n: '01', title: '上传合同', desc: '.docx 拖进来，或选示例' },
  { n: '02', title: '抽取条款', desc: 'LLM 识别 13 类核心条款' },
  { n: '03', title: '判定风险', desc: '规则 + 语义，给出等级与理由' },
  { n: '04', title: '修订建议', desc: '给出改写后的条款文本，可复制' },
]
</script>

<template>
  <div class="landing">
    <FallingLeaves :count="14" :opacity="0.26" fixed />
    <!-- Hero -->
    <section class="hero">
      <div class="hero-inner">
        <div class="hero-left">
          <div class="eyebrow">CONTRACT REVIEW · {{ greeting }}</div>
          <h1 class="title">
            合同风险<br />
            <em>一眼看清</em>
          </h1>
          <p class="lead">
            上传合同，自动识别 13 类核心条款、判定风险等级、给出可用的修订建议。
            不必逐条读完，也不必担心看漏。
          </p>
          <div class="cta">
            <el-button type="primary" size="large" class="solid" @click="router.push('/review')">
              开始审查合同
            </el-button>
            <button class="ghost" @click="router.push('/chat')">问问 AI 助手 →</button>
          </div>
          <div class="meta-line">
            <span>只依据合同原文</span>
            <i>·</i>
            <span>引用条款可核对</span>
            <i>·</i>
            <span>质量可评测</span>
          </div>
        </div>

        <div class="hero-right">
          <div class="suite">
            <div class="suite-top">
              <span class="suite-label">本 次 审 查</span>
              <span class="suite-tag">示例</span>
            </div>
            <div class="suite-rows">
              <div class="srow">
                <span class="k">核心条款</span>
                <span class="v">13 <em>类</em></span>
              </div>
              <div class="srow">
                <span class="k">高风险</span>
                <span class="v accent">3</span>
              </div>
              <div class="srow">
                <span class="k">中风险</span>
                <span class="v">10</span>
              </div>
              <div class="srow">
                <span class="k">平均耗时</span>
                <span class="v">16.6 <em>秒</em></span>
              </div>
            </div>
            <div class="suite-foot">
              <span>付款条款 · 违约金 · 保密条款</span>
              <span class="suite-link" @click="router.push('/review')">查看 →</span>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- 数据条 -->
    <section class="strip">
      <div class="strip-inner">
        <div v-for="(s, i) in stats" :key="s.label" class="strip-cell" :class="{ first: i === 0 }">
          <div class="strip-en">{{ s.en }}</div>
          <div class="strip-num">{{ s.value }}</div>
          <div class="strip-label">{{ s.label }}</div>
        </div>
      </div>
    </section>

    <!-- 痛点 -->
    <section class="section">
      <div class="section-inner">
        <div class="sec-head reveal">
          <div class="sec-eyebrow">WHY</div>
          <h2>审合同，不该靠「逐字读完」</h2>
        </div>
        <div class="grid3">
          <div
            v-for="(p, i) in pains"
            :key="p.n"
            class="item reveal"
            :style="{ transitionDelay: i * 90 + 'ms' }"
          >
            <div class="item-n">{{ p.n }}</div>
            <div class="item-title">{{ p.title }}</div>
            <div class="item-desc">{{ p.desc }}</div>
          </div>
        </div>
      </div>
    </section>

    <!-- 能力 -->
    <section class="section tint">
      <div class="section-inner">
        <div class="sec-head reveal">
          <div class="sec-eyebrow">CAPABILITY</div>
          <h2>不是「问一句答一句」，是完整链路</h2>
        </div>
        <div class="grid4">
          <div
            v-for="(a, i) in abilities"
            :key="a.n"
            class="item reveal"
            :style="{ transitionDelay: i * 90 + 'ms' }"
          >
            <div class="item-n">{{ a.n }}</div>
            <div class="item-title">{{ a.title }}</div>
            <div class="item-desc">{{ a.desc }}</div>
          </div>
        </div>
      </div>
    </section>

    <!-- 产品优势：第一梯队 -->
    <section class="section">
      <div class="section-inner">
        <div class="sec-head reveal">
          <div class="sec-eyebrow">WHY US</div>
          <h2>和直接用 AI 聊天，差在哪</h2>
        </div>
        <div class="adv-grid">
          <div
            v-for="(a, i) in advantages"
            :key="a.n"
            class="adv reveal"
            :style="{ transitionDelay: i * 90 + 'ms' }"
          >
            <div class="adv-n">{{ a.n }}</div>
            <div class="adv-title">{{ a.title }}</div>
            <div class="adv-desc">{{ a.desc }}</div>
            <div class="adv-proof">{{ a.proof }}</div>
          </div>
        </div>
      </div>
    </section>

    <!-- 对比 1：前置拦截 -->
    <section v-if="qaCases.length" class="section">
      <div class="section-inner">
        <div class="sec-head reveal">
          <div class="sec-eyebrow">GUARDRAILS</div>
          <h2>越界的问题，不该让模型硬答</h2>
        </div>
        <div class="cmp-list">
          <div v-for="c in qaCases" :key="c.question" class="cmp reveal">
            <div class="cmp-q">问：{{ c.question }}</div>
            <div class="cmp-cols">
              <div class="cmp-col before">
                <div class="cmp-tag">改前 · 照常调 LLM</div>
                <div class="cmp-text">{{ c.before.answer }}</div>
                <div class="cmp-meta">{{ c.before.cost }}<br />{{ c.before.why }}</div>
              </div>
              <div class="cmp-col after">
                <div class="cmp-tag">改后 · 前置拦截</div>
                <div class="cmp-text">{{ c.after.answer }}</div>
                <div class="cmp-meta">{{ c.after.cost }}<br />{{ c.after.why }}</div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- AI 助手能力 -->
    <section class="section">
      <div class="section-inner">
        <div class="sec-head reveal">
          <div class="sec-eyebrow">ASSISTANT</div>
          <h2>五件事，让它像个法务助手</h2>
        </div>
        <div class="abtable reveal">
          <div class="abrow abhead">
            <span>能力</span><span>实现方式</span><span>效果</span>
          </div>
          <div v-for="a in assistantAbilities" :key="a.name" class="abrow">
            <span class="ab-name">{{ a.name }}</span>
            <span class="ab-how">{{ a.how }}</span>
            <span class="ab-effect">{{ a.effect }}</span>
          </div>
        </div>
      </div>
    </section>

    <!-- 对比 2：版本对比 -->
    <section v-if="before && summary" class="section tint">
      <div class="section-inner">
        <div class="sec-head reveal">
          <div class="sec-eyebrow">EVALUATION</div>
          <h2>准确率是修出来的，不是写出来的</h2>
        </div>

        <div class="vtable reveal">
          <div class="vrow vhead">
            <span>指标</span><span>修复前</span><span>修复后</span><span>变化</span>
          </div>
          <div class="vrow">
            <span>判定准确率</span>
            <span class="old">{{ pct(before.judgment?.verdict_accuracy, 2) }}</span>
            <span class="new">{{ pct(summary.judgment?.verdict_accuracy, 2) }}</span>
            <span class="delta">{{ delta(before.judgment?.verdict_accuracy, summary.judgment?.verdict_accuracy) }}</span>
          </div>
          <div class="vrow">
            <span>严重度准确率</span>
            <span class="old">{{ pct(before.judgment?.severity_accuracy, 2) }}</span>
            <span class="new">{{ pct(summary.judgment?.severity_accuracy, 2) }}</span>
            <span class="delta">{{ delta(before.judgment?.severity_accuracy, summary.judgment?.severity_accuracy) }}</span>
          </div>
        </div>

        <div v-for="c in cases" :key="c.clause" class="vcase reveal">
          <div class="vcase-head">{{ c.contract }} · {{ c.clause }}</div>
          <div class="cmp-cols">
            <div class="cmp-col before">
              <div class="cmp-tag">修复前 · {{ c.before.verdict }}（{{ c.before.severity }}）</div>
              <div class="cmp-text">{{ c.before.reason }}</div>
            </div>
            <div class="cmp-col after">
              <div class="cmp-tag">修复后 · {{ c.after.verdict }}（{{ c.after.severity }}）</div>
              <div class="cmp-text">{{ c.after.reason }}</div>
            </div>
          </div>
          <div class="vcause">原因：{{ c.root_cause }}</div>
        </div>
      </div>
    </section>

    <!-- 流程 -->
    <section class="section">
      <div class="section-inner">
        <div class="sec-head reveal">
          <div class="sec-eyebrow">WORKFLOW</div>
          <h2>四步，从合同到修订建议</h2>
        </div>
        <div class="steps">
          <div
            v-for="(s, i) in steps"
            :key="s.n"
            class="step reveal"
            :style="{ transitionDelay: i * 90 + 'ms' }"
          >
            <div class="step-n">{{ s.n }}</div>
            <div class="step-title">{{ s.title }}</div>
            <div class="step-desc">{{ s.desc }}</div>
          </div>
        </div>
      </div>
    </section>

    <!-- 结尾 CTA -->
    <section class="closing">
      <div class="closing-inner reveal">
        <div class="sec-eyebrow light">GET STARTED</div>
        <h2 class="closing-title">把下一份合同，交给它先看一遍</h2>
        <div class="closing-cta">
          <el-button type="primary" size="large" class="solid" @click="router.push('/review')">
            开始审查
          </el-button>
          <button class="ghost light" @click="router.push('/eval')">看评测数据 →</button>
        </div>
      </div>
    </section>

    <SiteFooter />
  </div>
</template>

<style scoped>
.landing {
  --paper: #faf8f4;
  --ink: #14161a;
  --muted: #6b6f76;
  --line: #e6e2da;
  --accent: #1f3fb3;
  position: relative;
  background: var(--paper);
  color: var(--ink);
}
/* 滚动入场 */
.reveal {
  opacity: 0;
  transform: translateY(28px);
  transition:
    opacity 0.8s cubic-bezier(0.2, 0.6, 0.2, 1),
    transform 0.8s cubic-bezier(0.2, 0.6, 0.2, 1);
  will-change: opacity, transform;
}
.reveal.in {
  opacity: 1;
  transform: none;
}
@media (prefers-reduced-motion: reduce) {
  .reveal {
    opacity: 1;
    transform: none;
    transition: none;
  }
}
/* ============ Hero ============ */
.hero {
  position: relative;
  overflow: hidden;
  background:
    radial-gradient(900px 500px at 85% 0%, rgba(31, 63, 179, 0.06), transparent 65%),
    linear-gradient(180deg, #fbfaf7 0%, var(--paper) 100%);
  border-bottom: 1px solid var(--line);
}
.hero-inner {
  position: relative;
  z-index: 1;
  max-width: 1120px;
  margin: 0 auto;
  padding: 96px 28px 104px;
  display: grid;
  grid-template-columns: 1.2fr 0.8fr;
  gap: 72px;
  align-items: center;
}
.eyebrow {
  font-size: 11px;
  letter-spacing: 3px;
  color: var(--muted);
  margin-bottom: 26px;
}
.title {
  font-family: 'Noto Serif SC', 'Songti SC', 'SimSun', Georgia, serif;
  font-size: 62px;
  line-height: 1.32;
  font-weight: 600;
  letter-spacing: 2px;
  margin: 0 0 26px;
  color: var(--ink);
}
.title em {
  font-style: normal;
  position: relative;
}
.title em::after {
  content: '';
  position: absolute;
  left: 0;
  right: 0;
  bottom: 6px;
  height: 10px;
  background: rgba(31, 63, 179, 0.1);
  z-index: -1;
}
.lead {
  font-size: 14.5px;
  line-height: 2;
  color: var(--muted);
  margin: 0 0 36px;
  max-width: 460px;
  letter-spacing: 0.3px;
}
.cta {
  display: flex;
  align-items: center;
  gap: 22px;
  margin-bottom: 30px;
}
.solid {
  border-radius: 2px !important;
  letter-spacing: 1px;
}
.ghost {
  background: none;
  border: none;
  padding: 0;
  font-size: 13px;
  color: var(--ink);
  letter-spacing: 0.5px;
  cursor: pointer;
  border-bottom: 1px solid var(--ink);
  padding-bottom: 2px;
}
.ghost:hover {
  color: var(--accent);
  border-color: var(--accent);
}
.meta-line {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 12px;
  color: #9a9ea5;
  letter-spacing: 0.4px;
}
.meta-line i {
  font-style: normal;
  color: #cfcac1;
}
/* Hero 右侧卡片 */
.suite {
  background: #fff;
  border: 1px solid var(--line);
  border-radius: 2px;
  padding: 30px 28px 22px;
  box-shadow: 0 40px 80px -60px rgba(20, 22, 26, 0.5);
}
.suite-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-bottom: 18px;
  border-bottom: 1px solid var(--line);
  margin-bottom: 6px;
}
.suite-label {
  font-size: 10px;
  letter-spacing: 4px;
  color: var(--muted);
}
.suite-tag {
  font-size: 10px;
  color: #b4442f;
  border: 1px solid #e8cfc8;
  background: #fdf6f4;
  padding: 2px 8px;
  letter-spacing: 2px;
}
.srow {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  padding: 15px 0;
  border-bottom: 1px solid #f2efe9;
}
.srow .k {
  font-size: 12.5px;
  color: var(--muted);
  letter-spacing: 0.5px;
}
.srow .v {
  font-family: 'Noto Serif SC', 'Songti SC', Georgia, serif;
  font-size: 24px;
  font-weight: 600;
  color: var(--ink);
}
.srow .v em {
  font-style: normal;
  font-size: 11px;
  color: #9a9ea5;
  margin-left: 2px;
  font-family: system-ui, sans-serif;
}
.srow .v.accent {
  color: #b4442f;
}
.suite-foot {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-top: 16px;
  font-size: 11.5px;
  color: #9a9ea5;
  letter-spacing: 0.3px;
}
.suite-link {
  color: var(--accent);
  cursor: pointer;
  letter-spacing: 1px;
}
/* ============ 数据条 ============ */
.strip {
  background: #fff;
  border-bottom: 1px solid var(--line);
}
.strip-inner {
  max-width: 1120px;
  margin: 0 auto;
  display: grid;
  grid-template-columns: repeat(4, 1fr);
}
.strip-cell {
  padding: 34px 26px;
  border-left: 1px solid var(--line);
}
.strip-cell.first {
  border-left: none;
  padding-left: 28px;
}
.strip-en {
  font-size: 10px;
  font-style: italic;
  letter-spacing: 2px;
  color: #b3b0a8;
  margin-bottom: 10px;
}
.strip-num {
  font-family: 'Noto Serif SC', 'Songti SC', Georgia, serif;
  font-size: 34px;
  font-weight: 600;
  color: var(--ink);
  line-height: 1;
}
.strip-label {
  font-size: 11.5px;
  color: var(--muted);
  margin-top: 10px;
  letter-spacing: 0.5px;
}
/* ============ 区块 ============ */
.section {
  padding: 104px 0;
}
.section.tint {
  background: #fff;
  border-top: 1px solid var(--line);
  border-bottom: 1px solid var(--line);
}
.section-inner {
  max-width: 1120px;
  margin: 0 auto;
  padding: 0 28px;
}
.sec-head {
  margin-bottom: 56px;
}
.sec-eyebrow {
  font-size: 10px;
  letter-spacing: 4px;
  color: #b3b0a8;
  margin-bottom: 14px;
}
.sec-head h2 {
  font-family: 'Noto Serif SC', 'Songti SC', Georgia, serif;
  font-size: 32px;
  font-weight: 600;
  letter-spacing: 1.5px;
  color: var(--ink);
  margin: 0;
}
.grid3 {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 56px;
  border-top: 1px solid var(--line);
  padding-top: 44px;
}
.grid4 {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 44px;
  border-top: 1px solid var(--line);
  padding-top: 44px;
}
.item {
  padding: 0;
}
.item-n {
  font-size: 10px;
  letter-spacing: 2px;
  color: #c3bfb6;
  margin-bottom: 20px;
}
.item-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--ink);
  margin-bottom: 12px;
  letter-spacing: 0.5px;
}
.item-desc {
  font-size: 13px;
  line-height: 2;
  color: var(--muted);
}
/* 产品优势 */
.adv-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 44px;
  border-top: 1px solid var(--line);
  padding-top: 44px;
}
.adv {
  padding: 0;
}
.adv-n {
  font-size: 10px;
  letter-spacing: 2px;
  color: #c3bfb6;
  margin-bottom: 16px;
}
.adv-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--ink);
  margin-bottom: 12px;
  letter-spacing: 0.5px;
}
.adv-desc {
  font-size: 13px;
  line-height: 2;
  color: var(--muted);
  margin-bottom: 14px;
}
.adv-proof {
  display: inline-block;
  font-size: 11px;
  color: #0f766e;
  background: #f4faf8;
  border: 1px solid #d9ece5;
  border-radius: 2px;
  padding: 4px 9px;
  letter-spacing: 0.3px;
}
/* 助手能力表 */
.abtable {
  border-top: 1px solid var(--line);
}
.abrow {
  display: grid;
  grid-template-columns: 1fr 1.6fr 1.7fr;
  gap: 24px;
  padding: 16px 0;
  border-bottom: 1px solid var(--line);
  font-size: 12.5px;
}
.abhead {
  font-size: 11px;
  letter-spacing: 1.5px;
  color: #a39d92;
}
.ab-name {
  color: var(--ink);
  font-weight: 600;
  letter-spacing: 0.5px;
}
.ab-how {
  color: #6b6f76;
}
.ab-effect {
  color: #0f766e;
}
/* 对比块 */
.cmp-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.cmp {
  border: 1px solid var(--line);
  border-radius: 2px;
  background: #fff;
  padding: 22px 24px;
}
.cmp-q {
  font-size: 13px;
  color: #6b6f76;
  margin-bottom: 14px;
  letter-spacing: 0.3px;
}
.cmp-cols {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}
.cmp-col {
  border: 1px solid var(--line);
  border-radius: 2px;
  padding: 14px 16px;
}
.cmp-col.before {
  background: #fcfbf9;
}
.cmp-col.after {
  background: #f6fbf8;
  border-color: #cfe8da;
}
.cmp-tag {
  font-size: 11px;
  letter-spacing: 0.5px;
  color: #8a867d;
  margin-bottom: 8px;
}
.cmp-col.after .cmp-tag {
  color: #0f766e;
}
.cmp-text {
  font-size: 12.5px;
  line-height: 1.9;
  color: #475569;
}
.cmp-meta {
  font-size: 10.5px;
  color: #a39d92;
  margin-top: 10px;
  line-height: 1.8;
}
/* 版本对比表 */
.vtable {
  border: 1px solid var(--line);
  border-radius: 2px;
  overflow: hidden;
  margin-bottom: 20px;
  background: #fff;
}
.vrow {
  display: grid;
  grid-template-columns: 1.4fr 1fr 1fr 1fr;
  padding: 13px 18px;
  border-top: 1px solid var(--line);
  font-size: 12.5px;
  color: #475569;
}
.vrow:first-child {
  border-top: none;
  background: #faf8f4;
}
.vrow.vhead {
  font-size: 11px;
  letter-spacing: 1px;
  color: #8a867d;
}
.vrow .old {
  color: #a39d92;
}
.vrow .new {
  color: #14161a;
  font-weight: 700;
}
.vrow .delta {
  color: #0f766e;
  font-weight: 600;
}
.vcase {
  border: 1px solid var(--line);
  border-radius: 2px;
  background: #fff;
  padding: 22px 24px;
}
.vcase-head {
  font-size: 13px;
  font-weight: 600;
  color: #14161a;
  margin-bottom: 14px;
}
.vcause {
  font-size: 11.5px;
  color: #a39d92;
  margin-top: 14px;
  line-height: 1.8;
}
/* 流程 */
.steps {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 44px;
  border-top: 1px solid var(--line);
  padding-top: 44px;
}
.step {
  padding: 0;
}
.step-n {
  font-family: 'Noto Serif SC', 'Songti SC', Georgia, serif;
  font-size: 30px;
  color: #d8d3c9;
  margin-bottom: 16px;
}
.step-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--ink);
  margin-bottom: 8px;
}
.step-desc {
  font-size: 12.5px;
  color: var(--muted);
  line-height: 1.9;
}
/* ============ 结尾 ============ */
.closing {
  background: #14161a;
  padding: 110px 0;
}
.closing-inner {
  max-width: 1120px;
  margin: 0 auto;
  padding: 0 28px;
}
.sec-eyebrow.light {
  color: #6f7278;
}
.closing-title {
  font-family: 'Noto Serif SC', 'Songti SC', Georgia, serif;
  font-size: 40px;
  font-weight: 600;
  letter-spacing: 2px;
  color: #f5f3ef;
  margin: 18px 0 40px;
}
.closing-cta {
  display: flex;
  align-items: center;
  gap: 24px;
}
.ghost.light {
  color: #d8d5cf;
  border-color: #d8d5cf;
}
.ghost.light:hover {
  color: #fff;
  border-color: #fff;
}
@media (max-width: 1000px) {
  .hero-inner {
    grid-template-columns: 1fr;
    gap: 48px;
    padding: 64px 22px 72px;
  }
  .title {
    font-size: 42px;
  }
  .grid3,
  .grid4,
  .steps,
  .strip-inner {
    grid-template-columns: repeat(2, 1fr);
  }
  .grid3,
  .grid4,
  .steps {
    gap: 36px;
  }
  .closing-title {
    font-size: 30px;
  }
}
</style>
