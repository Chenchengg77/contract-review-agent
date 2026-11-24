<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import api from '../../api'

const stats = ref<any>(null)

onMounted(async () => {
  try {
    const { data } = await api.get('/me/stats')
    stats.value = data
  } catch {
    ElMessage.error('加载失败')
  }
})

const catMax = computed(() =>
  Math.max(1, ...((stats.value?.by_category || []).map((c: any) => c.count) as number[]))
)

const topCategory = computed(() => {
  const cats = stats.value?.by_category || []
  return cats.length ? cats[0] : null
})

const riskTotal = computed(() => {
  const s = stats.value
  if (!s) return 1
  return Math.max(1, s.high + s.mid + s.low)
})

// 风险画像：按合同类型分组
const maxHigh = computed(() => {
  const all = (stats.value?.type_profiles || []).flatMap((t: any) => t.top_clauses || [])
  return Math.max(1, ...all.map((c: any) => c.high as number))
})
function clauseWidth(c: any) {
  return Math.max(6, (c.high / maxHigh.value) * 100) + '%'
}
</script>

<template>
  <div class="page">
    <div class="page-head">
      <div class="page-icon" style="background: #ecfdf5; color: #059669">📊</div>
      <div>
        <h1 class="page-title">概览</h1>
        <p class="page-sub">你的审查数据（系统自动汇总）</p>
      </div>
    </div>

    <div class="card">
      <div class="mini-stats">
        <div class="mini">
          <div class="mini-num">{{ stats?.total ?? 0 }}</div>
          <div class="mini-label">审查次数</div>
        </div>
        <div class="mini">
          <div class="mini-num" style="color: #dc2626">{{ stats?.high ?? 0 }}</div>
          <div class="mini-label">高风险条款</div>
        </div>
        <div class="mini">
          <div class="mini-num" style="color: #d97706">{{ stats?.mid ?? 0 }}</div>
          <div class="mini-label">中风险条款</div>
        </div>
        <div class="mini">
          <div class="mini-num" style="color: #16a34a">{{ stats?.low ?? 0 }}</div>
          <div class="mini-label">低风险条款</div>
        </div>
      </div>

      <div class="sub-title">
        审查类型分布
        <span v-if="topCategory" class="top-tag">最常审：{{ topCategory.name }}（{{ topCategory.count }} 次）</span>
      </div>
      <div v-if="stats?.by_category?.length" class="cat-list">
        <div v-for="c in stats.by_category" :key="c.name" class="cat-row">
          <span class="cat-name">{{ c.name }}</span>
          <div class="cat-track">
            <div class="cat-fill" :style="{ width: (c.count / catMax) * 100 + '%' }"></div>
          </div>
          <span class="cat-count">{{ c.count }}</span>
        </div>
      </div>
      <div v-else class="empty-line">还没有审查记录，去「合同审查」试试</div>

      <div class="sub-title" style="margin-top: 20px">风险分布</div>
      <div class="risk-bar">
        <div class="seg" :style="{ width: ((stats?.high || 0) / riskTotal) * 100 + '%', background: '#dc2626' }"></div>
        <div class="seg" :style="{ width: ((stats?.mid || 0) / riskTotal) * 100 + '%', background: '#d97706' }"></div>
        <div class="seg" :style="{ width: ((stats?.low || 0) / riskTotal) * 100 + '%', background: '#16a34a' }"></div>
      </div>
    </div>

    <!-- 风险画像（按合同类型） -->
    <div class="card" style="margin-top: 16px">
      <div class="card-title">风险画像 · 按合同类型</div>
      <div v-if="stats?.type_profiles?.length">
        <div v-for="t in stats.type_profiles" :key="t.type" class="type-block">
          <div class="type-head">
            <span class="type-name">{{ t.type }}</span>
            <span class="type-meta">{{ t.reviews }} 次审查</span>
          </div>
          <div v-if="t.top_clauses.length" class="clause-list">
            <div v-for="(c, i) in t.top_clauses" :key="c.clause" class="clause-row">
              <span class="rank">{{ i + 1 }}</span>
              <span class="cname">{{ c.clause }}</span>
              <div class="ctrack">
                <div class="cfill" :style="{ width: clauseWidth(c) }"></div>
              </div>
              <span class="ccnt">{{ c.high }} 高 / {{ c.mid }} 中</span>
            </div>
          </div>
          <div v-else class="empty-line">该类型暂无判定明细</div>
        </div>
      </div>
      <div v-else class="empty-line">审查记录还不够，先多审几份合同</div>
    </div>
  </div>
</template>

<style scoped>
.card {
  background: #fff;
  border: 1px solid #e8edf5;
  border-radius: 16px;
  padding: 22px;
}
.card-title {
  font-size: 14px;
  font-weight: 600;
  color: #0f172a;
  margin-bottom: 16px;
}
.clause-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.type-block {
  padding: 14px 0;
  border-bottom: 1px dashed #eef2f7;
}
.type-block:last-child {
  border-bottom: none;
  padding-bottom: 0;
}
.type-head {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 10px;
}
.type-name {
  font-size: 13px;
  font-weight: 600;
  color: #0f172a;
}
.type-meta {
  font-size: 11px;
  color: #94a3b8;
}
.clause-row {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 12.5px;
}
.rank {
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: #f1f5f9;
  color: #64748b;
  font-size: 11px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.cname {
  width: 84px;
  color: #334155;
  flex-shrink: 0;
}
.ctrack {
  flex: 1;
  height: 9px;
  background: #f1f5f9;
  border-radius: 999px;
  overflow: hidden;
}
.cfill {
  height: 100%;
  background: linear-gradient(90deg, #f87171, #dc2626);
  border-radius: 999px;
}
.ccnt {
  width: 78px;
  text-align: right;
  color: #94a3b8;
  flex-shrink: 0;
}
.mini-stats {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
  margin-bottom: 22px;
}
.mini {
  background: #f8fafc;
  border: 1px solid #eef2f7;
  border-radius: 12px;
  padding: 14px;
  text-align: center;
}
.mini-num {
  font-size: 22px;
  font-weight: 800;
  color: #0f172a;
}
.mini-label {
  font-size: 11px;
  color: #94a3b8;
  margin-top: 2px;
}
.sub-title {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 12px;
  font-weight: 600;
  color: #475569;
  margin: 0 0 10px;
}
.top-tag {
  font-size: 11px;
  font-weight: 500;
  color: #047857;
  background: #ecfdf5;
  border: 1px solid #a7f3d0;
  border-radius: 999px;
  padding: 2px 10px;
}
.risk-bar {
  display: flex;
  height: 12px;
  border-radius: 999px;
  overflow: hidden;
  background: #f1f5f9;
}
.seg {
  height: 100%;
}
.cat-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.cat-row {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 12px;
}
.cat-name {
  width: 48px;
  color: #64748b;
  flex-shrink: 0;
}
.cat-track {
  flex: 1;
  height: 8px;
  background: #f1f5f9;
  border-radius: 999px;
  overflow: hidden;
}
.cat-fill {
  height: 100%;
  background: linear-gradient(90deg, #34d399, #10b981);
  border-radius: 999px;
}
.cat-count {
  width: 28px;
  text-align: right;
  color: #94a3b8;
}
.empty-line {
  font-size: 12px;
  color: #cbd5e1;
  padding: 8px 0;
}
@media (max-width: 900px) {
  .mini-stats {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>
