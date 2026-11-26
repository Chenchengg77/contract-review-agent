<script setup lang="ts">
import { onMounted, ref } from 'vue'
import api from '../api'

const summary = ref<any>(null)

onMounted(async () => {
  try {
    const { data } = await api.get('/eval')
    summary.value = data.summary
  } catch {
    /* ignore */
  }
})

function pct(v: number | undefined | null) {
  return v == null ? '—' : (v * 100).toFixed(2) + '%'
}
</script>

<template>
  <footer class="footer">
    <div class="footer-inner">
      <div class="top">
        <div class="brand-col">
          <div class="brand">
            <div class="logo">合</div>
            <div>
              <div class="brand-name">合同审查</div>
              <div class="brand-sub">CONTRACT REVIEW</div>
            </div>
          </div>
          <p class="brand-desc">
            这是一个<strong>合同智能审查 Agent</strong>：解析合同 → LLM 抽取 13 类条款 →
            规则 + 语义双层风险判定 → 生成审查报告与修订建议。
          </p>
        </div>

        <div class="info-col">
          <div class="info-title">技术栈</div>
          <ul>
            <li>后端 · FastAPI / SQLite</li>
            <li>前端 · Vue 3 / TypeScript / Vite</li>
            <li>AI · DeepSeek + 自研 RAG（BM25）</li>
          </ul>
        </div>

        <div class="info-col">
          <div class="info-title">评估</div>
          <ul>
            <li>{{ summary?.contracts ?? 31 }} 份合同 / 403 条金标</li>
            <li>抽取准确率 {{ pct(summary?.extraction?.accuracy) }}</li>
            <li>判定准确率 {{ pct(summary?.judgment?.verdict_accuracy) }}</li>
          </ul>
        </div>
      </div>

      <div class="scope">
        <span class="scope-label">适用范围</span>
        <span class="scope-text">
          面向<strong>商务合同</strong>（买卖 / 租赁 / 承揽 / 服务 / 建设）的 13 类核心条款审查；
          劳动合同、股权 / 投资合同等不在适用范围内。
        </span>
      </div>

      <div class="bottom">
        <span>© 2026 合同智能审查 Agent · 技术演示项目</span>
        <span class="disclaimer">⚠️ 仅作技术演示与辅助参考，不构成法律意见，不替代律师审查</span>
      </div>
    </div>
  </footer>
</template>

<style scoped>
.footer {
  background: #101216;
  color: #9a9ea5;
  padding: 72px 0 44px;
  border-top: 1px solid #24272c;
}
.footer-inner {
  max-width: 1120px;
  margin: 0 auto;
  padding: 0 28px;
}
.top {
  display: grid;
  grid-template-columns: 1.6fr 1fr 1fr;
  gap: 48px;
}
.brand {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 18px;
}
.logo {
  width: 38px;
  height: 38px;
  border: 1px solid #f5f3ef;
  background: transparent;
  display: flex;
  align-items: center;
  justify-content: center;
  font-family: 'Noto Serif SC', 'Songti SC', 'SimSun', Georgia, serif;
  font-size: 19px;
  font-weight: 600;
  color: #f5f3ef;
  line-height: 1;
  position: relative;
}
.logo::after {
  content: '';
  position: absolute;
  right: -1px;
  bottom: -1px;
  width: 7px;
  height: 7px;
  background: #b4442f;
}
.brand-name {
  font-family: 'Noto Serif SC', 'Songti SC', 'SimSun', Georgia, serif;
  font-size: 17px;
  font-weight: 600;
  color: #f5f3ef;
  letter-spacing: 3px;
}
.brand-sub {
  font-size: 8px;
  letter-spacing: 3.2px;
  color: #565a61;
  margin-top: 3px;
}
.brand-desc {
  font-size: 12.5px;
  line-height: 2.1;
  color: #8a8e95;
  margin: 0;
  max-width: 420px;
}
.brand-desc strong {
  color: #cfd2d6;
  font-weight: 500;
}
.info-title {
  font-size: 11px;
  letter-spacing: 2px;
  color: #6f7278;
  margin-bottom: 16px;
}
.info-col ul {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 12px;
  font-size: 12.5px;
  color: #8a8e95;
  line-height: 1.6;
}
.scope {
  margin-top: 44px;
  padding: 20px 0;
  border-top: 1px solid #24272c;
  border-bottom: 1px solid #24272c;
  display: flex;
  gap: 20px;
  font-size: 12.5px;
  line-height: 1.9;
  color: #8a8e95;
}
.scope-label {
  flex-shrink: 0;
  font-size: 11px;
  letter-spacing: 2px;
  color: #6f7278;
  padding-top: 1px;
}
.scope-text strong {
  color: #cfd2d6;
  font-weight: 500;
}
.bottom {
  margin-top: 26px;
  display: flex;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
  font-size: 11.5px;
  color: #6f7278;
  letter-spacing: 0.4px;
}
.disclaimer {
  color: #7a6b52;
}
@media (max-width: 900px) {
  .top {
    grid-template-columns: 1fr;
    gap: 32px;
  }
}
</style>
