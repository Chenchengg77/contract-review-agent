<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox, ElNotification } from 'element-plus'
import { Refresh } from '@element-plus/icons-vue'
import api from '../../api'

const router = useRouter()

const health = ref<any>(null)
const settings = ref({ guard_on: true, guard_low: 5.0, guard_high: 8.0, review_timeout: 180 })
const failures = ref<any[]>([])
const reviews = ref<any[]>([])
const saving = ref(false)

const detail = ref<any>(null)
const detailVisible = ref(false)

async function load() {
  try {
    const [h, s, f, r] = await Promise.all([
      api.get('/admin/health'),
      api.get('/admin/settings'),
      api.get('/admin/failures'),
      api.get('/reviews'),
    ])
    health.value = h.data
    settings.value = s.data
    failures.value = f.data.failures || []
    reviews.value = r.data.reviews || []
  } catch {
    ElMessage.error('加载失败')
  }
}

onMounted(load)

// ===== 健康检查 =====
const total = computed(() => health.value?.total ?? 0)
const failed = computed(() => health.value?.failed ?? 0)
const successRate = computed(() => (health.value?.success_rate ?? 1) * 100)
const avgDuration = computed(() => health.value?.avg_duration ?? 0)
const failRate = computed(() => (total.value ? failed.value / total.value : 0))

const services = computed(() => {
  const s = health.value?.services || {}
  const hybrid = health.value?.retrieval === 'hybrid'
  return [
    { key: 'db', name: '数据库', ok: !!s.db },
    { key: 'llm', name: 'AI 模型', ok: !!s.llm },
    { key: 'files', name: '文件解析', ok: !!s.files },
    { key: 'retrieval', name: hybrid ? '检索：混合' : '检索：关键词', ok: true },
  ]
})
const allOk = computed(() => services.value.every((s) => s.ok))
const servicesText = computed(() =>
  allOk.value
    ? '数据库 / AI 模型 / 文件解析 全部正常'
    : services.value
        .filter((s) => !s.ok)
        .map((s) => `${s.name}异常`)
        .join(' / ')
)

// 平均耗时：近 24h vs 前 24h（真实对比）
const durDelta = computed(() => {
  const now = Date.now() / 1000
  let curSum = 0
  let curN = 0
  let prevSum = 0
  let prevN = 0
  for (const r of reviews.value) {
    if (r.status !== 'ok' || !r.duration) continue
    const t = r.created_at || 0
    if (t > now - 86400) {
      curSum += r.duration
      curN += 1
    } else if (t > now - 172800) {
      prevSum += r.duration
      prevN += 1
    }
  }
  if (!curN || !prevN) return null
  return curSum / curN - prevSum / prevN
})
const durDeltaText = computed(() => {
  if (durDelta.value == null) return '近期无对比数据'
  const d = durDelta.value
  if (Math.abs(d) < 0.1) return '与前日持平'
  return `较前日 ${d > 0 ? '+' : ''}${d.toFixed(1)}s`
})

// 成功率环形
const RING_R = 26
const RING_C = 2 * Math.PI * RING_R
const ringDash = computed(() => `${(Math.max(0, Math.min(1, successRate.value / 100)) * RING_C).toFixed(1)} ${RING_C.toFixed(1)}`)

function fmt(ts: number) {
  if (!ts) return '暂无'
  const d = new Date(ts * 1000)
  const p = (n: number) => String(n).padStart(2, '0')
  return `${p(d.getMonth() + 1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}`
}

function initials(name: string) {
  return (name || '?').slice(0, 1).toUpperCase()
}

// 错误分类
function errType(err: string) {
  const e = err || ''
  if (/timed out|timeout|超时/i.test(e)) return '超时'
  if (/rate limit|429|限流/i.test(e)) return '限流'
  if (/parse|解析|docx|zip/i.test(e)) return '解析失败'
  if (/api key|401|403|unauthorized/i.test(e)) return '鉴权'
  return '其他'
}
function errClass(err: string) {
  const t = errType(err)
  if (t === '超时' || t === '限流') return 'warn'
  if (t === '解析失败' || t === '鉴权') return 'bad'
  return 'muted'
}

// ===== 配置 =====
async function save() {
  saving.value = true
  try {
    const { data } = await api.put('/admin/settings', settings.value)
    settings.value = data
    ElMessage.success('配置已生效，无需重启')
  } catch {
    ElMessage.error('保存失败')
  } finally {
    saving.value = false
  }
}

async function reset() {
  try {
    await ElMessageBox.confirm('把 AI 拦截配置恢复为默认（开启 / 5.0 / 8.0）？', '恢复默认', {
      type: 'info',
    })
  } catch {
    return
  }
  try {
    const { data } = await api.post('/admin/settings/reset')
    settings.value = data
    ElMessage.success('已恢复默认配置')
  } catch {
    ElMessage.error('恢复失败')
  }
}

// ===== 失败记录 =====
const kw = ref('')
const errFilter = ref('')
const page = ref(1)
const pageSize = ref(10)

const filteredFailures = computed(() => {
  const k = kw.value.trim().toLowerCase()
  return failures.value.filter((f) => {
    if (k) {
      const hay = `${f.username || ''} ${f.filename || ''}`.toLowerCase()
      if (!hay.includes(k)) return false
    }
    if (errFilter.value && errType(f.error) !== errFilter.value) return false
    return true
  })
})
const pagedFailures = computed(() => {
  const start = (page.value - 1) * pageSize.value
  return filteredFailures.value.slice(start, start + pageSize.value)
})

function gotoUser(name: string) {
  router.push({ path: '/admin/users', query: { q: name } })
}

// 查看原合同
const contractVisible = ref(false)
const contractLoading = ref(false)
const contractName = ref('')
const contractText = ref('')

async function openContract(name: string) {
  contractVisible.value = true
  contractLoading.value = true
  contractName.value = name
  contractText.value = ''
  try {
    const { data } = await api.get('/contract_text', { params: { name } })
    contractText.value = data.text || '（无正文）'
  } catch (e: any) {
    contractText.value = e.response?.data?.detail || '读取失败'
  } finally {
    contractLoading.value = false
  }
}

function showDetail(row: any) {
  detail.value = row
  detailVisible.value = true
}

async function retry(row: any) {
  try {
    await ElMessageBox.confirm(`重试「${row.filename}」？`, '确认重试', { type: 'info' })
  } catch {
    return
  }
  try {
    const { data } = await api.post('/admin/retry/' + row.id)
    ElMessage.success(
      `重试成功：高 ${data.overview.high} / 中 ${data.overview.mid} / 低 ${data.overview.low}`
    )
    load()
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '重试失败')
  }
}

async function injectDemo() {
  try {
    await ElMessageBox.confirm(
      '注入 10 条【模拟失败】记录（跨过 5% 告警阈值）？仅用于演示故障处理流程。',
      '模拟故障',
      { type: 'info' }
    )
  } catch {
    return
  }
  try {
    const { data } = await api.post('/admin/demo/failure')
    ElMessage.success(
      `已注入 ${data.injected} 条模拟失败，当前失败率 ${(data.rate * 100).toFixed(1)}%`
    )
    ElNotification({
      title: '系统告警',
      message: `近期失败率 ${(data.rate * 100).toFixed(1)}%，请查看失败记录`,
      type: 'warning',
      duration: 6000,
    })
    load()
  } catch {
    ElMessage.error('注入失败')
  }
}

async function clearFailures() {
  try {
    await ElMessageBox.confirm(
      '只清理【演示数据】（[DEMO] 开头）的失败记录；真实故障记录会保留。',
      '清理演示数据',
      { type: 'info' }
    )
  } catch {
    return
  }
  try {
    const { data } = await api.post('/admin/failures/clear')
    ElMessage.success(`已清理 ${data.cleared} 条演示失败记录（真实记录已保留）`)
    load()
  } catch {
    ElMessage.error('清理失败')
  }
}
</script>

<template>
  <div class="page">
    <div class="page-head">
      <div>
        <h1 class="page-title">系统运维</h1>
        <p class="page-sub">健康检查 · 运行时配置 · 失败记录与修复</p>
      </div>
    </div>

    <!-- 模块 1：健康检查 -->
    <div class="card">
      <div class="card-head">
        <div>
          <div class="card-title">健康检查</div>
          <div class="card-sub">系统实时状态与服务依赖</div>
        </div>
        <el-button text :icon="Refresh" @click="load">刷新</el-button>
      </div>

      <div class="health">
        <!-- 核心状态 -->
        <div class="core" :class="allOk ? 'ok' : 'bad'">
          <span class="pulse"></span>
          <div class="core-title">{{ allOk ? '系统正常' : '存在异常' }}</div>
          <div class="core-sub">{{ servicesText }}</div>
          <div class="core-services">
            <span v-for="s in services" :key="s.key" class="svc" :class="s.ok ? 'ok' : 'bad'">
              <i></i>{{ s.name }}
            </span>
          </div>
        </div>

        <!-- 右侧指标 -->
        <div class="metrics">
          <div class="metric">
            <div class="m-label">累计审查</div>
            <div class="m-value">{{ total }}</div>
            <div class="m-sub">份</div>
          </div>

          <div class="metric">
            <div class="m-label">失败次数</div>
            <div class="m-value" :class="failed > 0 ? 'bad' : 'ok'">{{ failed }}</div>
            <div class="m-sub">失败率 {{ (failRate * 100).toFixed(1) }}%</div>
          </div>

          <div class="metric ring-metric">
            <svg class="ring" viewBox="0 0 64 64">
              <circle class="ring-bg" cx="32" cy="32" :r="RING_R" />
              <circle class="ring-fg" cx="32" cy="32" :r="RING_R" :stroke-dasharray="ringDash" />
            </svg>
            <div class="ring-center">
              <div class="m-value">{{ successRate.toFixed(1) }}%</div>
              <div class="m-label">成功率</div>
            </div>
          </div>

          <div class="metric">
            <div class="m-label">平均耗时</div>
            <div class="m-value">{{ avgDuration || '—' }}<span v-if="avgDuration">s</span></div>
            <div class="m-sub" :class="durDelta == null ? 'muted' : durDelta > 0.1 ? 'bad' : 'ok'">
              {{ durDeltaText }}
            </div>
          </div>

          <div class="metric">
            <div class="m-label">最近审查</div>
            <div class="m-value small">{{ fmt(health?.last_at) }}</div>
            <div class="m-sub muted">更新时间 {{ fmt(Math.floor(Date.now() / 1000)) }}</div>
          </div>
        </div>
      </div>
    </div>

    <!-- 模块 2：运行时配置 -->
    <div class="card">
      <div class="card-head">
        <div>
          <div class="card-title">运行时配置</div>
          <div class="card-sub">改完立即生效，无需重启</div>
        </div>
      </div>

      <div class="cfg-section">
        <div class="section-title">AI 安全配置</div>
        <div class="cfg-rows">
          <div class="cfg-row">
            <div class="cfg-info">
              <div class="cfg-name">
                前置拦截
                <span class="tech">Guardrails</span>
                <el-tooltip
                  content="开启后，检索不到相关内容、或意图越界的问题会被直接拒答，不调用模型"
                  placement="top"
                >
                  <span class="help">?</span>
                </el-tooltip>
              </div>
              <div class="cfg-tip">关闭后，越界问题也会正常回答（用于前后对比演示）</div>
            </div>
            <div class="cfg-control">
              <el-switch v-model="settings.guard_on" active-text="开启" inactive-text="关闭" />
            </div>
          </div>

          <div class="cfg-row">
            <div class="cfg-info">
              <div class="cfg-name">
                检索阈值 · 低
                <el-tooltip content="BM25 检索分数低于该值时，判定为「与合同无关」并直接拒答" placement="top">
                  <span class="help">?</span>
                </el-tooltip>
              </div>
              <div class="cfg-tip">低于此分值直接拒答</div>
            </div>
            <div class="cfg-control">
              <el-input-number v-model="settings.guard_low" :min="0" :max="30" :step="0.5" />
            </div>
          </div>

          <div class="cfg-row">
            <div class="cfg-info">
              <div class="cfg-name">
                检索阈值 · 高
                <el-tooltip content="高于该值时直接放行，不做意图分类，省一次模型调用" placement="top">
                  <span class="help">?</span>
                </el-tooltip>
              </div>
              <div class="cfg-tip">高于此分值直接放行</div>
            </div>
            <div class="cfg-control">
              <el-input-number v-model="settings.guard_high" :min="0" :max="40" :step="0.5" />
            </div>
          </div>
        </div>
        <div class="cfg-note">灰区（低 ~ 高之间）会调用一次意图分类，判断是否越界。</div>
      </div>

      <div class="cfg-section">
        <div class="section-title">性能配置</div>
        <div class="cfg-rows">
          <div class="cfg-row">
            <div class="cfg-info">
              <div class="cfg-name">
                审查超时
                <span class="unit">秒</span>
                <el-tooltip content="单份合同审查的最长等待时间，超过即记为失败" placement="top">
                  <span class="help">?</span>
                </el-tooltip>
              </div>
              <div class="cfg-tip">演示用：改成 0.5 秒可制造真实超时故障</div>
            </div>
            <div class="cfg-control">
              <el-input-number v-model="settings.review_timeout" :min="0.5" :max="600" :step="0.5" />
            </div>
          </div>
        </div>
      </div>

      <div class="card-actions">
        <el-button text @click="reset">恢复默认</el-button>
        <el-button type="primary" :loading="saving" @click="save">保存配置</el-button>
      </div>
    </div>

    <!-- 模块 3：失败记录 -->
    <div class="card">
      <div class="card-head">
        <div>
          <div class="card-title">失败记录</div>
          <div class="card-sub">最近 20 条失败，可查看详情并一键重试</div>
        </div>
        <span v-if="failRate > 0.05" class="warn-tag">⚠️ 失败率偏高</span>
      </div>

      <!-- 工具栏 -->
      <div class="fail-toolbar">
        <el-input
          v-model="kw"
          placeholder="搜索用户 / 合同"
          clearable
          style="width: 220px"
          @input="page = 1"
        />
        <el-select v-model="errFilter" placeholder="错误类型" clearable style="width: 140px" @change="page = 1">
          <el-option label="超时" value="超时" />
          <el-option label="限流" value="限流" />
          <el-option label="解析失败" value="解析失败" />
          <el-option label="鉴权" value="鉴权" />
          <el-option label="其他" value="其他" />
        </el-select>
        <span v-if="kw || errFilter" class="filter-count">{{ filteredFailures.length }} 条</span>
        <div class="spacer"></div>
        <el-button size="small" @click="injectDemo">模拟故障</el-button>
        <el-button size="small" type="danger" plain @click="clearFailures">清理演示数据</el-button>
      </div>

      <el-table
        :data="pagedFailures"
        style="width: 100%"
        stripe
        :row-style="{ height: '52px' }"
        :header-cell-style="{ background: '#f8fafc', color: '#475569', fontWeight: '600', height: '42px' }"
      >
        <el-table-column label="序号" width="70" align="right">
          <template #default="{ $index }">
            <span class="idx">{{ (page - 1) * pageSize + $index + 1 }}</span>
          </template>
        </el-table-column>
        <el-table-column label="用户" width="150">
          <template #default="{ row }">
            <div class="user-cell">
              <span class="avatar">{{ initials(row.username) }}</span>
              <button class="user-link" @click.stop="gotoUser(row.username)">{{ row.username }}</button>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="合同" min-width="240">
          <template #default="{ row }">
            <button class="doc-link" :title="row.filename" @click.stop="openContract(row.filename)">
              <span class="doc-ico">📄</span>
              <span class="doc-name">{{ row.filename }}</span>
            </button>
          </template>
        </el-table-column>
        <el-table-column label="错误原因" min-width="280">
          <template #default="{ row }">
            <span class="err-type" :class="errClass(row.error)">{{ errType(row.error) }}</span>
            <span class="err-text">{{ row.error }}</span>
          </template>
        </el-table-column>
        <el-table-column label="时间" width="130" align="center">
          <template #default="{ row }"><span class="muted">{{ fmt(row.created_at) }}</span></template>
        </el-table-column>
        <el-table-column label="操作" width="150" align="center">
          <template #default="{ row }">
            <el-button link size="small" class="view-btn" @click.stop="showDetail(row)">查看详情</el-button>
            <el-button link size="small" class="retry-btn" @click.stop="retry(row)">重试</el-button>
          </template>
        </el-table-column>
        <template #empty>
          <div class="empty-state">
            <div class="empty-ico">✅</div>
            <div class="empty-title">暂无失败记录，系统运行正常</div>
            <div class="empty-hint">可点击右上角「模拟故障」测试异常处理流程</div>
          </div>
        </template>
      </el-table>

      <div class="pager">
        <span class="pager-info">共 {{ filteredFailures.length }} 条</span>
        <el-pagination
          :current-page="page"
          :page-size="pageSize"
          :page-sizes="[10, 20]"
          :total="filteredFailures.length"
          layout="prev, pager, next, sizes"
          background
          @current-change="(p: number) => (page = p)"
          @size-change="(s: number) => { pageSize = s; page = 1 }"
        />
      </div>
    </div>

    <!-- 错误详情 -->
    <el-dialog v-model="detailVisible" title="错误详情" width="640px">
      <div v-if="detail" class="detail">
        <div class="d-row"><span>合同</span>{{ detail.filename }}</div>
        <div class="d-row"><span>用户</span>{{ detail.username }}</div>
        <div class="d-row"><span>时间</span>{{ fmt(detail.created_at) }}</div>
        <div class="d-row"><span>记录 ID</span>{{ detail.id }}</div>
        <div class="d-row"><span>错误类型</span>
          <span class="err-type" :class="errClass(detail.error)">{{ errType(detail.error) }}</span>
        </div>
        <div class="d-row"><span>完整错误</span></div>
        <pre class="d-error">{{ detail.error || '（无错误信息）' }}</pre>
      </div>
    </el-dialog>

    <!-- 原合同 -->
    <el-dialog v-model="contractVisible" :title="contractName || '合同原文'" width="680px">
      <div v-loading="contractLoading">
        <pre class="contract-text">{{ contractText }}</pre>
      </div>
    </el-dialog>
  </div>
</template>

<style scoped>
.page-title {
  font-weight: 600;
  letter-spacing: 0.5px;
}
/* 卡片壳 */
.card {
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 22px;
  margin-bottom: 16px;
  box-shadow:
    0 1px 2px rgba(15, 23, 42, 0.04),
    0 8px 24px -20px rgba(15, 23, 42, 0.35);
}
.card-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 18px;
}
.card-title {
  font-size: 14px;
  font-weight: 600;
  color: #0f172a;
}
.card-sub {
  font-size: 11.5px;
  color: #94a3b8;
  margin-top: 4px;
}
.card-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 18px;
}
.warn-tag {
  font-size: 11px;
  color: #b45309;
  background: #fffbeb;
  border: 1px solid #fde68a;
  border-radius: 999px;
  padding: 2px 10px;
}
/* 健康检查 */
.health {
  display: grid;
  grid-template-columns: 1.05fr 2fr;
  gap: 16px;
}
.core {
  position: relative;
  border-radius: 12px;
  padding: 24px 22px;
  display: flex;
  flex-direction: column;
  justify-content: center;
  min-height: 170px;
  border: 1px solid;
}
.core.ok {
  background: linear-gradient(150deg, #f0fdf9 0%, #ecfdf5 100%);
  border-color: #a7f3d0;
}
.core.bad {
  background: linear-gradient(150deg, #fef2f2 0%, #fff1f2 100%);
  border-color: #fecaca;
}
.pulse {
  position: absolute;
  top: 18px;
  right: 18px;
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: #10b981;
}
.core.ok .pulse {
  box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.55);
  animation: pulse-ring 2s ease-out infinite;
}
.core.bad .pulse {
  background: #ef4444;
  box-shadow: 0 0 0 0 rgba(239, 68, 68, 0.55);
  animation: pulse-ring 2s ease-out infinite;
}
@keyframes pulse-ring {
  0% {
    box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.45);
  }
  70% {
    box-shadow: 0 0 0 12px rgba(16, 185, 129, 0);
  }
  100% {
    box-shadow: 0 0 0 0 rgba(16, 185, 129, 0);
  }
}
.core-title {
  font-size: 26px;
  font-weight: 800;
  letter-spacing: 1px;
  color: #0f766e;
}
.core.bad .core-title {
  color: #b91c1c;
}
.core-sub {
  font-size: 12.5px;
  color: #64748b;
  margin-top: 8px;
}
.core-services {
  display: flex;
  gap: 14px;
  margin-top: 18px;
  flex-wrap: wrap;
}
.svc {
  font-size: 11.5px;
  color: #475569;
  display: inline-flex;
  align-items: center;
  gap: 6px;
}
.svc i {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  display: inline-block;
}
.svc.ok i {
  background: #10b981;
}
.svc.bad i {
  background: #ef4444;
}
/* 指标 */
.metrics {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 12px;
}
.metric {
  border: 1px solid #eef2f7;
  border-radius: 10px;
  padding: 16px 14px;
  display: flex;
  flex-direction: column;
  justify-content: center;
}
.m-label {
  font-size: 11.5px;
  color: #94a3b8;
}
.m-value {
  font-size: 24px;
  font-weight: 800;
  color: #0f172a;
  line-height: 1.2;
  margin-top: 8px;
  letter-spacing: -0.3px;
}
.m-value.small {
  font-size: 15px;
  font-weight: 600;
}
.m-value.ok {
  color: #10b981;
}
.m-value.bad {
  color: #ef4444;
}
.m-sub {
  font-size: 10.5px;
  color: #94a3b8;
  margin-top: 5px;
}
.m-sub.ok {
  color: #059669;
}
.m-sub.bad {
  color: #dc2626;
}
.m-sub.muted {
  color: #b6c0cc;
}
/* 环形 */
.ring-metric {
  position: relative;
  align-items: center;
  padding: 8px;
}
.ring {
  width: 86px;
  height: 86px;
  transform: rotate(-90deg);
}
.ring-bg {
  fill: none;
  stroke: #f1f5f9;
  stroke-width: 7;
}
.ring-fg {
  fill: none;
  stroke: #14b8a6;
  stroke-width: 7;
  stroke-linecap: round;
  transition: stroke-dasharray 0.6s ease;
}
.ring-center {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}
.ring-center .m-value {
  font-size: 16px;
  margin: 0;
}
.ring-center .m-label {
  margin-top: 2px;
}
/* 配置表单 */
.cfg-section {
  margin-bottom: 18px;
}
.section-title {
  font-size: 12px;
  font-weight: 600;
  color: #334155;
  letter-spacing: 0.5px;
  padding-bottom: 10px;
  border-bottom: 1px solid #eef2f7;
  margin-bottom: 2px;
}
.cfg-rows {
  display: flex;
  flex-direction: column;
}
.cfg-row {
  display: grid;
  grid-template-columns: 1fr 200px;
  gap: 24px;
  align-items: center;
  padding: 16px 0;
  border-bottom: 1px solid #f6f8fb;
}
.cfg-row:last-child {
  border-bottom: none;
}
.cfg-name {
  font-size: 13px;
  font-weight: 600;
  color: #0f172a;
  display: flex;
  align-items: center;
  gap: 8px;
}
.tech,
.unit {
  font-size: 10.5px;
  color: #64748b;
  background: #f1f5f9;
  border-radius: 4px;
  padding: 1px 6px;
  font-weight: 500;
}
.help {
  width: 15px;
  height: 15px;
  border-radius: 50%;
  border: 1px solid #cbd5e1;
  color: #94a3b8;
  font-size: 10px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: help;
  transition: all 0.15s;
}
.help:hover {
  border-color: #14b8a6;
  color: #0f766e;
  background: #f0fdfa;
}
.cfg-tip {
  font-size: 11.5px;
  color: #94a3b8;
  margin-top: 6px;
  line-height: 1.6;
}
.cfg-control {
  display: flex;
  justify-content: flex-end;
}
.cfg-note {
  font-size: 11px;
  color: #94a3b8;
  background: #f8fafc;
  border: 1px solid #eef2f7;
  border-radius: 8px;
  padding: 8px 12px;
  margin-top: 12px;
}
/* 失败记录 */
.idx {
  color: #94a3b8;
  font-size: 12px;
}
.fail-toolbar {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 14px;
  flex-wrap: wrap;
}
.spacer {
  flex: 1;
}
.filter-count {
  font-size: 12px;
  color: #0f766e;
  background: #f0fdfa;
  border: 1px solid #99f6e4;
  border-radius: 999px;
  padding: 2px 10px;
}
.user-cell {
  display: flex;
  align-items: center;
  gap: 9px;
}
.avatar {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: #fee2e2;
  color: #b91c1c;
  font-size: 10.5px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.user-link {
  background: none;
  border: none;
  padding: 0;
  font-size: 12.5px;
  color: #0f172a;
  cursor: pointer;
  border-bottom: 1px dashed transparent;
}
.user-link:hover {
  color: #0d9488;
  border-bottom-color: #5eead4;
}
.doc-link {
  display: flex;
  align-items: center;
  gap: 7px;
  background: none;
  border: none;
  padding: 0;
  cursor: pointer;
  max-width: 100%;
  text-align: left;
}
.doc-ico {
  font-size: 13px;
  opacity: 0.85;
  flex-shrink: 0;
}
.doc-name {
  color: #0f172a;
  font-size: 12.5px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 230px;
}
.doc-link:hover .doc-name {
  color: #0d9488;
  text-decoration: underline;
}
/* 空状态 */
.empty-state {
  padding: 34px 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}
.empty-ico {
  width: 44px;
  height: 44px;
  border-radius: 50%;
  background: #ecfdf5;
  border: 1px solid #a7f3d0;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  margin-bottom: 4px;
}
.empty-title {
  font-size: 13px;
  font-weight: 600;
  color: #0f766e;
}
.empty-hint {
  font-size: 11.5px;
  color: #94a3b8;
}
.pager {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 14px;
}
.pager-info {
  font-size: 12px;
  color: #94a3b8;
}
.contract-text {
  background: #f8fafc;
  border: 1px solid #eef2f7;
  border-radius: 8px;
  padding: 16px;
  font-size: 12.5px;
  line-height: 1.9;
  color: #334155;
  white-space: pre-wrap;
  word-break: break-word;
  max-height: 60vh;
  overflow: auto;
  margin: 0;
}
:deep(.el-table) {
  --el-table-row-hover-bg-color: #f0fdfa;
  --el-table-border-color: #eef2f7;
  font-size: 12.5px;
}
:deep(.el-table th.el-table__cell) {
  background: #f8fafc !important;
  color: #475569;
  font-weight: 600;
  border-bottom: 1px solid #e2e8f0;
}
:deep(.el-table__body tr.el-table__row--striped td.el-table__cell) {
  background: #fbfcfd;
}
:deep(.el-table__body tr:hover > td.el-table__cell) {
  background: #f0fdfa !important;
}
:deep(.el-table td.el-table__cell) {
  padding: 0;
}
:deep(.el-table .cell) {
  line-height: 48px;
}
.err-type {
  font-size: 10.5px;
  padding: 1px 7px;
  border-radius: 999px;
  margin-right: 8px;
  font-weight: 600;
}
.err-type.warn {
  color: #b45309;
  background: #fffbeb;
  border: 1px solid #fde68a;
}
.err-type.bad {
  color: #b91c1c;
  background: #fef2f2;
  border: 1px solid #fecaca;
}
.err-type.muted {
  color: #64748b;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
}
.err-text {
  color: #475569;
  font-size: 12px;
}
.muted {
  color: #94a3b8;
  font-size: 12px;
}
.view-btn {
  color: #0d9488;
}
.retry-btn {
  color: #b45309;
}
.empty-line {
  font-size: 12px;
  color: #cbd5e1;
  padding: 14px 0;
}
/* 演示工具 */
.demo-tools {
  margin-top: 18px;
  border: 1px dashed #fecaca;
  background: #fffcfc;
  border-radius: 10px;
  padding: 14px 16px;
}
.demo-label {
  font-size: 11px;
  letter-spacing: 1.5px;
  color: #b45309;
  margin-bottom: 6px;
}
.demo-desc {
  font-size: 11.5px;
  color: #94a3b8;
  line-height: 1.7;
}
.demo-actions {
  display: flex;
  gap: 8px;
  margin-top: 10px;
}
/* 详情 */
.detail .d-row {
  display: flex;
  gap: 12px;
  padding: 8px 0;
  font-size: 13px;
  color: #334155;
  border-bottom: 1px solid #f8fafc;
}
.detail .d-row span {
  width: 48px;
  color: #94a3b8;
  flex-shrink: 0;
}
.d-error {
  background: #f8fafc;
  border: 1px solid #eef2f7;
  border-radius: 8px;
  padding: 12px;
  font-size: 12px;
  color: #b91c1c;
  white-space: pre-wrap;
  word-break: break-all;
  max-height: 240px;
  overflow: auto;
  margin: 0;
}
@media (max-width: 1280px) {
  .health {
    grid-template-columns: 1fr;
  }
  .metrics {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>
