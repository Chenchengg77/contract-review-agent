<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import * as echarts from 'echarts/core'
import { BarChart, LineChart, PieChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, LegendComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import api from '../../api'

echarts.use([GridComponent, TooltipComponent, LegendComponent, BarChart, LineChart, PieChart, CanvasRenderer])

const router = useRouter()
const stats = ref<any>(null)
const health = ref<any>(null)
const allReviews = ref<any[]>([])

const recent = computed(() => allReviews.value.slice(0, 8))

// 近 7 天趋势
const weekTrend = computed(() => {
  const out: { label: string; count: number }[] = []
  const now = new Date()
  for (let i = 6; i >= 0; i--) {
    const d = new Date(now.getFullYear(), now.getMonth(), now.getDate() - i)
    const start = d.getTime() / 1000
    const end = start + 86400
    const count = allReviews.value.filter((r) => r.created_at >= start && r.created_at < end).length
    out.push({ label: `${d.getMonth() + 1}/${d.getDate()}`, count })
  }
  return out
})

// 近 24h vs 前 24h
const trend = computed(() => {
  const now = Date.now() / 1000
  let cur = 0
  let prev = 0
  let curHigh = 0
  let prevHigh = 0
  for (const r of allReviews.value) {
    const t = r.created_at || 0
    if (!t) continue
    if (t > now - 86400) {
      cur += 1
      curHigh += r.high || 0
    } else if (t > now - 172800) {
      prev += 1
      prevHigh += r.high || 0
    }
  }
  return { cur, prev, curHigh, prevHigh }
})

function trendText(cur: number, prev: number) {
  if (!prev) return cur > 0 ? `近24h +${cur}` : '近24h 无'
  const d = ((cur - prev) / prev) * 100
  return `较前日 ${d >= 0 ? '+' : ''}${d.toFixed(0)}%`
}

const riskTotal = computed(() => {
  const s = stats.value || {}
  return Math.max(1, (s.high || 0) + (s.mid || 0) + (s.low || 0))
})
function pctOf(v: number) {
  return ((v / riskTotal.value) * 100).toFixed(1) + '%'
}

const cards = computed(() => {
  const s = stats.value || {}
  const avg = health.value?.avg_duration ?? 0
  return [
    {
      label: '审查总数',
      value: s.total ?? 0,
      core: 'teal',
      sub: '累计审查次数',
      trend: trendText(trend.value.cur, trend.value.prev),
      to: '/admin/reviews',
    },
    {
      label: '高风险条款',
      value: s.high ?? 0,
      core: 'red',
      sub: `占全部条款 ${pctOf(s.high ?? 0)}`,
      trend: trendText(trend.value.curHigh, trend.value.prevHigh),
    },
    { label: '用户数', value: s.users ?? 0, sub: '注册账号', to: '/admin/users' },
    { label: '低风险条款', value: s.low ?? 0, sub: `占 ${pctOf(s.low ?? 0)}` },
    { label: '平均耗时', value: avg ? avg + 's' : '—', sub: '单份审查' },
  ]
})

const catMax = computed(() =>
  Math.max(1, ...((stats.value?.by_category || []).map((c: any) => c.count) as number[]))
)
const userMax = computed(() =>
  Math.max(1, ...((stats.value?.top_users || []).map((u: any) => u.count) as number[]))
)

// ===== ECharts =====
const trendEl = ref<HTMLElement | null>(null)
const catEl = ref<HTMLElement | null>(null)
const riskEl = ref<HTMLElement | null>(null)

let trendChart: echarts.ECharts | null = null
let catChart: echarts.ECharts | null = null
let riskChart: echarts.ECharts | null = null

const GRID = { left: 44, right: 24, top: 24, bottom: 34 }

function renderTrend() {
  if (!trendEl.value) return
  trendChart = trendChart || echarts.init(trendEl.value)
  const labels = weekTrend.value.map((d) => d.label)
  const counts = weekTrend.value.map((d) => d.count)
  trendChart.setOption(
    {
      grid: GRID,
      tooltip: {
        trigger: 'axis',
        backgroundColor: 'rgba(15,23,42,.92)',
        borderWidth: 0,
        textStyle: { color: '#e2e8f0', fontSize: 12 },
        axisPointer: { type: 'line', lineStyle: { color: '#14b8a6', type: 'dashed' } },
        formatter: (ps: any) => `${ps[0].axisValue}<br/>审查 <b>${ps[0].data}</b> 次`,
      },
      xAxis: {
        type: 'category',
        data: labels,
        boundaryGap: false,
        axisLine: { lineStyle: { color: '#e2e8f0' } },
        axisTick: { show: false },
        axisLabel: { color: '#94a3b8', fontSize: 11 },
      },
      yAxis: {
        type: 'value',
        minInterval: 1,
        splitLine: { lineStyle: { color: '#f1f5f9' } },
        axisLabel: { color: '#94a3b8', fontSize: 11 },
      },
      series: [
        {
          type: 'line',
          data: counts,
          smooth: true,
          symbol: 'circle',
          symbolSize: 8,
          lineStyle: { width: 3, color: '#14b8a6' },
          itemStyle: { color: '#fff', borderColor: '#14b8a6', borderWidth: 3 },
          areaStyle: {
            color: {
              type: 'linear',
              x: 0,
              y: 0,
              x2: 0,
              y2: 1,
              colorStops: [
                { offset: 0, color: 'rgba(20,184,166,0.32)' },
                { offset: 1, color: 'rgba(20,184,166,0.02)' },
              ],
            },
          },
        },
      ],
    },
    true
  )
}

function renderCat() {
  if (!catEl.value) return
  catChart = catChart || echarts.init(catEl.value)
  const cats = (stats.value?.by_category || []).slice(0, 8)
  catChart.setOption(
    {
      grid: { left: 70, right: 44, top: 12, bottom: 24 },
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'shadow' },
        backgroundColor: 'rgba(15,23,42,.92)',
        borderWidth: 0,
        textStyle: { color: '#e2e8f0', fontSize: 12 },
        formatter: (ps: any) => `${ps[0].name}<br/>审查 <b>${ps[0].value}</b> 份`,
      },
      xAxis: {
        type: 'value',
        minInterval: 1,
        splitLine: { lineStyle: { color: '#f1f5f9' } },
        axisLabel: { color: '#94a3b8', fontSize: 11 },
      },
      yAxis: {
        type: 'category',
        data: cats.map((c: any) => c.name).reverse(),
        axisLine: { show: false },
        axisTick: { show: false },
        axisLabel: { color: '#475569', fontSize: 12 },
      },
      series: [
        {
          type: 'bar',
          data: cats.map((c: any) => c.count).reverse(),
          barWidth: 15,
          itemStyle: {
            borderRadius: [0, 8, 8, 0],
            color: {
              type: 'linear',
              x: 0,
              y: 0,
              x2: 1,
              y2: 0,
              colorStops: [
                { offset: 0, color: '#0d9488' },
                { offset: 1, color: '#5eead4' },
              ],
            },
          },
          label: { show: true, position: 'right', color: '#0f172a', fontSize: 11, fontWeight: 600 },
        },
      ],
    },
    true
  )
}

function renderRisk() {
  if (!riskEl.value) return
  riskChart = riskChart || echarts.init(riskEl.value)
  const s = stats.value || {}
  riskChart.setOption(
    {
      tooltip: {
        trigger: 'item',
        backgroundColor: 'rgba(15,23,42,.92)',
        borderWidth: 0,
        textStyle: { color: '#e2e8f0', fontSize: 12 },
        formatter: (p: any) => `${p.name}<br/><b>${p.value}</b> 条（${p.percent}%）`,
      },
      legend: {
        bottom: 0,
        icon: 'circle',
        itemWidth: 8,
        itemHeight: 8,
        textStyle: { color: '#64748b', fontSize: 11 },
      },
      series: [
        {
          type: 'pie',
          radius: ['58%', '82%'],
          center: ['50%', '45%'],
          avoidLabelOverlap: false,
          itemStyle: { borderColor: '#fff', borderWidth: 3 },
          label: { show: false },
          emphasis: { scale: true, scaleSize: 6 },
          data: [
            { value: s.high ?? 0, name: '高风险', itemStyle: { color: '#ef4444' } },
            { value: s.mid ?? 0, name: '中风险', itemStyle: { color: '#f59e0b' } },
            { value: s.low ?? 0, name: '低风险', itemStyle: { color: '#10b981' } },
          ],
        },
      ],
    },
    true
  )
}

function renderAll() {
  renderTrend()
  renderCat()
  renderRisk()
}

function onResize() {
  trendChart?.resize()
  catChart?.resize()
  riskChart?.resize()
}

const loading = ref(true)

onMounted(async () => {
  await Promise.allSettled([
    api.get('/admin/stats').then(({ data }) => (stats.value = data)),
    api.get('/admin/health').then(({ data }) => (health.value = data)),
    api.get('/reviews').then(({ data }) => (allReviews.value = data.reviews || [])),
  ])
  loading.value = false
  await nextTick()
  renderAll()
  window.addEventListener('resize', onResize)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', onResize)
  trendChart?.dispose()
  catChart?.dispose()
  riskChart?.dispose()
})

function fmt(ts: number) {
  return ts
    ? new Date(ts * 1000).toLocaleString('zh-CN', {
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
      })
    : '-'
}
</script>

<template>
  <div class="page" v-loading="loading">
    <div class="page-head">
      <div>
        <h1 class="page-title">系统概览</h1>
        <p class="page-sub">用户与审查数据的整体情况（聚合统计，不含个人合同明细）</p>
      </div>
    </div>

    <!-- 指标卡 -->
    <div class="kpis">
      <div
        v-for="s in cards"
        :key="s.label"
        class="kpi"
        :class="[s.core ? 'core ' + s.core : '', { clickable: s.to }]"
        @click="s.to && router.push(s.to)"
      >
        <div class="kpi-head">
          <span class="kpi-label">{{ s.label }}</span>
          <span v-if="s.trend" class="kpi-trend">{{ s.trend }}</span>
        </div>
        <div class="kpi-value">{{ s.value }}</div>
        <div class="kpi-sub">{{ s.sub }}</div>
      </div>
    </div>

    <!-- 趋势 + 排行 -->
    <div class="grid-main">
      <div class="card">
        <div class="card-head">
          <div class="card-title">近 7 天审查趋势</div>
          <div class="legend"><span><i class="d teal"></i>每日审查次数</span></div>
        </div>
        <div ref="trendEl" class="chart-box"></div>
      </div>

      <div class="card">
        <div class="card-head">
          <div class="card-title">活跃用户 Top 5</div>
          <div class="legend"><span>按审查次数</span></div>
        </div>
        <div v-if="stats?.top_users?.length" class="rank">
          <div v-for="(u, i) in stats.top_users" :key="u.username" class="rank-row">
            <span class="rank-no" :class="{ top: i === 0 }">{{ i + 1 }}</span>
            <div class="rank-body">
              <div class="rank-top">
                <span class="rank-name">{{ u.username }}</span>
                <span class="rank-count">{{ u.count }}</span>
              </div>
              <div class="rank-track">
                <div class="rank-fill" :style="{ width: (u.count / userMax) * 100 + '%' }"></div>
              </div>
            </div>
          </div>
        </div>
        <div v-else class="empty">暂无数据</div>
      </div>
    </div>

    <!-- 类型分布 + 风险构成 -->
    <div class="grid-main">
      <div class="card">
        <div class="card-head">
          <div class="card-title">合同类型分布</div>
          <div class="legend"><span>Top 8 类型</span></div>
        </div>
        <div ref="catEl" class="chart-box tall"></div>
      </div>

      <div class="card">
        <div class="card-head">
          <div class="card-title">风险构成</div>
          <div class="legend"><span>高 / 中 / 低</span></div>
        </div>
        <div ref="riskEl" class="chart-box"></div>
      </div>
    </div>

    <!-- 最近审查 -->
    <div class="card">
      <div class="card-head">
        <div class="card-title">最近审查记录</div>
        <button class="more" @click="router.push('/admin/reviews')">查看全部 →</button>
      </div>
      <table v-if="recent.length" class="recent">
        <thead>
          <tr>
            <th>用户</th>
            <th>合同</th>
            <th class="num">高</th>
            <th class="num">中</th>
            <th class="num">低</th>
            <th class="time">时间</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="r in recent" :key="r.id">
            <td>{{ r.username }}</td>
            <td class="fname">{{ r.filename }}</td>
            <td class="num hi">{{ r.high }}</td>
            <td class="num mid">{{ r.mid }}</td>
            <td class="num low">{{ r.low }}</td>
            <td class="time">{{ fmt(r.created_at) }}</td>
          </tr>
        </tbody>
      </table>
      <div v-else class="empty">暂无审查记录</div>
    </div>
  </div>
</template>

<style scoped>
.page {
  max-width: 1440px;
  margin: 0 auto;
}
.page-title {
  font-weight: 600;
  letter-spacing: 0.5px;
}
/* 指标卡 */
.kpis {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 16px;
  margin-bottom: 16px;
}
.kpi {
  position: relative;
  overflow: hidden;
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 18px 20px;
  display: flex;
  flex-direction: column;
  min-height: 132px;
  box-shadow:
    0 1px 2px rgba(15, 23, 42, 0.04),
    0 8px 24px -20px rgba(15, 23, 42, 0.35);
  transition:
    transform 0.2s ease,
    box-shadow 0.2s ease;
}
.kpi.clickable {
  cursor: pointer;
}
.kpi:hover {
  transform: translateY(-3px);
  box-shadow:
    0 2px 4px rgba(15, 23, 42, 0.05),
    0 16px 32px -20px rgba(15, 23, 42, 0.3);
}
.kpi-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: auto;
}
.kpi-label {
  font-size: 12.5px;
  color: #475569;
  font-weight: 500;
}
.kpi-trend {
  font-size: 10.5px;
  color: #0f766e;
  background: #f0fdfa;
  border: 1px solid #99f6e4;
  border-radius: 999px;
  padding: 2px 8px;
  white-space: nowrap;
}
.kpi-value {
  font-size: 30px;
  font-weight: 800;
  line-height: 1.1;
  letter-spacing: -0.5px;
  color: #0f172a;
  margin-top: 12px;
}
.kpi-sub {
  font-size: 11px;
  color: #94a3b8;
  margin-top: 5px;
}
.kpi.core {
  border: none;
  color: #f8fafc;
}
.kpi.core::after {
  content: '';
  position: absolute;
  right: -40px;
  top: -50px;
  width: 160px;
  height: 160px;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(255, 255, 255, 0.16), transparent 65%);
  pointer-events: none;
}
.kpi.core .kpi-label {
  color: rgba(248, 250, 252, 0.82);
}
.kpi.core .kpi-value {
  font-size: 40px;
  color: #fff;
  margin-top: 14px;
}
.kpi.core .kpi-sub {
  color: rgba(248, 250, 252, 0.62);
}
.kpi.core .kpi-trend {
  background: rgba(255, 255, 255, 0.16);
  border-color: rgba(255, 255, 255, 0.26);
  color: #fff;
}
.kpi.core.teal {
  background: linear-gradient(135deg, #0f172a 0%, #134e4a 62%, #0d9488 100%);
  box-shadow:
    0 2px 4px rgba(13, 148, 136, 0.12),
    0 18px 40px -24px rgba(13, 148, 136, 0.85);
}
.kpi.core.red {
  background: linear-gradient(135deg, #1c0a0a 0%, #7f1d1d 62%, #dc2626 100%);
  box-shadow:
    0 2px 4px rgba(220, 38, 38, 0.12),
    0 18px 40px -24px rgba(220, 38, 38, 0.8);
}
/* 卡片 */
.card {
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 22px;
  box-shadow:
    0 1px 2px rgba(15, 23, 42, 0.04),
    0 8px 24px -20px rgba(15, 23, 42, 0.35);
}
.card-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}
.card-title {
  font-size: 14px;
  font-weight: 600;
  color: #0f172a;
}
.legend {
  font-size: 11px;
  color: #94a3b8;
  display: flex;
  align-items: center;
  gap: 6px;
}
.legend .d {
  width: 8px;
  height: 8px;
  border-radius: 2px;
  display: inline-block;
}
.d.teal {
  background: #14b8a6;
}
.more {
  background: none;
  border: none;
  color: #0f766e;
  font-size: 11.5px;
  cursor: pointer;
  padding: 0;
}
.more:hover {
  color: #14b8a6;
}
.grid-main {
  display: grid;
  grid-template-columns: 2fr 1fr;
  gap: 16px;
  margin-bottom: 16px;
}
.chart-box {
  height: 260px;
  width: 100%;
}
.chart-box.tall {
  height: 300px;
}
/* 排行 */
.rank {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.rank-row {
  display: flex;
  gap: 12px;
  align-items: flex-start;
}
.rank-no {
  width: 20px;
  height: 20px;
  border-radius: 6px;
  background: #f1f5f9;
  color: #64748b;
  font-size: 11px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  margin-top: 1px;
}
.rank-no.top {
  background: #ccfbf1;
  color: #0f766e;
}
.rank-body {
  flex: 1;
  min-width: 0;
}
.rank-top {
  display: flex;
  justify-content: space-between;
  font-size: 12.5px;
  margin-bottom: 6px;
}
.rank-name {
  color: #334155;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.rank-count {
  color: #0f172a;
  font-weight: 600;
}
.rank-track {
  height: 8px;
  background: #f1f5f9;
  border-radius: 999px;
  overflow: hidden;
}
.rank-fill {
  height: 100%;
  border-radius: 999px;
  background: linear-gradient(90deg, #2dd4bf, #14b8a6);
}
/* 最近记录 */
.recent {
  width: 100%;
  border-collapse: collapse;
  font-size: 12.5px;
}
.recent th {
  text-align: left;
  font-weight: 500;
  color: #94a3b8;
  font-size: 11.5px;
  padding: 0 10px 10px 0;
  border-bottom: 1px solid #f1f5f9;
  white-space: nowrap;
}
.recent td {
  padding: 11px 10px 11px 0;
  border-bottom: 1px solid #f8fafc;
  color: #334155;
}
.recent tr:last-child td {
  border-bottom: none;
}
.recent .fname {
  max-width: 420px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: #0f172a;
}
.recent .num {
  text-align: right;
  width: 46px;
  font-weight: 600;
}
.recent td.hi {
  color: #ef4444;
}
.recent td.mid {
  color: #f59e0b;
}
.recent td.low {
  color: #10b981;
}
.recent .time {
  text-align: right;
  color: #94a3b8;
  white-space: nowrap;
}
.empty {
  font-size: 12px;
  color: #cbd5e1;
  padding: 10px 0;
}
@media (max-width: 1280px) {
  .kpis {
    grid-template-columns: repeat(3, 1fr);
  }
  .grid-main {
    grid-template-columns: 1fr;
  }
}
</style>
