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
let currentUser = null;

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
  let name = location.hash.replace('#/', '') || 'home';
  // 管理后台只对 admin 开放
  if (name === 'admin' && (!currentUser || currentUser.role !== 'admin')) {
    name = 'home';
    location.hash = '#/home';
  }
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
let chatLog = [];
let chatMode = 'contract';
let currentConvId = null;

function showChatEmpty() {
  const isLaw = chatMode === 'law';
  document.getElementById('chatMessages').innerHTML = `
    <div id="chatEmpty" class="h-full flex flex-col items-center justify-center text-center">
      <div class="w-16 h-16 rounded-2xl bg-brand-600 text-white flex items-center justify-center text-3xl mb-4">${isLaw ? '📚' : '⚖️'}</div>
      <div class="text-xl font-bold text-slate-800">${isLaw ? '法律知识助手' : '合同 AI 助手'}</div>
      <p class="text-sm text-slate-500 mt-2 max-w-md">${
        isLaw
          ? '问我任何法律问题（试用期、违约金、预付款、劳动合同…），我会基于法规库回答并引用法条。'
          : '选择左侧的合同，然后问我任何关于它的问题。我会只基于合同原文回答，并标注引用的条款。'
      }</p>
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
  chatLog.push({ role, html });
}

function escapeHtml(s) {
  return (s || '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}

function renderMarkdown(text) {
  if (!text) return '';
  try {
    if (typeof marked !== 'undefined') {
      return marked.parse(text);
    }
  } catch (e) {
    /* 回退到手写渲染 */
  }
  return escapeHtml(text)
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\n/g, '<br>');
}

async function sendChat() {
  const input = document.getElementById('chatInput');
  const q = input.value.trim();
  if (!q) return;

  let streamUrl, jsonUrl, body;
  if (chatMode === 'law') {
    streamUrl = '/api/law_chat_stream';
    jsonUrl = '/api/law_chat';
    body = { question: q, history: chatHistory };
  } else {
    const name = document.getElementById('chatContract').value;
    if (!name) { alert('请先选择一份合同'); return; }
    streamUrl = '/api/chat_stream';
    jsonUrl = '/api/chat';
    body = { name, question: q, history: chatHistory };
  }

  appendChat('user', escapeHtml(q));
  input.value = '';
  const btn = document.getElementById('chatSend');
  btn.disabled = true;
  btn.textContent = '思考中…';

  // 先创建 AI 气泡，边流式边填
  const box = document.getElementById('chatMessages');
  const empty = document.getElementById('chatEmpty');
  if (empty) empty.remove();
  const wrap = document.createElement('div');
  wrap.className = 'flex justify-start';
  wrap.innerHTML =
    '<div class="max-w-[75%] rounded-2xl px-4 py-3 text-sm leading-relaxed bg-white border border-slate-200 text-slate-700 shadow-sm"><div class="chatText"></div><div class="chatCites text-xs text-slate-400 mt-1.5"></div></div>';
  box.appendChild(wrap);
  const textEl = wrap.querySelector('.chatText');
  const citeEl = wrap.querySelector('.chatCites');

  let answer = '';
  let citations = [];

  try {
    let res = await fetch(streamUrl, {
      method: 'POST',
      headers: authHeaders({ 'Content-Type': 'application/json' }),
      body: JSON.stringify(body),
    });

    // 后端若还是旧版（无流式接口），回退到普通请求
    if (res.status === 404) {
      res = await fetch(jsonUrl, {
        method: 'POST',
        headers: authHeaders({ 'Content-Type': 'application/json' }),
        body: JSON.stringify(body),
      });
      if (!res.ok) { wrap.remove(); appendChat('assistant', '请求失败：' + res.status); return; }
      const data = await res.json();
      answer = data.answer || '';
      citations = data.citations || [];
      textEl.textContent = answer;
    } else if (!res.ok) {
      wrap.remove();
      appendChat('assistant', '请求失败：' + res.status);
      return;
    } else {
      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      let lastRender = 0;
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const parts = buffer.split('\n\n');
        buffer = parts.pop();
        for (const part of parts) {
          let ev = 'message';
          let data = '';
          for (const line of part.split('\n')) {
            if (line.startsWith('event:')) ev = line.slice(6).trim();
            else if (line.startsWith('data:')) data += line.slice(5).trim();
          }
          if (!data) continue;
          let obj;
          try { obj = JSON.parse(data); } catch (e) { continue; }
          if (ev === 'citations') {
            citations = obj.citations || [];
          } else if (ev === 'token') {
            answer += obj.text || '';
            const now = Date.now();
            if (now - lastRender > 120) {
              lastRender = now;
              textEl.innerHTML = renderMarkdown(answer);
              box.scrollTop = box.scrollHeight;
            }
          }
        }
      }
    }

    const cites = citations.filter((c) => c && c !== '正文');
    if (cites.length) citeEl.textContent = '引用：' + cites.join('、');
    textEl.innerHTML = renderMarkdown(answer);
    chatLog.push({
      role: 'assistant',
      html: renderMarkdown(answer) + (cites.length ? `<div class="text-xs text-slate-400 mt-1.5">引用：${cites.join('、')}</div>` : ''),
    });
    chatHistory.push({ role: 'user', content: q }, { role: 'assistant', content: answer });
    persistCurrent();
  } catch (e) {
    wrap.remove();
    appendChat('assistant', '出错了：' + e.message);
  } finally {
    btn.disabled = false;
    btn.textContent = '发送';
  }
}

function newChat() {
  chatHistory = [];
  chatLog = [];
  showChatEmpty();
  document.getElementById('chatInput').value = '';
}

// ---- 问答模式：合同 / 法律 ----
const QUICK = {
  contract: [
    ['违约金是怎么约定的？', '这份合同的违约金是怎么约定的？'],
    ['有没有责任上限？', '有没有责任上限？'],
    ['争议解决方式是什么？', '争议解决方式是什么？'],
    ['有哪些风险条款？', '这份合同有哪些风险条款？'],
    ['保密期限是多久？', '保密条款的期限是多久？'],
  ],
  law: [
    ['劳动合同试用期多久？', '劳动合同试用期最长可以约定多久？'],
    ['违约金上限多少？', '法律对违约金的上限有什么规定？'],
    ['口头合同有效吗？', '口头订立的合同有效吗？'],
    ['预付费能退吗？', '商家预收款后不履行，预付款能退吗？'],
    ['未签书面合同怎么办？', '用人单位超过一个月未签书面劳动合同，有什么法律后果？'],
  ],
};

function renderQuick() {
  const box = document.getElementById('chatQuick');
  box.innerHTML = QUICK[chatMode]
    .map(
      ([label, q]) =>
        `<button class="quick-q w-full text-left text-sm text-slate-600 px-3 py-2.5 rounded-lg border border-slate-200 hover:border-brand-400 hover:text-brand-600" data-q="${q}">${label}</button>`
    )
    .join('');
  box.querySelectorAll('.quick-q').forEach((b) =>
    b.addEventListener('click', () => {
      document.getElementById('chatInput').value = b.dataset.q;
      sendChat();
    })
  );
}

function setChatMode(mode) {
  chatMode = mode;
  document.querySelectorAll('.chatModeBtn').forEach((b) => {
    const active = b.dataset.chatMode === mode;
    b.className =
      'chatModeBtn flex-1 py-1.5 rounded-md text-xs font-medium ' +
      (active ? 'bg-white shadow text-slate-800' : 'text-slate-500');
  });
  const wrap = document.getElementById('contractSelectWrap');
  if (wrap) wrap.classList.toggle('hidden', mode === 'law');
  const hint = document.getElementById('chatHint');
  if (hint) {
    hint.textContent =
      mode === 'law'
        ? '提示：法律问答基于内置法规库（民法典 / 劳动合同法 / 消保法精选），回答会引用法条。'
        : '提示：助手只基于当前合同原文回答，找不到会直接说「没找到」。';
  }
  const input = document.getElementById('chatInput');
  if (input) {
    input.placeholder =
      mode === 'law' ? '输入法律问题…（Enter 发送）' : '问关于这份合同的问题…（Enter 发送）';
  }
  newChat();
  renderQuick();
}

// ---- 对话历史（localStorage）----
const CONV_KEY = 'chat_conversations';

function loadConvs() {
  try {
    return JSON.parse(localStorage.getItem(CONV_KEY) || '[]');
  } catch (e) {
    return [];
  }
}

function saveConvs(list) {
  localStorage.setItem(CONV_KEY, JSON.stringify(list.slice(0, 30)));
}

function persistCurrent() {
  if (!chatLog.length) return;
  const list = loadConvs();
  const firstUser = chatHistory.find((m) => m.role === 'user');
  const conv = {
    id: currentConvId || 'c_' + Date.now(),
    title: (firstUser ? firstUser.content : '新对话').slice(0, 22),
    mode: chatMode,
    contract: document.getElementById('chatContract').value || '',
    log: chatLog.slice(),
    history: chatHistory.slice(),
    updatedAt: Date.now(),
  };
  const idx = list.findIndex((c) => c.id === conv.id);
  if (idx >= 0) list[idx] = conv;
  else list.unshift(conv);
  saveConvs(list);
  currentConvId = conv.id;
  renderConvs();
}

function renderConvs() {
  const box = document.getElementById('convList');
  const list = loadConvs();
  if (!list.length) {
    box.innerHTML = '<div class="text-[11px] text-slate-300">暂无历史对话</div>';
    return;
  }
  box.innerHTML = list
    .map(
      (c) => `
    <button data-conv="${c.id}" class="conv-item w-full text-left px-2.5 py-2 rounded-lg hover:bg-slate-50 ${c.id === currentConvId ? 'bg-brand-50' : ''}">
      <div class="text-xs text-slate-700 truncate">${c.title}</div>
      <div class="text-[10px] text-slate-400 mt-0.5">${c.mode === 'law' ? '📚 法律' : '📄 合同'} · ${fmtTime(c.updatedAt / 1000)}</div>
    </button>`
    )
    .join('');
  box.querySelectorAll('[data-conv]').forEach((b) =>
    b.addEventListener('click', () => restoreConv(b.dataset.conv))
  );
}

function restoreConv(id) {
  const conv = loadConvs().find((c) => c.id === id);
  if (!conv) return;
  setChatMode(conv.mode || 'contract');
  if (conv.contract) {
    const sel = document.getElementById('chatContract');
    if (sel) sel.value = conv.contract;
  }
  currentConvId = conv.id;
  chatHistory = (conv.history || []).slice();
  chatLog = [];
  document.getElementById('chatMessages').innerHTML = '';
  (conv.log || []).forEach((m) => appendChat(m.role, m.html));
  if (!conv.log || !conv.log.length) showChatEmpty();
  renderConvs();
}

function newConversation() {
  persistCurrent();
  currentConvId = null;
  newChat();
  renderConvs();
}

document.getElementById('chatSend').addEventListener('click', sendChat);
document.getElementById('chatInput').addEventListener('keydown', (e) => {
  if (e.key === 'Enter') sendChat();
});
document.getElementById('chatNew').addEventListener('click', newConversation);
document.getElementById('chatContract').addEventListener('change', newChat);
document.getElementById('clearConvs').addEventListener('click', () => {
  if (!confirm('确定清空所有历史对话？')) return;
  localStorage.removeItem(CONV_KEY);
  currentConvId = null;
  renderConvs();
});
document.querySelectorAll('.chatModeBtn').forEach((b) =>
  b.addEventListener('click', () => setChatMode(b.dataset.chatMode))
);

setChatMode('contract');
renderConvs();

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
  currentUser = null;
  location.hash = '#/home';
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
  currentUser = user;
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
        <td class="px-4 py-2.5"><button data-del-user="${u.id}" data-name="${u.username}" class="text-xs text-red-500 hover:text-red-700">删除</button></td>
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
        <td class="px-4 py-2.5"><button data-del-review="${r.id}" class="text-xs text-red-500 hover:text-red-700">删除</button></td>
      </tr>`
        )
        .join('') ||
      '<tr><td colspan="5" class="px-4 py-6 text-center text-slate-400">暂无审查记录</td></tr>';

    document.querySelectorAll('[data-del-user]').forEach((b) =>
      b.addEventListener('click', () => delUser(b.dataset.delUser, b.dataset.name))
    );
    document.querySelectorAll('[data-del-review]').forEach((b) =>
      b.addEventListener('click', () => delReview(b.dataset.delReview))
    );
  } catch (e) {
    document.getElementById('adminUsersBody').innerHTML =
      '<tr><td colspan="5" class="px-4 py-6 text-center text-slate-400">加载失败</td></tr>';
  }
}

async function delUser(id, name) {
  if (!confirm(`确定删除用户「${name}」？其审查记录也会一并删除。`)) return;
  const res = await fetch('/api/admin/users/' + id, { method: 'DELETE', headers: authHeaders() });
  if (!res.ok) {
    const d = await res.json().catch(() => ({}));
    alert('删除失败：' + (d.detail || res.status));
    return;
  }
  loadAdmin();
}

async function delReview(id) {
  if (!confirm('确定删除这条审查记录？')) return;
  const res = await fetch('/api/reviews/' + id, { method: 'DELETE', headers: authHeaders() });
  if (!res.ok) {
    const d = await res.json().catch(() => ({}));
    alert('删除失败：' + (d.detail || res.status));
    return;
  }
  loadAdmin();
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
