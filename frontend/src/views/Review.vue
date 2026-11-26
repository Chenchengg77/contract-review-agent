<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useReviewStore } from '../stores/review'

interface Judgment {
  clause: string
  present: boolean
  verdict: string
  severity: string
  reason: string
  revision?: string
}

const store = useReviewStore()
const router = useRouter()
const file = ref<File | null>(null)
const tab = ref<'file' | 'sample'>('file')
const dragging = ref(false)

const clauseTypes = [
  '付款条款',
  '违约金',
  '争议解决',
  '保密条款',
  '知识产权',
  '合同终止',
  '责任上限',
  '验收条款',
  '交付条款',
  '发票条款',
  '竞业限制',
  '数据合规',
  '不可抗力',
]

onMounted(() => store.loadContracts())

async function copyText(t: string) {
  try {
    await navigator.clipboard.writeText(t)
    ElMessage.success('已复制，可粘贴到合同里')
  } catch {
    ElMessage.error('复制失败，请手动选中复制')
  }
}

watch(
  () => store.error,
  (v) => {
    if (v) {
      ElMessage.error(v)
      store.error = ''
    }
  }
)

function onFile(e: Event) {
  const f = (e.target as HTMLInputElement).files?.[0] || null
  file.value = f
  if (f) store.selected = ''
}

function onDrop(e: DragEvent) {
  dragging.value = false
  const f = e.dataTransfer?.files?.[0] || null
  if (f) {
    file.value = f
    store.selected = ''
    tab.value = 'file'
  }
}

function start() {
  store.start(file.value)
}

/** 人工确认：通过后继续执行报告节点 */
function approve() {
  store.resumeGraph('approve')
}

function fmtTime(ts: number) {
  if (!ts) return ''
  const d = new Date(ts * 1000)
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

// 缺失的条款（用于提示"本范本缺少 N 类条款"）
const missingClauses = computed<string[]>(() =>
  (store.result?.judgments || [])
    .filter((j: Judgment) => j.verdict === '缺失')
    .map((j: Judgment) => j.clause)
)

// 风险最高的一条（用于主动追问）
const topRisk = computed<Judgment | null>(() => {
  const js: Judgment[] = store.result?.judgments || []
  return js.find((j) => j.severity === '高') || null
})

const proactiveText = computed(() => {
  const ov = store.result?.overview
  if (!ov) return ''
  const parts = [`审完了：${ov.high} 条高风险、${ov.mid} 条中风险。`]
  if (topRisk.value) parts.push(`其中「${topRisk.value.clause}」风险最高。`)
  parts.push('想让我展开讲哪条？直接问我就行。')
  return parts.join('')
})

const stageLabels = ['① 解析', '② 抽取', '③ 判定', '④ 修订']

const verdictColor: Record<string, string> = {
  合规: '#16a34a',
  偏离: '#d97706',
  缺失: '#64748b',
  冲突: '#dc2626',
}
const severityColor: Record<string, string> = { 高: '#dc2626', 中: '#d97706', 低: '#16a34a' }

function badgeStyle(color: string) {
  return { background: color + '18', color, border: '1px solid ' + color + '40' }
}
</script>

<template>
  <div class="page">
    <div class="page-head">
      <div class="page-icon" style="background: #eff6ff; color: #2563eb">🔍</div>
      <div>
        <h1 class="page-title">合同审查</h1>
        <p class="page-sub">上传合同，自动识别 13 类核心条款并判定风险，给出修订建议。</p>
      </div>
    </div>

    <div class="layout">
      <!-- 主列 -->
      <div class="main-col">
        <!-- 上次审查提示 -->
        <div v-if="store.lastReview && store.contracts.includes(store.lastReview.filename)" class="last-hint">
          <span class="lh-dot"></span>
          <span class="lh-text">
            欢迎回来 —— 上次你审了「{{ store.lastReview.filename }}」（{{ fmtTime(store.lastReview.created_at) }}）
          </span>
          <button
            class="lh-btn"
            @click="store.selected = store.lastReview!.filename; file = null; tab = 'sample'"
          >
            继续看这一份
          </button>
        </div>

        <!-- 选择合同 -->
        <el-card shadow="never" class="card upload-card">
          <div class="up-tabs">
            <button class="up-tab" :class="{ active: tab === 'file' }" @click="tab = 'file'">
              上传本地文件
            </button>
            <button class="up-tab" :class="{ active: tab === 'sample' }" @click="tab = 'sample'">
              选用示范合同
            </button>
          </div>

          <label
            v-show="tab === 'file'"
            class="drop-zone"
            :class="{ filled: !!file, dragging }"
            @dragover.prevent="dragging = true"
            @dragleave="dragging = false"
            @drop.prevent="onDrop"
          >
            <input type="file" accept=".docx" class="hidden-input" @change="onFile" />
            <svg class="dz-ico" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.4">
              <path d="M7 3.5h7.2L18.5 8v12.5H7z" stroke-linejoin="round" />
              <path d="M14 3.5V8h4.2" stroke-linejoin="round" />
              <path d="M9.6 12.2h5M9.6 15.4h5M9.6 18.2h3" stroke-linecap="round" />
            </svg>
            <div class="dz-title">{{ file ? file.name : '点击选择 .docx 合同' }}</div>
            <div class="dz-sub">{{ file ? '已选择，可点此更换' : '或将文件拖拽到此处' }}</div>
            <span class="scan"></span>
          </label>

          <div v-show="tab === 'sample'" class="sample">
            <label class="lbl">选示例合同</label>
            <el-select
              v-model="store.selected"
              placeholder="选择示例"
              filterable
              style="width: 100%"
              @change="file = null"
            >
              <el-option v-for="c in store.contracts" :key="c" :label="c" :value="c" />
            </el-select>
            <div class="sample-tip">共 {{ store.contracts.length }} 份示范文本</div>
          </div>
        </el-card>

        <!-- 配置 -->
        <el-card shadow="never" class="card">
          <div class="cfg-row">
            <div class="cfg-field">
              <label class="lbl">关注点（可选）</label>
              <el-input v-model="store.focus" placeholder="例如：重点关注付款、违约责任与争议解决" />
            </div>
            <div class="cfg-field stance">
              <label class="lbl">审查立场</label>
              <el-select v-model="store.perspective" placeholder="中立" clearable style="width: 100%">
                <el-option label="中立" value="" />
                <el-option label="甲方" value="甲方" />
                <el-option label="乙方" value="乙方" />
              </el-select>
            </div>
            <el-button type="primary" size="large" :loading="store.loading" @click="start">
              开始审查
            </el-button>
          </div>

          <div class="run-options">
            <el-checkbox v-model="store.graphMode" class="graph-toggle">
              人工确认（LangGraph）：高风险条款先暂停，确认后才生成报告
            </el-checkbox>
          </div>

          <div class="tip">
            提示：审查在后台进行，切到其他页面再回来也不会中断。
          </div>
        </el-card>

        <!-- 待人工确认 -->
        <el-card v-if="store.pending" shadow="never" class="card pending-card">
          <div class="pending-head">
            <span class="pending-title">
              发现 {{ store.pending.high_risk.length }} 项高风险条款
            </span>
            <span class="pending-sub">确认后才会生成正式报告</span>
          </div>

          <div class="pending-list">
            <div v-for="(j, i) in store.pending.high_risk" :key="i" class="pending-item">
              <div class="p-head">
                <span class="p-clause">{{ j.clause_no ? j.clause_no + ' ' : '' }}{{ j.clause }}</span>
                <span class="p-badge">{{ j.severity }}</span>
                <span class="p-verdict">{{ j.verdict }}</span>
              </div>
              <p class="p-reason">{{ j.reason }}</p>
            </div>
          </div>

          <div class="pending-actions">
            <el-button size="small" @click="store.pending = null">放弃</el-button>
            <el-button type="primary" :loading="store.loading" @click="approve">
              确认并生成报告
            </el-button>
          </div>
        </el-card>

        <!-- 进度 -->
        <el-card v-if="store.loading" shadow="never" class="card">
          <div class="progress-head">
            <span>审查进度</span>
            <span class="pct">{{ Math.round(store.progress) }}%</span>
          </div>
          <el-progress :percentage="store.progress" :show-text="false" :stroke-width="8" />
          <div class="stages">
            <div v-for="(s, i) in stageLabels" :key="s" class="stage" :class="{ active: i <= store.stage }">{{ s }}</div>
          </div>
        </el-card>

        <!-- 结果 -->
        <template v-if="store.result">
          <div class="overview">
            <div class="ov-card">
              <div class="ov-num" style="color: #dc2626">{{ store.result.overview.high }}</div>
              <div class="ov-label">高风险</div>
            </div>
            <div class="ov-card">
              <div class="ov-num" style="color: #d97706">{{ store.result.overview.mid }}</div>
              <div class="ov-label">中风险</div>
            </div>
            <div class="ov-card">
              <div class="ov-num" style="color: #16a34a">{{ store.result.overview.low }}</div>
              <div class="ov-label">低风险</div>
            </div>
          </div>

          <div v-if="missingClauses.length" class="missing-hint">
            <span class="mh-icon">⚠️</span>
            <div class="mh-body">
              <div class="mh-title">本范本缺少 {{ missingClauses.length }} 类条款，建议补充</div>
              <div class="mh-list">{{ missingClauses.join('、') }}</div>
              <div class="mh-tip">空白范本通常不覆盖这些条款，签约前可参考下方修订建议补充。</div>
            </div>
          </div>

          <el-card shadow="never" class="card">
            <div class="table-wrap">
              <table class="tbl">
                <thead>
                  <tr>
                    <th>条款</th>
                    <th>判定</th>
                    <th>等级</th>
                    <th>问题 / 修订建议</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="j in (store.result.judgments as Judgment[])" :key="j.clause">
                    <td class="clause">{{ j.clause }}</td>
                    <td>
                      <span class="badge" :style="badgeStyle(verdictColor[j.verdict] || '#64748b')">{{ j.verdict }}</span>
                    </td>
                    <td>
                      <span class="badge" :style="badgeStyle(severityColor[j.severity] || '#64748b')">{{ j.severity }}</span>
                    </td>
                    <td>
                      <div class="reason">{{ j.reason }}</div>
                      <div v-if="j.revision" class="revision">
                        <span class="rev-text">📝 修订建议：{{ j.revision }}</span>
                        <button class="copy-btn" @click="copyText(j.revision)">复制</button>
                      </div>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </el-card>

          <div class="assistant-note">
            <div class="an-avatar">⚖️</div>
            <div class="an-body">
              <div class="an-text">{{ proactiveText }}</div>
              <button class="an-btn" @click="router.push('/chat')">去 AI 对话问细节 →</button>
            </div>
          </div>
        </template>

        <!-- 空状态 -->
        <el-card v-else-if="!store.loading" shadow="never" class="card empty-card">
          <div class="empty-state">
            <div class="empty-icon">📄</div>
            <div class="empty-title">还没有审查结果</div>
            <p>选择一份示例合同，或上传你的 .docx 合同，然后点「开始审查」。</p>
          </div>
        </el-card>
      </div>

      <!-- 侧栏 -->
      <aside class="side-col">
        <el-card shadow="never" class="card">
          <div class="side-title">覆盖的 13 类核心条款</div>
          <div class="clause-list">
            <span v-for="c in clauseTypes" :key="c" class="clause-tag">{{ c }}</span>
          </div>
        </el-card>

        <el-card shadow="never" class="card">
          <div class="side-title">审查说明</div>
          <ul class="notes">
            <li>判定结果：<b>合规 / 偏离 / 缺失 / 冲突</b></li>
            <li>每条给出原文定位与修订建议</li>
            <li>风险等级分高 / 中 / 低</li>
            <li>审查在后台进行，切换页面不中断</li>
            <li>适用于<b>商务合同</b>（买卖/租赁/承揽/服务/建设）</li>
          </ul>
        </el-card>
      </aside>
    </div>
  </div>
</template>

<style scoped>
.layout {
  display: grid;
  grid-template-columns: 1fr 300px;
  gap: 16px;
  align-items: start;
}
.main-col {
  display: flex;
  flex-direction: column;
  gap: 16px;
  min-width: 0;
}
.side-col {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.card {
  border-radius: 16px;
}

/* 上传区 */
.upload-card {
  border: 1px solid #ece7f6 !important;
  background: linear-gradient(180deg, #fffdf8 0%, #fffbf4 100%);
  border-radius: 14px;
}
.up-tabs {
  display: flex;
  gap: 28px;
  border-bottom: 1px solid #efeaf9;
  margin-bottom: 16px;
}
.up-tab {
  background: none;
  border: none;
  padding: 0 0 11px;
  font-size: 13px;
  color: #8a867d;
  cursor: pointer;
  letter-spacing: 0.5px;
  border-bottom: 2px solid transparent;
  margin-bottom: -1px;
  transition: color 0.15s;
}
.up-tab:hover {
  color: #4f46e5;
}
.up-tab.active {
  color: #14161a;
  border-bottom-color: #a5b4fc;
}
.drop-zone {
  position: relative;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 190px;
  border: 1.5px dashed #c8c2ee;
  border-radius: 14px;
  padding: 26px 20px;
  text-align: center;
  cursor: pointer;
  transition:
    background 0.2s,
    border-color 0.2s,
    box-shadow 0.2s;
  background: #fffdf8;
}
.drop-zone:hover,
.drop-zone.dragging {
  border-color: #a5b4fc;
  background: #fffefb;
  box-shadow: 0 0 0 4px rgba(139, 92, 246, 0.06);
}
.drop-zone.filled {
  border-style: solid;
  border-color: #bbf7d0;
  background: #f7fdf9;
}
.hidden-input {
  display: none;
}
.dz-ico {
  width: 34px;
  height: 34px;
  color: #8b8ae0;
  margin-bottom: 10px;
}
.drop-zone.filled .dz-ico {
  color: #10b981;
}
.dz-title {
  font-size: 14px;
  font-weight: 600;
  color: #14161a;
  word-break: break-all;
}
.dz-sub {
  font-size: 12px;
  color: #a39d92;
  margin-top: 4px;
}
/* 扫描线：hover / 拖拽时出现 */
.scan {
  position: absolute;
  top: 0;
  bottom: 0;
  left: -45%;
  width: 45%;
  background: linear-gradient(90deg, transparent, rgba(96, 165, 250, 0.13), transparent);
  opacity: 0;
  pointer-events: none;
}
.drop-zone:hover .scan,
.drop-zone.dragging .scan {
  opacity: 1;
  animation: scan-x 3.8s linear infinite;
}
@keyframes scan-x {
  0% {
    left: -45%;
  }
  100% {
    left: 100%;
  }
}
.sample {
  min-width: 0;
}
.sample-tip {
  font-size: 11px;
  color: #a39d92;
  margin-top: 6px;
}

/* 配置 */
.cfg-row {
  display: grid;
  grid-template-columns: 1fr 180px auto;
  gap: 16px;
  align-items: end;
}
.cfg-field {
  flex: 1;
}
.lbl {
  display: block;
  font-size: 12px;
  color: #64748b;
  margin-bottom: 6px;
}
.tip {
  margin-top: 10px;
  font-size: 12px;
  color: #94a3b8;
}
.pref-chip {
  margin-top: 10px;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: #1d4ed8;
  background: #eff6ff;
  border: 1px solid #bfdbfe;
  border-radius: 999px;
  padding: 5px 12px;
}
.pref-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #22c55e;
}
.pref-link {
  background: none;
  border: none;
  color: #1d4ed8;
  font-size: 12px;
  cursor: pointer;
  text-decoration: underline;
  padding: 0;
}

/* 进度 */
.progress-head {
  display: flex;
  justify-content: space-between;
  font-size: 14px;
  margin-bottom: 10px;
}
.pct {
  color: #1d4ed8;
  font-weight: 700;
}
.stages {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 8px;
  margin-top: 14px;
}
.stage {
  text-align: center;
  font-size: 12px;
  padding: 6px;
  border-radius: 8px;
  background: #f8fafc;
  color: #94a3b8;
}
.stage.active {
  background: #eff6ff;
  color: #1d4ed8;
  font-weight: 600;
}

/* 概览 */
.overview {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 14px;
}
.ov-card {
  background: #fff;
  border: 1px solid #e8edf5;
  border-radius: 16px;
  padding: 18px;
  text-align: center;
}
.ov-num {
  font-size: 28px;
  font-weight: 800;
}
.ov-label {
  font-size: 12px;
  color: #94a3b8;
  margin-top: 4px;
}

/* 表格 */
.table-wrap {
  overflow-x: auto;
}
.tbl {
  width: 100%;
  border-collapse: collapse;
  font-size: 14px;
}
.tbl th {
  text-align: left;
  padding: 10px 12px;
  background: #f8fafc;
  color: #475569;
  font-weight: 500;
}
.tbl td {
  padding: 12px;
  border-bottom: 1px solid #f1f5f9;
  vertical-align: top;
}
.clause {
  font-weight: 600;
  white-space: nowrap;
}
.badge {
  display: inline-block;
  font-size: 12px;
  padding: 2px 8px;
  border-radius: 6px;
}
.reason {
  color: #475569;
  line-height: 1.6;
}
.revision {
  margin-top: 6px;
  font-size: 12px;
  color: #1f3fb3;
  background: #f4f6fc;
  border: 1px solid #dde3f5;
  border-radius: 2px;
  padding: 8px 10px;
  line-height: 1.6;
  display: flex;
  align-items: flex-start;
  gap: 10px;
}
.rev-text {
  flex: 1;
}
.copy-btn {
  flex-shrink: 0;
  background: none;
  border: 1px solid #dde3f5;
  color: #1f3fb3;
  font-size: 11px;
  padding: 2px 9px;
  border-radius: 2px;
  cursor: pointer;
  letter-spacing: 0.5px;
  transition: all 0.15s;
}
.copy-btn:hover {
  background: #1f3fb3;
  color: #fff;
  border-color: #1f3fb3;
}

/* 上次审查提示 */
.last-hint {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
  background: #fff;
  border: 1px solid #ece7f6;
  border-radius: 12px;
  padding: 12px 16px;
  font-size: 12.5px;
  color: #475569;
  box-shadow: 0 10px 26px -22px rgba(79, 70, 229, 0.55);
}
.lh-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #8b5cf6;
  flex-shrink: 0;
  animation: lh-breath 2.6s ease-in-out infinite;
}
@keyframes lh-breath {
  0%,
  100% {
    box-shadow: 0 0 0 0 rgba(139, 92, 246, 0.45);
    opacity: 0.7;
  }
  50% {
    box-shadow: 0 0 0 7px rgba(139, 92, 246, 0);
    opacity: 1;
  }
}
.lh-text {
  flex: 1;
  min-width: 200px;
}
.lh-btn {
  background: none;
  border: none;
  color: #4f46e5;
  font-size: 12.5px;
  font-weight: 600;
  cursor: pointer;
  padding: 0;
  letter-spacing: 0.3px;
}
.lh-btn:hover {
  text-decoration: underline;
}

/* 主动追问 */
.assistant-note {
  display: flex;
  gap: 12px;
  background: #fff;
  border: 1px solid #e8edf5;
  border-radius: 16px;
  padding: 16px 18px;
}
.an-avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: linear-gradient(135deg, #3b82f6, #6366f1);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 17px;
  flex-shrink: 0;
}
.an-body {
  flex: 1;
}
.an-text {
  font-size: 13.5px;
  color: #334155;
  line-height: 1.7;
}
.an-btn {
  margin-top: 10px;
  background: #eff6ff;
  border: 1px solid #bfdbfe;
  color: #1d4ed8;
  font-size: 12.5px;
  border-radius: 8px;
  padding: 6px 12px;
  cursor: pointer;
}
.an-btn:hover {
  background: #dbeafe;
}

/* 缺失条款提示 */
.missing-hint {
  display: flex;
  gap: 12px;
  align-items: flex-start;
  background: #fffbeb;
  border: 1px solid #fde68a;
  border-radius: 14px;
  padding: 16px 18px;
}
.mh-icon {
  font-size: 18px;
  line-height: 1.4;
}
.mh-title {
  font-size: 13.5px;
  font-weight: 600;
  color: #92400e;
  margin-bottom: 4px;
}
.mh-list {
  font-size: 12.5px;
  color: #b45309;
  line-height: 1.7;
  margin-bottom: 4px;
}
.mh-tip {
  font-size: 12px;
  color: #a16207;
  opacity: 0.85;
}

/* 空状态 */
.empty-card {
  min-height: 260px;
  display: flex;
  align-items: center;
  justify-content: center;
}
.empty-state {
  text-align: center;
  padding: 20px;
}
.empty-icon {
  font-size: 40px;
  margin-bottom: 10px;
}
.empty-title {
  font-size: 16px;
  font-weight: 600;
  color: #0f172a;
  margin-bottom: 6px;
}
.empty-state p {
  font-size: 13px;
  color: #94a3b8;
  margin: 0;
}

/* 侧栏 */
.side-title {
  font-size: 13px;
  font-weight: 600;
  color: #0f172a;
  margin-bottom: 12px;
}
.clause-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.clause-tag {
  font-size: 11.5px;
  color: #475569;
  background: #f8fafc;
  border: 1px solid #e8edf5;
  border-radius: 6px;
  padding: 3px 8px;
}
.notes {
  margin: 0;
  padding-left: 18px;
  font-size: 12px;
  color: #64748b;
  line-height: 2;
}
.notes b {
  color: #334155;
}

@media (max-width: 1100px) {
  .layout {
    grid-template-columns: 1fr;
  }
}
/* 人工确认 */
.run-options {
  margin-top: 10px;
}
.graph-toggle :deep(.el-checkbox__label) {
  font-size: 12px;
  color: #6b6f76;
}
.pending-card {
  border: 1px solid #f3ded9 !important;
  background: linear-gradient(180deg, #fffdfc 0%, #fff9f7 100%);
}
.pending-head {
  display: flex;
  align-items: baseline;
  gap: 10px;
  margin-bottom: 14px;
}
.pending-title {
  font-size: 14px;
  font-weight: 600;
  color: #b4544a;
}
.pending-sub {
  font-size: 11.5px;
  color: #a39d92;
}
.pending-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.pending-item {
  border: 1px solid #f3e4e0;
  border-radius: 8px;
  background: #fff;
  padding: 12px 14px;
}
.p-head {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
}
.p-clause {
  font-size: 13px;
  font-weight: 600;
  color: #14161a;
}
.p-badge {
  font-size: 10.5px;
  padding: 1px 8px;
  border-radius: 999px;
  background: #fff2f0;
  color: #b4544a;
}
.p-verdict {
  font-size: 11.5px;
  color: #94a3b8;
  margin-left: auto;
}
.p-reason {
  font-size: 12px;
  line-height: 1.8;
  color: #64748b;
  margin: 0;
}
.pending-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 16px;
}
</style>
