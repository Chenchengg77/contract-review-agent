<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { ArrowLeft } from '@element-plus/icons-vue'
import api from '../../api'

const route = useRoute()
const router = useRouter()

const detail = ref<any>(null)
const loading = ref(true)

onMounted(async () => {
  try {
    const { data } = await api.get('/reviews/' + route.params.id)
    detail.value = data
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '记录不存在')
  } finally {
    loading.value = false
  }
})

const judgments = computed<any[]>(() => detail.value?.judgments || [])

const counts = computed(() => {
  const d = detail.value || {}
  return { high: d.high ?? 0, mid: d.mid ?? 0, low: d.low ?? 0 }
})

const total = computed(() => counts.value.high + counts.value.mid + counts.value.low)
const riskPct = (v: number) => (total.value ? (v / total.value) * 100 : 0)

function sevClass(s: string) {
  if (s === '高') return 'high'
  if (s === '中') return 'mid'
  if (s === '低') return 'low'
  return 'none'
}

function fmt(ts: number) {
  if (!ts) return '—'
  const d = new Date(ts * 1000)
  const p = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}`
}

async function copyText(t: string) {
  try {
    await navigator.clipboard.writeText(t)
    ElMessage.success('已复制')
  } catch {
    ElMessage.error('复制失败')
  }
}

function back() {
  router.push({ path: '/me/reviews', query: { from: String(route.params.id) } })
}
</script>

<template>
  <div class="page">
    <div class="page-head">
      <div>
        <button class="back" @click="back">
          <el-icon><ArrowLeft /></el-icon> 返回我的审查
        </button>
        <h1 class="page-title">审查报告</h1>
        <p class="page-sub">{{ detail?.filename || '加载中…' }}</p>
      </div>
    </div>

    <div v-loading="loading" class="panel">
      <template v-if="detail">
        <div class="doc-head">
          <div class="doc-name">{{ detail.filename }}</div>
          <div class="doc-meta">
            <span class="cat">{{ detail.category }}</span>
            <span>审查于 {{ fmt(detail.created_at) }}</span>
          </div>
        </div>

        <div class="stats">
          <div class="stat">
            <b>{{ counts.high }}</b><span>高风险</span>
          </div>
          <div class="stat">
            <b>{{ counts.mid }}</b><span>中风险</span>
          </div>
          <div class="stat">
            <b>{{ counts.low }}</b><span>低风险</span>
          </div>
          <div class="stat">
            <b>{{ judgments.length }}</b><span>条款</span>
          </div>
        </div>

        <div class="risk-bar">
          <i class="seg high" :style="{ width: riskPct(counts.high) + '%' }"></i>
          <i class="seg mid" :style="{ width: riskPct(counts.mid) + '%' }"></i>
          <i class="seg low" :style="{ width: riskPct(counts.low) + '%' }"></i>
        </div>

        <div v-if="detail.status === 'failed'" class="fail">
          审查失败：{{ detail.error || '未知错误' }}
        </div>

        <div class="list-head">
          <span>条款明细</span>
          <span class="list-sub">按原文顺序 · 点击可复制修订建议</span>
        </div>

        <div v-if="judgments.length" class="jlist">
          <div v-for="(j, i) in judgments" :key="i" class="jitem">
            <div class="jhead">
              <span class="jclause">{{ j.clause_no ? j.clause_no + ' ' : '' }}{{ j.clause }}</span>
              <span class="jsev" :class="sevClass(j.severity)">{{ j.severity }}</span>
              <span class="jverdict">{{ j.verdict }}</span>
            </div>
            <p class="jreason">{{ j.reason }}</p>
            <div v-if="j.revision" class="jrev">
              <span class="jrev-text">修订建议：{{ j.revision }}</span>
              <button class="jrev-copy" @click="copyText(j.revision)">复制</button>
            </div>
          </div>
        </div>
        <div v-else class="empty">暂无条款明细</div>
      </template>

      <div v-else-if="!loading" class="empty">记录不存在或无权查看</div>
    </div>
  </div>
</template>

<style scoped>
.page-title {
  font-weight: 600;
  letter-spacing: 0.5px;
  margin-top: 10px;
}
.back {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  background: none;
  border: none;
  padding: 0;
  font-size: 12px;
  color: #6b6f76;
  cursor: pointer;
}
.back:hover {
  color: #2563eb;
}
.panel {
  background: #fff;
  border: 1px solid #eae6de;
  border-radius: 12px;
  padding: 24px;
  min-height: 200px;
}
.doc-head {
  border-bottom: 1px solid #f4f2ec;
  padding-bottom: 16px;
  margin-bottom: 18px;
}
.doc-name {
  font-size: 15px;
  font-weight: 600;
  color: #14161a;
  line-height: 1.5;
  word-break: break-all;
}
.doc-meta {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 11.5px;
  color: #94a3b8;
  margin-top: 8px;
}
.cat {
  padding: 1px 8px;
  border-radius: 999px;
  background: #f8f7f3;
  border: 1px solid #ece7de;
  color: #6b6f76;
}
/* 统计 */
.stats {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
  margin-bottom: 14px;
}
.stat {
  background: #fbfaf6;
  border: 1px solid #f1eee7;
  border-radius: 10px;
  padding: 14px;
  text-align: center;
}
.stat b {
  display: block;
  font-size: 22px;
  color: #14161a;
}
.stat span {
  font-size: 11px;
  color: #94a3b8;
}
.risk-bar {
  display: flex;
  height: 8px;
  border-radius: 999px;
  overflow: hidden;
  background: #f4f2ec;
  margin-bottom: 20px;
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
.fail {
  background: #fef2f2;
  border: 1px solid #fecaca;
  color: #b91c1c;
  font-size: 12.5px;
  padding: 10px 12px;
  border-radius: 8px;
  margin-bottom: 16px;
}
/* 列表 */
.list-head {
  display: flex;
  align-items: baseline;
  gap: 10px;
  font-size: 13px;
  font-weight: 600;
  color: #14161a;
  margin-bottom: 12px;
}
.list-sub {
  font-size: 11px;
  font-weight: 400;
  color: #a39d92;
}
.jlist {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.jitem {
  border: 1px solid #f1eee7;
  border-radius: 10px;
  padding: 14px 16px;
  transition: background 0.18s;
}
.jitem:hover {
  background: #fdfcf9;
}
.jhead {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}
.jclause {
  font-size: 13px;
  font-weight: 600;
  color: #14161a;
}
.jsev {
  font-size: 10.5px;
  padding: 1px 8px;
  border-radius: 999px;
}
.jsev.high {
  background: #fff2f0;
  color: #b4544a;
}
.jsev.mid {
  background: #fffbe6;
  color: #a3812f;
}
.jsev.low {
  background: #f0f9ff;
  color: #3f7d6a;
}
.jsev.none {
  background: #f6f4ef;
  color: #8a867d;
}
.jverdict {
  font-size: 11.5px;
  color: #94a3b8;
  margin-left: auto;
}
.jreason {
  font-size: 12.5px;
  line-height: 1.9;
  color: #475569;
  margin: 0 0 8px;
}
.jrev {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  background: #f7fafd;
  border: 1px solid #e6eefb;
  border-radius: 8px;
  padding: 9px 11px;
  font-size: 12px;
  line-height: 1.8;
  color: #1e4fa8;
}
.jrev-text {
  flex: 1;
}
.jrev-copy {
  flex-shrink: 0;
  background: none;
  border: 1px solid #d6e2f7;
  color: #2563eb;
  border-radius: 6px;
  padding: 1px 9px;
  font-size: 11px;
  cursor: pointer;
}
.jrev-copy:hover {
  background: #2563eb;
  color: #fff;
  border-color: #2563eb;
}
.empty {
  font-size: 12px;
  color: #b3b0a8;
  padding: 20px 0;
}
@media (max-width: 900px) {
  .stats {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>
