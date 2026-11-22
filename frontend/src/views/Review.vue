<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { useReviewStore } from '../stores/review'

interface Judgment {
  clause: string
  present: boolean
  verdict: string
  severity: string
  reason: string
  revision?: string
}

const store = useReviewStore()
const file = ref<File | null>(null)

const clauseTypes = [
  '付款条款',
  '违约金',
  '争议解决',
  '保密条款',
  '知识产权',
  '合同终止',
  '责任上限',
  '验收条款',
  '交付条款',
  '发票条款',
  '竞业限制',
  '通知送达',
  '不可抗力',
]

onMounted(() => store.loadContracts())

watch(
  () => store.error,
  (v) => {
    if (v) {
      ElMessage.error(v)
      store.error = ''
    }
  }
)

function onFile(e: Event) {
  const f = (e.target as HTMLInputElement).files?.[0] || null
  file.value = f
  if (f) store.selected = ''
}

function onDrop(e: DragEvent) {
  const f = e.dataTransfer?.files?.[0] || null
  if (f) {
    file.value = f
    store.selected = ''
  }
}

function start() {
  store.start(file.value)
}

const stageLabels = ['① 解析', '② 抽取', '③ 判定', '④ 修订']

const verdictColor: Record<string, string> = {
  合规: '#16a34a',
  偏离: '#d97706',
  缺失: '#64748b',
  冲突: '#dc2626',
}
const severityColor: Record<string, string> = { 高: '#dc2626', 中: '#d97706', 低: '#16a34a' }

function badgeStyle(color: string) {
  return { background: color + '18', color, border: '1px solid ' + color + '40' }
}
</script>

<template>
  <div class="page">
    <div class="page-head">
      <div class="page-icon" style="background: #eff6ff; color: #2563eb">🔍</div>
      <div>
        <h1 class="page-title">合同审查</h1>
        <p class="page-sub">上传合同，自动识别 13 类核心条款并判定风险，给出修订建议。</p>
      </div>
    </div>

    <div class="layout">
      <!-- 主列 -->
      <div class="main-col">
        <!-- 选择合同 -->
        <el-card shadow="never" class="card">
          <div class="upload-row">
            <label class="drop-zone" :class="{ filled: !!file }" @dragover.prevent @drop.prevent="onDrop">
              <input type="file" accept=".docx" class="hidden-input" @change="onFile" />
              <div class="dz-icon">{{ file ? '✅' : '📄' }}</div>
              <div class="dz-title">{{ file ? file.name : '点击选择 .docx 合同' }}</div>
              <div class="dz-sub">{{ file ? '已选择，可点此更换' : '或把文件拖到这里' }}</div>
            </label>

            <div class="divider"><span>或</span></div>

            <div class="sample">
              <label class="lbl">选示例合同</label>
              <el-select
                v-model="store.selected"
                placeholder="选择示例"
                filterable
                style="width: 100%"
                @change="file = null"
              >
                <el-option v-for="c in store.contracts" :key="c" :label="c" :value="c" />
              </el-select>
              <div class="sample-tip">共 {{ store.contracts.length }} 份示范文本</div>
            </div>
          </div>
        </el-card>

        <!-- 配置 -->
        <el-card shadow="never" class="card">
          <div class="cfg-row">
            <div class="cfg-field">
              <label class="lbl">关注点（可选）</label>
              <el-input v-model="store.focus" placeholder="例如：重点关注付款、违约责任与争议解决" />
            </div>
            <el-button type="primary" size="large" :loading="store.loading" @click="start">开始审查</el-button>
          </div>
          <div class="tip">提示：审查在后台进行，切到其他页面再回来也不会中断。</div>
        </el-card>

        <!-- 进度 -->
        <el-card v-if="store.loading" shadow="never" class="card">
          <div class="progress-head">
            <span>审查进度</span>
            <span class="pct">{{ Math.round(store.progress) }}%</span>
          </div>
          <el-progress :percentage="store.progress" :show-text="false" :stroke-width="8" />
          <div class="stages">
            <div v-for="(s, i) in stageLabels" :key="s" class="stage" :class="{ active: i <= store.stage }">{{ s }}</div>
          </div>
        </el-card>

        <!-- 结果 -->
        <template v-if="store.result">
          <div class="overview">
            <div class="ov-card">
              <div class="ov-num" style="color: #dc2626">{{ store.result.overview.high }}</div>
              <div class="ov-label">高风险</div>
            </div>
            <div class="ov-card">
              <div class="ov-num" style="color: #d97706">{{ store.result.overview.mid }}</div>
              <div class="ov-label">中风险</div>
            </div>
            <div class="ov-card">
              <div class="ov-num" style="color: #16a34a">{{ store.result.overview.low }}</div>
              <div class="ov-label">低风险</div>
            </div>
          </div>

          <el-card shadow="never" class="card">
            <div class="table-wrap">
              <table class="tbl">
                <thead>
                  <tr>
                    <th>条款</th>
                    <th>判定</th>
                    <th>等级</th>
                    <th>问题 / 修订建议</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="j in (store.result.judgments as Judgment[])" :key="j.clause">
                    <td class="clause">{{ j.clause }}</td>
                    <td>
                      <span class="badge" :style="badgeStyle(verdictColor[j.verdict] || '#64748b')">{{ j.verdict }}</span>
                    </td>
                    <td>
                      <span class="badge" :style="badgeStyle(severityColor[j.severity] || '#64748b')">{{ j.severity }}</span>
                    </td>
                    <td>
                      <div class="reason">{{ j.reason }}</div>
                      <div v-if="j.revision" class="revision">📝 修订建议：{{ j.revision }}</div>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </el-card>
        </template>

        <!-- 空状态 -->
        <el-card v-else-if="!store.loading" shadow="never" class="card empty-card">
          <div class="empty-state">
            <div class="empty-icon">📄</div>
            <div class="empty-title">还没有审查结果</div>
            <p>选择一份示例合同，或上传你的 .docx 合同，然后点「开始审查」。</p>
          </div>
        </el-card>
      </div>

      <!-- 侧栏 -->
      <aside class="side-col">
        <el-card shadow="never" class="card">
          <div class="side-title">覆盖的 13 类核心条款</div>
          <div class="clause-list">
            <span v-for="c in clauseTypes" :key="c" class="clause-tag">{{ c }}</span>
          </div>
        </el-card>

        <el-card shadow="never" class="card">
          <div class="side-title">审查说明</div>
          <ul class="notes">
            <li>判定结果：<b>合规 / 偏离 / 缺失 / 冲突</b></li>
            <li>每条给出原文定位与修订建议</li>
            <li>风险等级分高 / 中 / 低</li>
            <li>审查在后台进行，切换页面不中断</li>
          </ul>
        </el-card>
      </aside>
    </div>
  </div>
</template>

<style scoped>
.layout {
  display: grid;
  grid-template-columns: 1fr 300px;
  gap: 16px;
  align-items: start;
}
.main-col {
  display: flex;
  flex-direction: column;
  gap: 16px;
  min-width: 0;
}
.side-col {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.card {
  border-radius: 16px;
}

/* 上传区 */
.upload-row {
  display: flex;
  align-items: center;
  gap: 18px;
}
.drop-zone {
  flex: 1;
  border: 1.5px dashed #cbd5e1;
  border-radius: 14px;
  padding: 26px 20px;
  text-align: center;
  cursor: pointer;
  transition: all 0.2s;
  background: #fbfcfe;
}
.drop-zone:hover {
  border-color: #2563eb;
  background: #f5f8ff;
}
.drop-zone.filled {
  border-style: solid;
  border-color: #bbf7d0;
  background: #f0fdf4;
}
.hidden-input {
  display: none;
}
.dz-icon {
  font-size: 26px;
  margin-bottom: 8px;
}
.dz-title {
  font-size: 14px;
  font-weight: 600;
  color: #0f172a;
  word-break: break-all;
}
.dz-sub {
  font-size: 12px;
  color: #94a3b8;
  margin-top: 4px;
}
.divider {
  color: #cbd5e1;
  font-size: 12px;
}
.sample {
  flex: 1;
  min-width: 0;
}
.sample-tip {
  font-size: 11px;
  color: #94a3b8;
  margin-top: 6px;
}

/* 配置 */
.cfg-row {
  display: flex;
  gap: 16px;
  align-items: flex-end;
}
.cfg-field {
  flex: 1;
}
.lbl {
  display: block;
  font-size: 12px;
  color: #64748b;
  margin-bottom: 6px;
}
.tip {
  margin-top: 10px;
  font-size: 12px;
  color: #94a3b8;
}

/* 进度 */
.progress-head {
  display: flex;
  justify-content: space-between;
  font-size: 14px;
  margin-bottom: 10px;
}
.pct {
  color: #1d4ed8;
  font-weight: 700;
}
.stages {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 8px;
  margin-top: 14px;
}
.stage {
  text-align: center;
  font-size: 12px;
  padding: 6px;
  border-radius: 8px;
  background: #f8fafc;
  color: #94a3b8;
}
.stage.active {
  background: #eff6ff;
  color: #1d4ed8;
  font-weight: 600;
}

/* 概览 */
.overview {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 14px;
}
.ov-card {
  background: #fff;
  border: 1px solid #e8edf5;
  border-radius: 16px;
  padding: 18px;
  text-align: center;
}
.ov-num {
  font-size: 28px;
  font-weight: 800;
}
.ov-label {
  font-size: 12px;
  color: #94a3b8;
  margin-top: 4px;
}

/* 表格 */
.table-wrap {
  overflow-x: auto;
}
.tbl {
  width: 100%;
  border-collapse: collapse;
  font-size: 14px;
}
.tbl th {
  text-align: left;
  padding: 10px 12px;
  background: #f8fafc;
  color: #475569;
  font-weight: 500;
}
.tbl td {
  padding: 12px;
  border-bottom: 1px solid #f1f5f9;
  vertical-align: top;
}
.clause {
  font-weight: 600;
  white-space: nowrap;
}
.badge {
  display: inline-block;
  font-size: 12px;
  padding: 2px 8px;
  border-radius: 6px;
}
.reason {
  color: #475569;
  line-height: 1.6;
}
.revision {
  margin-top: 6px;
  font-size: 12px;
  color: #1d4ed8;
  background: #eff6ff;
  border-radius: 8px;
  padding: 8px 10px;
  line-height: 1.6;
}

/* 空状态 */
.empty-card {
  min-height: 260px;
  display: flex;
  align-items: center;
  justify-content: center;
}
.empty-state {
  text-align: center;
  padding: 20px;
}
.empty-icon {
  font-size: 40px;
  margin-bottom: 10px;
}
.empty-title {
  font-size: 16px;
  font-weight: 600;
  color: #0f172a;
  margin-bottom: 6px;
}
.empty-state p {
  font-size: 13px;
  color: #94a3b8;
  margin: 0;
}

/* 侧栏 */
.side-title {
  font-size: 13px;
  font-weight: 600;
  color: #0f172a;
  margin-bottom: 12px;
}
.clause-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.clause-tag {
  font-size: 11.5px;
  color: #475569;
  background: #f8fafc;
  border: 1px solid #e8edf5;
  border-radius: 6px;
  padding: 3px 8px;
}
.notes {
  margin: 0;
  padding-left: 18px;
  font-size: 12px;
  color: #64748b;
  line-height: 2;
}
.notes b {
  color: #334155;
}

@media (max-width: 1100px) {
  .layout {
    grid-template-columns: 1fr;
  }
}
</style>
