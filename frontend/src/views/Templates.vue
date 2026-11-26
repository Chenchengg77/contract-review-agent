<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { renderAsync } from 'docx-preview'
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
const docxContainer = ref<HTMLElement | null>(null)
const docxError = ref('')
const zoom = ref(1)

function setZoom(delta: number) {
  zoom.value = Math.min(1.6, Math.max(0.4, Math.round((zoom.value + delta) * 10) / 10))
}

function resetZoom() {
  zoom.value = 1
}

function fitWidth() {
  const el = docxContainer.value
  if (!el) return
  const page = el.querySelector('.docx-wrapper > section.docx') as HTMLElement | null
  if (!page) return
  // 用内容实际宽度，避免测量过早拿到偏小的值
  const w = Math.max(page.offsetWidth || 0, page.scrollWidth || 0, 700)
  const scrollEl = el.closest('.docx-scroll') as HTMLElement | null
  const avail = (scrollEl?.clientWidth || el.clientWidth) - 32
  if (avail > 0) {
    zoom.value = Math.min(1.2, Math.max(0.35, Math.round((avail / w) * 100) / 100))
  }
}

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

// 低饱和分类配色（浅底 + 深字 + 圆点）
const CAT: Record<string, { bg: string; fg: string; dot: string }> = {
  买卖: { bg: '#fff8ed', fg: '#b45309', dot: '#f0b45e' },
  建设: { bg: '#eff6ff', fg: '#1e4fa8', dot: '#7aa5e8' },
  租赁: { bg: '#eefbf3', fg: '#0f7a52', dot: '#6fc79a' },
  承揽: { bg: '#f5f3ff', fg: '#5b46b8', dot: '#a795e8' },
  服务: { bg: '#eefbf8', fg: '#0f766e', dot: '#66c9bd' },
  其他: { bg: '#f7f8fa', fg: '#4b5563', dot: '#b3bac5' },
  示例: { bg: '#fefce8', fg: '#a16207', dot: '#e5c76b' },
  自定义: { bg: '#fdf4f8', fg: '#9d174d', dot: '#e59ab8' },
}
const catStyle = (c: string) => {
  const k = CAT[c] || CAT['其他']
  return { background: k.bg, color: k.fg }
}
const catDot = (c: string) => (CAT[c] || CAT['其他']).dot

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

function onResize() {
  if (previewOpen.value) fitWidth()
}
onMounted(() => window.addEventListener('resize', onResize))
onBeforeUnmount(() => window.removeEventListener('resize', onResize))

async function openPreview(t: Template) {
  previewTitle.value = t.title
  previewBlocks.value = []
  docxError.value = ''
  previewOpen.value = true
  previewLoading.value = true
  await nextTick()
  try {
    const resp = await api.get('/templates/download', {
      params: { name: t.name },
      responseType: 'blob',
    })
    if (docxContainer.value) {
      docxContainer.value.innerHTML = ''
      await renderAsync(resp.data, docxContainer.value, null, {
        className: 'docx',
        inWrapper: true,
        breakPages: true,
        ignoreWidth: false,
        ignoreHeight: false,
        renderHeaders: true,
        renderFooters: true,
        // 忽略 Word 记录的「上次分页位置」，避免多出空白页
        ignoreLastRenderedPageBreak: true,
      })
      await nextTick()

      // 清理空白页（开头/中间/末尾都可能出现，保留至少一页）
      const pages = Array.from(
        docxContainer.value?.querySelectorAll('.docx-wrapper > section.docx') || []
      ) as HTMLElement[]
      const isBlank = (el: HTMLElement) => {
        const txt = (el.textContent || '').replace(/\s/g, '')
        const hasMedia = !!el.querySelector('img, table, svg, canvas')
        return txt.length <= 1 && !hasMedia
      }
      const blankPages = pages.filter(isBlank)
      // 只有还存在非空白页时才删，避免把空文档删光
      if (blankPages.length < pages.length) blankPages.forEach((p) => p.remove())

      // 等布局稳定后多次测量，保证整页可见
      setTimeout(fitWidth, 120)
      setTimeout(fitWidth, 450)
    }
  } catch {
    docxError.value = '文档渲染失败，已切换为文本预览'
    try {
      const { data } = await api.get('/templates/preview', { params: { name: t.name } })
      previewBlocks.value = data.blocks || []
    } catch {
      ElMessage.error('预览加载失败')
    }
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

function resetFilters() {
  search.value = ''
  category.value = '全部'
}

// 按「纸页」切分：每页约 46 个段落块
const PER_PAGE = 46
const pages = computed<any[][]>(() => {
  const out: any[][] = []
  const blocks = previewBlocks.value || []
  for (let i = 0; i < blocks.length; i += PER_PAGE) out.push(blocks.slice(i, i + PER_PAGE))
  return out.length ? out : [[]]
})
</script>

<template>
  <div class="page">
    <div class="page-head head">
      <div class="head-left">
        <div class="page-icon">
          <svg viewBox="0 0 24 24" fill="none" stroke="#14161a" stroke-width="1.3">
            <path d="M6.5 3.5h7L18 8v12.5h-11.5z" stroke-linejoin="round" />
            <path d="M13.5 3.5V8H18" stroke-linejoin="round" />
            <path d="M9 12h6M9 15.2h6M9 18.2h3.5" stroke-linecap="round" />
          </svg>
        </div>
        <div>
          <h1 class="page-title">合同模板库</h1>
          <p class="page-sub">标准合同模板管理，提供多种行业范本</p>
        </div>
      </div>
      <div class="actions">
        <el-input v-model="search" placeholder="搜索模板名称…" class="search" style="width: 220px" clearable />
        <button class="create-btn" @click="pickFile">+ 自定义模板</button>
        <input ref="fileInput" type="file" accept=".docx" style="display: none" @change="onFile" />
      </div>
    </div>

    <div class="tabs">
      <button
        v-for="c in categories"
        :key="c"
        class="pill"
        :class="{ active: category === c }"
        @click="category = c"
      >
        <i v-if="c !== '全部'" class="pill-dot" :style="{ background: catDot(c) }"></i>
        {{ c }}
        <span class="pill-count">{{ countOf(c) }}</span>
      </button>
    </div>

    <transition name="fade" mode="out-in">
      <div :key="category + search" class="grid">
        <!-- 骨架屏 -->
        <template v-if="loading">
          <div v-for="i in 6" :key="'sk' + i" class="card sk">
            <div class="sk-top"><span class="sk-block sk-ico"></span><span class="sk-block sk-badge"></span></div>
            <div class="sk-block sk-title"></div>
            <div class="sk-block sk-meta"></div>
            <div class="sk-block sk-line"></div>
            <div class="sk-block sk-line short"></div>
          </div>
        </template>

        <template v-else>
          <div v-for="t in filtered" :key="t.name" class="card">
            <div class="card-top">
              <div class="icon" :style="{ background: catStyle(t.category).background }">
                <svg viewBox="0 0 24 24" fill="none" :stroke="catStyle(t.category).color" stroke-width="1.3">
                  <path d="M7 3.5h6.5L18 8v12.5H7z" stroke-linejoin="round" />
                  <path d="M13 3.5V8h5" stroke-linejoin="round" />
                  <path d="M9.4 12h5.4M9.4 15.2h5.4M9.4 18.2h3" stroke-linecap="round" />
                </svg>
              </div>
              <span class="version">v1.0</span>
            </div>

            <div class="name" :title="t.title">{{ t.title }}</div>

            <div class="meta">
              <span class="tag-cat" :style="catStyle(t.category)">{{ t.category }}</span>
              <span class="tag-count">{{ t.clause_count }} 条</span>
            </div>

            <el-tooltip :content="t.description" placement="top" :disabled="!t.description">
              <p class="desc">{{ t.description }}</p>
            </el-tooltip>

            <div class="card-actions">
              <button class="link" @click="openPreview(t)">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.4">
                  <circle cx="11" cy="11" r="6.5" />
                  <path d="m16 16 4 4" stroke-linecap="round" />
                </svg>
                预览
              </button>
              <button class="link" @click="download(t)">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.4">
                  <path d="M12 4v10m0 0 3.5-3.5M12 14l-3.5-3.5" stroke-linecap="round" stroke-linejoin="round" />
                  <path d="M5 17.5V20h14v-2.5" stroke-linecap="round" />
                </svg>
                下载
              </button>
            </div>
          </div>

          <!-- 无结果 -->
          <div v-if="!filtered.length" class="empty-card">
            <svg class="empty-ico" viewBox="0 0 48 48" fill="none" stroke="#c9c4ba" stroke-width="1.5">
              <rect x="10" y="8" width="22" height="30" rx="2" />
              <path d="M16 16h10M16 21h10M16 26h6" stroke-linecap="round" />
              <circle cx="33" cy="33" r="6" />
              <path d="m37.5 37.5 4 4" stroke-linecap="round" />
            </svg>
            <div class="empty-title">没有匹配的模板</div>
            <div class="empty-sub">换个关键词，或清空筛选看看全部模板</div>
            <button class="empty-btn" @click="resetFilters">重置筛选</button>
          </div>
        </template>
      </div>
    </transition>

    <el-dialog
      v-model="previewOpen"
      :title="previewTitle"
      width="min(1100px, 94vw)"
      top="3vh"
      class="doc-dialog"
    >
      <div v-loading="previewLoading" class="doc-wrap">
        <div class="doc-toolbar">
          <span class="doc-name">{{ previewTitle }}</span>
          <div class="doc-tools">
            <span class="doc-meta">{{ docxError ? '文本预览（渲染失败）' : '原始格式' }}</span>
            <button class="zbtn" title="缩小" @click="setZoom(-0.1)">−</button>
            <span class="zval">{{ Math.round(zoom * 100) }}%</span>
            <button class="zbtn" title="放大" @click="setZoom(0.1)">＋</button>
            <button class="zbtn wide" @click="resetZoom">100%</button>
            <button class="zbtn wide" @click="fitWidth">适应宽度</button>
          </div>
        </div>

        <div class="docx-scroll">
          <div ref="docxContainer" class="docx-container" :style="{ zoom: zoom }"></div>

          <!-- 兜底文本预览 -->
          <div v-if="docxError" class="fallback">
            <div class="fallback-tip">{{ docxError }}</div>
            <div v-for="(page, pi) in pages" :key="pi" class="doc-page">
              <div class="page-body">
                <template v-for="(b, i) in page" :key="i">
                  <div
                    v-if="b.type === 'paragraph'"
                    class="p"
                    :class="{
                      heading: b.clause_no,
                      title: pi === 0 && i === 0 && !b.clause_no && (b.text || '').length < 40,
                    }"
                  >
                    <strong v-if="b.clause_no">{{ b.clause_no }}</strong>
                    <span>{{ b.clause_no ? b.text.slice(b.clause_no.length).trim() : b.text }}</span>
                  </div>
                  <table v-else-if="b.type === 'table'" class="p-table">
                    <tbody>
                      <tr v-for="(row, ri) in b.rows" :key="ri">
                        <td v-for="(cell, ci) in row" :key="ci">{{ cell }}</td>
                      </tr>
                    </tbody>
                  </table>
                </template>
                <div v-if="!page.length" class="doc-empty">（空文档）</div>
              </div>
              <div class="page-no">— {{ pi + 1 }} / {{ pages.length }} —</div>
            </div>
          </div>
        </div>
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
.page-icon {
  width: 44px;
  height: 44px;
  border-radius: 12px;
  background: #f8f7f3;
  border: 1px solid #ece7de;
  display: flex;
  align-items: center;
  justify-content: center;
  animation: icon-breath 3.6s ease-in-out infinite;
}
.page-icon svg {
  width: 24px;
  height: 24px;
}
@keyframes icon-breath {
  0%,
  100% {
    opacity: 0.86;
  }
  50% {
    opacity: 1;
  }
}
.page-title {
  font-weight: 600;
  letter-spacing: 0.5px;
}
.actions {
  display: flex;
  gap: 10px;
  align-items: center;
}
/* 搜索框：柔和蓝光 */
.search :deep(.el-input__wrapper) {
  border-radius: 8px;
  box-shadow: 0 0 0 1px #e6e2da inset;
  transition: box-shadow 0.2s;
}
.search :deep(.el-input__wrapper:hover) {
  box-shadow: 0 0 0 1px #d8d2c6 inset;
}
.search :deep(.el-input__wrapper.is-focus) {
  box-shadow:
    0 0 0 1px #c7d9f8 inset,
    0 0 0 3px rgba(96, 165, 250, 0.1);
}
/* 自定义模板按钮 */
.create-btn {
  padding: 8px 16px;
  border-radius: 8px;
  border: 1px solid #14161a;
  background: #14161a;
  color: #f7f5f1;
  font-size: 13px;
  letter-spacing: 0.5px;
  cursor: pointer;
  transition:
    background 0.2s,
    box-shadow 0.2s,
    transform 0.12s;
}
.create-btn:hover {
  background: #26292f;
  border-color: #26292f;
  box-shadow: 0 0 0 4px rgba(20, 22, 26, 0.06);
}
.create-btn:active {
  transform: scale(0.98);
}
/* 分类胶囊 */
.tabs {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 20px;
}
.pill {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  padding: 6px 14px;
  border-radius: 999px;
  border: 1px solid #e6e2da;
  background: #fff;
  font-size: 12.5px;
  color: #6b6f76;
  cursor: pointer;
  transition:
    background 0.2s,
    border-color 0.2s,
    color 0.2s;
}
.pill:hover {
  background: #f7fafd;
  border-color: #d6e2f7;
}
.pill.active {
  background: #eef4fc;
  border-color: #c7d9f8;
  color: #1e4fa8;
  font-weight: 600;
}
.pill-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  display: inline-block;
}
.pill-count {
  font-size: 11px;
  color: #a8a29a;
}
.pill.active .pill-count {
  color: #5b7fb8;
}
/* 网格 */
.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(270px, 1fr));
  gap: 16px;
  min-height: 120px;
}
/* 卡片 */
.card {
  background: #fff;
  border: 1px solid #eae6de;
  border-radius: 12px;
  padding: 18px;
  display: flex;
  flex-direction: column;
  transition:
    transform 0.25s ease,
    box-shadow 0.25s ease,
    border-color 0.25s ease;
}
.card:hover {
  transform: translateY(-2px);
  border-color: #d6e2f7;
  box-shadow:
    0 2px 4px rgba(15, 23, 42, 0.03),
    0 16px 32px -24px rgba(15, 23, 42, 0.45);
}
.card-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 14px;
}
.icon {
  width: 34px;
  height: 34px;
  border-radius: 9px;
  display: flex;
  align-items: center;
  justify-content: center;
}
.icon svg {
  width: 19px;
  height: 19px;
}
.version {
  font-size: 10.5px;
  color: #8a867d;
  background: #f6f4ef;
  border: 1px solid #ece7de;
  border-radius: 6px;
  padding: 2px 7px;
  letter-spacing: 0.4px;
}
.name {
  font-size: 14px;
  font-weight: 600;
  color: #14161a;
  line-height: 1.5;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  margin-bottom: 10px;
}
.meta {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 10px;
}
.tag-cat {
  font-size: 11px;
  padding: 2px 9px;
  border-radius: 999px;
  font-weight: 500;
}
.tag-count {
  font-size: 11px;
  color: #8a867d;
  background: #f7f6f2;
  border: 1px solid #ece7de;
  border-radius: 999px;
  padding: 2px 9px;
}
.desc {
  font-size: 12px;
  line-height: 1.8;
  color: #8a867d;
  margin: 0 0 14px;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  min-height: 43px;
}
.card-actions {
  margin-top: auto;
  display: flex;
  gap: 18px;
  padding-top: 12px;
  border-top: 1px solid #f4f2ec;
}
.link {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  background: none;
  border: none;
  padding: 0;
  font-size: 12px;
  color: #8a867d;
  cursor: pointer;
  transition: color 0.2s;
}
.link svg {
  width: 14px;
  height: 14px;
  transition: stroke 0.2s;
}
.link:hover {
  color: #2563eb;
}
/* 骨架屏 */
.card.sk {
  pointer-events: none;
}
.sk-block {
  display: block;
  background: linear-gradient(90deg, #f5f3ee 25%, #faf9f5 37%, #f5f3ee 63%);
  background-size: 400% 100%;
  animation: sk-shine 1.4s ease infinite;
  border-radius: 6px;
}
@keyframes sk-shine {
  0% {
    background-position: 100% 50%;
  }
  100% {
    background-position: 0 50%;
  }
}
.sk-top {
  display: flex;
  justify-content: space-between;
  margin-bottom: 14px;
}
.sk-ico {
  width: 34px;
  height: 34px;
  border-radius: 9px;
}
.sk-badge {
  width: 38px;
  height: 18px;
}
.sk-title {
  height: 14px;
  width: 78%;
  margin-bottom: 12px;
}
.sk-meta {
  height: 12px;
  width: 45%;
  margin-bottom: 14px;
}
.sk-line {
  height: 10px;
  width: 100%;
  margin-bottom: 8px;
}
.sk-line.short {
  width: 60%;
}
/* 空状态 */
.empty-card {
  grid-column: 1 / -1;
  background: #fff;
  border: 1px solid #eae6de;
  border-radius: 12px;
  padding: 54px 20px;
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
  margin-top: 12px;
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
/* 过渡 */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.22s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
/* docx 原样渲染 */
:global(.doc-dialog .el-dialog__body) {
  padding: 0 12px 10px;
}
.doc-tools {
  display: flex;
  align-items: center;
  gap: 6px;
}
.zbtn {
  border: 1px solid #e6e2da;
  background: #fff;
  color: #475569;
  border-radius: 6px;
  min-width: 26px;
  height: 24px;
  font-size: 12px;
  line-height: 1;
  cursor: pointer;
  padding: 0 7px;
  transition: all 0.15s;
}
.zbtn.wide {
  padding: 0 10px;
  font-size: 11.5px;
}
.zbtn:hover {
  border-color: #c7d9f8;
  background: #f7fafd;
  color: #1e4fa8;
}
.zval {
  font-size: 11.5px;
  color: #64748b;
  min-width: 38px;
  text-align: center;
}
.docx-scroll {
  background: #eceff3;
  border-radius: 8px;
  max-height: 74vh;
  overflow: auto;
  padding: 10px 0;
}
.docx-container :deep(.docx-wrapper) {
  background: #eceff3 !important;
  padding: 12px 0 18px !important;
}
.docx-container :deep(.docx-wrapper > section.docx) {
  box-shadow:
    0 1px 2px rgba(15, 23, 42, 0.12),
    0 12px 28px -18px rgba(15, 23, 42, 0.35) !important;
  margin-bottom: 18px !important;
}
.docx-container :deep(.docx) {
  color: #1a1a1a;
}
.fallback {
  padding: 0 12px;
}
.fallback-tip {
  font-size: 11.5px;
  color: #b45309;
  background: #fffbeb;
  border: 1px solid #fde68a;
  border-radius: 6px;
  padding: 6px 10px;
  margin-bottom: 12px;
}
/* Word 风格预览 */
.doc-wrap {
  display: flex;
  flex-direction: column;
}
.doc-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 11.5px;
  color: #94a3b8;
  padding: 0 2px 10px;
}
.doc-name {
  max-width: 70%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.doc-scroll {
  background: #eceff3;
  border-radius: 8px;
  padding: 22px 0;
  max-height: 68vh;
  overflow: auto;
}
.doc-page {
  width: 660px;
  max-width: calc(100% - 32px);
  margin: 0 auto 18px;
  background: #fff;
  box-shadow:
    0 1px 2px rgba(15, 23, 42, 0.12),
    0 10px 26px -14px rgba(15, 23, 42, 0.28);
  padding: 58px 64px 40px;
  min-height: 780px;
  display: flex;
  flex-direction: column;
}
.doc-page:last-child {
  margin-bottom: 0;
}
.page-body {
  flex: 1;
  font-family: 'SimSun', 'Songti SC', 'Noto Serif SC', Georgia, serif;
  font-size: 14px;
  line-height: 2.05;
  color: #1a1a1a;
}
.p {
  margin: 0 0 6px;
}
.p.heading {
  font-weight: 700;
  margin-top: 12px;
}
.p.heading strong {
  margin-right: 6px;
}
.p.title {
  text-align: center;
  font-size: 19px;
  font-weight: 700;
  letter-spacing: 3px;
  margin: 0 0 24px;
}
.p-table {
  width: 100%;
  border-collapse: collapse;
  margin: 10px 0;
  font-family: 'SimSun', 'Songti SC', serif;
  font-size: 12.5px;
}
.p-table td {
  border: 1px solid #b9b9b9;
  padding: 6px 9px;
  line-height: 1.7;
}
.page-no {
  text-align: center;
  font-family: 'SimSun', 'Songti SC', serif;
  font-size: 11px;
  color: #a8a29a;
  margin-top: 24px;
}
.doc-empty {
  font-size: 12px;
  color: #b3b0a8;
  padding: 20px 0;
}
@media (max-width: 760px) {
  .head {
    align-items: flex-start;
  }
  .actions {
    width: 100%;
  }
  .search {
    flex: 1;
  }
}
</style>
