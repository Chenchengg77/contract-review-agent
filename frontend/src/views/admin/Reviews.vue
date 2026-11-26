<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Refresh, Download, Delete } from '@element-plus/icons-vue'
import api from '../../api'

const route = useRoute()
const router = useRouter()

const reviews = ref<any[]>([])
const loading = ref(false)
const selection = ref<any[]>([])

// 筛选
const userKw = ref(String(route.query.user || ''))
const riskFilter = ref('')
const typeFilter = ref('')
const dateRange = ref<string[] | null>(null)
const keyword = ref('')
const page = ref(1)
const pageSize = ref(10)

const users = computed(() => Array.from(new Set(reviews.value.map((r) => r.username))).filter(Boolean))
const categories = computed(() => Array.from(new Set(reviews.value.map((r) => r.category))).filter(Boolean))

const filtered = computed(() => {
  return reviews.value.filter((r) => {
    if (userKw.value && !String(r.username || '').includes(userKw.value)) return false
    if (keyword.value) {
      const kw = keyword.value.toLowerCase()
      if (!String(r.filename || '').toLowerCase().includes(kw)) return false
    }
    if (typeFilter.value && r.category !== typeFilter.value) return false
    if (riskFilter.value === 'high' && !(r.high > 0)) return false
    if (riskFilter.value === 'mid' && !(r.mid > 0)) return false
    if (riskFilter.value === 'low' && !(r.low > 0)) return false
    if (dateRange.value && dateRange.value.length === 2) {
      const d = new Date(r.created_at * 1000)
      const p = (n: number) => String(n).padStart(2, '0')
      const day = `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`
      if (day < dateRange.value[0] || day > dateRange.value[1]) return false
    }
    return true
  })
})

const paged = computed(() => {
  const start = (page.value - 1) * pageSize.value
  return filtered.value.slice(start, start + pageSize.value)
})

function resetPage() {
  page.value = 1
}

const hasFilter = computed(
  () => !!(userKw.value || riskFilter.value || typeFilter.value || dateRange.value || keyword.value)
)

function clearFilters() {
  userKw.value = ''
  riskFilter.value = ''
  typeFilter.value = ''
  dateRange.value = null
  keyword.value = ''
  page.value = 1
}

async function load() {
  loading.value = true
  try {
    const { data } = await api.get('/reviews')
    reviews.value = data.reviews || []
  } catch {
    ElMessage.error('加载失败')
  } finally {
    loading.value = false
  }
}

onMounted(load)

// 批量删除
async function batchDelete() {
  if (!selection.value.length) return
  try {
    await ElMessageBox.confirm(
      `确定删除选中的 ${selection.value.length} 条审查记录？删除后不可恢复。`,
      '批量删除',
      { type: 'warning', confirmButtonText: '确认删除' }
    )
  } catch {
    return
  }
  let ok = 0
  for (const r of selection.value) {
    try {
      await api.delete('/reviews/' + r.id)
      ok += 1
    } catch {
      /* ignore */
    }
  }
  ElMessage.success(`已删除 ${ok} 条`)
  load()
}

async function del(r: any) {
  try {
    await ElMessageBox.confirm(
      `确定删除「${r.username}」对「${r.filename}」的审查记录？不可恢复。`,
      '确认删除',
      { type: 'warning', confirmButtonText: '确认删除' }
    )
  } catch {
    return
  }
  try {
    await api.delete('/reviews/' + r.id)
    ElMessage.success('已删除')
    load()
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '删除失败')
  }
}

// 导出 CSV（Excel 可直接打开）
function exportCsv() {
  const rows = filtered.value
  if (!rows.length) {
    ElMessage.warning('当前没有可导出的记录')
    return
  }
  const head = ['用户', '合同', '类型', '高风险', '中风险', '低风险', '状态', '时间']
  const lines = rows.map((r) =>
    [r.username, r.filename, r.category, r.high, r.mid, r.low, statusText(r), fmt(r.created_at)]
      .map((v) => `"${String(v ?? '').replace(/"/g, '""')}"`)
      .join(',')
  )
  const csv = '\ufeff' + [head.join(','), ...lines].join('\r\n')
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `审查记录_${new Date().toISOString().slice(0, 10)}.csv`
  a.click()
  URL.revokeObjectURL(url)
  ElMessage.success(`已导出 ${rows.length} 条`)
}

// 详情
const detailVisible = ref(false)
const detailLoading = ref(false)
const detail = ref<any>(null)

async function openDetail(r: any) {
  detailVisible.value = true
  detailLoading.value = true
  detail.value = null
  try {
    const { data } = await api.get('/reviews/' + r.id)
    detail.value = data
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '加载详情失败')
  } finally {
    detailLoading.value = false
  }
}

function gotoUser(name: string) {
  router.push({ path: '/admin/users', query: { q: name } })
}

// 展示
function statusText(r: any) {
  if (r.status === 'failed') return '失败'
  if (r.status === 'retried') return '已重试'
  if (r.status === 'processing') return '处理中'
  return '已完成'
}
function statusClass(r: any) {
  if (r.status === 'failed') return 'bad'
  if (r.status === 'processing') return 'warn'
  if (r.status === 'retried') return 'muted'
  return 'ok'
}

function severClass(s: string) {
  if (s === '高') return 'high'
  if (s === '中') return 'mid'
  if (s === '低') return 'low'
  return 'muted'
}

function initials(name: string) {
  return (name || '?').slice(0, 1).toUpperCase()
}

function fmt(ts: number) {
  if (!ts) return '—'
  const d = new Date(ts * 1000)
  const p = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}`
}

// 高风险行高亮
function rowClass({ row }: { row: any }) {
  return row.high > 0 ? 'row-high' : ''
}
</script>

<template>
  <div class="page">
    <div class="page-head">
      <div>
        <h1 class="page-title">审查记录</h1>
        <p class="page-sub">全部用户的审查记录，共 {{ reviews.length }} 条</p>
      </div>
    </div>

    <el-card shadow="never">
      <!-- 工具栏 -->
      <div class="toolbar">
        <div class="filters">
          <el-select
            v-model="userKw"
            placeholder="全部用户"
            clearable
            filterable
            style="width: 150px"
            @change="resetPage"
          >
            <el-option v-for="u in users" :key="u" :label="u" :value="u" />
          </el-select>

          <el-select v-model="riskFilter" placeholder="风险等级" clearable style="width: 132px" @change="resetPage">
            <el-option label="高风险" value="high" />
            <el-option label="中风险" value="mid" />
            <el-option label="低风险" value="low" />
          </el-select>

          <el-select v-model="typeFilter" placeholder="合同类型" clearable style="width: 132px" @change="resetPage">
            <el-option v-for="c in categories" :key="c" :label="c" :value="c" />
          </el-select>

          <el-date-picker
            v-model="dateRange"
            type="daterange"
            value-format="YYYY-MM-DD"
            range-separator="至"
            start-placeholder="开始日期"
            end-placeholder="结束日期"
            style="width: 250px"
            @change="resetPage"
          />

          <el-input
            v-model="keyword"
            placeholder="搜索合同名"
            clearable
            style="width: 160px"
            @input="resetPage"
          />

          <button v-if="hasFilter" class="link-btn" @click="clearFilters">清空筛选</button>
        </div>

        <div class="actions">
          <el-tooltip content="刷新" placement="top">
            <el-button :icon="Refresh" circle @click="load" />
          </el-tooltip>
          <el-button :icon="Download" @click="exportCsv">导出记录</el-button>
          <el-button
            type="danger"
            plain
            :icon="Delete"
            :disabled="!selection.length"
            @click="batchDelete"
          >
            批量删除{{ selection.length ? `（${selection.length}）` : '' }}
          </el-button>
        </div>
      </div>

      <!-- 表格 -->
      <el-table
        :data="paged"
        v-loading="loading"
        style="width: 100%"
        row-key="id"
        stripe
        highlight-current-row
        :max-height="560"
        :row-class-name="rowClass"
        :row-style="{ height: '48px' }"
        :header-cell-style="{ background: '#f8fafc', color: '#475569', fontWeight: '600', height: '44px' }"
        @selection-change="(rows: any[]) => (selection = rows)"
      >
        <el-table-column type="selection" width="46" align="center" />

        <el-table-column label="序号" width="70" align="right">
          <template #default="{ $index }">
            <span class="idx">{{ (page - 1) * pageSize + $index + 1 }}</span>
          </template>
        </el-table-column>

        <el-table-column label="用户" min-width="150">
          <template #default="{ row }">
            <div class="user-cell">
              <span class="avatar">{{ initials(row.username) }}</span>
              <button class="user-link" @click.stop="gotoUser(row.username)">{{ row.username }}</button>
            </div>
          </template>
        </el-table-column>

        <el-table-column label="合同名称" min-width="280">
          <template #default="{ row }">
            <button class="doc-link" :title="row.filename" @click.stop="openDetail(row)">
              <span class="doc-ico">📄</span>
              <span class="doc-name">{{ row.filename }}</span>
            </button>
          </template>
        </el-table-column>

        <el-table-column label="风险分布" width="210">
          <template #default="{ row }">
            <span class="risk-tag high">高 {{ row.high }}</span>
            <span class="risk-tag mid">中 {{ row.mid }}</span>
            <span class="risk-tag low">低 {{ row.low }}</span>
          </template>
        </el-table-column>

        <el-table-column label="审查状态" width="110" align="center">
          <template #default="{ row }">
            <span class="st" :class="statusClass(row)">{{ statusText(row) }}</span>
          </template>
        </el-table-column>

        <el-table-column label="时间" width="150" align="center">
          <template #default="{ row }"><span class="muted">{{ fmt(row.created_at) }}</span></template>
        </el-table-column>

        <el-table-column label="操作" width="150" align="center">
          <template #default="{ row }">
            <el-button link size="small" class="view-btn" @click.stop="openDetail(row)">查看报告</el-button>
            <el-button link size="small" class="del-btn" @click.stop="del(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <div class="pager">
        <span class="pager-info">共 {{ filtered.length }} 条记录</span>
        <el-pagination
          :current-page="page"
          :page-size="pageSize"
          :page-sizes="[10, 20, 50]"
          :total="filtered.length"
          layout="prev, pager, next, sizes"
          background
          @current-change="(p: number) => (page = p)"
          @size-change="(s: number) => { pageSize = s; page = 1 }"
        />
      </div>
    </el-card>

    <!-- 报告详情 -->
    <el-drawer v-model="detailVisible" title="审查报告" size="560px">
      <div v-loading="detailLoading">
        <template v-if="detail">
          <div class="d-head">
            <div class="d-name">{{ detail.filename }}</div>
            <div class="d-meta">
              {{ detail.category }} · {{ detail.username || '—' }} · {{ fmt(detail.created_at) }}
            </div>
          </div>

          <div class="d-stats">
            <div class="d-stat high"><b>{{ detail.high }}</b><span>高风险</span></div>
            <div class="d-stat mid"><b>{{ detail.mid }}</b><span>中风险</span></div>
            <div class="d-stat low"><b>{{ detail.low }}</b><span>低风险</span></div>
            <div class="d-stat"><b>{{ (detail.judgments || []).length }}</b><span>条款</span></div>
          </div>

          <div v-if="detail.status === 'failed'" class="d-fail">
            审查失败：{{ detail.error || '未知错误' }}
          </div>

          <div v-if="(detail.judgments || []).length" class="d-list">
            <div v-for="(j, i) in detail.judgments" :key="i" class="d-item">
              <div class="d-item-head">
                <span class="d-clause">{{ j.clause }}</span>
                <span class="d-sev" :class="severClass(j.severity)">{{ j.severity }}</span>
                <span class="d-verdict">{{ j.verdict }}</span>
              </div>
              <div class="d-reason">{{ j.reason }}</div>
              <div v-if="j.revision" class="d-rev">修订建议：{{ j.revision }}</div>
            </div>
          </div>
          <div v-else class="empty">暂无判定明细</div>
        </template>
      </div>
    </el-drawer>
  </div>
</template>

<style scoped>
.page-title {
  font-weight: 600;
  letter-spacing: 0.5px;
}
:deep(.el-card) {
  border-radius: 12px;
  border-color: #e2e8f0;
  box-shadow:
    0 1px 2px rgba(15, 23, 42, 0.04),
    0 8px 24px -20px rgba(15, 23, 42, 0.35);
}
/* 工具栏 */
.toolbar {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 16px;
  flex-wrap: wrap;
}
.filters {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}
.actions {
  display: flex;
  align-items: center;
  gap: 8px;
}
.link-btn {
  background: none;
  border: none;
  color: #0f766e;
  font-size: 12px;
  cursor: pointer;
  padding: 0 2px;
}
.link-btn:hover {
  text-decoration: underline;
}
/* 表格 */
:deep(.el-table) {
  --el-table-row-hover-bg-color: #f0fdfa;
  --el-table-current-row-bg-color: #ccfbf1;
  --el-table-border-color: #eef2f7;
  font-size: 13px;
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
:deep(.el-table__body tr.current-row > td.el-table__cell) {
  background: #ccfbf1 !important;
  box-shadow: inset 2px 0 0 #14b8a6;
}
/* 高风险行 */
:deep(.el-table__body tr.row-high > td.el-table__cell) {
  background: #fef6f5;
}
:deep(.el-table__body tr.row-high:hover > td.el-table__cell) {
  background: #fdecea !important;
}
:deep(.el-table td.el-table__cell) {
  padding: 0;
}
:deep(.el-table .cell) {
  line-height: 48px;
}
/* 单元格 */
.idx {
  color: #94a3b8;
  font-size: 12px;
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
  background: #e2e8f0;
  color: #475569;
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
  font-size: 13px;
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
  max-width: 250px;
}
.doc-link:hover .doc-name {
  color: #0d9488;
  text-decoration: underline;
}
/* 风险标签 */
.risk-tag {
  display: inline-block;
  font-size: 11px;
  font-weight: 600;
  padding: 1px 7px;
  border-radius: 999px;
  margin-right: 4px;
  line-height: 18px;
}
.risk-tag.high {
  color: #b91c1c;
  background: #fef2f2;
  border: 1px solid #fecaca;
}
.risk-tag.mid {
  color: #b45309;
  background: #fffbeb;
  border: 1px solid #fde68a;
}
.risk-tag.low {
  color: #047857;
  background: #ecfdf5;
  border: 1px solid #a7f3d0;
}
/* 状态 */
.st {
  font-size: 12px;
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-weight: 500;
}
.st::before {
  content: '';
  width: 6px;
  height: 6px;
  border-radius: 50%;
}
.st.ok {
  color: #0f766e;
}
.st.ok::before {
  background: #10b981;
}
.st.bad {
  color: #b91c1c;
}
.st.bad::before {
  background: #ef4444;
}
.st.warn {
  color: #b45309;
}
.st.warn::before {
  background: #f59e0b;
  animation: pulse 1.4s ease-in-out infinite;
}
.st.muted {
  color: #64748b;
}
.st.muted::before {
  background: #cbd5e1;
}
@keyframes pulse {
  0%,
  100% {
    opacity: 1;
  }
  50% {
    opacity: 0.35;
  }
}
.muted {
  color: #94a3b8;
  font-size: 12px;
}
.view-btn {
  color: #0d9488;
}
.del-btn {
  color: #ef4444;
}
/* 分页 */
.pager {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 16px;
}
.pager-info {
  font-size: 12px;
  color: #94a3b8;
}
/* 详情抽屉 */
.d-head {
  border-bottom: 1px solid #eef2f7;
  padding-bottom: 16px;
  margin-bottom: 16px;
}
.d-name {
  font-size: 15px;
  font-weight: 600;
  color: #0f172a;
  line-height: 1.5;
  word-break: break-all;
}
.d-meta {
  font-size: 12px;
  color: #94a3b8;
  margin-top: 6px;
}
.d-stats {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 10px;
  margin-bottom: 18px;
}
.d-stat {
  background: #f8fafc;
  border: 1px solid #eef2f7;
  border-radius: 10px;
  padding: 12px 10px;
  text-align: center;
}
.d-stat b {
  display: block;
  font-size: 20px;
  color: #0f172a;
}
.d-stat span {
  font-size: 11px;
  color: #94a3b8;
}
.d-stat.high b {
  color: #ef4444;
}
.d-stat.mid b {
  color: #f59e0b;
}
.d-stat.low b {
  color: #10b981;
}
.d-fail {
  background: #fef2f2;
  border: 1px solid #fecaca;
  color: #b91c1c;
  font-size: 12.5px;
  padding: 10px 12px;
  border-radius: 8px;
  margin-bottom: 16px;
}
.d-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.d-item {
  border: 1px solid #eef2f7;
  border-radius: 10px;
  padding: 12px 14px;
}
.d-item-head {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
}
.d-clause {
  font-size: 13px;
  font-weight: 600;
  color: #0f172a;
}
.d-sev {
  font-size: 10.5px;
  padding: 1px 7px;
  border-radius: 999px;
}
.d-sev.high {
  color: #b91c1c;
  background: #fef2f2;
}
.d-sev.mid {
  color: #b45309;
  background: #fffbeb;
}
.d-sev.low {
  color: #047857;
  background: #ecfdf5;
}
.d-sev.muted {
  color: #64748b;
  background: #f8fafc;
}
.d-verdict {
  font-size: 11.5px;
  color: #64748b;
  margin-left: auto;
}
.d-reason {
  font-size: 12.5px;
  color: #475569;
  line-height: 1.8;
}
.d-rev {
  font-size: 12px;
  color: #1f3fb3;
  background: #f4f6fc;
  border: 1px solid #dde3f5;
  border-radius: 6px;
  padding: 8px 10px;
  margin-top: 8px;
  line-height: 1.7;
}
.empty {
  font-size: 12px;
  color: #cbd5e1;
  padding: 10px 0;
}
</style>
