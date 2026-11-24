<script setup lang="ts">
import { onMounted, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { useCompareStore } from '../stores/compare'

const store = useCompareStore()

const stageLabels = ['① 解析 A', '② 解析 B', '③ 逐条比对', '④ 生成差异']

onMounted(() => store.loadContracts())

watch(
  () => store.error,
  (v) => {
    if (v) {
      ElMessage.warning(v)
      store.error = ''
    }
  }
)

function run() {
  store.run()
}

const changeColor: Record<string, string> = {
  修改: '#2563eb',
  新增: '#16a34a',
  删除: '#dc2626',
  相同: '#64748b',
}

function changeClass(change: string) {
  return change === '修改' ? 'row-modify' : change === '新增' ? 'row-add' : change === '删除' ? 'row-del' : ''
}

const total = () => {
  if (!store.result) return 1
  const s = store.result.summary
  return (s['修改'] || 0) + (s['新增'] || 0) + (s['删除'] || 0) + (s['相同'] || 0) || 1
}
</script>

<template>
  <div class="page">
    <div class="page-head">
      <div class="page-icon" style="background: #f5f3ff; color: #7c3aed">⚖️</div>
      <div>
        <h1 class="page-title">合同对比</h1>
        <p class="page-sub">选择两份合同，逐条比对 13 类条款的差异。</p>
      </div>
    </div>

    <el-card shadow="never" class="card">
      <div class="grid">
        <div>
          <label class="lbl">A 合同（原版）</label>
          <el-select v-model="store.a" placeholder="选择 A" filterable style="width: 100%">
            <el-option v-for="c in store.contracts" :key="c" :label="c" :value="c" />
          </el-select>
        </div>
        <div>
          <label class="lbl">B 合同（新版）</label>
          <el-select v-model="store.b" placeholder="选择 B" filterable style="width: 100%">
            <el-option v-for="c in store.contracts" :key="c" :label="c" :value="c" />
          </el-select>
        </div>
        <div class="btn-cell">
          <el-button type="primary" :loading="store.loading" @click="run">开始对比</el-button>
        </div>
      </div>
    </el-card>

    <el-card v-if="store.loading" shadow="never" class="card">
      <div class="progress-head">
        <span>对比进度</span>
        <span class="pct">{{ Math.round(store.progress) }}%</span>
      </div>
      <el-progress :percentage="store.progress" :show-text="false" :stroke-width="8" />
      <div class="stages">
        <div v-for="(s, i) in stageLabels" :key="s" class="stage" :class="{ active: i <= store.stage }">{{ s }}</div>
      </div>
    </el-card>

    <template v-if="store.result">
      <div class="overview">
        <div v-for="k in ['修改', '新增', '删除', '相同']" :key="k" class="ov-card">
          <div class="ov-num" :style="{ color: changeColor[k] }">{{ store.result.summary[k] || 0 }}</div>
          <div class="ov-label">{{ k }}</div>
        </div>
      </div>

      <el-card shadow="never" class="card">
        <div class="dist-title">差异分布</div>
        <div class="dist-bar">
          <div
            v-for="k in ['修改', '新增', '删除', '相同']"
            :key="k"
            :style="{ width: ((store.result.summary[k] || 0) / total()) * 100 + '%', background: changeColor[k] }"
          ></div>
        </div>
      </el-card>

      <el-card shadow="never" class="card">
        <div class="table-head">
          <span class="th-title">差异明细</span>
          <div class="legend">
            <span v-for="k in ['修改', '新增', '删除', '相同']" :key="k" class="lg">
              <i :style="{ background: changeColor[k] }"></i>{{ k }}
            </span>
          </div>
        </div>
        <div class="table-wrap">
          <table class="tbl">
            <thead>
              <tr>
                <th>条款</th>
                <th>变化</th>
                <th>A 合同</th>
                <th>B 合同</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="d in store.result.diffs" :key="d.clause" :class="changeClass(d.change)">
                <td class="clause">{{ d.clause }}</td>
                <td>
                  <span class="badge" :style="{ color: changeColor[d.change], background: changeColor[d.change] + '18' }">
                    {{ d.change }}
                  </span>
                </td>
                <td class="text" :title="d.a_text">{{ d.a_text }}</td>
                <td class="text" :title="d.b_text">{{ d.b_text }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </el-card>
    </template>
  </div>
</template>

<style scoped>
.page {
  max-width: 1120px;
  margin: 0 auto;
  padding: 32px;
}
h1 {
  margin: 0 0 6px;
  font-size: 24px;
}
.sub {
  color: #64748b;
  font-size: 14px;
  margin: 0 0 20px;
}
.card {
  margin-bottom: 16px;
  border-radius: 14px;
  border: 1px solid #e2e8f0;
}
.grid {
  display: grid;
  grid-template-columns: 1fr 1fr 140px;
  gap: 16px;
  align-items: end;
}
.lbl {
  display: block;
  font-size: 12px;
  color: #64748b;
  margin-bottom: 6px;
}
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
.overview {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 14px;
  margin-bottom: 16px;
}
.ov-card {
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 14px;
  padding: 16px;
  text-align: center;
}
.ov-num {
  font-size: 26px;
  font-weight: 800;
}
.ov-label {
  font-size: 12px;
  color: #94a3b8;
  margin-top: 4px;
}
.dist-title {
  font-size: 13px;
  font-weight: 600;
  margin-bottom: 10px;
}
.dist-bar {
  display: flex;
  height: 16px;
  border-radius: 999px;
  overflow: hidden;
  background: #f1f5f9;
}
.table-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}
.th-title {
  font-weight: 600;
}
.legend {
  display: flex;
  gap: 12px;
  font-size: 12px;
  color: #64748b;
}
.lg {
  display: flex;
  align-items: center;
  gap: 4px;
}
.lg i {
  width: 10px;
  height: 10px;
  border-radius: 2px;
  display: inline-block;
}
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
  padding: 10px 12px;
  border-bottom: 1px solid #f1f5f9;
  vertical-align: top;
}
.clause {
  font-weight: 600;
  white-space: nowrap;
}
.text {
  color: #475569;
  max-width: 320px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.badge {
  display: inline-block;
  font-size: 12px;
  padding: 2px 8px;
  border-radius: 6px;
}
.row-modify td {
  background: #eff6ff;
}
.row-add td {
  background: #f0fdf4;
}
.row-del td {
  background: #fef2f2;
}
</style>
