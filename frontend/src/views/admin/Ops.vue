<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox, ElNotification } from 'element-plus'
import api from '../../api'

const health = ref<any>(null)
const settings = ref({ guard_on: true, guard_low: 5.0, guard_high: 8.0, review_timeout: 180 })
const failures = ref<any[]>([])
const saving = ref(false)

const detail = ref<any>(null)
const detailVisible = ref(false)

async function load() {
  try {
    const [h, s, f] = await Promise.all([
      api.get('/admin/health'),
      api.get('/admin/settings'),
      api.get('/admin/failures'),
    ])
    health.value = h.data
    settings.value = s.data
    failures.value = f.data.failures || []
  } catch {
    ElMessage.error('加载失败')
  }
}

onMounted(load)

async function save() {
  saving.value = true
  try {
    const { data } = await api.put('/admin/settings', settings.value)
    settings.value = data
    ElMessage.success('配置已保存，立即生效')
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

const failRate = () => {
  const h = health.value
  if (!h || !h.total) return 0
  return h.failed / h.total
}

function fmt(ts: number) {
  return ts ? new Date(ts * 1000).toLocaleString('zh-CN') : '-'
}
</script>

<template>
  <div class="page">
    <div class="page-head">
      <div class="page-icon" style="background: #fff7ed; color: #ea580c">🛠️</div>
      <div>
        <h1 class="page-title">系统运维</h1>
        <p class="page-sub">健康检查 · 运行时配置 · 失败记录与修复</p>
      </div>
    </div>

    <!-- 健康检查 -->
    <div class="card">
      <div class="card-title">
        健康检查
        <span v-if="failRate() > 0.05" class="alert-tag">⚠️ 失败率偏高</span>
      </div>
      <div class="health-grid">
        <div class="h-item">
          <div class="h-num" :style="{ color: health?.db ? '#16a34a' : '#dc2626' }">
            {{ health?.db ? '正常' : '异常' }}
          </div>
          <div class="h-label">数据库</div>
        </div>
        <div class="h-item">
          <div class="h-num">{{ health?.total ?? 0 }}</div>
          <div class="h-label">累计审查</div>
        </div>
        <div class="h-item">
          <div class="h-num" :style="{ color: (health?.failed ?? 0) > 0 ? '#dc2626' : '#16a34a' }">
            {{ health?.failed ?? 0 }}
          </div>
          <div class="h-label">失败次数</div>
        </div>
        <div class="h-item">
          <div
            class="h-num"
            :style="{ color: failRate() > 0.05 ? '#dc2626' : '#0f172a' }"
          >
            {{ ((health?.success_rate ?? 1) * 100).toFixed(1) }}%
          </div>
          <div class="h-label">成功率</div>
        </div>
        <div class="h-item">
          <div class="h-num">{{ health?.avg_duration ?? 0 }}s</div>
          <div class="h-label">平均耗时</div>
        </div>
        <div class="h-item">
          <div class="h-num small">{{ fmt(health?.last_at) }}</div>
          <div class="h-label">最近一次审查</div>
        </div>
      </div>
    </div>

    <!-- 运行时配置 -->
    <div class="card">
      <div class="card-title">
        运行时配置
        <span class="hint">改完立即生效，无需重启</span>
      </div>

      <div class="cfg-row">
        <div class="cfg-item">
          <label>AI 前置拦截（Guardrails）</label>
          <el-switch v-model="settings.guard_on" active-text="开启" inactive-text="关闭" />
          <div class="cfg-tip">关闭后，越界问题也会正常回答（用于对比演示）</div>
        </div>
        <div class="cfg-item">
          <label>检索阈值 · 低（低于此分直接拒答）</label>
          <el-input-number v-model="settings.guard_low" :min="0" :max="30" :step="0.5" />
        </div>
        <div class="cfg-item">
          <label>检索阈值 · 高（高于此分直接放行）</label>
          <el-input-number v-model="settings.guard_high" :min="0" :max="40" :step="0.5" />
        </div>
        <div class="cfg-item">
          <label>审查超时（秒）</label>
          <el-input-number v-model="settings.review_timeout" :min="0.5" :max="600" :step="0.5" />
          <div class="cfg-tip">演示用：改成 0.5 秒可制造**真实超时**故障</div>
        </div>
      </div>

      <div class="btn-row">
        <el-button type="primary" :loading="saving" @click="save">保存配置</el-button>
        <el-button @click="reset">恢复默认</el-button>
      </div>
      <div class="cfg-tip" style="margin-top: 10px">
        灰区（低 ~ 高之间）会调用一次意图分类判断是否越界。
      </div>
    </div>

    <!-- 失败记录 -->
    <div class="card">
      <div class="card-title">
        失败记录（最近 20 条）
        <el-button size="small" plain class="demo-btn" @click="injectDemo">模拟故障（演示用）</el-button>
        <el-button size="small" plain type="danger" @click="clearFailures">清理演示数据</el-button>
      </div>
      <el-table :data="failures" style="width: 100%">
        <el-table-column prop="username" label="用户" width="110" />
        <el-table-column prop="filename" label="合同" min-width="200" show-overflow-tooltip />
        <el-table-column prop="error" label="错误原因" min-width="220" show-overflow-tooltip />
        <el-table-column label="时间" width="180">
          <template #default="{ row }">{{ fmt(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="150">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="showDetail(row)">详情</el-button>
            <el-button link type="warning" size="small" @click="retry(row)">重试</el-button>
          </template>
        </el-table-column>
        <template #empty>
          <div class="empty-line">暂无失败记录 —— 系统运行正常 ✅</div>
        </template>
      </el-table>
    </div>

    <!-- 错误详情 -->
    <el-dialog v-model="detailVisible" title="错误详情" width="620px">
      <div v-if="detail" class="detail">
        <div class="d-row"><span>合同</span>{{ detail.filename }}</div>
        <div class="d-row"><span>用户</span>{{ detail.username }}</div>
        <div class="d-row"><span>时间</span>{{ fmt(detail.created_at) }}</div>
        <div class="d-row"><span>错误</span></div>
        <pre class="d-error">{{ detail.error || '（无错误信息）' }}</pre>
      </div>
    </el-dialog>
  </div>
</template>

<style scoped>
.card {
  background: #fff;
  border: 1px solid #e8edf5;
  border-radius: 16px;
  padding: 22px;
  margin-bottom: 16px;
}
.card-title {
  font-size: 14px;
  font-weight: 600;
  color: #0f172a;
  margin-bottom: 16px;
  display: flex;
  align-items: center;
  gap: 10px;
}
.hint {
  font-size: 11px;
  font-weight: 400;
  color: #94a3b8;
}
.alert-tag {
  font-size: 11px;
  font-weight: 500;
  color: #dc2626;
  background: #fef2f2;
  border: 1px solid #fecaca;
  border-radius: 999px;
  padding: 2px 10px;
}
.demo-btn {
  margin-left: auto;
  font-size: 12px;
}
.health-grid {
  display: grid;
  grid-template-columns: repeat(6, 1fr);
  gap: 12px;
}
.h-item {
  background: #f8fafc;
  border: 1px solid #eef2f7;
  border-radius: 12px;
  padding: 14px;
  text-align: center;
}
.h-num {
  font-size: 20px;
  font-weight: 800;
  color: #0f172a;
}
.h-num.small {
  font-size: 12px;
  font-weight: 600;
  line-height: 1.6;
}
.h-label {
  font-size: 11px;
  color: #94a3b8;
  margin-top: 4px;
}
.cfg-row {
  display: grid;
  grid-template-columns: 1.3fr 1fr 1fr 1fr;
  gap: 18px;
  margin-bottom: 18px;
}
.cfg-item label {
  display: block;
  font-size: 12px;
  color: #64748b;
  margin-bottom: 8px;
}
.cfg-tip {
  font-size: 11px;
  color: #94a3b8;
  margin-top: 6px;
}
.btn-row {
  display: flex;
  gap: 10px;
}
.empty-line {
  color: #94a3b8;
  padding: 24px;
  text-align: center;
  font-size: 13px;
}
.detail {
  font-size: 13px;
  color: #334155;
}
.d-row {
  display: flex;
  gap: 10px;
  padding: 6px 0;
}
.d-row span {
  color: #94a3b8;
  width: 48px;
  flex-shrink: 0;
}
.d-error {
  background: #f8fafc;
  border: 1px solid #eef2f7;
  border-radius: 10px;
  padding: 12px;
  font-size: 12px;
  color: #b91c1c;
  white-space: pre-wrap;
  word-break: break-all;
  margin: 6px 0 0;
}
@media (max-width: 1100px) {
  .health-grid {
    grid-template-columns: repeat(3, 1fr);
  }
  .cfg-row {
    grid-template-columns: 1fr;
  }
}
</style>
