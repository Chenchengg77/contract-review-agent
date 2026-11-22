<template>
  <div class="page">
    <div class="page-head">
      <div class="page-icon" style="background: #f8fafc; color: #475569">📖</div>
      <div>
        <h1 class="page-title">关于这个项目</h1>
        <p class="page-sub">合同智能审查 Agent · 技术演示与辅助参考</p>
      </div>
    </div>

    <div class="block">
      <p>
        这是一个<strong>合同智能审查 Agent</strong>：解析合同 → LLM 抽取 13 类条款 →
        规则 + 语义双层风险判定 → 生成审查报告与修订建议。
      </p>
    </div>

    <div class="block">
      <h3>技术栈</h3>
      <ul>
        <li><strong>后端</strong>：Python / FastAPI / SQLite</li>
        <li><strong>前端</strong>：Vue 3 / TypeScript / Vite / Element Plus / Pinia</li>
        <li><strong>AI</strong>：DeepSeek API + 自研 RAG（jieba + BM25 + 字符 n-gram）</li>
      </ul>
    </div>

    <div class="block">
      <h3>评估</h3>
      <p>评估集 31 份合同 / 403 条金标，抽取准确率 95.53%，单份成本约 1 分钱。</p>
    </div>

    <div class="disclaimer">
      ⚠️ 免责声明：本工具仅作技术演示与辅助参考，不构成法律意见，不替代律师或专业人士的审查。
    </div>
  </div>
</template>

<style scoped>
.page {
  max-width: 760px;
  margin: 0 auto;
  padding: 40px 32px;
}
h1 {
  font-size: 24px;
  margin: 0 0 24px;
}
.block {
  margin-bottom: 22px;
  line-height: 1.8;
  color: #334155;
}
.block h3 {
  margin: 0 0 8px;
  font-size: 16px;
}
.block ul {
  margin: 0;
  padding-left: 20px;
}
.disclaimer {
  background: #fffbeb;
  border: 1px solid #fde68a;
  color: #92400e;
  border-radius: 12px;
  padding: 14px 16px;
  font-size: 13px;
}
</style>
