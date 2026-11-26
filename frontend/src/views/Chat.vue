<script setup lang="ts">
import { computed, nextTick, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { marked } from 'marked'
import api from '../api'

interface Msg {
  role: 'user' | 'assistant'
  html: string
}

// 工具调用展示名
const TOOL_LABEL: Record<string, string> = {
  get_clause: '查合同条款',
  search_law: '查法条',
  calc_penalty: '算金额',
  get_review_summary: '读审查结论',
}

interface Conv {
  id: string
  title: string
  mode: 'contract' | 'law'
  contract: string
  log: Msg[]
  history: { role: string; content: string }[]
  updatedAt: number
}

const CONV_KEY = 'chat_conversations'

const mode = ref<'contract' | 'law'>('contract')
const contracts = ref<string[]>([])
const contract = ref('')
const input = ref('')
const messages = ref<Msg[]>([])
const history = ref<{ role: string; content: string }[]>([])
const sending = ref(false)
const convs = ref<Conv[]>([])
const currentId = ref<string | null>(null)
const box = ref<HTMLElement | null>(null)

const QUICK: Record<string, [string, string][]> = {
  contract: [
    ['违约金是怎么约定的？', '这份合同的违约金是怎么约定的？'],
    ['有没有责任上限？', '有没有责任上限？'],
    ['争议解决方式是什么？', '争议解决方式是什么？'],
    ['有哪些风险条款？', '这份合同有哪些风险条款？'],
  ],
  law: [
    ['劳动合同试用期多久？', '劳动合同试用期最长可以约定多久？'],
    ['违约金上限多少？', '法律对违约金的上限有什么规定？'],
    ['口头合同有效吗？', '口头订立的合同有效吗？'],
    ['预付费能退吗？', '商家预收款后不履行，预付款能退吗？'],
  ],
}

const quick = computed(() => QUICK[mode.value])

const hint = computed(() =>
  mode.value === 'law'
    ? '提示：法律问答基于内置法规库（民法典 / 劳动合同法 / 消保法精选），回答会引用法条。'
    : '提示：助手只基于当前合同原文回答，找不到会直接说「没找到」。'
)

onMounted(async () => {
  try {
    const [c, s] = await Promise.all([api.get('/contracts'), api.get('/me/stats')])
    contracts.value = c.data.contracts || []
    // 默认选「上次审查的那份」，更贴合使用习惯
    const last = s.data?.recent?.[0]?.filename
    if (contracts.value.length) {
      contract.value = last && contracts.value.includes(last) ? last : contracts.value[0]
    }
  } catch {
    /* ignore */
  }
  loadConvs()
})

function md(text: string): string {
  try {
    let html = marked.parse(text) as string
    // 把「第X条」变成可点击的引用
    html = html.replace(
      /第([一二三四五六七八九十百零〇0-9]+)条/g,
      '<span class="clause-link" data-clause="第$1条">第$1条</span>'
    )
    return html
  } catch {
    return text
  }
}

// —— 引用可点击：点击「第X条」查看原文 ——
const clauseVisible = ref(false)
const clauseTitle = ref('')
const clauseText = ref('')

async function onAnswerClick(e: MouseEvent) {
  const el = (e.target as HTMLElement).closest('.clause-link') as HTMLElement | null
  if (!el) return
  const clause = el.dataset.clause || ''
  if (!clause) return
  try {
    const { data } = await api.get('/clause_text', {
      params: { name: contract.value, clause },
    })
    clauseTitle.value = clause
    clauseText.value = data.text || '（未找到该条款原文）'
    clauseVisible.value = true
  } catch {
    ElMessage.error('获取条款原文失败')
  }
}

function scrollToBottom() {
  nextTick(() => {
    if (box.value) box.value.scrollTop = box.value.scrollHeight
  })
}

function setMode(m: 'contract' | 'law') {
  mode.value = m
  newConversation(false)
}

function newConversation(save = true) {
  if (save) persist()
  currentId.value = null
  messages.value = []
  history.value = []
  input.value = ''
}

function persist() {
  if (!messages.value.length) return
  const firstUser = history.value.find((m) => m.role === 'user')
  const conv: Conv = {
    id: currentId.value || 'c_' + Date.now(),
    title: (firstUser?.content || '新对话').slice(0, 22),
    mode: mode.value,
    contract: contract.value,
    log: JSON.parse(JSON.stringify(messages.value)),
    history: JSON.parse(JSON.stringify(history.value)),
    updatedAt: Date.now(),
  }
  const idx = convs.value.findIndex((c) => c.id === conv.id)
  if (idx >= 0) convs.value[idx] = conv
  else convs.value.unshift(conv)
  convs.value = convs.value.slice(0, 30)
  localStorage.setItem(CONV_KEY, JSON.stringify(convs.value))
  currentId.value = conv.id
}

function loadConvs() {
  try {
    convs.value = JSON.parse(localStorage.getItem(CONV_KEY) || '[]')
  } catch {
    convs.value = []
  }
}

function restore(c: Conv) {
  mode.value = c.mode
  contract.value = c.contract
  currentId.value = c.id
  messages.value = JSON.parse(JSON.stringify(c.log))
  history.value = JSON.parse(JSON.stringify(c.history))
  scrollToBottom()
}

function delConv(id: string) {
  convs.value = convs.value.filter((c) => c.id !== id)
  localStorage.setItem(CONV_KEY, JSON.stringify(convs.value))
  if (currentId.value === id) newConversation(false)
}

function clearConvs() {
  convs.value = []
  localStorage.removeItem(CONV_KEY)
  currentId.value = null
}

async function send() {
  const q = input.value.trim()
  if (!q || sending.value) return
  if (mode.value === 'contract' && !contract.value) {
    ElMessage.warning('请先选择一份合同')
    return
  }

  messages.value.push({ role: 'user', html: q })
  input.value = ''
  scrollToBottom()

  sending.value = true
  messages.value.push({ role: 'assistant', html: '思考中…' })
  const idx = messages.value.length - 1
  scrollToBottom()

  let answer = ''
  let citations: string[] = []
  let tools: any[] = []
  let lastRender = 0

  try {
    const url = mode.value === 'law' ? '/api/law_chat_stream' : '/api/chat_stream'
    const body =
      mode.value === 'law'
        ? { question: q, history: history.value }
        : { name: contract.value, question: q, history: history.value }

    const res = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: 'Bearer ' + (localStorage.getItem('token') || ''),
      },
      body: JSON.stringify(body),
    })
    if (!res.ok || !res.body) throw new Error('请求失败：' + res.status)

    const reader = res.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })
      const parts = buffer.split('\n\n')
      buffer = parts.pop() || ''
      for (const part of parts) {
        let ev = 'message'
        let data = ''
        for (const line of part.split('\n')) {
          if (line.startsWith('event:')) ev = line.slice(6).trim()
          else if (line.startsWith('data:')) data += line.slice(5).trim()
        }
        if (!data) continue
        let obj: any
        try {
          obj = JSON.parse(data)
        } catch {
          continue
        }
        if (ev === 'citations') {
          citations = obj.citations || []
        } else if (ev === 'tools') {
          tools = obj.tools || []
        } else if (ev === 'token') {
          answer += obj.text || ''
          const now = Date.now()
          if (now - lastRender > 120) {
            lastRender = now
            messages.value[idx].html = md(answer)
            scrollToBottom()
          }
        }
      }
    }

    const cites = citations.filter((c) => c && c !== '正文')
    const toolHtml = tools.length
      ? `<div class="tool-chips">${tools
          .map((t: any) => `<span class="tool-chip">${TOOL_LABEL[t.name] || t.name}</span>`)
          .join('')}</div>`
      : ''
    messages.value[idx].html =
      toolHtml +
      md(answer) +
      (cites.length ? `<div class="cites">引用：${cites.join('、')}</div>` : '')
    history.value.push({ role: 'user', content: q }, { role: 'assistant', content: answer })
    persist()
  } catch (e: any) {
    messages.value[idx].html = '出错了：' + (e.message || e)
  } finally {
    sending.value = false
    scrollToBottom()
  }
}
</script>

<template>
  <div class="chat-page">
    <!-- 左栏 -->
    <aside class="side">
      <div class="side-top">
        <div class="title">💬 AI 助手</div>
        <div class="model">模型：DeepSeek-Chat</div>
        <div class="mode-switch">
          <button :class="{ active: mode === 'contract' }" @click="setMode('contract')">📄 合同问答</button>
          <button :class="{ active: mode === 'law' }" @click="setMode('law')">📚 法律问答</button>
        </div>
        <div v-if="mode === 'contract'" class="field">
          <label>当前合同</label>
          <el-select v-model="contract" placeholder="选择合同" filterable style="width: 100%">
            <el-option v-for="c in contracts" :key="c" :label="c" :value="c" />
          </el-select>
        </div>
        <button class="new-btn" @click="newConversation()">+ 新对话</button>
      </div>

      <div class="conv-section">
        <div class="section-head">
          <span>历史对话</span>
          <button class="clear" @click="clearConvs">清空</button>
        </div>
        <div v-if="!convs.length" class="empty">暂无历史对话</div>
        <div
          v-for="c in convs"
          :key="c.id"
          class="conv-item"
          :class="{ active: c.id === currentId }"
          @click="restore(c)"
        >
          <div class="conv-title">{{ c.title }}</div>
          <div class="conv-meta">
            <span>{{ c.mode === 'law' ? '📚 法律' : '📄 合同' }}</span>
            <button class="del" @click.stop="delConv(c.id)">删除</button>
          </div>
        </div>
      </div>

      <div class="quick-section">
        <div class="section-head"><span>快捷问题</span></div>
        <button v-for="[label, q] in quick" :key="label" class="quick" @click="input = q; send()">{{ label }}</button>
        <div class="hint">{{ hint }}</div>
      </div>
    </aside>

    <!-- 右栏 -->
    <div class="main">
      <div ref="box" class="messages">
        <div v-if="!messages.length" class="empty-state">
          <div class="es-mark">问</div>
          <div class="es-title">{{ mode === 'law' ? '法律知识助手' : '合同 AI 助手' }}</div>
          <p>{{ hint }}</p>
          <div class="es-cards">
            <button
              v-for="[label, q] in quick"
              :key="label"
              class="es-card"
              @click="input = q; send()"
            >
              {{ label }}
            </button>
          </div>
        </div>
        <div v-for="(m, i) in messages" :key="i" class="msg" :class="m.role">
          <div class="bubble chat-text" v-html="m.html" @click="onAnswerClick"></div>
        </div>
      </div>
      <div class="input-bar">
        <div class="pill">
          <input
            v-model="input"
            :placeholder="mode === 'law' ? '输入法律问题…（Enter 发送）' : '问关于这份合同的问题…（Enter 发送）'"
            @keyup.enter="send"
          />
          <button class="send-round" :disabled="sending" @click="send">{{ sending ? '…' : '发送' }}</button>
        </div>
      </div>
    </div>

    <!-- 引用原文 -->
    <el-dialog v-model="clauseVisible" :title="clauseTitle || '条款原文'" width="640px">
      <pre class="clause-origin">{{ clauseText }}</pre>
    </el-dialog>
  </div>
</template>

<style scoped>
.chat-page {
  display: flex;
  height: calc(100vh - 64px);
  background: #faf8f4;
}
/* 可点击的条款引用 */
:deep(.clause-link) {
  color: #1d4ed8;
  cursor: pointer;
  border-bottom: 1px dashed #93c5fd;
  padding: 0 1px;
}
:deep(.clause-link:hover) {
  background: #eff6ff;
  border-radius: 3px;
}
.clause-origin {
  background: #f8fafc;
  border: 1px solid #eef2f7;
  border-radius: 10px;
  padding: 14px;
  font-size: 13px;
  line-height: 1.9;
  color: #334155;
  white-space: pre-wrap;
  word-break: break-word;
  max-height: 420px;
  overflow: auto;
  margin: 0;
}
.side {
  width: 288px;
  flex-shrink: 0;
  background: #fdfcf9;
  border-right: 1px solid #e6e2da;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.side-top {
  padding: 20px;
  border-bottom: 1px solid #ece7de;
}
.title {
  font-family: 'Noto Serif SC', 'Songti SC', 'SimSun', Georgia, serif;
  font-weight: 600;
  letter-spacing: 1px;
  color: #14161a;
}
.model {
  font-size: 11.5px;
  color: #a39d92;
  margin: 5px 0 14px;
  letter-spacing: 0.4px;
}
.mode-switch {
  display: flex;
  background: #f1ece4;
  border-radius: 2px;
  padding: 3px;
  margin-bottom: 14px;
}
.mode-switch button {
  flex: 1;
  border: none;
  background: none;
  padding: 7px 4px;
  border-radius: 2px;
  font-size: 12px;
  color: #7a746a;
  cursor: pointer;
  letter-spacing: 0.4px;
  transition:
    background 0.2s ease,
    color 0.2s ease,
    box-shadow 0.2s ease;
}
.mode-switch button.active {
  background: #fff;
  color: #14161a;
  font-weight: 600;
  box-shadow: 0 1px 3px rgba(20, 22, 26, 0.08);
}
.new-btn {
  width: 100%;
  margin-top: 12px;
  padding: 9px 0;
  background: #14161a;
  color: #f7f5f1;
  border: none;
  border-radius: 2px;
  font-size: 13px;
  letter-spacing: 2px;
  cursor: pointer;
  transition: background 0.2s;
}
.new-btn:hover {
  background: #26292f;
}
.field label {
  display: block;
  font-size: 12px;
  color: #64748b;
  margin-bottom: 6px;
}
.conv-section {
  padding: 14px 20px;
  border-bottom: 1px solid #f1f5f9;
  max-height: 240px;
  overflow: auto;
}
.section-head {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  color: #64748b;
  font-weight: 600;
  margin-bottom: 10px;
}
.clear {
  background: none;
  border: none;
  font-size: 11px;
  color: #94a3b8;
  cursor: pointer;
}
.clear:hover {
  color: #dc2626;
}
.empty {
  font-size: 11px;
  color: #cbd5e1;
}
.conv-item {
  padding: 8px 10px;
  border-radius: 8px;
  cursor: pointer;
  margin-bottom: 4px;
}
.conv-item:hover {
  background: #f8fafc;
}
.conv-item.active {
  background: #eff6ff;
}
.conv-title {
  font-size: 12px;
  color: #334155;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.conv-meta {
  display: flex;
  justify-content: space-between;
  font-size: 10px;
  color: #94a3b8;
  margin-top: 3px;
}
.del {
  background: none;
  border: none;
  font-size: 10px;
  color: #cbd5e1;
  cursor: pointer;
}
.del:hover {
  color: #dc2626;
}
.quick-section {
  padding: 14px 20px;
  flex: 1;
  overflow: auto;
}
.quick {
  display: block;
  width: 100%;
  text-align: left;
  font-size: 13px;
  color: #475569;
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 9px 12px;
  margin-bottom: 8px;
  cursor: pointer;
}
.quick:hover {
  border-color: #93c5fd;
  color: #1d4ed8;
}
.hint {
  font-size: 11px;
  color: #94a3b8;
  margin-top: 10px;
  line-height: 1.6;
}
.main {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
}
.messages {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.empty-state {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  padding: 0 24px;
}
.es-mark {
  width: 54px;
  height: 54px;
  border: 1px solid #14161a;
  display: flex;
  align-items: center;
  justify-content: center;
  font-family: 'Noto Serif SC', 'Songti SC', 'SimSun', Georgia, serif;
  font-size: 26px;
  font-weight: 600;
  color: #14161a;
  margin-bottom: 20px;
  position: relative;
  background: linear-gradient(135deg, #1e3a8a, #4f46e5 60%, #7c3aed);
  -webkit-background-clip: text;
  background-clip: text;
}
.es-mark::after {
  content: '';
  position: absolute;
  right: -1px;
  bottom: -1px;
  width: 8px;
  height: 8px;
  background: #b4442f;
}
.es-title {
  font-family: 'Noto Serif SC', 'Songti SC', 'SimSun', Georgia, serif;
  font-size: 22px;
  font-weight: 600;
  color: #14161a;
  margin-bottom: 10px;
  letter-spacing: 1.5px;
}
.empty-state p {
  max-width: 460px;
  font-size: 13px;
  line-height: 1.9;
  color: #8a867d;
  margin: 0 0 30px;
}
.es-cards {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
  max-width: 520px;
  width: 100%;
}
.es-card {
  background: #fff;
  border: 1px solid #e6e2da;
  border-radius: 2px;
  padding: 13px 16px;
  font-size: 12.5px;
  color: #14161a;
  text-align: left;
  cursor: pointer;
  letter-spacing: 0.4px;
  transition: all 0.18s;
}
.es-card:hover {
  border-color: #14161a;
  transform: translateY(-1px);
  box-shadow: 0 10px 24px -20px rgba(20, 22, 26, 0.6);
}
.msg {
  display: flex;
}
.msg.user {
  justify-content: flex-end;
}
.bubble {
  max-width: 75%;
  border-radius: 16px;
  padding: 12px 16px;
  font-size: 14px;
  line-height: 1.7;
}
.msg.user .bubble {
  background: #1d4ed8;
  color: #fff;
}
.msg.assistant .bubble {
  background: #fff;
  border: 1px solid #e2e8f0;
  color: #334155;
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
}
:deep(.cites) {
  font-size: 12px;
  color: #94a3b8;
  margin-top: 8px;
}
:deep(.tool-chips) {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 8px;
}
:deep(.tool-chip) {
  font-size: 10.5px;
  padding: 2px 8px;
  border-radius: 999px;
  background: #f1f5fb;
  border: 1px solid #e2eaf8;
  color: #4a6b9a;
}
.input-bar {
  border-top: 1px solid #e6e2da;
  background: #faf8f4;
  padding: 14px 20px;
}
.pill {
  display: flex;
  align-items: center;
  gap: 8px;
  background: #fff;
  border: 1px solid #e0dbd1;
  border-radius: 999px;
  padding: 4px 6px 4px 18px;
  transition: border-color 0.2s;
}
.pill:focus-within {
  border-color: #14161a;
}
.pill input {
  flex: 1;
  border: none;
  outline: none;
  background: transparent;
  font-size: 13.5px;
  padding: 9px 0;
  color: #14161a;
}
.pill input::placeholder {
  color: #b3b0a8;
}
.send-round {
  padding: 8px 18px;
  border-radius: 999px;
  background: #14161a;
  color: #f7f5f1;
  border: none;
  font-size: 12.5px;
  letter-spacing: 1.5px;
  cursor: pointer;
  transition: background 0.2s;
  flex-shrink: 0;
}
.send-round:hover {
  background: #26292f;
}
.send-round:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
</style>
