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
  if (!c.high) return '2%'
  return Math.max(6, (c.high / maxHigh.value) * 100) + '%'
}
</script>

<template>
  <div class="page">
    <div class="page-head">
      <div class="page-icon" style="background: #f1ede6; color: #14161a">📊</div>
      <div>
        <h1 class="page-title">概览</h1>
        <p class="page-sub">你的审查数据（系统自动汇总）</p>
      </div>
    </div>

    <!-- 统计 -->
    <div class="stack">
      <div class="card">
        <div class="mini-stats">
        <div class="mini">
          <div class="mini-num">{{ stats?.total ?? 0 }}</div>
          <div class="mini-label">审查次数</div>
        </div>
        <div class="mini">
          <div class="mini-num accent">{{ stats?.high ?? 0 }}</div>
          <div class="mini-label">高风险条款</div>
        </div>
        <div class="mini">
          <div class="mini-num">{{ stats?.mid ?? 0 }}</div>
          <div class="mini-label">中风险条款</div>
        </div>
        <div class="mini">
          <div class="mini-num">{{ stats?.low ?? 0 }}</div>
          <div class="mini-label">低风险条款</div>
        </div>
      </div>

      <div class="sub-title">
        <span>审查类型分布</span>
        <span v-if="topCategory" class="top-tag">最常审 · {{ topCategory.name }}（{{ topCategory.count }} 次）</span>
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

      <div class="sub-title" style="margin-top: 28px">
        <span>风险分布</span>
      </div>
      <div class="risk-bar">
        <div class="seg high" :style="{ width: ((stats?.high || 0) / riskTotal) * 100 + '%' }"></div>
        <div class="seg mid" :style="{ width: ((stats?.mid || 0) / riskTotal) * 100 + '%' }"></div>
        <div class="seg low" :style="{ width: ((stats?.low || 0) / riskTotal) * 100 + '%' }"></div>
      </div>
      <div class="risk-legend">
        <span><i class="dot high"></i>高风险 <b>{{ stats?.high ?? 0 }}</b></span>
        <span><i class="dot mid"></i>中风险 <b>{{ stats?.mid ?? 0 }}</b></span>
        <span><i class="dot low"></i>低风险 <b>{{ stats?.low ?? 0 }}</b></span>
      </div>
    </div>

    <!-- 风险画像 -->
    <div class="card">
      <div class="sub-title" style="margin: 0 0 6px">
        <span>风险画像 · 按合同类型</span>
      </div>
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
              <span class="ccnt">{{ c.high }}<em>高</em> · {{ c.mid }}<em>中</em></span>
            </div>
          </div>
          <div v-else class="empty-line">该类型暂无判定明细</div>
        </div>
      </div>
      <div v-else class="empty-line">审查记录还不够，先多审几份合同</div>
    </div>
    </div>
  </div>
</template>

<style scoped>
.page {
  position: relative;
}
.card {
  background: #fff;
  border: 1px solid #ece7de;
  border-radius: 4px;
  padding: 32px;
  box-shadow: 0 18px 50px -48px rgba(20, 22, 26, 0.5);
  animation: card-in 0.55s cubic-bezier(0.2, 0.7, 0.2, 1) both;
  transition: box-shadow 0.2s ease, transform 0.2s ease;
}
.card:hover {
  transform: translateY(-2px);
  box-shadow: 0 26px 60px -48px rgba(20, 22, 26, 0.6);
}
.card + .card {
  animation-delay: 0.08s;
}
@keyframes card-in {
  from {
    opacity: 0;
    transform: translateY(16px);
  }
  to {
    opacity: 1;
    transform: none;
  }
}
/* 卡片间距 */
.stack {
  display: flex;
  flex-direction: column;
}
.stack .card + .card {
  margin-top: 20px;
}
.mini-stats {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  background: #fbfaf6;
  border: 1px solid #efeae1;
  border-radius: 3px;
  margin-bottom: 32px;
}
.mini {
  padding: 22px 20px;
  border-left: 1px solid #efeae1;
  text-align: center;
}
.mini:first-child {
  border-left: none;
}
.mini-num {
  font-family: 'Noto Serif SC', 'Songti SC', 'SimSun', Georgia, serif;
  font-size: 32px;
  font-weight: 600;
  color: #14161a;
  line-height: 1;
}
.mini-num.accent {
  color: #b4442f;
}
.mini-label {
  font-size: 11.5px;
  color: #8a867d;
  margin-top: 10px;
  letter-spacing: 0.5px;
}
.sub-title {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 11px;
  letter-spacing: 2px;
  color: #8a867d;
  margin-bottom: 16px;
}
.top-tag {
  font-size: 10.5px;
  letter-spacing: 1px;
  color: #1f3fb3;
  border: 1px solid #d9e0f4;
  background: #f4f6fc;
  padding: 2px 9px;
}
.cat-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.cat-row {
  display: flex;
  align-items: center;
  gap: 14px;
  font-size: 12.5px;
}
.cat-name {
  width: 52px;
  color: #4b4f55;
  flex-shrink: 0;
  letter-spacing: 0.5px;
}
.cat-track {
  flex: 1;
  height: 6px;
  background: #f1ede6;
  overflow: hidden;
}
.cat-fill {
  height: 100%;
  background: #14161a;
}
.cat-count {
  width: 28px;
  text-align: right;
  color: #8a867d;
}
.risk-bar {
  display: flex;
  height: 10px;
  overflow: hidden;
  background: #f1ede6;
}
.seg + .seg {
  margin-left: 2px;
}
.seg.high {
  background: #c23b2e;
}
.seg.mid {
  background: #d9a021;
}
.seg.low {
  background: #3f7f5f;
}
.risk-legend {
  display: flex;
  gap: 26px;
  margin-top: 14px;
  font-size: 11.5px;
  color: #6b6f76;
  letter-spacing: 0.4px;
}
.risk-legend span {
  display: inline-flex;
  align-items: center;
  gap: 7px;
}
.risk-legend b {
  color: #14161a;
  font-weight: 600;
}
.dot {
  width: 8px;
  height: 8px;
  display: inline-block;
}
.dot.high {
  background: #c23b2e;
}
.dot.mid {
  background: #d9a021;
}
.dot.low {
  background: #3f7f5f;
}
.type-block {
  padding: 18px 0;
  border-bottom: 1px solid #f1ede6;
}
.type-block:last-child {
  border-bottom: none;
  padding-bottom: 0;
}
.type-head {
  display: flex;
  align-items: baseline;
  gap: 12px;
  margin-bottom: 14px;
}
.type-name {
  font-size: 13.5px;
  font-weight: 600;
  color: #14161a;
  letter-spacing: 0.5px;
}
.type-meta {
  font-size: 11px;
  color: #b3b0a8;
  letter-spacing: 0.5px;
}
.clause-list {
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.clause-row {
  display: flex;
  align-items: center;
  gap: 14px;
  font-size: 12.5px;
}
.rank {
  width: 14px;
  color: #c3bfb6;
  font-size: 10.5px;
  flex-shrink: 0;
}
.cname {
  width: 88px;
  color: #4b4f55;
  flex-shrink: 0;
}
.ctrack {
  width: 200px;
  flex-shrink: 0;
  height: 4px;
  background: #f1ede6;
  overflow: hidden;
}
.cfill {
  height: 100%;
  background: #b4442f;
}
.ccnt {
  font-size: 11.5px;
  color: #8a867d;
  letter-spacing: 0.3px;
  flex-shrink: 0;
}
.ccnt em {
  font-style: normal;
  font-size: 10px;
  color: #b3b0a8;
  margin-left: 1px;
}
.empty-line {
  font-size: 12px;
  color: #b3b0a8;
  padding: 10px 0;
}
@media (max-width: 900px) {
  .mini-stats {
    grid-template-columns: repeat(2, 1fr);
  }
  .mini:nth-child(3) {
    border-left: none;
  }
}
</style>
