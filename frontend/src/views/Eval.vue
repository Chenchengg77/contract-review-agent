<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import api from '../api'

const summary = ref<any>(null)
const before = ref<any>(null)
const cases = ref<any[]>([])
const qaCases = ref<any[]>([])
const per = ref<any[]>([])

onMounted(async () => {
  try {
    const { data } = await api.get('/eval')
    summary.value = data.summary
    before.value = data.before
    cases.value = data.cases || []
    qaCases.value = data.qa_cases || []
    per.value = data.per_contract || []
  } catch {
    /* ignore */
  }
})

const pct = (v: number | undefined | null) => (v == null ? '-' : (v * 100).toFixed(2) + '%')

/** AI 助手能力清单（一张表，面试时快速过） */
const abilities = [
  { name: '前置拦截', how: '检索阈值 + 意图分类（Guardrails）', effect: '越界问题拒答；阈值命中零成本' },
  { name: '审查上下文', how: '注入最近一次审查摘要', effect: '能回答「哪条高风险」' },
  { name: '人设语气', how: 'system prompt 人设 + 语气规则', effect: '更像法务顾问，避免机器人腔' },
  { name: '主动追问', how: '审查完成后模板文案', effect: '引导用户继续提问' },
  { name: '记住用户', how: '/me/stats 最近记录', effect: '默认上次审查的合同' },
]

const delta = (a: number | undefined, b: number | undefined) => {
  if (a == null || b == null) return '-'
  const d = (b - a) * 100
  return (d >= 0 ? '+' : '') + d.toFixed(2) + '%'
}

const metrics = computed(() => {
  const s = summary.value
  if (!s) return [] as { label: string; value: string }[]
  const out: { label: string; value: string }[] = []
  const push = (label: string, value: any) => out.push({ label, value: String(value) })
  if (s.version != null) push('评估版本', 'v' + s.version)
  if (s.contracts != null) push('合同数', s.contracts)
  if (s.extraction) {
    push('抽取准确率', pct(s.extraction.accuracy))
    push('抽取精确率', pct(s.extraction.precision))
    push('抽取召回率', pct(s.extraction.recall))
    push('抽取 F1', pct(s.extraction.f1))
  }
  if (s.judgment) {
    push('判定准确率', pct(s.judgment.verdict_accuracy))
    push('严重度准确率', pct(s.judgment.severity_accuracy))
  }
  if (s.total_tokens != null) push('总 tokens', s.total_tokens)
  if (s.total_seconds != null) push('总耗时', s.total_seconds + ' s')
  if (s.failed != null) push('失败数', Array.isArray(s.failed) ? s.failed.length : s.failed)
  return out
})
</script>

<template>
  <div class="page">
    <div class="page-head">
      <div class="page-icon" style="background: #ecfeff; color: #0891b2">📊</div>
      <div>
        <h1 class="page-title">评估数据</h1>
        <p class="page-sub">31 份合同 / 403 条金标的抽取与判定指标（来自离线评测）。</p>
      </div>
    </div>

    <!-- 版本对比 -->
    <div v-if="before && summary" class="compare">
      <div class="compare-title">
        版本对比：修复「条款正文只取到标题」前后
        <span class="compare-sub">真实评测数据</span>
      </div>

      <div class="ctable">
        <div class="ct-row ct-head">
          <span>指标</span><span>修复前</span><span>修复后</span><span>变化</span>
        </div>
        <div class="ct-row">
          <span>判定准确率</span>
          <span class="old">{{ pct(before.judgment?.verdict_accuracy) }}</span>
          <span class="new">{{ pct(summary.judgment?.verdict_accuracy) }}</span>
          <span class="delta">{{ delta(before.judgment?.verdict_accuracy, summary.judgment?.verdict_accuracy) }}</span>
        </div>
        <div class="ct-row">
          <span>严重度准确率</span>
          <span class="old">{{ pct(before.judgment?.severity_accuracy) }}</span>
          <span class="new">{{ pct(summary.judgment?.severity_accuracy) }}</span>
          <span class="delta">{{ delta(before.judgment?.severity_accuracy, summary.judgment?.severity_accuracy) }}</span>
        </div>
      </div>

      <div v-for="c in cases" :key="c.clause" class="case">
        <div class="case-head">{{ c.contract }} · {{ c.clause }}</div>
        <div class="case-cols">
          <div class="case-col old-col">
            <div class="col-title">修复前</div>
            <div class="verdict">{{ c.before.verdict }}（{{ c.before.severity }}）</div>
            <div class="reason">{{ c.before.reason }}</div>
          </div>
          <div class="case-col new-col">
            <div class="col-title">修复后</div>
            <div class="verdict">{{ c.after.verdict }}（{{ c.after.severity }}）</div>
            <div class="reason">{{ c.after.reason }}</div>
          </div>
        </div>
        <div class="cause">原因：{{ c.root_cause }}</div>
      </div>
    </div>

    <!-- AI 助手前置拦截对比 -->
    <div v-if="qaCases.length" class="compare">
      <div class="compare-title">
        AI 助手：前置拦截（Guardrails）前后对比
        <span class="compare-sub">真实数据</span>
      </div>

      <div v-for="c in qaCases" :key="c.question" class="case">
        <div class="case-head">问题：{{ c.question }}</div>
        <div class="case-cols">
          <div class="case-col old-col">
            <div class="col-title">改前（prompt 兜底）</div>
            <div class="verdict">照常调 LLM</div>
            <div class="reason">{{ c.before.answer }}</div>
            <div class="meta">{{ c.before.cost }}<br />{{ c.before.why }}</div>
          </div>
          <div class="case-col new-col">
            <div class="col-title">改后（前置拦截）</div>
            <div class="verdict">拒绝回答</div>
            <div class="reason">{{ c.after.answer }}</div>
            <div class="meta">{{ c.after.cost }}<br />{{ c.after.why }}</div>
          </div>
        </div>
      </div>
    </div>

    <!-- AI 助手能力 -->
    <div class="compare">
      <div class="compare-title">AI 助手能力</div>
      <div class="ctable">
        <div class="ct-row ability ability-head">
          <span>能力</span><span>实现方式</span><span>效果</span>
        </div>
        <div v-for="a in abilities" :key="a.name" class="ct-row ability">
          <span class="new">{{ a.name }}</span>
          <span>{{ a.how }}</span>
          <span>{{ a.effect }}</span>
        </div>
      </div>
    </div>

    <div v-if="metrics.length" class="stats">
      <div v-for="m in metrics" :key="m.label" class="stat">
        <div class="num">{{ m.value }}</div>
        <div class="label">{{ m.label }}</div>
      </div>
    </div>
    <div v-else class="empty">暂无评估数据</div>

    <el-card v-if="per.length" shadow="never" class="card">
      <div class="card-title">逐份合同</div>
      <el-table :data="per" style="width: 100%" max-height="520">
        <el-table-column prop="file" label="合同" min-width="260" show-overflow-tooltip />
        <el-table-column label="抽取准确率" width="120">
          <template #default="{ row }">{{ pct(row.accuracy_rate) }}</template>
        </el-table-column>
        <el-table-column label="判定准确率" width="120">
          <template #default="{ row }">{{ pct(row.verdict_accuracy) }}</template>
        </el-table-column>
        <el-table-column label="严重度准确率" width="130">
          <template #default="{ row }">{{ pct(row.severity_accuracy) }}</template>
        </el-table-column>
        <el-table-column prop="tokens" label="tokens" width="100" />
        <el-table-column label="耗时" width="90">
          <template #default="{ row }">{{ row.seconds }}s</template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<style scoped>
.compare {
  background: #fff;
  border: 1px solid #e8edf5;
  border-radius: 16px;
  padding: 22px;
  margin-bottom: 16px;
}
.compare-title {
  font-size: 14px;
  font-weight: 700;
  color: #0f172a;
  margin-bottom: 14px;
  display: flex;
  align-items: center;
  gap: 10px;
}
.compare-sub {
  font-size: 11px;
  font-weight: 500;
  color: #0891b2;
  background: #ecfeff;
  border: 1px solid #a5f3fc;
  border-radius: 999px;
  padding: 2px 10px;
}
.ctable {
  border: 1px solid #eef2f7;
  border-radius: 12px;
  overflow: hidden;
  margin-bottom: 18px;
}
.ct-row {
  display: grid;
  grid-template-columns: 1.4fr 1fr 1fr 1fr;
  padding: 10px 14px;
  font-size: 13px;
  color: #334155;
  border-bottom: 1px solid #f1f5f9;
}
.ct-row:last-child {
  border-bottom: none;
}
.ct-head {
  background: #f8fafc;
  font-size: 12px;
  color: #64748b;
  font-weight: 500;
}
.ct-row.ability {
  grid-template-columns: 0.9fr 1.5fr 1.6fr;
}
.ability-head {
  font-size: 12px;
  color: #64748b;
}
.old {
  color: #94a3b8;
}
.new {
  color: #0f172a;
  font-weight: 600;
}
.delta {
  color: #16a34a;
  font-weight: 700;
}
.case {
  border: 1px solid #eef2f7;
  border-radius: 12px;
  padding: 14px;
  margin-bottom: 12px;
}
.case-head {
  font-size: 13px;
  font-weight: 600;
  color: #0f172a;
  margin-bottom: 10px;
}
.case-cols {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}
.case-col {
  border-radius: 10px;
  padding: 12px;
}
.old-col {
  background: #f8fafc;
  border: 1px solid #eef2f7;
}
.new-col {
  background: #f0fdf4;
  border: 1px solid #bbf7d0;
}
.col-title {
  font-size: 11px;
  color: #94a3b8;
  margin-bottom: 6px;
}
.verdict {
  font-size: 13px;
  font-weight: 600;
  color: #0f172a;
  margin-bottom: 6px;
}
.reason {
  font-size: 12px;
  color: #475569;
  line-height: 1.7;
}
.cause {
  margin-top: 10px;
  font-size: 12px;
  color: #64748b;
  line-height: 1.7;
}
.meta {
  margin-top: 8px;
  font-size: 11px;
  color: #94a3b8;
  line-height: 1.6;
  border-top: 1px dashed #e2e8f0;
  padding-top: 6px;
}
.page {
  max-width: 1120px;
  margin: 0 auto;
  padding: 32px;
}
h1 {
  margin: 0 0 6px;
  font-size: 24px;
}
.sub {
  color: #64748b;
  font-size: 14px;
  margin: 0 0 20px;
}
.stats {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(170px, 1fr));
  gap: 14px;
  margin-bottom: 20px;
}
.stat {
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 14px;
  padding: 18px;
}
.num {
  font-size: 22px;
  font-weight: 800;
  color: #0f172a;
}
.label {
  font-size: 12px;
  color: #94a3b8;
  margin-top: 4px;
}
.card {
  border-radius: 14px;
  border: 1px solid #e2e8f0;
}
.card-title {
  font-weight: 600;
  margin-bottom: 12px;
}
.empty {
  color: #94a3b8;
  padding: 40px;
  text-align: center;
}
</style>
