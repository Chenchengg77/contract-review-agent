<script setup lang="ts">
import { computed, nextTick, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Search, Refresh } from '@element-plus/icons-vue'
import api from '../../api'

const route = useRoute()
const router = useRouter()

const reviews = ref<any[]>([])
const loading = ref(true)

// 筛选
const keyword = ref('')
const typeFilter = ref('')
const riskFilter = ref('')
const dateRange = ref<string[] | null>(null)
const page = ref(1)
const pageSize = ref(10)

const categories = computed(() =>
  Array.from(new Set(reviews.value.map((r) => r.category).filter(Boolean)))
)

const filtered = computed(() => {
  return reviews.value.filter((r) => {
    if (keyword.value.trim()) {
      const kw = keyword.value.trim().toLowerCase()
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

const hasFilter = computed(
  () => !!(keyword.value || typeFilter.value || riskFilter.value || dateRange.value)
)

function resetFilters() {
  keyword.value = ''
  typeFilter.value = ''
  riskFilter.value = ''
  dateRange.value = null
  page.value = 1
}

function onFilter() {
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

function openReport(r: any) {
  router.push(`/me/reviews/${r.id}`)
}

function fmt(ts: number) {
  if (!ts) return '—'
  const d = new Date(ts * 1000)
  const p = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}`
}

// 高亮当前返回的详情（可选）
const highlightId = computed(() => Number(route.query.from || 0))
</script>

<template>
  <div class="page">
    <div class="page-head">
      <div class="page-icon">
        <svg viewBox="0 0 24 24" fill="none" stroke="#14161a" stroke-width="1.3">
          <path d="M6.5 3.5h7L18 8v12.5H6.5z" stroke-linejoin="round" />
          <path d="M13.5 3.5V8H18" stroke-linejoin="round" />
          <path d="M9 12h6M9 15.2h6M9 18.2h3.5" stroke-linecap="round" />
        </svg>
      </div>
      <div>
        <h1 class="page-title">我的审查</h1>
        <p class="page-sub">共 {{ reviews.length }} 条审查记录 · 可筛选、查看报告</p>
      </div>
    </div>

    <div class="panel">
      <!-- 工具栏 -->
      <div class="toolbar">
        <el-input
          v-model="keyword"
          placeholder="搜索合同名称"
          clearable
          :prefix-icon="Search"
          style="width: 200px"
          @input="onFilter"
        />
        <el-select v-model="typeFilter" placeholder="合同类型" clearable style="width: 130px" @change="onFilter">
          <el-option v-for="c in categories" :key="c" :label="c" :value="c" />
        </el-select>
        <el-select v-model="riskFilter" placeholder="风险等级" clearable style="width: 130px" @change="onFilter">
          <el-option label="含高风险" value="high" />
          <el-option label="含中风险" value="mid" />
          <el-option label="含低风险" value="low" />
        </el-select>
        <el-date-picker
          v-model="dateRange"
          type="daterange"
          value-format="YYYY-MM-DD"
          range-separator="至"
          start-placeholder="开始日期"
          end-placeholder="结束日期"
          style="width: 240px"
          @change="onFilter"
        />
        <button v-if="hasFilter" class="link-btn" @click="resetFilters">重置</button>
        <div class="spacer"></div>
        <el-button :icon="Refresh" circle @click="load" />
      </div>

      <!-- 表格 -->
      <el-table
        v-if="loading"
        :data="[]"
        class="sk-table"
        style="width: 100%"
      >
        <el-table-column label="合同" min-width="320">
          <template #default>
            <span class="sk-bar" style="width: 72%"></span>
          </template>
        </el-table-column>
        <el-table-column label="风险分布" width="210">
          <template #default><span class="sk-bar" style="width: 64%"></span></template>
        </el-table-column>
        <el-table-column label="时间" width="160" align="center">
          <template #default><span class="sk-bar" style="width: 60%"></span></template>
        </el-table-column>
        <el-table-column label="操作" width="110" align="center">
          <template #default><span class="sk-bar" style="width: 50%"></span></template>
        </el-table-column>
      </el-table>

      <template v-else>
        <el-table
          :data="paged"
          style="width: 100%"
          row-key="id"
          stripe
          :row-style="{ height: '52px' }"
          :row-class-name="({ row }: any) => (row.id === highlightId ? 'row-flash' : '')"
          :header-cell-style="{ background: '#fbfaf6', color: '#6b6f76', fontWeight: '600', height: '42px' }"
        >
          <el-table-column label="合同名称" min-width="320">
            <template #default="{ row }">
              <el-tooltip :content="row.filename" placement="top" :show-after="400">
                <span class="fname">{{ row.filename }}</span>
              </el-tooltip>
            </template>
          </el-table-column>

          <el-table-column label="风险分布" width="210">
            <template #default="{ row }">
              <span class="tag high">高 {{ row.high }}</span>
              <span class="tag mid">中 {{ row.mid }}</span>
              <span class="tag low">低 {{ row.low }}</span>
            </template>
          </el-table-column>

          <el-table-column label="时间" width="160" align="center">
            <template #default="{ row }"><span class="time">{{ fmt(row.created_at) }}</span></template>
          </el-table-column>

          <el-table-column label="操作" width="110" align="center">
            <template #default="{ row }">
              <el-button link class="view-btn" @click="openReport(row)">查看报告</el-button>
            </template>
          </el-table-column>
        </el-table>

        <!-- 空状态 -->
        <div v-if="!filtered.length" class="empty-card">
          <svg class="empty-ico" viewBox="0 0 48 48" fill="none" stroke="#c9c4ba" stroke-width="1.5">
            <rect x="11" y="8" width="22" height="30" rx="2" />
            <path d="M17 16h10M17 21h10M17 26h6" stroke-linecap="round" />
            <circle cx="33" cy="33" r="6" />
            <path d="m37.5 37.5 4 4" stroke-linecap="round" />
          </svg>
          <div class="empty-title">{{ hasFilter ? '没有匹配的审查记录' : '还没有审查记录' }}</div>
          <div class="empty-sub">
            {{ hasFilter ? '换个筛选条件试试' : '去「合同审查」上传一份合同，结果会出现在这里' }}
          </div>
          <button v-if="hasFilter" class="empty-btn" @click="resetFilters">重置筛选</button>
        </div>

        <!-- 分页 -->
        <div v-if="filtered.length" class="pager">
          <span class="pager-info">共 {{ filtered.length }} 条</span>
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
      </template>
    </div>
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
.panel {
  background: #fff;
  border: 1px solid #eae6de;
  border-radius: 12px;
  padding: 18px 20px 16px;
}
/* 工具栏 */
.toolbar {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 16px;
  flex-wrap: wrap;
}
.spacer {
  flex: 1;
}
.link-btn {
  background: none;
  border: none;
  color: #2563eb;
  font-size: 12px;
  cursor: pointer;
  padding: 0 2px;
}
.link-btn:hover {
  text-decoration: underline;
}
/* 表格 */
:deep(.el-table) {
  --el-table-row-hover-bg-color: #fafafa;
  --el-table-border-color: #f4f2ec;
  font-size: 13px;
}
:deep(.el-table th.el-table__cell) {
  background: #fbfaf6 !important;
  color: #6b6f76;
  font-weight: 600;
  border-bottom: 1px solid #ece7de;
}
:deep(.el-table__body tr.el-table__row--striped td.el-table__cell) {
  background: #fdfcf9;
}
:deep(.el-table__body tr:hover > td.el-table__cell) {
  background: #fafafa !important;
}
:deep(.el-table td.el-table__cell) {
  padding: 0;
}
:deep(.el-table .cell) {
  line-height: 52px;
}
:deep(.el-table__body tr.row-flash > td.el-table__cell) {
  background: #f4f8ff !important;
}
.fname {
  color: #14161a;
  font-size: 12.5px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 300px;
  display: inline-block;
  vertical-align: middle;
}
/* 风险标签 */
.tag {
  display: inline-block;
  font-size: 11px;
  font-weight: 600;
  padding: 2px 9px;
  border-radius: 999px;
  margin-right: 6px;
  line-height: 18px;
}
.tag.high {
  background: #fff2f0;
  color: #b4544a;
}
.tag.mid {
  background: #fffbe6;
  color: #a3812f;
}
.tag.low {
  background: #f0f9ff;
  color: #3f7d6a;
}
.time {
  color: #94a3b8;
  font-size: 12px;
}
.view-btn {
  color: #2563eb;
  font-size: 12.5px;
}
/* 骨架 */
.sk-bar {
  display: inline-block;
  height: 12px;
  border-radius: 6px;
  background: linear-gradient(90deg, #f5f3ee 25%, #faf9f5 37%, #f5f3ee 63%);
  background-size: 400% 100%;
  animation: sk-shine 1.4s ease infinite;
}
@keyframes sk-shine {
  0% {
    background-position: 100% 50%;
  }
  100% {
    background-position: 0 50%;
  }
}
:deep(.sk-table .el-table__row) {
  height: 52px;
}
/* 空状态 */
.empty-card {
  padding: 46px 20px 40px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}
.empty-ico {
  width: 52px;
  height: 52px;
  margin-bottom: 6px;
}
.empty-title {
  font-size: 13.5px;
  font-weight: 600;
  color: #475569;
}
.empty-sub {
  font-size: 11.5px;
  color: #a39d92;
}
.empty-btn {
  margin-top: 10px;
  padding: 6px 16px;
  border-radius: 8px;
  border: 1px solid #e6e2da;
  background: #fff;
  font-size: 12px;
  color: #475569;
  cursor: pointer;
  transition: all 0.2s;
}
.empty-btn:hover {
  border-color: #c7d9f8;
  background: #f7fafd;
  color: #1e4fa8;
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
</style>
