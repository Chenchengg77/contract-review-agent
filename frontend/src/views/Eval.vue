<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import api from '../api'

const summary = ref<any>(null)
const per = ref<any[]>([])

onMounted(async () => {
  try {
    const { data } = await api.get('/eval')
    summary.value = data.summary
    per.value = data.per_contract || []
  } catch {
    /* ignore */
  }
})

const pct = (v: number | undefined | null) => (v == null ? '-' : (v * 100).toFixed(2) + '%')

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
