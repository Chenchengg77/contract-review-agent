<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { Upload } from '@element-plus/icons-vue'
import { useCompareStore } from '../stores/compare'

const store = useCompareStore()

const stageTexts = ['正在解析文档', '抽取合同条款', '对齐条款', '识别差异', '生成对比报告']

onMounted(() => store.loadContracts())

watch(
  () => store.error,
  (v) => {
    if (v) {
      ElMessage.warning(v)
      store.error = ''
    }
  }
)

// 上传
const fileInputA = ref<HTMLInputElement | null>(null)
const fileInputB = ref<HTMLInputElement | null>(null)

function pick(side: 'a' | 'b') {
  if (side === 'a') fileInputA.value?.click()
  else fileInputB.value?.click()
}
function onPick(e: Event, side: 'a' | 'b') {
  const f = (e.target as HTMLInputElement).files?.[0] || null
  if (!f) return
  if (!f.name.toLowerCase().endsWith('.docx')) {
    ElMessage.warning('只支持 .docx 合同')
    return
  }
  if (side === 'a') store.aFile = f
  else store.bFile = f
}
function clearFile(side: 'a' | 'b') {
  if (side === 'a') {
    store.aFile = null
    if (fileInputA.value) fileInputA.value.value = ''
  } else {
    store.bFile = null
    if (fileInputB.value) fileInputB.value.value = ''
  }
}

// 品类一致性提示
const category = (name: string) => (name || '').split('_')[0]

function run() {
  if (!store.aFile && !store.bFile && store.a && store.b && category(store.a) !== category(store.b)) {
    ElMessage.warning(
      `两份合同品类不一致（${category(store.a)} vs ${category(store.b)}），语义比对效果有限，结果仅供参考`
    )
  }
  store.run()
}

// 结果
const tab = ref<'diff' | 'stat' | 'risk'>('diff')
const onlyDiff = ref(true)

const diffs = computed<any[]>(() => store.result?.diffs || [])
const shownDiffs = computed(() => (onlyDiff.value ? diffs.value.filter((d) => d.change !== '相同') : diffs.value))

const summary = computed(() => store.result?.summary || { 修改: 0, 新增: 0, 删除: 0, 相同: 0 })
const totalClauses = computed(
  () => (summary.value['修改'] || 0) + (summary.value['新增'] || 0) + (summary.value['删除'] || 0) + (summary.value['相同'] || 0)
)
const highDiffs = computed(() => diffs.value.filter((d) => d.severity === '高' && d.change !== '相同').length)

const riskList = computed(() => {
  const order: Record<string, number> = { 高: 0, 中: 1, 低: 2 }
  return diffs.value
    .filter((d) => d.change !== '相同')
    .slice()
    .sort((x, y) => (order[x.severity] ?? 3) - (order[y.severity] ?? 3))
})

const CHANGE_COLOR: Record<string, string> = {
  新增: '#10b981',
  删除: '#ef4444',
  修改: '#f59e0b',
  相同: '#cbd5e1',
}

const donut = computed(() => {
  const s = summary.value
  const total = Math.max(1, totalClauses.value)
  const seg = [
    { k: '新增', v: s['新增'] || 0, c: '#10b981' },
    { k: '修改', v: s['修改'] || 0, c: '#f59e0b' },
    { k: '删除', v: s['删除'] || 0, c: '#ef4444' },
    { k: '相同', v: s['相同'] || 0, c: '#e2e8f0' },
  ]
  let acc = 0
  const parts = seg.map((x) => {
    const start = (acc / total) * 100
    acc += x.v
    const end = (acc / total) * 100
    return `${x.c} ${start.toFixed(1)}% ${end.toFixed(1)}%`
  })
  return `conic-gradient(${parts.join(',')})`
})

function sevClass(s: string) {
  if (s === '高') return 'sev-high'
  if (s === '中') return 'sev-mid'
  if (s === '低') return 'sev-low'
  return 'sev-none'
}

// 导出 / 复制
function buildReport() {
  const r = store.result
  if (!r) return ''
  const lines: string[] = []
  lines.push(`# 合同对比报告`)
  lines.push('')
  lines.push(`- A（原版）：${r.a}`)
  lines.push(`- B（新版）：${r.b}`)
  lines.push(`- 生成时间：${new Date().toLocaleString('zh-CN')}`)
  lines.push('')
  lines.push(`## 差异统计`)
  lines.push('')
  lines.push(`| 合计 | 新增 | 删除 | 修改 | 相同 |`)
  lines.push(`|---|---|---|---|---|`)
  lines.push(
    `| ${totalClauses.value} | ${summary.value['新增'] || 0} | ${summary.value['删除'] || 0} | ${summary.value['修改'] || 0} | ${summary.value['相同'] || 0} |`
  )
  lines.push('')
  lines.push(`## 差异明细`)
  lines.push('')
  for (const d of diffs.value) {
    if (d.change === '相同') continue
    lines.push(`### ${d.clause}（${d.change}${d.severity ? ' · ' + d.severity + '风险' : ''}）`)
    if (d.note) lines.push(`> ${d.note}`)
    lines.push('')
    lines.push(`- A：${(d.a_text || '').slice(0, 300)}`)
    lines.push(`- B：${(d.b_text || '').slice(0, 300)}`)
    lines.push('')
  }
  return lines.join('\n')
}

function exportReport() {
  const text = buildReport()
  if (!text) {
    ElMessage.warning('还没有可导出的对比结果')
    return
  }
  const blob = new Blob([`\ufeff${text}`], { type: 'text/markdown;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `合同对比报告_${new Date().toISOString().slice(0, 10)}.md`
  a.click()
  URL.revokeObjectURL(url)
  ElMessage.success('已导出对比报告（Markdown）')
}

async function copySummary() {
  if (!store.result) {
    ElMessage.warning('还没有可复制的对比结果')
    return
  }
  const s = summary.value
  const lines = [
    `合同对比：${store.result.a} → ${store.result.b}`,
    `共 ${totalClauses.value} 类条款：新增 ${s['新增'] || 0}、删除 ${s['删除'] || 0}、修改 ${s['修改'] || 0}、相同 ${s['相同'] || 0}`,
    '',
    ...riskList.value.map((d) => `· ${d.clause}（${d.change}${d.severity ? ' / ' + d.severity + '风险' : ''}）${d.note || ''}`),
  ]
  try {
    await navigator.clipboard.writeText(lines.join('\n'))
    ElMessage.success('已复制差异摘要')
  } catch {
    ElMessage.error('复制失败，请手动选中复制')
  }
}

const stageText = computed(() => stageTexts[Math.min(store.stage, stageTexts.length - 1)])
</script>

<template>
  <div class="page">
    <div class="page-head">
      <div class="page-icon">
        <svg viewBox="0 0 24 24" fill="none" stroke="#14161a" stroke-width="1.3">
          <path d="M3 20h18" stroke-linecap="round" />
          <path d="M7.5 20V9.5M7.5 9.5 4 11V6.5L7.5 4 11 6.5V11z" stroke-linejoin="round" />
          <path d="M16.5 20V9.5M16.5 9.5 13 11V6.5L16.5 4 20 6.5V11z" stroke-linejoin="round" />
        </svg>
      </div>
      <div>
        <h1 class="page-title">合同对比</h1>
        <p class="page-sub">选择两份合同，AI 逐条比对 13 类条款差异，识别新增、修改、删除内容。</p>
      </div>
    </div>

    <!-- 选择区 -->
    <div class="pick-wrap">
      <div class="pick-card">
        <div class="pick-title">A 合同（原版）</div>
        <el-select v-model="store.a" placeholder="选择 A 合同" filterable class="pick-select" :disabled="!!store.aFile">
          <el-option v-for="c in store.contracts" :key="c" :label="c" :value="c" />
        </el-select>
        <div class="pick-note">
          <template v-if="store.aFile">
            已选本地文件：<b>{{ store.aFile.name }}</b>
            <button class="link" @click="clearFile('a')">移除</button>
          </template>
          <template v-else>可选择模板库合同，也支持上传本地文件</template>
        </div>
        <div class="pick-foot">
          <el-button size="small" :icon="Upload" @click="pick('a')">上传文件</el-button>
          <input ref="fileInputA" type="file" accept=".docx" class="hidden" @change="onPick($event, 'a')" />
        </div>
      </div>

      <div class="arrow" :class="{ breathing: store.loading }">
        <svg viewBox="0 0 48 24" fill="none" stroke="currentColor" stroke-width="1.5">
          <path d="M4 12h38" stroke-linecap="round" />
          <path d="M36 6l6 6-6 6M12 6 6 12l6 6" stroke-linecap="round" stroke-linejoin="round" />
        </svg>
      </div>

      <div class="pick-card">
        <div class="pick-title">B 合同（新版）</div>
        <el-select v-model="store.b" placeholder="选择 B 合同" filterable class="pick-select" :disabled="!!store.bFile">
          <el-option v-for="c in store.contracts" :key="c" :label="c" :value="c" />
        </el-select>
        <div class="pick-note">
          <template v-if="store.bFile">
            已选本地文件：<b>{{ store.bFile.name }}</b>
            <button class="link" @click="clearFile('b')">移除</button>
          </template>
          <template v-else>可选择模板库合同，也支持上传本地文件</template>
        </div>
        <div class="pick-foot">
          <el-button size="small" :icon="Upload" @click="pick('b')">上传文件</el-button>
          <input ref="fileInputB" type="file" accept=".docx" class="hidden" @change="onPick($event, 'b')" />
        </div>
      </div>
    </div>

    <!-- 开始对比 -->
    <div class="run-wrap">
      <el-button type="primary" size="large" :loading="store.loading" class="run-btn" @click="run">
        开始对比
      </el-button>
      <div v-if="store.loading" class="status">
        <transition name="fade" mode="out-in">
          <span :key="stageText" class="status-text">{{ stageText }}</span>
        </transition>
        <div class="thin-bar"><i :style="{ width: store.progress + '%' }"></i></div>
      </div>
    </div>

    <!-- 结果 -->
    <div v-if="store.result" class="result-card">
      <div class="tabs">
        <button class="tab" :class="{ active: tab === 'diff' }" @click="tab = 'diff'">对照 Diff 视图</button>
        <button class="tab" :class="{ active: tab === 'stat' }" @click="tab = 'stat'">差异统计看板</button>
        <button class="tab" :class="{ active: tab === 'risk' }" @click="tab = 'risk'">风险摘要列表</button>
      </div>

      <!-- Tab1 -->
      <div v-show="tab === 'diff'" class="tab-body">
        <div class="diff-head">
          <span class="diff-a">{{ store.result.a }}</span>
          <span class="diff-arrow">→</span>
          <span class="diff-b">{{ store.result.b }}</span>
          <div class="spacer"></div>
          <label class="switch"><input v-model="onlyDiff" type="checkbox" /> 只看差异</label>
        </div>

        <div class="legend">
          <span><i style="background: #10b981"></i>新增</span>
          <span><i style="background: #ef4444"></i>删除</span>
          <span><i style="background: #f59e0b"></i>修改</span>
          <span><i style="background: #cbd5e1"></i>相同</span>
        </div>

        <div v-if="!shownDiffs.length" class="empty-line">两份合同的 13 类条款完全一致</div>

        <div v-for="d in shownDiffs" :key="d.clause" class="diff-row" :class="'chg-' + d.change">
          <div class="diff-clause">
            {{ d.clause }}
            <span class="chg-badge" :style="{ color: CHANGE_COLOR[d.change], borderColor: CHANGE_COLOR[d.change] + '66' }">
              {{ d.change }}
            </span>
          </div>
          <div class="diff-cols">
            <div class="diff-col a">
              <div class="col-label">A</div>
              <div class="col-text">{{ d.a_text }}</div>
            </div>
            <div class="diff-col b">
              <div class="col-label">B</div>
              <div class="col-text">{{ d.b_text }}</div>
            </div>
          </div>
        </div>
      </div>

      <!-- Tab2 -->
      <div v-show="tab === 'stat'" class="tab-body">
        <div class="stat-wrap">
          <div class="stat-cards">
            <div class="stat-card">
              <div class="stat-num">{{ totalClauses }}</div>
              <div class="stat-label">总条款</div>
            </div>
            <div class="stat-card">
              <div class="stat-num" style="color: #10b981">{{ summary['新增'] || 0 }}</div>
              <div class="stat-label">新增</div>
            </div>
            <div class="stat-card">
              <div class="stat-num" style="color: #ef4444">{{ summary['删除'] || 0 }}</div>
              <div class="stat-label">删除</div>
            </div>
            <div class="stat-card">
              <div class="stat-num" style="color: #f59e0b">{{ summary['修改'] || 0 }}</div>
              <div class="stat-label">修改</div>
            </div>
            <div class="stat-card">
              <div class="stat-num" style="color: #b91c1c">{{ highDiffs }}</div>
              <div class="stat-label">高风险差异</div>
            </div>
          </div>

          <div class="donut-wrap">
            <div class="donut" :style="{ background: donut }">
              <div class="donut-hole">
                <b>{{ totalClauses }}</b>
                <span>条款</span>
              </div>
            </div>
            <div class="donut-legend">
              <span><i style="background: #10b981"></i>新增 {{ summary['新增'] || 0 }}</span>
              <span><i style="background: #f59e0b"></i>修改 {{ summary['修改'] || 0 }}</span>
              <span><i style="background: #ef4444"></i>删除 {{ summary['删除'] || 0 }}</span>
              <span><i style="background: #e2e8f0"></i>相同 {{ summary['相同'] || 0 }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Tab3 -->
      <div v-show="tab === 'risk'" class="tab-body">
        <div v-if="!riskList.length" class="empty-line">没有需要关注的差异</div>
        <div v-for="d in riskList" :key="d.clause" class="risk-item" :class="sevClass(d.severity)">
          <div class="risk-head">
            <span class="sev">{{ d.severity || '—' }}</span>
            <span class="risk-clause">{{ d.clause }}</span>
            <span class="risk-change">{{ d.change }}</span>
            <span v-if="d.severity_from === 'rule'" class="risk-from">规则推断</span>
          </div>
          <p class="risk-note">{{ d.note || '条款有变化，建议人工复核。' }}</p>
        </div>
      </div>

      <div class="panel-actions">
        <el-button size="small" @click="copySummary">复制差异摘要</el-button>
        <el-button size="small" @click="exportReport">导出对比报告</el-button>
      </div>
    </div>

    <!-- 空状态 -->
    <div v-else-if="!store.loading" class="empty-card">
      <svg class="empty-ico" viewBox="0 0 64 64" fill="none" stroke="#c9c4ba" stroke-width="1.6">
        <rect x="12" y="10" width="18" height="26" rx="2" />
        <rect x="36" y="22" width="18" height="26" rx="2" />
        <path d="M30 30h6" stroke-linecap="round" />
        <path d="M33 27l3 3-3 3" stroke-linecap="round" stroke-linejoin="round" />
      </svg>
      <div class="empty-title">选择两份合同并点击「开始对比」，查看条款差异</div>
      <div class="empty-sub">支持模板库合同，也支持上传本地 .docx 文件</div>
    </div>
  </div>
</template>

<style scoped>
.page-title {
  font-weight: 600;
  letter-spacing: 0.5px;
}
.page-icon {
  width: 44px;
  height: 44px;
  border-radius: 12px;
  background: #f8f7f3;
  border: 1px solid #ece7de;
  display: flex;
  align-items: center;
  justify-content: center;
}
.page-icon svg {
  width: 24px;
  height: 24px;
}
/* 选择区 */
.pick-wrap {
  display: grid;
  grid-template-columns: 1fr 64px 1fr;
  align-items: stretch;
  gap: 16px;
  margin-bottom: 18px;
}
.pick-card {
  background: #fff;
  border: 1px solid #e6ebf5;
  border-radius: 12px;
  padding: 20px;
  box-shadow:
    0 1px 2px rgba(15, 23, 42, 0.03),
    0 10px 26px -24px rgba(15, 23, 42, 0.5);
}
.pick-title {
  font-size: 13.5px;
  font-weight: 600;
  color: #14161a;
  margin-bottom: 14px;
  letter-spacing: 0.5px;
}
.pick-select {
  width: 100%;
  margin-bottom: 10px;
}
.pick-note {
  font-size: 11.5px;
  color: #94a3b8;
  line-height: 1.7;
  min-height: 20px;
}
.pick-note b {
  color: #334155;
  font-weight: 500;
}
.link {
  background: none;
  border: none;
  color: #2563eb;
  font-size: 11.5px;
  cursor: pointer;
  padding: 0 0 0 6px;
}
.pick-foot {
  margin-top: 12px;
  display: flex;
  justify-content: flex-end;
}
.hidden {
  display: none;
}
/* 双向箭头 */
.arrow {
  display: flex;
  align-items: center;
  justify-content: center;
  color: #cbd5e1;
  transition:
    color 0.25s,
    opacity 0.25s;
}
.arrow svg {
  width: 40px;
  height: 22px;
}
.arrow:hover {
  color: #2563eb;
}
.arrow.breathing {
  animation: arrow-breath 1.8s ease-in-out infinite;
}
@keyframes arrow-breath {
  0%,
  100% {
    opacity: 0.45;
  }
  50% {
    opacity: 1;
  }
}
/* 开始对比 */
.run-wrap {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  margin-bottom: 20px;
}
.run-btn {
  min-width: 180px;
  border-radius: 8px;
}
.status {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  min-height: 34px;
}
.status-text {
  font-size: 12.5px;
  color: #64748b;
  letter-spacing: 0.5px;
}
.thin-bar {
  width: 320px;
  height: 2px;
  background: #eef2f7;
  border-radius: 2px;
  overflow: hidden;
}
.thin-bar i {
  display: block;
  height: 100%;
  background: linear-gradient(90deg, #93c5fd, #2563eb);
  transition: width 0.4s linear;
}
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.25s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
/* 结果卡 */
.result-card {
  background: #fff;
  border: 1px solid #e6ebf5;
  border-radius: 12px;
  padding: 20px 22px 16px;
  box-shadow:
    0 1px 2px rgba(15, 23, 42, 0.03),
    0 10px 26px -24px rgba(15, 23, 42, 0.5);
}
.tabs {
  display: flex;
  gap: 26px;
  border-bottom: 1px solid #eef2f7;
  margin-bottom: 16px;
}
.tab {
  background: none;
  border: none;
  padding: 0 0 11px;
  font-size: 13px;
  color: #8a867d;
  cursor: pointer;
  letter-spacing: 0.4px;
  border-bottom: 2px solid transparent;
  margin-bottom: -1px;
  transition: color 0.15s;
}
.tab:hover {
  color: #2563eb;
}
.tab.active {
  color: #14161a;
  border-bottom-color: #2563eb;
}
.tab-body {
  padding-top: 4px;
}
/* Diff */
.diff-head {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: #94a3b8;
  margin-bottom: 12px;
}
.diff-a,
.diff-b {
  color: #334155;
  max-width: 260px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.spacer {
  flex: 1;
}
.switch {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
  user-select: none;
}
.legend {
  display: flex;
  gap: 18px;
  font-size: 11.5px;
  color: #94a3b8;
  margin-bottom: 14px;
}
.legend span {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}
.legend i {
  width: 10px;
  height: 10px;
  border-radius: 2px;
  display: inline-block;
}
.diff-row {
  border: 1px solid #eef2f7;
  border-radius: 10px;
  padding: 14px 16px;
  margin-bottom: 10px;
}
.diff-row.chg-新增 {
  border-left: 3px solid #10b981;
  background: #f8fdfa;
}
.diff-row.chg-删除 {
  border-left: 3px solid #ef4444;
  background: #fef8f7;
}
.diff-row.chg-修改 {
  border-left: 3px solid #f59e0b;
  background: #fffdf6;
}
.diff-clause {
  font-size: 13px;
  font-weight: 600;
  color: #14161a;
  margin-bottom: 10px;
  display: flex;
  align-items: center;
  gap: 8px;
}
.chg-badge {
  font-size: 10.5px;
  border: 1px solid;
  border-radius: 999px;
  padding: 1px 8px;
  font-weight: 500;
}
.diff-cols {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px;
}
.diff-col {
  min-width: 0;
}
.col-label {
  font-size: 10px;
  letter-spacing: 1.5px;
  color: #b3b0a8;
  margin-bottom: 4px;
}
.col-text {
  font-size: 12px;
  line-height: 1.8;
  color: #475569;
  max-height: 96px;
  overflow: auto;
  word-break: break-word;
}
/* 统计 */
.stat-wrap {
  display: grid;
  grid-template-columns: 1.4fr 1fr;
  gap: 24px;
  align-items: center;
}
.stat-cards {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 10px;
}
.stat-card {
  border: 1px solid #eef2f7;
  border-radius: 10px;
  padding: 14px 10px;
  text-align: center;
}
.stat-num {
  font-size: 22px;
  font-weight: 800;
  color: #0f172a;
  line-height: 1.1;
}
.stat-label {
  font-size: 11px;
  color: #94a3b8;
  margin-top: 6px;
}
.donut-wrap {
  display: flex;
  align-items: center;
  gap: 18px;
  justify-content: center;
}
.donut {
  width: 120px;
  height: 120px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
}
.donut-hole {
  width: 78px;
  height: 78px;
  background: #fff;
  border-radius: 50%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}
.donut-hole b {
  font-size: 20px;
  color: #0f172a;
}
.donut-hole span {
  font-size: 10px;
  color: #94a3b8;
}
.donut-legend {
  display: flex;
  flex-direction: column;
  gap: 8px;
  font-size: 11.5px;
  color: #64748b;
}
.donut-legend span {
  display: flex;
  align-items: center;
  gap: 6px;
}
.donut-legend i {
  width: 9px;
  height: 9px;
  border-radius: 2px;
}
/* 风险列表 */
.risk-item {
  border: 1px solid #eef2f7;
  border-radius: 10px;
  padding: 12px 14px;
  margin-bottom: 10px;
}
.risk-item.sev-high {
  border-left: 3px solid #ef4444;
}
.risk-item.sev-mid {
  border-left: 3px solid #f59e0b;
}
.risk-item.sev-low {
  border-left: 3px solid #10b981;
}
.risk-head {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 6px;
}
.sev {
  font-size: 10.5px;
  padding: 1px 8px;
  border-radius: 999px;
  font-weight: 600;
}
.sev-high .sev {
  color: #b91c1c;
  background: #fef2f2;
}
.sev-mid .sev {
  color: #b45309;
  background: #fffbeb;
}
.sev-low .sev {
  color: #047857;
  background: #ecfdf5;
}
.sev-none .sev {
  color: #64748b;
  background: #f8fafc;
}
.risk-clause {
  font-size: 13px;
  font-weight: 600;
  color: #14161a;
}
.risk-change {
  font-size: 11.5px;
  color: #94a3b8;
}
.risk-from {
  margin-left: auto;
  font-size: 10px;
  color: #b3b0a8;
  border: 1px solid #ece7de;
  border-radius: 999px;
  padding: 1px 7px;
}
.risk-note {
  font-size: 12px;
  color: #64748b;
  line-height: 1.8;
  margin: 0;
}
/* 底部操作 */
.panel-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  padding-top: 14px;
  margin-top: 6px;
  border-top: 1px solid #f4f7fb;
}
/* 空状态 */
.empty-card {
  background: #fff;
  border: 1px solid #e6ebf5;
  border-radius: 12px;
  padding: 56px 20px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  box-shadow:
    0 1px 2px rgba(15, 23, 42, 0.03),
    0 10px 26px -24px rgba(15, 23, 42, 0.5);
}
.empty-ico {
  width: 64px;
  height: 64px;
  margin-bottom: 6px;
}
.empty-title {
  font-size: 13.5px;
  font-weight: 600;
  color: #475569;
}
.empty-sub {
  font-size: 11.5px;
  color: #a39d92;
}
.empty-line {
  font-size: 12px;
  color: #b3b0a8;
  padding: 16px 0;
}
@media (max-width: 1000px) {
  .pick-wrap {
    grid-template-columns: 1fr;
  }
  .arrow {
    transform: rotate(90deg);
    padding: 6px 0;
  }
  .stat-wrap {
    grid-template-columns: 1fr;
  }
  .stat-cards {
    grid-template-columns: repeat(2, 1fr);
  }
  .diff-cols {
    grid-template-columns: 1fr;
  }
}
</style>
