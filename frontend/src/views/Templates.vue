<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '../api'

interface Template {
  name: string
  title: string
  category: string
  clause_count: number
  description: string
  headings: string[]
}

const templates = ref<Template[]>([])
const loading = ref(false)
const search = ref('')
const category = ref('全部')
const previewOpen = ref(false)
const previewTitle = ref('')
const previewBlocks = ref<any[]>([])
const previewLoading = ref(false)
const fileInput = ref<HTMLInputElement | null>(null)

const categories = computed(() => {
  const set = new Set(templates.value.map((t) => t.category))
  return ['全部', ...Array.from(set)]
})

function countOf(cat: string) {
  return cat === '全部' ? templates.value.length : templates.value.filter((t) => t.category === cat).length
}

const filtered = computed(() => {
  let list = templates.value
  if (category.value !== '全部') list = list.filter((t) => t.category === category.value)
  if (search.value.trim()) {
    const q = search.value.trim()
    list = list.filter((t) => t.title.includes(q) || t.name.includes(q))
  }
  return list
})

const ICONS: Record<string, string> = {
  买卖: '📦',
  租赁: '🏠',
  承揽: '🔧',
  服务: '🤝',
  建设: '🏗️',
  其他: '📄',
  示例: '🧪',
  自定义: '⭐',
}

async function load() {
  loading.value = true
  try {
    const { data } = await api.get('/templates', { params: { t: Date.now() } })
    templates.value = data.templates || []
  } catch {
    ElMessage.error('模板加载失败')
  } finally {
    loading.value = false
  }
}

onMounted(load)

async function openPreview(t: Template) {
  previewTitle.value = t.title
  previewBlocks.value = []
  previewOpen.value = true
  previewLoading.value = true
  try {
    const { data } = await api.get('/templates/preview', { params: { name: t.name } })
    previewBlocks.value = data.blocks || []
  } catch {
    ElMessage.error('预览加载失败')
  } finally {
    previewLoading.value = false
  }
}

function download(t: Template) {
  window.open('/api/templates/download?name=' + encodeURIComponent(t.name), '_blank')
}

function pickFile() {
  fileInput.value?.click()
}

async function onFile(e: Event) {
  const f = (e.target as HTMLInputElement).files?.[0]
  if (!f) return
  const fd = new FormData()
  fd.append('file', f)
  try {
    const { data } = await api.post('/templates/upload', fd)
    ElMessage.success('上传成功：' + data.name)
    await load()
  } catch (err: any) {
    ElMessage.error(err.response?.data?.detail || '上传失败')
  } finally {
    (e.target as HTMLInputElement).value = ''
  }
}
</script>

<template>
  <div class="page">
    <div class="page-head head">
      <div class="head-left">
        <div class="page-icon" style="background: #ecfdf5; color: #059669">📄</div>
        <div>
          <h1 class="page-title">合同模板库</h1>
          <p class="page-sub">标准合同模板管理，提供多种行业范本</p>
        </div>
      </div>
      <div class="actions">
        <el-input v-model="search" placeholder="搜索模板名称…" style="width: 220px" clearable />
        <el-button type="primary" @click="pickFile">+ 自定义模板</el-button>
        <input ref="fileInput" type="file" accept=".docx" style="display: none" @change="onFile" />
      </div>
    </div>

    <div class="tabs">
      <button
        v-for="c in categories"
        :key="c"
        class="tab"
        :class="{ active: category === c }"
        @click="category = c"
      >
        {{ c }} ({{ countOf(c) }})
      </button>
    </div>

    <div v-loading="loading" class="grid">
      <div v-for="t in filtered" :key="t.name" class="card">
        <div class="card-top">
          <div class="icon">{{ ICONS[t.category] || '📄' }}</div>
          <span class="version">v1.0</span>
        </div>
        <div class="name" :title="t.title">{{ t.title }}</div>
        <div class="meta">
          <span class="cat">{{ t.category }}</span>
          <span class="count">{{ t.clause_count }} 条</span>
        </div>
        <p class="desc">{{ t.description }}</p>
        <div class="card-actions">
          <button class="link" @click="openPreview(t)">预览</button>
          <button class="link" @click="download(t)">下载</button>
        </div>
      </div>
      <div v-if="!filtered.length && !loading" class="empty">没有匹配的模板</div>
    </div>

    <el-dialog v-model="previewOpen" :title="previewTitle" width="720px" top="6vh">
      <div v-loading="previewLoading" class="preview">
        <template v-for="(b, i) in previewBlocks" :key="i">
          <div v-if="b.type === 'paragraph'" class="para" :class="{ heading: b.clause_no }">
            <strong v-if="b.clause_no">{{ b.clause_no }}</strong>
            <span>{{ b.clause_no ? b.text.slice(b.clause_no.length).trim() : b.text }}</span>
          </div>
          <table v-else-if="b.type === 'table'" class="preview-table">
            <tbody>
              <tr v-for="(row, ri) in b.rows" :key="ri">
                <td v-for="(cell, ci) in row" :key="ci">{{ cell }}</td>
              </tr>
            </tbody>
          </table>
        </template>
        <div v-if="!previewBlocks.length && !previewLoading" class="empty">（空文档）</div>
      </div>
      <template #footer>
        <el-button @click="previewOpen = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.page {
  max-width: 1180px;
  margin: 0 auto;
  padding: 32px;
}
.head {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  gap: 16px;
  margin-bottom: 20px;
  flex-wrap: wrap;
}
.head-left {
  display: flex;
  align-items: center;
  gap: 14px;
}
h1 {
  margin: 0;
  font-size: 24px;
}
.sub {
  color: #64748b;
  font-size: 14px;
  margin: 4px 0 0;
}
.actions {
  display: flex;
  gap: 10px;
  align-items: center;
}
.tabs {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 20px;
}
.tab {
  border: 1px solid #e2e8f0;
  background: #fff;
  color: #475569;
  border-radius: 8px;
  padding: 7px 14px;
  font-size: 13px;
  cursor: pointer;
}
.tab.active {
  background: #1d4ed8;
  border-color: #1d4ed8;
  color: #fff;
}
.grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  min-height: 120px;
}
.card {
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 14px;
  padding: 18px;
  display: flex;
  flex-direction: column;
  transition: all 0.2s;
}
.card:hover {
  transform: translateY(-2px);
  box-shadow: 0 12px 24px -12px rgba(29, 78, 216, 0.2);
  border-color: #bfdbfe;
}
.card-top {
  display: flex;
  justify-content: space-between;
  margin-bottom: 12px;
}
.icon {
  width: 44px;
  height: 44px;
  border-radius: 12px;
  background: #eff6ff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
}
.version {
  font-size: 11px;
  color: #94a3b8;
  background: #f8fafc;
  padding: 2px 8px;
  border-radius: 6px;
  height: fit-content;
}
.name {
  font-weight: 600;
  font-size: 14px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  margin-bottom: 6px;
}
.meta {
  display: flex;
  gap: 8px;
  font-size: 12px;
  color: #94a3b8;
  margin-bottom: 8px;
}
.cat {
  color: #1d4ed8;
  background: #eff6ff;
  padding: 1px 6px;
  border-radius: 4px;
}
.desc {
  font-size: 12px;
  color: #94a3b8;
  line-height: 1.6;
  flex: 1;
  margin: 0 0 12px;
}
.card-actions {
  display: flex;
  gap: 14px;
  border-top: 1px solid #f1f5f9;
  padding-top: 10px;
}
.link {
  background: none;
  border: none;
  color: #1d4ed8;
  font-size: 12px;
  cursor: pointer;
}
.link:hover {
  text-decoration: underline;
}
.empty {
  grid-column: 1 / -1;
  text-align: center;
  color: #94a3b8;
  padding: 40px;
  font-size: 13px;
}
.preview {
  max-height: 62vh;
  overflow: auto;
  font-size: 13px;
  line-height: 1.8;
  color: #334155;
}
.para {
  padding: 2px 0;
}
.para.heading {
  margin-top: 10px;
  font-weight: 500;
  color: #0f172a;
}
.preview-table {
  border-collapse: collapse;
  margin: 8px 0;
  font-size: 12px;
}
.preview-table td {
  border: 1px solid #e2e8f0;
  padding: 4px 8px;
}
</style>
