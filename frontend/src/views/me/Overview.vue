<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Document, WarningFilled, Warning, CircleCheck } from '@element-plus/icons-vue'
import * as echarts from 'echarts/core'
import { BarChart } from 'echarts/charts'
import { GridComponent, TooltipComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import api from '../../api'

echarts.use([GridComponent, TooltipComponent, BarChart, CanvasRenderer])

const stats = ref<any>(null)

// 低饱和分类色（与模板库分类 tag 对应）
const CAT_COLOR: Record<string, string> = {
  买卖: '#e8b977',
  建设: '#8fb2e8',
  租赁: '#8fd0ab',
  承揽: '#b3a3e8',
  服务: '#7fcbc1',
  其他: '#bcc3cd',
  示例: '#e3cb84',
  自定义: '#e2a3c0',
}
const catColor = (c: string) => CAT_COLOR[c] || CAT_COLOR['其他']

const riskTotal = computed(() => {
  const s = stats.value
  if (!s) return 1
  return Math.max(1, (s.high || 0) + (s.mid || 0) + (s.low || 0))
})

const kpis = computed(() => {
  const s = stats.value || {}
  return [
    { label: '审查次数', value: s.total ?? 0, bg: '#f7f8fa', color: '#64748b', icon: Document },
    { label: '高风险条款', value: s.high ?? 0, bg: '#fff2f0', color: '#d9736a', icon: WarningFilled },
    { label: '中风险条款', value: s.mid ?? 0, bg: '#fffbe6', color: '#c9a13a', icon: Warning },
    { label: '低风险条款', value: s.low ?? 0, bg: '#f0f9ff', color: '#4aa882', icon: CircleCheck },
  ]
})

const maxHigh = computed(() => {
  const all = (stats.value?.type_profiles || []).flatMap((t: any) => t.top_clauses || [])
  return Math.max(1, ...all.map((c: any) => c.high as number))
})
function clauseWidth(c: any) {
  if (!c.high) return '2%'
  return Math.max(6, (c.high / maxHigh.value) * 100) + '%'
}

// ===== ECharts：合同类型分布 =====
const catEl = ref<HTMLElement | null>(null)
let catChart: echarts.ECharts | null = null

function renderCat() {
  if (!catEl.value) return
  catChart = catChart || echarts.init(catEl.value)
  const list = (stats.value?.by_category || []).slice(0, 8)
  if (!list.length) {
    catChart.clear()
    return
  }
  const rows = list.slice().reverse()
  catChart.setOption(
    {
      grid: { left: 64, right: 36, top: 8, bottom: 16 },
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'shadow' },
        backgroundColor: 'rgba(20,22,26,.92)',
        borderWidth: 0,
        textStyle: { color: '#f1f5f9', fontSize: 12 },
        formatter: (ps: any) => `${ps[0].name}<br/>审查 <b>${ps[0].value}</b> 次`,
      },
      xAxis: {
        type: 'value',
        minInterval: 1,
        splitLine: { lineStyle: { color: '#f4f2ec' } },
        axisLabel: { color: '#b3b0a8', fontSize: 10 },
      },
      yAxis: {
        type: 'category',
        data: rows.map((c: any) => c.name),
        axisLine: { show: false },
        axisTick: { show: false },
        axisLabel: { color: '#6b6f76', fontSize: 11.5 },
      },
      series: [
        {
          type: 'bar',
          barWidth: 13,
          data: rows.map((c: any) => ({
            value: c.count,
            itemStyle: { color: catColor(c.name), borderRadius: [0, 7, 7, 0] },
          })),
          label: { show: true, position: 'right', color: '#8a867d', fontSize: 11 },
          animationDuration: 600,
          animationEasing: 'cubicOut',
        },
      ],
    },
    true
  )
}

function onResize() {
  catChart?.resize()
}

onMounted(async () => {
  try {
    const { data } = await api.get('/me/stats')
    stats.value = data
  } catch {
    ElMessage.error('加载失败')
  }
  await nextTick()
  renderCat()
  window.addEventListener('resize', onResize)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', onResize)
  catChart?.dispose()
})
</script>

<template>
  <div class="page">
    <div class="page-head">
      <div class="page-icon">
        <svg viewBox="0 0 24 24" fill="none" stroke="#14161a" stroke-width="1.3">
          <path d="M4 19.5V10M9.3 19.5V5.5M14.7 19.5V13M20 19.5V8" stroke-linecap="round" />
        </svg>
      </div>
      <div>
        <h1 class="page-title">概览</h1>
        <p class="page-sub">个人审查数据汇总 · 系统自动统计</p>
      </div>
    </div>

    <!-- 卡片 A：审查指标汇总 -->
    <section class="panel">
      <div class="panel-title">审查指标汇总</div>
      <div class="kpis">
        <div v-for="k in kpis" :key="k.label" class="kpi" :style="{ background: k.bg }">
          <el-icon class="kpi-ico" :style="{ color: k.color }"><component :is="k.icon" /></el-icon>
          <div class="kpi-num" :style="{ color: k.color }">{{ k.value }}</div>
          <div class="kpi-label">{{ k.label }}</div>
        </div>
      </div>
    </section>

    <!-- 卡片 B：合同类型 & 风险分布 -->
    <section class="panel">
      <div class="panel-title">合同类型 &amp; 风险分布</div>

      <div v-if="stats?.by_category?.length" ref="catEl" class="chart"></div>
      <div v-else class="empty-line">还没有审查记录，去「合同审查」试试</div>

      <div class="risk-block">
        <div class="risk-head">
          <span>风险构成</span>
          <span class="risk-total">共 {{ riskTotal }} 条判定</span>
        </div>
        <div class="risk-bar">
          <el-tooltip v-if="stats?.high" :content="`高风险 ${stats.high} 条`" placement="top">
            <i class="seg high" :style="{ width: ((stats?.high || 0) / riskTotal) * 100 + '%' }"></i>
          </el-tooltip>
          <el-tooltip v-if="stats?.mid" :content="`中风险 ${stats.mid} 条`" placement="top">
            <i class="seg mid" :style="{ width: ((stats?.mid || 0) / riskTotal) * 100 + '%' }"></i>
          </el-tooltip>
          <el-tooltip v-if="stats?.low" :content="`低风险 ${stats.low} 条`" placement="top">
            <i class="seg low" :style="{ width: ((stats?.low || 0) / riskTotal) * 100 + '%' }"></i>
          </el-tooltip>
          <span v-if="!stats?.high && !stats?.mid && !stats?.low" class="seg none"></span>
        </div>
        <div class="risk-legend">
          <span><i class="dot high"></i>高风险 <b>{{ stats?.high ?? 0 }}</b></span>
          <span><i class="dot mid"></i>中风险 <b>{{ stats?.mid ?? 0 }}</b></span>
          <span><i class="dot low"></i>低风险 <b>{{ stats?.low ?? 0 }}</b></span>
        </div>
      </div>
    </section>

    <!-- 卡片 C：分类型风险画像 -->
    <section class="panel">
      <div class="panel-title">分类型风险画像</div>

      <div v-if="stats?.type_profiles?.length" class="type-list">
        <div v-for="t in stats.type_profiles" :key="t.type" class="type-block">
          <div class="type-head">
            <span
              class="type-tag"
              :style="{
                color: catColor(t.type),
                borderColor: catColor(t.type) + '66',
                background: catColor(t.type) + '14',
              }"
            >
              {{ t.type }}
            </span>
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
          <div v-else class="empty-line small">该类型暂无判定明细</div>
        </div>
      </div>
      <div v-else class="empty-line">审查记录还不够，先多审几份合同</div>
    </section>
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
/* 卡片容器 */
.panel {
  background: #fff;
  border: 1px solid #eae6de;
  border-radius: 12px;
  padding: 20px 22px;
  margin-bottom: 16px;
}
.panel-title {
  font-size: 13px;
  font-weight: 600;
  color: #14161a;
  letter-spacing: 0.5px;
  margin-bottom: 16px;
}
/* 指标卡 */
.kpis {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 14px;
}
.kpi {
  border-radius: 10px;
  padding: 16px 16px 14px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  transition:
    transform 0.25s ease,
    box-shadow 0.25s ease;
  cursor: default;
}
.kpi:hover {
  transform: translateY(-2px);
  box-shadow:
    0 2px 4px rgba(15, 23, 42, 0.03),
    0 14px 28px -22px rgba(15, 23, 42, 0.4);
}
.kpi-ico {
  font-size: 15px;
  opacity: 0.9;
}
.kpi-num {
  font-size: 26px;
  font-weight: 800;
  line-height: 1;
  letter-spacing: -0.3px;
}
.kpi-label {
  font-size: 11.5px;
  color: #6b6f76;
}
/* 图表 */
.chart {
  height: 200px;
  width: 100%;
}
/* 风险条 */
.risk-block {
  margin-top: 18px;
  border-top: 1px solid #f4f2ec;
  padding-top: 16px;
}
.risk-head {
  display: flex;
  justify-content: space-between;
  font-size: 11.5px;
  color: #8a867d;
  margin-bottom: 10px;
}
.risk-total {
  color: #b3b0a8;
}
.risk-bar {
  display: flex;
  height: 9px;
  border-radius: 999px;
  overflow: hidden;
  background: #f4f2ec;
}
.seg {
  display: block;
  height: 100%;
}
.seg + .seg {
  margin-left: 2px;
}
.seg.high {
  background: #e0a19a;
}
.seg.mid {
  background: #e6cc9c;
}
.seg.low {
  background: #a9cfba;
}
.seg.none {
  width: 100%;
  background: #f0eee8;
}
.risk-legend {
  display: flex;
  gap: 22px;
  margin-top: 12px;
  font-size: 11.5px;
  color: #6b6f76;
}
.risk-legend span {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}
.risk-legend b {
  color: #14161a;
  font-weight: 600;
}
.dot {
  width: 8px;
  height: 8px;
  border-radius: 2px;
  display: inline-block;
}
.dot.high {
  background: #e0a19a;
}
.dot.mid {
  background: #e6cc9c;
}
.dot.low {
  background: #a9cfba;
}
/* 风险画像 */
.type-list {
  display: flex;
  flex-direction: column;
}
.type-block {
  padding: 14px 0;
  border-bottom: 1px solid #f6f4ef;
}
.type-block:last-child {
  border-bottom: none;
  padding-bottom: 0;
}
.type-block:first-child {
  padding-top: 0;
}
.type-head {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 12px;
}
.type-tag {
  font-size: 11px;
  padding: 2px 10px;
  border-radius: 999px;
  border: 1px solid;
  font-weight: 500;
}
.type-meta {
  font-size: 11px;
  color: #a8a29a;
}
.clause-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.clause-row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 5px 8px;
  margin: 0 -8px;
  border-radius: 8px;
  font-size: 12.5px;
  transition: background 0.18s;
}
.clause-row:hover {
  background: #fbfaf6;
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
  background: #f4f2ec;
  border-radius: 999px;
  overflow: hidden;
}
.cfill {
  height: 100%;
  background: #e0a19a;
  border-radius: 999px;
}
.ccnt {
  font-size: 11.5px;
  color: #8a867d;
  flex-shrink: 0;
}
.ccnt em {
  font-style: normal;
  font-size: 10px;
  color: #b3b0a8;
  margin-left: 1px;
}
.empty-line {
  font-size: 12.5px;
  color: #b3b0a8;
  padding: 14px 0;
}
.empty-line.small {
  font-size: 11.5px;
  padding: 4px 0;
}
@media (max-width: 900px) {
  .kpis {
    grid-template-columns: repeat(2, 1fr);
  }
  .ctrack {
    flex: 1;
    width: auto;
  }
}
</style>
