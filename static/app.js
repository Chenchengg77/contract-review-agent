// 合同智能审查 Agent 前端逻辑（多模块 + hash 路由）

// ---- 认证 ----
function getToken() {
  return localStorage.getItem('token') || '';
}
function setToken(t) {
  localStorage.setItem('token', t);
}
function clearToken() {
  localStorage.removeItem('token');
}
function authHeaders(extra = {}) {
  const t = getToken();
  return t ? { ...extra, Authorization: 'Bearer ' + t } : extra;
}

// ---- 路由 ----
const PAGES = ['home', 'review', 'chat', 'compare', 'templates', 'eval', 'admin', 'about'];

function showPage(name) {
  document.querySelectorAll('[data-page]').forEach((el) => {
    el.classList.toggle('hidden', el.dataset.page !== name);
    if (el.dataset.page === name) el.classList.add('fade-in');
  });
  document.querySelectorAll('.nav-link').forEach((el) => {
    el.classList.toggle('active', el.dataset.nav === name);
  });
  // 切页后滚动到顶部
  document.querySelector('main').scrollTop = 0;
  if (name === 'admin') loadAdmin();
}

function route() {
  const name = location.hash.replace('#/', '') || 'home';
  showPage(PAGES.includes(name) ? name : 'home');
}

window.addEventListener('hashchange', route);

// ---- 判定 / 等级 颜色映射 ----
const verdictClass = {
  合规: 'bg-green-100 text-green-700',
  偏离: 'bg-amber-100 text-amber-700',
  缺失: 'bg-slate-100 text-slate-500',
  冲突: 'bg-red-100 text-red-700',
};
const severityClass = {
  高: 'bg-red-100 text-red-700',
  中: 'bg-amber-100 text-amber-700',
  低: 'bg-green-100 text-green-700',
};
const changeClass = {
  修改: 'bg-blue-100 text-blue-700',
  新增: 'bg-green-100 text-green-700',
  删除: 'bg-red-100 text-red-700',
  相同: 'bg-slate-100 text-slate-500',
};

function badge(text, map) {
  return `<span class="px-2.5 py-1 rounded-full text-xs font-semibold ${map[text] || 'bg-slate-100 text-slate-500'}">${text}</span>`;
}

function fillSelect(el, names) {
  el.innerHTML = '<option value="">（选择合同）</option>' +
    names.map((n) => `<option value="${n}">${n}</option>`).join('');
}

// ---- 加载示例合同（三个下拉共用） ----
async function loadContracts() {
  try {
    const res = await fetch('/api/contracts');
    const data = await res.json();
    const names = data.contracts || [];
    fillSelect(document.getElementById('sampleSelect'), names);
    fillSelect(document.getElementById('compareA'), names);
    fillSelect(document.getElementById('compareB'), names);
    fillSelect(document.getElementById('chatContract'), names);
  } catch (e) {
    ['sampleSelect', 'compareA', 'compareB'].forEach((id) => {
      document.getElementById(id).innerHTML = '<option value="">加载失败</option>';
    });
  }
}

// ---- 加载评估 ----
async function loadEval() {
  const box = document.getElementById('evalMetrics');
  const tableBox = document.getElementById('evalTable');
  try {
    const res = await fetch('/api/eval');
    const data = await res.json();
    if (!data.summary) { box.innerHTML = '<p class="text-slate-400">暂无评估数据</p>'; return; }
    const e = data.summary.extraction || {};
    const j = data.summary.judgment || {};
    const items = [
      ['抽取准确率', (e.accuracy * 100).toFixed(2) + '%'],
      ['抽取 F1', (e.f1 * 100).toFixed(2) + '%'],
      ['判定准确率', (j.verdict_accuracy * 100).toFixed(2) + '%'],
      ['severity 准确率', (j.severity_accuracy * 100).toFixed(2) + '%'],
    ];
    box.innerHTML = items.map(([k, v]) => `
      <div class="bg-white rounded-xl p-5 shadow-sm border border-slate-100">
        <div class="text-2xl font-bold text-brand-600">${v}</div>
        <div class="text-sm text-slate-500 mt-1">${k}</div>
      </div>`).join('');

    const rows = (data.per_contract || []).map((r) => `
      <tr class="border-b border-slate-100 hover:bg-slate-50">
        <td class="px-4 py-2 text-slate-700">${r.file}</td>
        <td class="px-4 py-2 text-center">${(r.accuracy_rate * 100).toFixed(0)}%</td>
        <td class="px-4 py-2 text-center">${Math.round(r.verdict_accuracy * 13)}/13</td>
      </tr>`).join('');
    tableBox.innerHTML = `
      <table class="w-full text-sm">
        <thead><tr class="text-left text-slate-500"><th class="px-4 py-2 font-medium">合同</th><th class="px-4 py-2 font-medium text-center">抽取准确率</th><th class="px-4 py-2 font-medium text-center">判定一致</th></tr></thead>
        <tbody>${rows}</tbody>
      </table>`;
  } catch (e) {
    box.innerHTML = '<p class="text-slate-400">评估数据加载失败</p>';
  }
}

// ---- 审查结果渲染 ----
function renderResult(data) {
  const p = data.process;
  document.getElementById('processBar').innerHTML = `
    <span>📄 ${p.paragraphs} 段</span>
    <span>🏷️ ${p.headings} 个条款标题</span>
    <span>⏱️ ${p.seconds} 秒</span>
    <span>🪙 ${p.tokens} tokens</span>`;

  const o = data.overview;
  const cards = [
    ['🔴 高风险', o.high, 'text-red-600'],
    ['🟡 中风险', o.mid, 'text-amber-600'],
    ['🟢 低风险', o.low, 'text-green-600'],
  ];
  document.getElementById('overview').innerHTML = cards.map(([label, val, color]) => `
    <div class="bg-slate-50 rounded-xl p-5 text-center border border-slate-100">
      <div class="text-3xl font-bold ${color}">${val}</div>
      <div class="text-sm text-slate-500 mt-1">${label}</div>
    </div>`).join('');

  const rows = data.judgments
    .filter((j) => j.verdict !== '合规')
    .map((j) => `
      <tr class="border-b border-slate-100 hover:bg-slate-50 align-top">
        <td class="px-4 py-2.5 font-medium">${j.clause}</td>
        <td class="px-4 py-2.5">${badge(j.verdict, verdictClass)}</td>
        <td class="px-4 py-2.5">${badge(j.severity, severityClass)}</td>
        <td class="px-4 py-2.5 text-slate-600">${j.reason}${j.revision ? `<div class="mt-1.5 text-xs text-brand-600 bg-brand-50 rounded p-2">📝 修订建议：${j.revision}</div>` : ''}</td>
      </tr>`).join('');
  document.getElementById('tableBody').innerHTML =
    rows || '<tr><td colspan="4" class="px-4 py-6 text-center text-slate-400">✅ 无风险条款</td></tr>';

  document.getElementById('result').classList.remove('hidden');
}

// ---- 选择合同 & 进度 ----
let selectedContract = null;

function showProgress() {
  document.getElementById('result').classList.add('hidden');
  document.getElementById('progressPanel').classList.remove('hidden');
  updateProgress(0);
}

function updateProgress(pct) {
  document.getElementById('progressBar').style.width = pct + '%';
  document.getElementById('progressPct').textContent = Math.round(pct) + '%';
  const stage = pct < 25 ? 0 : pct < 55 ? 1 : pct < 80 ? 2 : 3;
  document.querySelectorAll('#stageList .stage').forEach((el, i) => {
    el.className = 'stage px-2 py-1.5 rounded-lg text-center ' +
      (i <= stage ? 'bg-brand-50 text-brand-600 font-medium' : 'bg-slate-50 text-slate-400');
  });
}

function hideProgress() {
  document.getElementById('progressPanel').classList.add('hidden');
}

async function runReview(body, isFile) {
  showProgress();
  let pct = 0;
  const timer = setInterval(() => {
    pct = Math.min(pct + 3, 92);
    updateProgress(pct);
  }, 250);

  try {
    const res = isFile
      ? await fetch('/api/review', { method: 'POST', body, headers: authHeaders() })
      : await fetch('/api/review_sample', {
          method: 'POST',
          headers: authHeaders({ 'Content-Type': 'application/json' }),
          body: JSON.stringify(body),
        });
    if (!res.ok) {
      clearInterval(timer);
      hideProgress();
      alert('审查失败：' + res.status);
      return;
    }
    const data = await res.json();
    clearInterval(timer);
    updateProgress(100);
    setTimeout(() => {
      hideProgress();
      renderResult(data);
    }, 400);
  } catch (e) {
    clearInterval(timer);
    hideProgress();
    alert('请求出错：' + e.message);
  }
}

// ---- 对比渲染 ----
function renderCompare(data) {
  const s = data.summary;
  const cards = [
    ['🔵 修改', s['修改'], 'text-blue-600'],
    ['🟢 新增', s['新增'], 'text-green-600'],
    ['🔴 删除', s['删除'], 'text-red-600'],
    ['⚪ 相同', s['相同'], 'text-slate-500'],
  ];
  document.getElementById('compareSummary').innerHTML = cards.map(([label, val, color]) => `
    <div class="bg-slate-50 rounded-xl p-4 text-center border border-slate-100">
      <div class="text-2xl font-bold ${color}">${val}</div>
      <div class="text-xs text-slate-500 mt-1">${label}</div>
    </div>`).join('');

  // 差异分布条
  const total = s['修改'] + s['新增'] + s['删除'] + s['相同'] || 1;
  const seg = (val, color) =>
    val > 0 ? `<div class="${color}" style="width:${(val / total) * 100}%"></div>` : '';
  document.getElementById('compareDistBar').innerHTML =
    seg(s['修改'], 'bg-blue-400') + seg(s['新增'], 'bg-green-400') +
    seg(s['删除'], 'bg-red-400') + seg(s['相同'], 'bg-slate-300');

  const rows = data.diffs.map((d) => {
    const cls = d.change === '修改' ? 'diff-modify' : d.change === '新增' ? 'diff-add' : d.change === '删除' ? 'diff-del' : '';
    return `
      <tr class="${cls} border-b border-slate-100">
        <td class="px-4 py-2.5 font-medium">${d.clause}</td>
        <td class="px-4 py-2.5">${badge(d.change, changeClass)}</td>
        <td class="px-4 py-2.5 text-slate-600 max-w-xs truncate" title="${d.a_text}">${d.a_text}</td>
        <td class="px-4 py-2.5 text-slate-600 max-w-xs truncate" title="${d.b_text}">${d.b_text}</td>
      </tr>`;
  }).join('');
  document.getElementById('compareBody').innerHTML = rows;
  document.getElementById('compareResult').classList.remove('hidden');
}

function showCompareProgress() {
  document.getElementById('compareResult').classList.add('hidden');
  document.getElementById('compareProgressPanel').classList.remove('hidden');
  updateCompareProgress(0);
}

function updateCompareProgress(pct) {
  document.getElementById('compareProgressBar').style.width = pct + '%';
  document.getElementById('comparePct').textContent = Math.round(pct) + '%';
  const stage = pct < 25 ? 0 : pct < 55 ? 1 : pct < 80 ? 2 : 3;
  document.querySelectorAll('#compareStageList .cstage').forEach((el, i) => {
    el.className = 'cstage px-2 py-1.5 rounded-lg text-center ' +
      (i <= stage ? 'bg-brand-50 text-brand-600 font-medium' : 'bg-slate-50 text-slate-400');
  });
}

function hideCompareProgress() {
  document.getElementById('compareProgressPanel').classList.add('hidden');
}

async function runCompare() {
  const a = document.getElementById('compareA').value;
  const b = document.getElementById('compareB').value;
  if (!a || !b) { alert('请分别选择 A、B 两份合同'); return; }
  if (a === b) { alert('A 和 B 不能是同一份合同'); return; }

  showCompareProgress();
  let pct = 0;
  const timer = setInterval(() => {
    pct = Math.min(pct + 3, 92);
    updateCompareProgress(pct);
  }, 250);

  const btn = document.getElementById('compareBtn');
  btn.disabled = true;
  btn.textContent = '对比中…';

  try {
    const res = await fetch('/api/compare', {
      method: 'POST',
      headers: authHeaders({ 'Content-Type': 'application/json' }),
      body: JSON.stringify({ a, b }),
    });
    if (!res.ok) { clearInterval(timer); hideCompareProgress(); alert('对比失败：' + res.status); return; }
    const data = await res.json();
    clearInterval(timer);
    updateCompareProgress(100);
    setTimeout(() => {
      hideCompareProgress();
      renderCompare(data);
    }, 400);
  } catch (e) {
    clearInterval(timer);
    hideCompareProgress();
    alert('请求出错：' + e.message);
  } finally {
    btn.disabled = false;
    btn.textContent = '开始对比';
  }
}

// ---- 事件绑定 ----
document.getElementById('fileInput').addEventListener('change', (e) => {
  if (e.target.files.length) {
    selectedContract = { file: e.target.files[0] };
    document.getElementById('sampleSelect').value = '';
  }
});

document.getElementById('sampleSelect').addEventListener('change', (e) => {
  if (e.target.value) {
    selectedContract = { name: e.target.value };
    document.getElementById('fileInput').value = '';
  }
});

document.getElementById('startReviewBtn').addEventListener('click', () => {
  if (!selectedContract) { alert('请先选择合同（上传文件或选示例）'); return; }
  const focus = document.getElementById('reviewFocus').value.trim();
  if (selectedContract.file) {
    const fd = new FormData();
    fd.append('file', selectedContract.file);
    fd.append('focus', focus);
    runReview(fd, true);
  } else {
    runReview({ name: selectedContract.name, focus }, false);
  }
});

document.getElementById('compareBtn').addEventListener('click', runCompare);

// ---- AI 对话 ----
let chatHistory = [];

function showChatEmpty() {
  document.getElementById('chatMessages').innerHTML = `
    <div id="chatEmpty" class="h-full flex flex-col items-center justify-center text-center">
      <div class="w-16 h-16 rounded-2xl bg-brand-600 text-white flex items-center justify-center text-3xl mb-4">⚖️</div>
      <div class="text-xl font-bold text-slate-800">合同 AI 助手</div>
      <p class="text-sm text-slate-500 mt-2 max-w-md">选择左侧的合同，然后问我任何关于它的问题。我会只基于合同原文回答，并标注引用的条款。</p>
    </div>`;
}

function appendChat(role, html) {
  const box = document.getElementById('chatMessages');
  const empty = document.getElementById('chatEmpty');
  if (empty) empty.remove();
  const isUser = role === 'user';
  box.insertAdjacentHTML('beforeend', `
    <div class="flex ${isUser ? 'justify-end' : 'justify-start'}">
      <div class="max-w-[75%] rounded-2xl px-4 py-3 text-sm leading-relaxed ${isUser ? 'bg-brand-600 text-white' : 'bg-white border border-slate-200 text-slate-700 shadow-sm'}">${html}</div>
    </div>`);
  box.scrollTop = box.scrollHeight;
}

async function sendChat() {
  const name = document.getElementById('chatContract').value;
  const input = document.getElementById('chatInput');
  const q = input.value.trim();
  if (!name) { alert('请先选择一份合同'); return; }
  if (!q) return;

  appendChat('user', q);
  input.value = '';
  const btn = document.getElementById('chatSend');
  btn.disabled = true;
  btn.textContent = '思考中…';

  try {
    const res = await fetch('/api/chat', {
      method: 'POST',
      headers: authHeaders({ 'Content-Type': 'application/json' }),
      body: JSON.stringify({ name, question: q, history: chatHistory }),
    });
    if (!res.ok) { appendChat('assistant', '请求失败：' + res.status); return; }
    const data = await res.json();
    let html = data.answer;
    const cites = (data.citations || []).filter((c) => c && c !== '正文');
    if (cites.length) html += `<div class="text-xs text-slate-400 mt-1.5">引用：${cites.join('、')}</div>`;
    appendChat('assistant', html);
    chatHistory.push({ role: 'user', content: q }, { role: 'assistant', content: data.answer });
  } catch (e) {
    appendChat('assistant', '出错了：' + e.message);
  } finally {
    btn.disabled = false;
    btn.textContent = '发送';
  }
}

function newChat() {
  chatHistory = [];
  showChatEmpty();
  document.getElementById('chatInput').value = '';
}

document.getElementById('chatSend').addEventListener('click', sendChat);
document.getElementById('chatInput').addEventListener('keydown', (e) => {
  if (e.key === 'Enter') sendChat();
});
document.getElementById('chatNew').addEventListener('click', newChat);
document.getElementById('chatContract').addEventListener('change', newChat);
document.querySelectorAll('.quick-q').forEach((b) =>
  b.addEventListener('click', () => {
    document.getElementById('chatInput').value = b.dataset.q;
    sendChat();
  })
);

// ---- 合同模板 ----
let templatesData = [];
let templateCat = '全部';
let templateQuery = '';

const TEMPLATE_ICONS = { 买卖: '📦', 租赁: '🏠', 承揽: '🔧', 服务: '🤝', 建设: '🏗️', 其他: '📄', 示例: '🧪' };
const TEMPLATE_ICON_BG = {
  买卖: 'bg-blue-50 text-blue-600',
  租赁: 'bg-green-50 text-green-600',
  承揽: 'bg-amber-50 text-amber-600',
  服务: 'bg-purple-50 text-purple-600',
  建设: 'bg-orange-50 text-orange-600',
  其他: 'bg-slate-100 text-slate-600',
  示例: 'bg-pink-50 text-pink-600',
};

async function loadTemplates() {
  const catBox = document.getElementById('templateCats');
  try {
    const res = await fetch('/api/templates?t=' + Date.now());
    const data = await res.json();
    templatesData = data.templates || [];
    renderTemplateCats();
    renderTemplates();
  } catch (e) {
    catBox.innerHTML = '<span class="text-slate-400 text-sm">模板加载失败</span>';
  }
}

function renderTemplateCats() {
  const box = document.getElementById('templateCats');
  const counts = {};
  templatesData.forEach((t) => { counts[t.category] = (counts[t.category] || 0) + 1; });
  const cats = ['全部', ...Object.keys(counts)];
  box.innerHTML = cats
    .map((c) => {
      const n = c === '全部' ? templatesData.length : counts[c];
      const active = c === templateCat ? 'bg-brand-600 text-white border-brand-600' : 'bg-white border-slate-300 text-slate-600 hover:border-brand-500';
      return `<button data-cat="${c}" class="cat-btn px-3 py-1.5 rounded-lg text-sm border ${active}">${c} (${n})</button>`;
    })
    .join('');
  box.querySelectorAll('.cat-btn').forEach((b) =>
    b.addEventListener('click', () => {
      templateCat = b.dataset.cat;
      renderTemplateCats();
      renderTemplates();
    })
  );
}

function renderTemplates() {
  let list = templatesData;
  if (templateCat !== '全部') list = list.filter((t) => t.category === templateCat);
  if (templateQuery) list = list.filter((t) => t.title.includes(templateQuery) || t.name.includes(templateQuery));

  document.getElementById('templateGrid').innerHTML =
    list
      .map(
        (t) => `
      <div class="bg-white rounded-xl shadow-sm border border-slate-100 p-5 hover-card flex flex-col">
        <div class="flex items-start justify-between mb-3">
          <div class="w-12 h-12 rounded-xl ${TEMPLATE_ICON_BG[t.category] || 'bg-slate-100 text-slate-600'} flex items-center justify-center text-2xl">${TEMPLATE_ICONS[t.category] || '📄'}</div>
          <span class="text-xs px-2 py-0.5 rounded bg-slate-100 text-slate-500">v1.0</span>
        </div>
        <div class="font-semibold text-slate-800 mb-1 truncate" title="${t.title}">${t.title}</div>
        <div class="flex items-center gap-2 mb-2">
          <span class="text-xs px-2 py-0.5 rounded bg-brand-50 text-brand-600">${t.category}</span>
          <span class="text-xs text-slate-400">${t.clause_count} 条</span>
        </div>
        <p class="text-xs text-slate-500 leading-relaxed mb-4 flex-1">${t.description}</p>
        <div class="flex items-center gap-4 text-xs border-t border-slate-100 pt-3">
          <button class="text-brand-600 hover:underline" data-preview="${t.name}">预览</button>
          <a class="text-brand-600 hover:underline" href="/api/templates/download?name=${encodeURIComponent(t.name)}">下载</a>
        </div>
      </div>`
      )
      .join('') || '<div class="text-slate-400 text-sm col-span-4 py-10 text-center">没有匹配的模板</div>';

  document.querySelectorAll('[data-preview]').forEach((b) =>
    b.addEventListener('click', () => openPreview(b.dataset.preview))
  );
}

async function openPreview(name) {
  const t = templatesData.find((x) => x.name === name);
  const title = t ? t.title : name;
  document.getElementById('previewTitle').textContent = title;
  document.getElementById('previewBody').innerHTML = '<div class="text-slate-400">加载中…</div>';
  document.getElementById('previewDownload').href = '/api/templates/download?name=' + encodeURIComponent(name);
  document.getElementById('previewModal').classList.remove('hidden');

  try {
    const res = await fetch('/api/templates/preview?name=' + encodeURIComponent(name));
    if (!res.ok) { document.getElementById('previewBody').innerHTML = '加载失败'; return; }
    const data = await res.json();
    const html = (data.blocks || [])
      .map((b) => {
        if (b.type === 'table') {
          const trs = b.rows
            .map(
              (row) =>
                `<tr>${row
                  .map((c) => `<td class="border border-slate-200 px-2 py-1 align-top text-slate-600 whitespace-pre-wrap">${c}</td>`)
                  .join('')}</tr>`
            )
            .join('');
          return `<table class="my-2 border-collapse text-xs">${trs}</table>`;
        }
        if (b.clause_no) {
          return `<div class="mt-3"><span class="font-semibold text-slate-800">${b.clause_no}</span> <span class="text-slate-700">${b.text.slice(b.clause_no.length).trim()}</span></div>`;
        }
        return `<div class="text-slate-600 pl-4 py-0.5">${b.text}</div>`;
      })
      .join('');
    document.getElementById('previewBody').innerHTML = html || '<div class="text-slate-400">（空文档）</div>';
  } catch (e) {
    document.getElementById('previewBody').innerHTML = '加载出错：' + e.message;
  }
}

function closePreview() {
  document.getElementById('previewModal').classList.add('hidden');
}

document.getElementById('previewClose').addEventListener('click', closePreview);
document.getElementById('previewClose2').addEventListener('click', closePreview);
document.getElementById('previewModal').addEventListener('click', (e) => {
  if (e.target.id === 'previewModal') closePreview();
});
document.getElementById('templateSearch').addEventListener('input', (e) => {
  templateQuery = e.target.value.trim();
  renderTemplates();
});

// 自定义模板上传
document.getElementById('btnCustomTemplate').addEventListener('click', () => {
  document.getElementById('templateFile').click();
});
document.getElementById('templateFile').addEventListener('change', async (e) => {
  const f = e.target.files[0];
  if (!f) return;
  const fd = new FormData();
  fd.append('file', f);
  try {
    const res = await fetch('/api/templates/upload', { method: 'POST', body: fd, headers: authHeaders() });
    if (!res.ok) { alert('上传失败：' + res.status); return; }
    const data = await res.json();
    alert('上传成功：' + data.name);
    await loadTemplates();
  } catch (err) {
    alert('上传出错：' + err.message);
  } finally {
    e.target.value = '';
  }
});

// ---- 认证 UI ----
let authMode = 'login';

function animateCounters() {
  document.querySelectorAll('#authOverlay [data-count]').forEach((el) => {
    const target = parseFloat(el.dataset.count);
    const suffix = el.dataset.suffix || '';
    const dur = 900;
    const start = performance.now();
    function step(now) {
      const p = Math.min((now - start) / dur, 1);
      const val = target * (1 - Math.pow(1 - p, 3));
      el.textContent = (Number.isInteger(target) ? Math.round(val) : val.toFixed(1)) + suffix;
      if (p < 1) requestAnimationFrame(step);
    }
    requestAnimationFrame(step);
  });
}

function showAuthOverlay(show) {
  document.getElementById('authOverlay').classList.toggle('hidden', !show);
  if (show) animateCounters();
}

function setAuthMode(mode) {
  authMode = mode;
  document.querySelectorAll('.authTab').forEach((b) => {
    const active = b.dataset.authTab === mode;
    b.className =
      'authTab pb-3 px-1 mr-6 text-sm font-medium border-b-2 ' +
      (active ? 'border-brand-600 text-brand-600' : 'border-transparent text-slate-400');
  });
  document.getElementById('authSubmit').textContent = mode === 'login' ? '登录' : '注册';
  document.getElementById('authError').classList.add('hidden');
}

async function submitAuth() {
  const username = document.getElementById('authUser').value.trim();
  const password = document.getElementById('authPass').value;
  const errBox = document.getElementById('authError');
  errBox.classList.add('hidden');
  if (!username || !password) {
    errBox.textContent = '请填写用户名和密码';
    errBox.classList.remove('hidden');
    return;
  }
  try {
    const url = authMode === 'login' ? '/api/auth/login' : '/api/auth/register';
    const res = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password }),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      errBox.textContent = data.detail || '操作失败';
      errBox.classList.remove('hidden');
      return;
    }
    setToken(data.token);
    applyUser(data.user);
    showAuthOverlay(false);
    bootApp();
  } catch (e) {
    errBox.textContent = '网络错误：' + e.message;
    errBox.classList.remove('hidden');
  }
}

async function logout() {
  try {
    await fetch('/api/auth/logout', { method: 'POST', headers: authHeaders() });
  } catch (e) {
    /* ignore */
  }
  clearToken();
  location.reload();
}

async function checkAuth() {
  if (!getToken()) {
    showAuthOverlay(true);
    return;
  }
  try {
    const res = await fetch('/api/auth/me', { headers: authHeaders() });
    if (!res.ok) {
      clearToken();
      showAuthOverlay(true);
      return;
    }
    const user = await res.json();
    applyUser(user);
    bootApp();
  } catch (e) {
    showAuthOverlay(true);
  }
}

function applyUser(user) {
  document.getElementById('navUser').textContent = '👤 ' + user.username;
  document.getElementById('navAdmin').style.display = user.role === 'admin' ? 'flex' : 'none';
}

function fmtTime(ts) {
  if (!ts) return '-';
  return new Date(ts * 1000).toLocaleString('zh-CN');
}

async function loadAdmin() {
  try {
    const [uRes, rRes] = await Promise.all([
      fetch('/api/admin/users', { headers: authHeaders() }),
      fetch('/api/reviews', { headers: authHeaders() }),
    ]);
    const users = (await uRes.json()).users || [];
    const reviews = (await rRes.json()).reviews || [];

    document.getElementById('adminUserCount').textContent = users.length + ' 位用户';
    document.getElementById('adminUsersBody').innerHTML = users
      .map(
        (u) => `
      <tr class="border-b border-slate-100">
        <td class="px-4 py-2.5 text-slate-500">${u.id}</td>
        <td class="px-4 py-2.5 font-medium">${u.username}</td>
        <td class="px-4 py-2.5">${badge(u.role === 'admin' ? '管理员' : '普通用户', u.role === 'admin' ? 'bg-purple-100 text-purple-700' : 'bg-slate-100 text-slate-600')}</td>
        <td class="px-4 py-2.5 text-slate-500">${fmtTime(u.created_at)}</td>
      </tr>`
      )
      .join('');

    document.getElementById('adminReviewCount').textContent = reviews.length + ' 条记录';
    document.getElementById('adminReviewsBody').innerHTML =
      reviews
        .map(
          (r) => `
      <tr class="border-b border-slate-100">
        <td class="px-4 py-2.5 font-medium">${r.username}</td>
        <td class="px-4 py-2.5 text-slate-600">${r.filename}</td>
        <td class="px-4 py-2.5"><span class="text-red-600">${r.high}</span> / <span class="text-amber-600">${r.mid}</span> / <span class="text-green-600">${r.low}</span></td>
        <td class="px-4 py-2.5 text-slate-500">${fmtTime(r.created_at)}</td>
      </tr>`
        )
        .join('') ||
      '<tr><td colspan="4" class="px-4 py-6 text-center text-slate-400">暂无审查记录</td></tr>';
  } catch (e) {
    document.getElementById('adminUsersBody').innerHTML =
      '<tr><td colspan="4" class="px-4 py-6 text-center text-slate-400">加载失败</td></tr>';
  }
}

function bootApp() {
  route();
  loadContracts();
  loadEval();
  loadTemplates();
}

document.querySelectorAll('.authTab').forEach((b) =>
  b.addEventListener('click', () => setAuthMode(b.dataset.authTab))
);
document.getElementById('authSubmit').addEventListener('click', submitAuth);
document.getElementById('authPass').addEventListener('keydown', (e) => {
  if (e.key === 'Enter') submitAuth();
});
document.getElementById('navLogout').addEventListener('click', logout);

// ---- 初始化 ----
checkAuth();
