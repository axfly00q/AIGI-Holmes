/* global */
'use strict';

function $(id) { return document.getElementById(id); }
function setStatus(el, msg, type) {
  el.textContent = msg;
  el.className = 'status-msg' + (type ? ' ' + type : '');
}
function spinnerHTML() { return '<span class="spinner"></span>'; }

const AUTH_KEY      = 'aigi_token';
const AUTH_REFRESH_KEY = 'aigi_refresh';
const AUTH_USER_KEY = 'aigi_user';

function getToken() { return localStorage.getItem(AUTH_KEY); }
function authHeaders() {
  const t = getToken();
  return t ? { 'Authorization': 'Bearer ' + t } : {};
}
function saveAuth(tokens, username, role) {
  localStorage.setItem(AUTH_KEY, tokens.access_token);
  if (tokens.refresh_token) localStorage.setItem(AUTH_REFRESH_KEY, tokens.refresh_token);
  localStorage.setItem(AUTH_USER_KEY, JSON.stringify({ username, role }));
  updateAuthBar();
}
function clearAuth() {
  localStorage.removeItem(AUTH_KEY);
  localStorage.removeItem(AUTH_REFRESH_KEY);
  localStorage.removeItem(AUTH_USER_KEY);
  updateAuthBar();
}
function updateAuthBar() {
  const raw = localStorage.getItem(AUTH_USER_KEY);
  if (raw) {
    const u = JSON.parse(raw);
    $('authGuest').hidden = true;
    $('authUser').hidden  = false;
    $('authUsername').textContent = u.username;
    const badge = $('authRoleBadge');
    badge.textContent = u.role;
    badge.className   = 'auth-role-badge role-' + u.role;
    $('btnShowRole').hidden = false;
    const isAdmin = u.role === 'admin';
    // Show/hide admin-only history sub-tabs
    document.querySelectorAll('.history-tab-admin').forEach(el => {
      el.style.display = isAdmin ? 'inline-block' : 'none';
    });
    // If not admin and currently on admin-panel tab, switch back to my-records
    if (!isAdmin) {
      const activeHistSub = document.querySelector('.history-tab-btn.active');
      if (activeHistSub && activeHistSub.dataset.historyTab === 'admin-panel') {
        switchHistoryTab('my-records');
      }
    }
  } else {
    $('authGuest').hidden = false;
    $('authUser').hidden  = true;
    document.querySelectorAll('.history-tab-admin').forEach(el => {
      el.style.display = 'none';
    });
  }
  updateBatchAccess();
  if (!raw && $('reportDownload')) $('reportDownload').hidden = true;
}

$('btnShowLogin').addEventListener('click',  () => { $('loginModal').hidden = false; });
$('btnModalClose').addEventListener('click', () => { $('loginModal').hidden = true;  });
$('btnLogout').addEventListener('click',     () => { clearAuth(); });

$('tabLoginBtn').addEventListener('click', () => {
  $('loginForm').hidden    = false;
  $('registerForm').hidden = true;
  $('tabLoginBtn').classList.add('active');
  $('tabRegisterBtn').classList.remove('active');
});
$('tabRegisterBtn').addEventListener('click', () => {
  $('loginForm').hidden    = true;
  $('registerForm').hidden = false;
  $('tabRegisterBtn').classList.add('active');
  $('tabLoginBtn').classList.remove('active');
});

$('btnLogin').addEventListener('click', async () => {
  const username = $('loginUser').value.trim();
  const password = $('loginPass').value;
  if (!username || !password) { setStatus($('loginStatus'), '请填写用户名和密码', 'error'); return; }
  const r = await fetch('/api/auth/login', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password }),
  });
  const d = await r.json();
  if (!r.ok) { setStatus($('loginStatus'), '' + (d.message || '登录失败'), 'error'); return; }
  const role = JSON.parse(atob(d.access_token.split('.')[1])).role;
  saveAuth(d, username, role);
  $('loginModal').hidden = true;
  $('loginUser').value = '';
  $('loginPass').value = '';
  setStatus($('loginStatus'), '', '');
});

$('btnRegister').addEventListener('click', async () => {
  const username = $('regUser').value.trim();
  const password = $('regPass').value;
  if (!username || !password) { setStatus($('registerStatus'), '请填写用户名和密码', 'error'); return; }
  const r = await fetch('/api/auth/register', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password }),
  });
  const d = await r.json();
  if (!r.ok) { setStatus($('registerStatus'), '' + (d.message || '注册失败'), 'error'); return; }
  const role = JSON.parse(atob(d.access_token.split('.')[1])).role;
  saveAuth(d, username, role);
  $('loginModal').hidden = true;
  $('regUser').value = '';
  $('regPass').value = '';
  setStatus($('registerStatus'), '', '');
});

$('loginPass').addEventListener('keydown',   e => { if (e.key === 'Enter') $('btnLogin').click(); });
$('regPass').addEventListener('keydown',     e => { if (e.key === 'Enter') $('btnRegister').click(); });

updateAuthBar();

function openRoleModal() {
  $('roleStep1').hidden  = false;
  $('roleStep2').hidden  = true;
  $('rolePass').value    = '';
  $('roleTargetUser').value = '';
  $('roleSelect').value  = 'user';
  $('rolePassError').hidden = true;
  setStatus($('roleStatus'), '', '');
  $('roleModal').hidden  = false;
}
function closeRoleModal() { $('roleModal').hidden = true; }
$('btnShowRole').addEventListener('click', openRoleModal);
$('btnRoleModalClose').addEventListener('click', closeRoleModal);
$('roleModal').addEventListener('click', e => { if (e.target === $('roleModal')) closeRoleModal(); });

$('btnRoleUnlock').addEventListener('click', () => {
  if ($('rolePass').value === 'aigi') {
    $('rolePassError').hidden = true;
    $('roleStep1').hidden = true;
    $('roleStep2').hidden = false;
    setStatus($('roleStatus'), '✅ 密码正确，已进入角色管理界面', 'success');
  } else {
    $('rolePassError').hidden = false;
    $('rolePass').value = '';
    $('rolePass').focus();
    $('btnRoleUnlock').disabled = true;
    setTimeout(() => { $('btnRoleUnlock').disabled = false; }, 2000);
  }
});
$('rolePass').addEventListener('keydown', e => { if (e.key === 'Enter') $('btnRoleUnlock').click(); });

$('btnRoleChange').addEventListener('click', async () => {
  const targetUsername = $('roleTargetUser').value.trim();
  const newRole = $('roleSelect').value;
  if (!targetUsername) { setStatus($('roleStatus'), '请输入目标用户名', 'error'); return; }
  $('btnRoleChange').disabled = true;
  $('btnRoleChange').textContent = '修改中…';
  try {
    const r = await fetch(`/api/auth/admin/users/${encodeURIComponent(targetUsername)}/role`, {
      method: 'PATCH', headers: { 'Content-Type': 'application/json', ...authHeaders() },
      body: JSON.stringify({ role: newRole }),
    });
    const d = await r.json();
    if (!r.ok) { setStatus($('roleStatus'), '' + (d.detail || d.message || '修改失败'), 'error');
    } else {
      setStatus($('roleStatus'), `已将 ${d.username} 的角色改为 ${d.role}`, 'success');
      const rawUser = localStorage.getItem(AUTH_USER_KEY);
      if (rawUser) {
        const cu = JSON.parse(rawUser);
        if (cu.username === d.username) {
          cu.role = d.role;
          localStorage.setItem(AUTH_USER_KEY, JSON.stringify(cu));
          // Auto-refresh JWT so new role takes effect immediately without re-login
          const savedRefresh = localStorage.getItem(AUTH_REFRESH_KEY);
          if (savedRefresh) {
            fetch('/api/auth/refresh', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ refresh_token: savedRefresh }),
            }).then(rr => rr.ok ? rr.json() : null).then(newTokens => {
              if (newTokens) {
                localStorage.setItem(AUTH_KEY, newTokens.access_token);
                if (newTokens.refresh_token) localStorage.setItem(AUTH_REFRESH_KEY, newTokens.refresh_token);
              }
              updateAuthBar();
            }).catch(() => updateAuthBar());
          } else {
            updateAuthBar();
          }
        }
      }
      $('roleTargetUser').value = '';
    }
  } catch (err) { setStatus($('roleStatus'), '网络错误', 'error');
  } finally { $('btnRoleChange').disabled = false; $('btnRoleChange').textContent = '修改角色'; }
});
$('roleTargetUser').addEventListener('keydown', e => { if (e.key === 'Enter') $('btnRoleChange').click(); });

async function downloadReport(id, fmt) {
  const r = await fetch(`/api/report/${id}/export?format=${fmt}`, { headers: authHeaders() });
  if (!r.ok) { alert('下载失败，请先登录。'); return; }
  const blob = await r.blob();
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = `report_${id}.${fmt === 'pdf' ? 'pdf' : 'xlsx'}`;
  a.click();
  URL.revokeObjectURL(a.href);
}

const _tabTitles = { upload: '上传图片', url: '新闻检测', batch: '批量检测', history: '检测历史', text: '文本检测' };

function switchToTab(tabName) {
  // Close modals if open
  const _imgModal = $('imageSearchModal');
  if (_imgModal && !_imgModal.hidden) _imgModal.hidden = true;
  document.querySelectorAll('.sidebar-nav-item').forEach(b => b.classList.remove('active'));
  document.querySelectorAll('.tab-pane').forEach(p => p.classList.remove('active'));
  const navItem = document.querySelector(`.sidebar-nav-item[data-tab="${tabName}"]`);
  if (navItem) navItem.classList.add('active');
  const pane = $('tab-' + tabName);
  if (pane) pane.classList.add('active');
  if ($('topBarTitle')) $('topBarTitle').textContent = _tabTitles[tabName] || tabName;
  // When switching to history tab, load my records if needed
  if (tabName === 'history') {
    const raw = localStorage.getItem(AUTH_USER_KEY);
    if (!raw) {
      $('loginModal').hidden = false;
      return;
    }
    const activeHistSub = document.querySelector('.history-tab-btn.active');
    if (activeHistSub) {
      const subTab = activeHistSub.dataset.historyTab;
      if (subTab === 'my-records') loadMyRecords(1);
      else if (subTab === 'admin-panel') {
        const activeAdminSub = document.querySelector('.admin-sub-tab-btn.active');
        const adminTab = activeAdminSub ? activeAdminSub.dataset.adminTab : 'dashboard';
        _loadAdminSubTab(adminTab);
      }
    }
  }
}

document.querySelectorAll('.sidebar-nav-item').forEach(btn => {
  btn.addEventListener('click', () => {
    switchToTab(btn.dataset.tab);
  });
});

const dropZone   = $('dropZone');
const dropHint   = $('dropHint');
const previewImg = $('previewImg');
const fileInput  = $('fileInput');
const btnReupload = $('btnReupload');
const btnClear   = $('btnClear');
const btnDetect  = $('btnDetect');
const uploadStatus = $('uploadStatus');
let selectedFile = null;

function showPreview(file) {
  selectedFile = file;
  const url = URL.createObjectURL(file);
  previewImg.src = url;
  previewImg.style.display = 'block';
  dropHint.style.display = 'none';
  btnReupload.hidden = false;
  btnClear.hidden = false;
  btnDetect.disabled = false;
  setStatus(uploadStatus, '', '');
  hideResultCard();
}

function clearUpload() {
  lastDetectionId = null;
  lastDetectionLabel = '';
  selectedFile = null;
  previewImg.src = '';
  previewImg.style.display = 'none';
  dropHint.style.display = 'flex';
  btnReupload.hidden = true;
  btnClear.hidden = true;
  btnDetect.disabled = true;
  fileInput.value = '';
  setStatus(uploadStatus, '', '');
  $('reportDownload').hidden = true;
  if($('quickActions')) $('quickActions').hidden = true;
  const es = $('explainSection'); if (es) es.hidden = true;
  const camOvl = $('camOverlay');
  camOvl.src = ''; camOvl.classList.remove('visible');
  $('btnCamToggle').hidden = true; $('btnCamToggle').classList.remove('active');
  hideResultCard();
}

function hideResultCard() {
  $('resultCard').style.display = 'none';
  $('resultEmpty').style.display = 'flex';
  const es = $('explainSection'); if (es) es.hidden = true;
  const rp = document.querySelector('.result-panel');
  if (rp) { rp.style.alignItems = 'center'; rp.style.justifyContent = 'center'; }
}

fileInput.addEventListener('change', e => { const f = e.target.files[0]; if (f) showPreview(f); });
dropZone.addEventListener('click', () => { if (!selectedFile) fileInput.click(); });
dropZone.addEventListener('dragover', e => { e.preventDefault(); dropZone.classList.add('drag-over'); });
dropZone.addEventListener('dragleave', () => dropZone.classList.remove('drag-over'));
dropZone.addEventListener('drop', e => {
  e.preventDefault(); dropZone.classList.remove('drag-over');
  const f = e.dataTransfer.files[0]; if (f && f.type.startsWith('image/')) showPreview(f);
});
btnReupload.addEventListener('click', e => { e.stopPropagation(); fileInput.click(); });
btnClear.addEventListener('click', e => { e.stopPropagation(); clearUpload(); });

$('btnCamToggle').addEventListener('click', e => {
  e.stopPropagation();
  const cam = $('camOverlay');
  const btn = $('btnCamToggle');
  const show = !cam.classList.contains('visible');
  cam.classList.toggle('visible', show);
  btn.classList.toggle('active', show);
  btn.textContent = show ? '原图' : '热力图';
});

function renderResult(data) {
  const isReal = data.label === 'REAL';
  const cls = isReal ? 'real' : 'fake';
  const v = $('verdict');
  v.className = 'verdict ' + cls;
  $('verdictIcon').textContent = isReal ? '' : '';
  $('verdictLabel').textContent = data.label_zh;
  const c = Math.round(data.confidence);
  $('confValue').textContent = c + '%';
  const b = $('confBar');
  b.className = 'progress-bar ' + cls;
  b.style.width = '0%';
  requestAnimationFrame(()=>{requestAnimationFrame(()=>{b.style.width=c+'%';});});
  const rows = $('probRows'); rows.innerHTML='';
  (data.probs||[]).forEach(p=>{
    const pc = p.label==='REAL'?'real':'fake';
    const s=Math.round(p.score);
    rows.insertAdjacentHTML('beforeend',`
    <div class="prob-row">
      <div class="prob-row-header">
        <span class="prob-row-label">${p.label_zh}</span>
        <span class="prob-row-score">${s}%</span>
      </div>
      <div class="prob-track">
        <div class="prob-fill ${pc}" style="width:0%" data-score="${s}"></div>
      </div>
    </div>`);
  });
  requestAnimationFrame(()=>{requestAnimationFrame(()=>{
    rows.querySelectorAll('.prob-fill').forEach(e=>{e.style.width=e.dataset.score+'%';});
  });});
  const exp = data.explanation;
  const es = $('explainSection');
  if(exp && es){
    const lev = $('explainLevel');
    lev.textContent=exp.level;
    lev.className='explain-level '+cls;
    $('explainSummary').textContent=exp.summary;
    const clist = $('explainClues'); clist.innerHTML='';
    (exp.clues||[]).forEach(x=>{const li=document.createElement('li');li.textContent=x;clist.appendChild(li);});
    clist.style.display=exp.clues?.length?'':'none';
    $('explainDisclaimer').textContent=exp.disclaimer||'';
    es.hidden = false;
    es.removeAttribute('open'); // collapsed by default; user can click to expand
  }else if(es){ es.hidden = true; }
  const cam = $('camOverlay');
  if(data.cam_image){cam.src=data.cam_image;$('btnCamToggle').hidden=false;}
  else{cam.src='';$('btnCamToggle').hidden=true;}
  $('resultEmpty').style.display='none';
  $('resultCard').style.display='flex';
  const rp=document.querySelector('.result-panel');
  if(rp){rp.style.alignItems='flex-start';rp.style.justifyContent='flex-start';}
}

btnDetect.addEventListener('click', async ()=>{
  if(!selectedFile)return;
  btnDetect.disabled=true;
  btnDetect.classList.add('loading');
  btnDetect.innerHTML=spinnerHTML()+'检测中…';
  const fd=new FormData();
  fd.append('image',selectedFile);
  try{
    const res=await fetch('/api/detect?cam=1',{method:'POST',body:fd,headers:authHeaders()});
    const data=await res.json();
    if(!res.ok||data.error){
      setStatus(uploadStatus,'检测失败','error');
    }else{
      renderResult(data);
      lastDetectionId = data.detection_id || null;
      lastDetectionLabel = data.label || '';
      setStatus(uploadStatus,'检测完成','success');
      const rd=$('reportDownload');
      if(data.detection_id&&getToken()){
        rd.hidden=false;
        $('btnDownloadPdf').onclick=()=>downloadReport(data.detection_id,'pdf');
        $('btnDownloadExcel').onclick=()=>downloadReport(data.detection_id,'excel');
      }else{rd.hidden=true;}

      // ✅ 自动显示快捷按钮
      if($('quickActions')){
        $('quickActions').hidden=false;
      }

      // ✅ 显示 AI 分析面板（仅在判定为 AI 生成时）
      currentDetectionId = data.detection_id || null;
      if($('aiAnalysisPanel') && data.label === 'FAKE'){
        $('aiAnalysisPanel').hidden=false;
        resetAnalysisPanel();
        // 加载该检测的历史记录（支持多轮对话）
        if (currentDetectionId) {
          loadAnalysisHistory(currentDetectionId);
        }
      } else if($('aiAnalysisPanel')){
        $('aiAnalysisPanel').hidden=true;
      }
    }
  }catch(e){
    setStatus(uploadStatus,'网络错误','error');
  }finally{
    btnDetect.classList.remove('loading');
    btnDetect.innerHTML='开始检测';
    btnDetect.disabled=false;
  }
});

const urlInput = $('urlInput');
const btnUrl = $('btnUrl');
const urlStatus = $('urlStatus');
const gallery = $('gallery');
const reportSection = $('reportSection');
const reportBody = $('reportBody');
let _urlRadarChart = null;
let _urlArticleText = '';
let _urlTextResult = null;
let _urlPageTitle = '';
let _urlPageSummary = '';
let lastDetectionId = null;   // detection_id of the last single-image result
let lastDetectionLabel = '';  // 'FAKE' or 'REAL'

function _escHtml(s){return s?s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;'):'';}

function buildGalleryCard(it){
  const c=it.label==='REAL'?'real':'fake';
  const catBadge = it.category ? `<span class="gallery-card__cat">${it.category}</span>` : '';
  const consistencyHtml = it.consistency ? `<div class="gallery-card__consistency"><span class="consistency-dot" style="background:${it.consistency.score>=60?'#22c55e':it.consistency.score>=40?'#f59e0b':'#ef4444'}"></span><span>${it.consistency.assessment} ${Math.round(it.consistency.score)}%</span></div>` : '';
  const mb=(it.probs||[]).map(p=>{
    const pc=p.label==='REAL'?'real':'fake';
    const s=Math.round(p.score);
    return `<div class="mini-row"><span class="mini-label">${p.label_zh}</span><div class="mini-track"><div class="mini-fill ${pc}" style="width:0%" data-score="${s}"></div></div><span class="mini-score">${s}%</span></div>`;
  }).join('');
  // 点击按钮时调用 _searchFromCard(this) 来读取 data-category
  const searchBtn = `<button class="gallery-card__search-similar" data-category="${_escHtml(it.category || '')}" onclick="_searchFromCard(this)" title="用文章标题和图片类别在网络查找类似图片">查找类似图片</button>`;
  return `<div class="gallery-card"><img class="gallery-card__img" src="${it.thumbnail}" alt="图"/><div class="gallery-card__body"><div class="gallery-card__top-row"><span class="gallery-card__badge ${c}">${it.label_zh}</span>${catBadge}</div><p class="gallery-card__conf">置信度：<span>${Math.round(it.confidence)}%</span></p>${consistencyHtml}<div class="gallery-card__mini-bars">${mb}</div>${searchBtn}</div></div>`;
}
function buildReportRow(it){
  const c=it.label==='REAL'?'real':'fake';
  const conText = it.consistency ? ` · 图文一致性: ${it.consistency.assessment}(${Math.round(it.consistency.score)}%)` : '';
  return `<div class="report-row"><span class="report-row__index">图${it.index}</span><span class="report-row__badge ${c}">${_escHtml(it.label_zh)}</span><span class="report-row__conf">${Math.round(it.confidence)}%</span><span class="report-row__url">${_escHtml(it.url)}${conText}</span></div>`;
}

async function detectUrlText() {
  if (!_urlArticleText) return;
  const btn = $('btnDetectUrlText');
  if (btn) { btn.disabled = true; btn.innerHTML = spinnerHTML() + '\u68c0\u6d4b\u4e2d…'; }
  try {
    const res = await fetch('/api/text/detect', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...authHeaders() },
      body: JSON.stringify({ text: _urlArticleText, xai_method: 'lime', num_features: 15 }),
    });
    const result = await res.json();
    if (!res.ok) throw new Error(result.detail || `HTTP ${res.status}`);
    _urlTextResult = result;
    renderUrlTextResult(result);
  } catch (err) {
    showToast('\u6587\u672c\u68c0\u6d4b\u5931\u8d25\uff1a' + err.message);
  } finally {
    const b = $('btnDetectUrlText');
    if (b) { b.disabled = false; b.textContent = '\u91cd\u65b0\u68c0\u6d4b'; }
  }
}

function renderUrlTextResult(result) {
  const wrap = $('urlTextDetectResult');
  if (!wrap) return;
  const isFake = result.label === 'FAKE';
  const color = isFake ? '#ef4444' : '#22c55e';
  const lime = result.explanations && result.explanations.lime;
  const topKws = lime ? (lime.top_positive || []).slice(0, 8).map(t =>
    `<span class="url-text-kw url-text-kw--fake">${(t.token||'').replace(/</g,'&lt;').replace(/>/g,'&gt;')} <small>${(t.weight||t.contribution||0).toFixed(3)}</small></span>`
  ).join('') : '';
  const realKws = lime ? (lime.top_negative || []).slice(0, 5).map(t =>
    `<span class="url-text-kw url-text-kw--real">${(t.token||'').replace(/</g,'&lt;').replace(/>/g,'&gt;')} <small>${Math.abs(t.weight||t.contribution||0).toFixed(3)}</small></span>`
  ).join('') : '';
  wrap.innerHTML = `
    <div class="url-text-result-card">
      <div class="url-text-result-badge" style="background:${color}">${result.label_zh||result.label}</div>
      <div class="url-text-result-info">
        <span class="url-text-result-label">${result.label_zh||result.label}</span>
        <span class="url-text-result-conf">置信度 ${(result.confidence||0).toFixed(1)}%</span>
      </div>
    </div>
    ${(topKws||realKws) ? `<div class="url-text-kw-section">${topKws ? `<div class="url-text-kw-row"><span class="url-text-kw-title">AI 特征词：</span>${topKws}</div>` : ''}${realKws ? `<div class="url-text-kw-row"><span class="url-text-kw-title">真实特征词：</span>${realKws}</div>` : ''}</div>` : ''}
    ${result.highlighted_html ? `<div class="url-text-highlighted"><span class="url-text-kw-title">标注文本：</span><div class="url-text-box">${result.highlighted_html}</div></div>` : ''}
  `;
  wrap.hidden = false;
  _updateReportWithTextResult(result);
}

function _updateReportWithTextResult(result) {
  const dimEl = $('reportDimensions');
  if (!dimEl || dimEl.innerHTML === '') return;
  const isFake = result.label === 'FAKE';
  const color = isFake ? '#ef4444' : '#22c55e';
  const desc = isFake ? '文章内容留1aAI生成，建议结合其他信息核实。' : '文章内容未检测到明显AI生成特征。';
  const html = `<div class="url-text-report-row" style="margin-top:12px;padding:12px 16px;background:#f8fafc;border-radius:6px;border-left:3px solid ${color};font-size:14px;"><strong style="color:#374151;">文章文本检测：</strong><span style="color:${color};font-weight:600;margin:0 8px;">${result.label_zh||result.label}</span>· 置信度 ${(result.confidence||0).toFixed(1)}% · <span style="color:#64748b;">${desc}</span></div>`;
  const existing = dimEl.querySelector('.url-text-report-row');
  if (existing) { existing.outerHTML = html; } else { dimEl.insertAdjacentHTML('beforeend', html); }
}

function renderUrlAnalysis(d) {
  // Show summary panel
  if (d.page_title || d.page_summary) {
    $('urlPageTitle').textContent = d.page_title || '未知标题';
    $('urlPageSummary').textContent = d.page_summary || '无法提取摘要';
    $('urlSummaryPanel').hidden = false;
    // Show translate button when summary is available
    const summary = d.page_summary || '';
    const translateBtn = $('btnTranslateSummary');
    const translatedEl = $('urlSummaryTranslated');
    if (translateBtn && summary.length > 0) {
      translateBtn.style.display = 'inline-block';
      translateBtn.textContent = '翻译成中文';
      translateBtn.disabled = false;
      if (translatedEl) { translatedEl.style.display = 'none'; translatedEl.textContent = ''; }
    }
  } else {
    $('urlSummaryPanel').hidden = true;
  }

  // Text detection wrap: show if article_text available, reset state
  _urlArticleText = d.article_text || '';
  _urlPageTitle = d.page_title || '';
  _urlPageSummary = d.page_summary || '';
  _urlTextResult = null;
  const _textWrap = $('urlTextDetectWrap');
  if (_textWrap) {
    _textWrap.hidden = !_urlArticleText;
    const _tr = $('urlTextDetectResult');
    if (_tr) { _tr.hidden = true; _tr.innerHTML = ''; }
    const _tbtn = $('btnDetectUrlText');
    if (_tbtn) { _tbtn.disabled = false; _tbtn.textContent = '\u68c0\u6d4b\u6587\u7ae0\u6587\u672c'; }
  }

  // Show analysis layout
  $('urlAnalysisLayout').hidden = false;

  // Render gallery cards
  gallery.innerHTML = d.results.map(buildGalleryCard).join('');
  requestAnimationFrame(()=>{requestAnimationFrame(()=>{
    gallery.querySelectorAll('.mini-fill').forEach(x=>x.style.width=x.dataset.score+'%');
  });});

  // Render stats
  const dim = d.dimensions || {};
  $('urlStatsTotal').textContent = dim.image_count || d.count;
  $('urlStatsReal').textContent = dim.real_count || 0;
  $('urlStatsFake').textContent = dim.fake_count || 0;

  // Score circle
  const score = d.overall_score || 0;
  const scoreEl = $('urlScoreValue');
  scoreEl.textContent = Math.round(score);
  const circumference = 2 * Math.PI * 44;
  const arc = $('urlScoreArc');
  const offset = circumference * (score / 100);
  arc.style.strokeDasharray = `${offset} ${circumference}`;
  arc.style.stroke = score >= 70 ? '#22c55e' : score >= 40 ? '#f59e0b' : '#ef4444';
  scoreEl.style.color = score >= 70 ? '#22c55e' : score >= 40 ? '#f59e0b' : '#ef4444';

  // Radar chart
  if (!_urlRadarChart && typeof echarts !== 'undefined') {
    _urlRadarChart = echarts.init($('urlRadarChart'), null, {renderer:'canvas'});
  }
  if (_urlRadarChart) {
    _urlRadarChart.setOption({
      backgroundColor: 'transparent',
      tooltip: {trigger:'item'},
      radar: {
        indicator: [
          {name:'真实性', max:100},
          {name:'置信度', max:100},
          {name:'图文一致', max:100},
          {name:'公章完整性', max:100},
          {name:'频率自然性', max:100},
          {name:'边界一致性', max:100},
        ],
        shape: 'polygon',
        axisLine: {lineStyle:{color:'#e2e8f0'}},
        splitLine: {lineStyle:{color:'#e2e8f0'}},
        splitArea: {areaStyle:{color:['#f8fafc','#f1f5f9']}},
        axisName: {color:'#64748b', fontSize:11},
      },
      series: [{
        type: 'radar',
        data: [{
          name: '分析结果',
          value: [
            dim.authenticity || 0,
            dim.confidence || 0,
            dim.consistency || 50,
            dim.seal || 50,
            dim.frequency || 50,
            dim.edge || 50,
          ],
          lineStyle: {color:'#60a5fa'},
          areaStyle: {color:'rgba(96,165,250,0.2)'},
          itemStyle: {color:'#60a5fa'},
        }],
      }],
    });
  }

  // Consistency bar
  const conScore = dim.consistency || 50;
  const conBar = $('urlConsistencyBar');
  conBar.style.width = conScore + '%';
  conBar.style.background = conScore >= 60 ? '#22c55e' : conScore >= 40 ? '#f59e0b' : '#ef4444';
  $('urlConsistencyText').textContent = (conScore >= 60 ? '一致' : conScore >= 40 ? '部分一致' : '不一致') + ' ' + Math.round(conScore) + '%';

  // Category tags
  const cats = dim.categories || {};
  $('urlCatTags').innerHTML = Object.entries(cats).map(([k,v]) => `<span class="cat-tag">${k} ${v}张</span>`).join('');

  // Report section
  reportBody.innerHTML = d.results.map(buildReportRow).join('');

  // Report dimensions summary
  const dimSummary = $('reportDimensions');
  const verdictText = dim.verdict || (score>=70?'该新闻页面图片以真实内容为主，图文一致性较好，可信度较高。':score>=40?'该新闻页面存在部分可疑图片，建议进一步核实。':'该新闻页面多张图片被判定为AI生成，建议谨慎引用，必要时核实图片来源。');
  dimSummary.innerHTML = `
    <div class="report-dim-grid report-dim-grid--7">
      <div class="report-dim-item">
        <span class="report-dim-label">综合评分</span>
        <span class="report-dim-value" style="color:${score>=70?'#22c55e':score>=40?'#f59e0b':'#ef4444'}">${Math.round(score)}</span>
      </div>
      <div class="report-dim-item">
        <span class="report-dim-label">真实率</span>
        <span class="report-dim-value">${Math.round(dim.authenticity||0)}%</span>
      </div>
      <div class="report-dim-item">
        <span class="report-dim-label">平均置信度</span>
        <span class="report-dim-value">${Math.round(dim.confidence||0)}%</span>
      </div>
      <div class="report-dim-item">
        <span class="report-dim-label">图文一致性</span>
        <span class="report-dim-value">${Math.round(dim.consistency||50)}%</span>
      </div>
      <div class="report-dim-item">
        <span class="report-dim-label">公章完整性</span>
        <span class="report-dim-value">${Math.round(dim.seal||50)}%</span>
      </div>
      <div class="report-dim-item">
        <span class="report-dim-label">频率自然性</span>
        <span class="report-dim-value">${Math.round(dim.frequency||50)}%</span>
      </div>
      <div class="report-dim-item">
        <span class="report-dim-label">边界一致性</span>
        <span class="report-dim-value">${Math.round(dim.edge||50)}%</span>
      </div>
    </div>
    <div class="report-conclusion">
      <strong>检测结论：</strong>${verdictText}
    </div>
  `;
  reportSection.hidden = false;

  // F1: show quick-actions toolbar
  const _qa = $('urlQuickActions');
  if (_qa) _qa.hidden = false;
}

btnUrl.addEventListener('click', async ()=>{
  const u=urlInput.value.trim();
  if(!u){setStatus(urlStatus,'请输入URL','error');return;}
  btnUrl.disabled=true;
  btnUrl.classList.add('loading');
  btnUrl.innerHTML=spinnerHTML()+'抓取中…';
  gallery.innerHTML='';
  reportSection.hidden=true;
  $('urlSummaryPanel').hidden=true;
  $('urlAnalysisLayout').hidden=true;
  const _textWrapReset = $('urlTextDetectWrap'); if (_textWrapReset) _textWrapReset.hidden = true;
  const _qa = $('urlQuickActions'); if (_qa) _qa.hidden = true;
  // F2: Progressive status feedback with staged messages
  setStatus(urlStatus,'正在抓取页面内容…','');
  const _pt1 = setTimeout(()=>{ if(btnUrl.disabled){ btnUrl.innerHTML=spinnerHTML()+'提取图片…'; setStatus(urlStatus,'正在识别并提取图片链接…',''); }}, 2200);
  const _pt2 = setTimeout(()=>{ if(btnUrl.disabled){ btnUrl.innerHTML=spinnerHTML()+'AI 检测中…'; setStatus(urlStatus,'正在进行 AI 检测分析，请稍候…',''); }}, 4800);
  try{
    const res=await fetch('/api/detect-url',{method:'POST',headers:{'Content-Type':'application/json',...authHeaders()},body:JSON.stringify({url:u})});
    clearTimeout(_pt1); clearTimeout(_pt2);
    const d=await res.json();
    if(!res.ok||d.error){setStatus(urlStatus,`${d.detail||d.message||'请求失败'}`,'error');
    }else{
      const cnt = d.count||(d.results||[]).length;
      setStatus(urlStatus,`检测完成，共分析 ${cnt} 张图片`,'success');
      renderUrlAnalysis(d);
    }
  }catch(e){
    clearTimeout(_pt1); clearTimeout(_pt2);
    setStatus(urlStatus,'网络错误','error');
  }finally{btnUrl.classList.remove('loading');btnUrl.innerHTML='抓取并检测';btnUrl.disabled=false;}
});
urlInput.addEventListener('keydown',e=>{if(e.key==='Enter')btnUrl.click();});

// URL export PDF - print-based
$('btnUrlExportPdf').addEventListener('click', () => {
  const reportEl = $('reportSection');
  if (!reportEl) return;
  const w = window.open('', '_blank');
  w.document.write(`<!DOCTYPE html><html><head><meta charset="utf-8"><title>AIGI-Holmes 检测报告</title>
  <style>body{font-family:sans-serif;padding:20px;color:#333}
  .report-dim-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin:16px 0}
  .report-dim-grid--7{grid-template-columns:repeat(4,1fr)}
  .report-dim-item{background:#f5f5f5;border-radius:8px;padding:12px;text-align:center}
  .report-dim-label{font-size:12px;color:#666;display:block}
  .report-dim-value{font-size:22px;font-weight:700;display:block;margin-top:4px}
  .report-row{display:flex;gap:10px;padding:6px 0;border-bottom:1px solid #eee;font-size:14px}
  .report-row__badge{padding:2px 8px;border-radius:4px;font-size:12px;font-weight:600}
  .report-row__badge.fake{background:#fee;color:#c00}
  .report-row__badge.real{background:#efe;color:#060}
  .report-conclusion{background:#f9f9f9;padding:12px;border-radius:8px;margin-top:12px;font-size:14px}
  </style></head><body><h1>AIGI-Holmes 新闻图片检测报告</h1>`);
  w.document.write(reportEl.innerHTML);
  w.document.write('</body></html>');
  w.document.close();
  w.print();
});

// F1: URL quick-action — merged share button (copy + dialog)
$('btnUrlShare').addEventListener('click', () => {
  const url = urlInput.value.trim() || window.location.href;
  // Auto-copy to clipboard silently
  if (navigator.clipboard) { navigator.clipboard.writeText(url).catch(()=>{}); }
  // Show share dialog with URL pre-filled
  openActionModal(`
    <div style="padding:20px;">
      <h3 style="color:#1e293b;margin:0 0 8px;font-size:1rem;">分享检测链接</h3>
      <p style="color:#64748b;font-size:0.85rem;margin:0 0 12px;">链接已自动复制到剪贴板，也可手动选择复制：</p>
      <input type="text" value="${_escHtml(url)}" readonly
        style="width:100%;padding:8px 10px;border-radius:6px;border:1px solid #e2e8f0;background:#f8fafc;color:#1e293b;font-size:0.85rem;box-sizing:border-box;"
        onclick="this.select();" />
      <button class="btn-detect" id="btnActionConfirm" style="margin-top:14px;width:100%;">关闭</button>
    </div>
  `);
  $('btnActionConfirm').addEventListener('click', closeActionModal);
});

$('btnUrlScrollTop').addEventListener('click', () => {
  window.scrollTo({ top: 0, behavior: 'smooth' });
});

// 文章文本检测按鈕
$('btnDetectUrlText').addEventListener('click', detectUrlText);

// Translation button for news summary
document.addEventListener('click', (e) => {
  if (e.target && e.target.id === 'btnTranslateSummary') {
    const btn = e.target;
    const summaryEl = $('urlPageSummary');
    const translatedEl = $('urlSummaryTranslated');
    if (!summaryEl || !translatedEl) return;
    const text = summaryEl.textContent.trim();
    if (!text) return;
    btn.disabled = true;
    btn.textContent = '翻译中...';
    translatedEl.style.display = 'block';
    translatedEl.textContent = '';
    fetch('/api/translate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text }),
    }).then(res => {
      if (!res.ok || !res.body) {
        translatedEl.textContent = '翻译失败';
        btn.disabled = false;
        btn.textContent = '重新翻译';
        return;
      }
      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      let fullText = '';
      function read() {
        reader.read().then(({ done, value }) => {
          if (done) {
            btn.textContent = '重新翻译';
            btn.disabled = false;
            return;
          }
          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split('\n');
          buffer = lines.pop();
          for (const line of lines) {
            if (!line.startsWith('data: ')) continue;
            const data = line.slice(6);
            if (data === '[DONE]') { btn.textContent = '重新翻译'; btn.disabled = false; return; }
            try {
              const parsed = JSON.parse(data);
              if (parsed.error) { translatedEl.textContent = '翻译失败：' + parsed.error; btn.disabled = false; btn.textContent = '重新翻译'; return; }
              if (parsed.chunk) { fullText += parsed.chunk; translatedEl.textContent = fullText; }
            } catch {}
          }
          read();
        });
      }
      read();
    }).catch(() => {
      translatedEl.textContent = '翻译失败';
      btn.disabled = false;
      btn.textContent = '重新翻译';
    });
  }
});

function updateBatchAccess(){
  const raw=localStorage.getItem(AUTH_USER_KEY);
  const role=raw?JSON.parse(raw).role:null;
  const allow=role==='auditor'||role==='admin';
  const hint=$('batchAuthHint');
  if(!raw){hint.hidden=false;hint.querySelector('p').textContent='批量检测需要登录';
  }else if(!allow){hint.hidden=false;hint.querySelector('p').innerHTML='需要 auditor / admin';
  }else{hint.hidden=true;}
}

/* ── Batch detection — WebSocket + drag-drop ───── */
let _batchWs=null;
let _batchRunning=false;
let _batchIndexOffset=0;

const _ACCEPTED_RE = /\.(jpe?g|png|webp|gif|bmp|pdf|docx?|html?|txt)$/i;

// 批量统计七维分类（每张结果出来立即更新雷达图）
const _BATCH_CATS=['人物','动物','建筑','风景','食物','交通','其他'];
function _makeCatMap(){const m={};_BATCH_CATS.forEach(c=>{m[c]={c:0,r:0,f:0};});return m;}
let _batchStats={total:0,realCount:0,fakeCount:0,confSum:0,cats:_makeCatMap()};
let _radarChart=null;

function _resetBatchStats(){
  _batchStats.total=0;_batchStats.realCount=0;_batchStats.fakeCount=0;_batchStats.confSum=0;
  _BATCH_CATS.forEach(c=>{_batchStats.cats[c].c=0;_batchStats.cats[c].r=0;_batchStats.cats[c].f=0;});
}

// 每张结果到达时调用，立即更新所有统计数字和雷达图
function _updateBatchStatsFromResult(r){
  const cat=(_BATCH_CATS.indexOf(r.category)>=0)?r.category:'其他';
  const realScore=(r.probs.find(p=>p.label==='REAL')||{score:0}).score;
  const fakeScore=(r.probs.find(p=>p.label==='FAKE')||{score:0}).score;
  _batchStats.total++;
  if(r.label==='REAL') _batchStats.realCount++; else _batchStats.fakeCount++;
  _batchStats.confSum+=r.confidence;
  _batchStats.cats[cat].c++;
  _batchStats.cats[cat].r+=realScore;
  _batchStats.cats[cat].f+=fakeScore;
  _refreshStatsPanel();
}

function _refreshStatsPanel(){
  // 首次调用时展开两栏布局
  const layout=$('batchResultLayout');
  if(layout.hidden){
    layout.hidden=false;
    // 容器可见后初始化雷达图
    if(!_radarChart&&typeof echarts!=='undefined'){
      _radarChart=echarts.init($('statsRadar'),null,{renderer:'canvas'});
      _radarChart.setOption({
        backgroundColor:'transparent',
        tooltip:{trigger:'item'},
        legend:{bottom:0,textStyle:{color:'#64748b',fontSize:11},data:['真实照片','AI生成']},
        radar:{
          indicator:_BATCH_CATS.map(c=>({name:c,max:100})),
          shape:'polygon',
          axisLine:{lineStyle:{color:'#e2e8f0'}},
          splitLine:{lineStyle:{color:'#e2e8f0'}},
          splitArea:{areaStyle:{color:['#f8fafc','#f1f5f9']}},
          axisName:{color:'#64748b',fontSize:11}
        },
        series:[{
          type:'radar',
          data:[
            {name:'真实照片',value:[0,0,0,0,0,0,0],
             lineStyle:{color:'#4ade80'},areaStyle:{color:'rgba(74,222,128,0.15)'},
             itemStyle:{color:'#4ade80'}},
            {name:'AI生成',value:[0,0,0,0,0,0,0],
             lineStyle:{color:'#f87171'},areaStyle:{color:'rgba(248,113,113,0.15)'},
             itemStyle:{color:'#f87171'}}
          ]
        }]
      });
    }
  }
  // 可信率
  const avg=_batchStats.total?Math.round(_batchStats.confSum/_batchStats.total):0;
  const valEl=$('statsCredibility');
  valEl.textContent=avg;
  valEl.style.color=avg>=70?'#4ade80':(avg>=40?'#f97316':'#f87171');
  $('statsTotal').textContent=_batchStats.total;
  $('statsReal').textContent=_batchStats.realCount;
  $('statsFake').textContent=_batchStats.fakeCount;
  // 雷达图实时刷新
  if(_radarChart){
    const realVals=_BATCH_CATS.map(c=>{const d=_batchStats.cats[c];return d.c?Math.round(d.r/d.c):0;});
    const fakeVals=_BATCH_CATS.map(c=>{const d=_batchStats.cats[c];return d.c?Math.round(d.f/d.c):0;});
    _radarChart.setOption({series:[{data:[{value:realVals},{value:fakeVals}]}]});
  }
  // 分类标签
  const tags=_BATCH_CATS.filter(c=>_batchStats.cats[c].c>0)
    .map(c=>`<span class="cat-tag">${c} ${_batchStats.cats[c].c}张</span>`).join('');
  $('statsCats').innerHTML=tags;
}

// 文件夹选取：使用 File System Access API，避免浏览器显示“是否上传到此站点”对话框
async function _pickFolderWithoutDialog(){
  if(typeof window.showDirectoryPicker==='function'){
    try{
      const dirHandle=await window.showDirectoryPicker({mode:'read'});
      const files=[];
      await _collectFilesFromDir(dirHandle,files);
      const filtered=files.filter(f=>_ACCEPTED_RE.test(f.name));
      if(filtered.length) handleBatchFiles(filtered);
    }catch(e){
      if(e.name!=='AbortError') console.warn('showDirectoryPicker failed:',e);
    }
  }else{
    // 降级：触发隐藏 input（Firefox等尚不支持 File System Access API）
    $('folderInput').click();
  }
}

async function _collectFilesFromDir(dirHandle,files){
  for await(const entry of dirHandle.values()){
    if(entry.kind==='file'){
      files.push(await entry.getFile());
    }else if(entry.kind==='directory'){
      await _collectFilesFromDir(entry,files);
    }
  }
}

function initBatchZone(){
  const landing=$('batchLanding');
  const batchInput=$('batchInput');
  const folderInput=$('folderInput');

  // Drag & drop on landing
  landing.addEventListener('dragover',e=>{e.preventDefault();landing.classList.add('drag-over');});
  landing.addEventListener('dragleave',()=>landing.classList.remove('drag-over'));
  landing.addEventListener('drop',e=>{
    e.preventDefault();
    landing.classList.remove('drag-over');
    if(e.dataTransfer.files.length) handleBatchFiles(e.dataTransfer.files);
  });

  // File input (individual files)
  batchInput.addEventListener('change',()=>{
    if(batchInput.files.length) handleBatchFiles(batchInput.files);
    batchInput.value='';
  });

  // Folder input — fallback for browsers without File System Access API
  folderInput.addEventListener('change',()=>{
    const filtered=[...folderInput.files].filter(f=>_ACCEPTED_RE.test(f.name));
    if(filtered.length) handleBatchFiles(filtered);
    folderInput.value='';
  });

  // Folder picker buttons — File System Access API (无“是否上传到此站点”对话框)
  $('btnPickFolder').addEventListener('click',_pickFolderWithoutDialog);
  $('btnPickFolderBar').addEventListener('click',_pickFolderWithoutDialog);

  // Cancel button
  $('btnBatchCancel').addEventListener('click',resetBatchZone);
}

async function handleBatchFiles(fileList){
  const raw=localStorage.getItem(AUTH_USER_KEY);
  const role=raw?JSON.parse(raw).role:null;
  if(role!=='auditor'&&role!=='admin'){
    setStatus($('batchStatus'),'需要 auditor / admin 权限','error');
    return;
  }
  if(_batchRunning)return;
  _batchRunning=true;

  const allFiles=[...fileList].filter(f=>_ACCEPTED_RE.test(f.name)||f.type.startsWith('image/'));
  if(allFiles.length>50){
    setStatus($('batchStatus'),`已自动截取前 50 个文件（共选择 ${allFiles.length} 个）`,'warn');
  }
  const files=allFiles.slice(0,50);
  if(!files.length){_batchRunning=false;return;}

  // Switch to bar mode
  $('batchLanding').hidden=true;
  $('batchBar').hidden=false;
  // 不清空 gallery，结果堆叠追加
  setStatus($('batchStatus'),'','');
  $('uploadLabel').textContent='上传中 0%';
  $('uploadProgressBar').style.width='0%';
  $('detectLabel').textContent='检测进度 0/0';
  $('detectProgressBar').style.width='0%';
  $('detectProgressBar').classList.remove('complete');

  // 1. Init job
  let jobId;
  try{
    const initRes=await fetch('/api/detect-batch-init',{method:'POST',headers:authHeaders()});
    if(!initRes.ok){throw new Error('init failed');}
    const initData=await initRes.json();
    jobId=initData.job_id;
  }catch(e){
    setStatus($('batchStatus'),'初始化失败','error');
    resetBatchZone();
    return;
  }

  // 2. Open WebSocket
  const proto=location.protocol==='https:'?'wss:':'ws:';
  const token=getToken();
  const wsUrl=`${proto}//${location.host}/ws/detect/${jobId}?token=${token}`;
  const ws=new WebSocket(wsUrl);
  _batchWs=ws;

  let totalImages=0;
  let doneImages=0;
  const sourceGroups={};

  ws.onmessage=function(e){
    const d=JSON.parse(e.data);
    const g=$('batchGallery');

    if(d.type==='start'){
      totalImages=d.total;
      $('detectLabel').textContent=`检测进度 0/${totalImages}`;

    }else if(d.type==='result'){
      // 检测完一张立即渲染卡片，无需骨架占位
      doneImages++;
      $('detectLabel').textContent=`检测进度 ${doneImages}/${totalImages}`;
      const pct=totalImages?Math.round(doneImages/totalImages*100):0;
      $('detectProgressBar').style.width=pct+'%';

      const r=d.result;
      const cardHtml=buildGalleryCard({...r, index:d.index+_batchIndexOffset+1, url:d.filename});

      if(d.source){
        let group=sourceGroups[d.source];
        if(!group){
          group=document.createElement('details');
          group.className='batch-source-group';
          group.open=true;
          const summary=document.createElement('summary');
          summary.textContent=d.source;
          group.appendChild(summary);
          const inner=document.createElement('div');
          inner.className='gallery batch-source-gallery';
          group.appendChild(inner);
          g.appendChild(group);
          sourceGroups[d.source]=group;
        }
        group.querySelector('.batch-source-gallery').insertAdjacentHTML('beforeend',cardHtml);
      }else{
        g.insertAdjacentHTML('beforeend',cardHtml);
      }

      // 触发进度条动画
      requestAnimationFrame(()=>{requestAnimationFrame(()=>{
        const cards=g.querySelectorAll('.gallery-card:not(.skip-card)');
        if(cards.length){
          cards[cards.length-1].querySelectorAll('.mini-fill').forEach(x=>{
            x.style.width=x.dataset.score+'%';
          });
        }
      });});

      _updateBatchStatsFromResult(r);

    }else if(d.type==='item_skip'){
      const skipCard=`<div class="gallery-card skip-card"><div class="gallery-card__body"><span class="gallery-card__badge" style="background:#e2e8f0;color:#64748b">跳过</span><p class="gallery-card__conf">${d.filename||''}</p><p style="font-size:0.82rem;color:#94a3b8;margin:4px 0 0">${d.reason||''}</p></div></div>`;
      g.insertAdjacentHTML('beforeend',skipCard);

    }else if(d.type==='complete'){
      $('detectProgressBar').classList.add('complete');
      _batchIndexOffset+=doneImages;
      setStatus($('batchStatus'),`本批检测完成 ${d.count} 张，累计 ${_batchIndexOffset} 张`,'success');
      _batchRunning=false;
      _batchWs=null;
    }
  };

  ws.onerror=function(){
    if(_batchRunning){
      setStatus($('batchStatus'),'WebSocket 连接失败','error');
      _batchRunning=false;
      _batchWs=null;
    }
  };

  ws.onclose=function(){
    if(_batchRunning){
      _batchRunning=false;
      _batchWs=null;
    }
  };

  // 3. Upload files via XHR (so we get upload progress)
  const fd=new FormData();
  files.forEach(f=>fd.append('files',f));

  const xhr=new XMLHttpRequest();
  xhr.open('POST','/api/detect-batch-run?job_id='+encodeURIComponent(jobId));
  const tk=getToken();
  if(tk) xhr.setRequestHeader('Authorization','Bearer '+tk);

  xhr.upload.onprogress=function(ev){
    if(ev.lengthComputable){
      const pct=Math.round(ev.loaded/ev.total*100);
      $('uploadLabel').textContent='上传中 '+pct+'%';
      $('uploadProgressBar').style.width=pct+'%';
    }
  };
  xhr.onload=function(){
    $('uploadLabel').textContent='上传完成';
    $('uploadProgressBar').style.width='100%';
  };
  xhr.onerror=function(){
    setStatus($('batchStatus'),'上传失败','error');
    resetBatchZone();
  };
  // 等 WebSocket 建立后再发送文件，避免缓存命中时处理完成早于 WS 连接（403 竞态）
  ws.onopen=function(){ xhr.send(fd); };
}

function resetBatchZone(){
  _batchRunning=false;
  _batchIndexOffset=0;
  if(_batchWs){try{_batchWs.close();}catch(e){}_batchWs=null;}
  _resetBatchStats();
  $('batchResultLayout').hidden=true;
  $('statsCredibility').textContent='--';
  $('statsCredibility').style.color='';
  $('statsTotal').textContent='0';
  $('statsReal').textContent='0';
  $('statsFake').textContent='0';
  $('statsCats').innerHTML='';
  if(_radarChart){
    _radarChart.setOption({series:[{data:[{value:[0,0,0,0,0,0,0]},{value:[0,0,0,0,0,0,0]}]}]});
  }
  $('batchLanding').hidden=false;
  $('batchBar').hidden=true;
  $('batchGallery').innerHTML='';
  setStatus($('batchStatus'),'','');
  $('batchInput').value='';
  $('folderInput').value='';
}

// Initialize on load
initBatchZone();

// ✅ 核心修改：统一风格弹窗逻辑
const actionModal = $('actionModal');
const actionModalContent = $('actionModalContent');
const btnActionModalClose = $('btnActionModalClose');

// 关闭弹窗
function closeActionModal() {
  actionModal.hidden = true;
}
btnActionModalClose.addEventListener('click', closeActionModal);
actionModal.addEventListener('click', e => {
  if (e.target === actionModal) closeActionModal();
});

// 打开弹窗并填充内容
function openActionModal(htmlContent) {
  actionModalContent.innerHTML = htmlContent;
  actionModal.hidden = false;
}

// 快捷操作按钮绑定
document.addEventListener('DOMContentLoaded',()=>{
  // 1. 标记为误判 — 真实反馈表单
  $('btnMarkMisjudge').addEventListener('click', () => {
    if (!lastDetectionId) {
      openActionModal(`<div style="text-align:center;padding:24px">
        <div style="font-size:1rem;font-weight:600;color:#f59e0b;margin-bottom:12px">提示</div>
        <p style="color:#64748b;margin:0 0 16px">无检测记录，请先对图片进行检测</p>
        <button class="btn-detect" id="btnActionConfirm" style="width:100%">确定</button>
      </div>`);
      $('btnActionConfirm').addEventListener('click', closeActionModal);
      return;
    }
    const detectedZh = lastDetectionLabel === 'FAKE' ? 'AI生成' : '真实照片';
    const detectedColor = lastDetectionLabel === 'FAKE' ? '#f87171' : '#4ade80';
    openActionModal(`
      <div style="padding:20px">
        <h3 style="color:#1e293b;margin:0 0 12px;font-size:1rem">标记误判</h3>
        <p style="color:#64748b;font-size:0.85rem;margin:0 0 16px">AI 判定为
          <strong style="color:${detectedColor}">${detectedZh}</strong>，您认为实际应该是：</p>
        <div style="display:flex;gap:10px;margin-bottom:14px">
          <label style="flex:1;border:2px solid ${lastDetectionLabel==='REAL'?'#f87171':'#e2e8f0'};border-radius:8px;padding:10px;cursor:pointer;text-align:center;background:#f8fafc" id="lblFeedFake">
            <input type="radio" name="feedLabel" value="FAKE" style="margin-right:6px"${lastDetectionLabel==='REAL'?' checked':''}>
            <span style="color:#f87171;font-weight:600">AI生成</span>
          </label>
          <label style="flex:1;border:2px solid ${lastDetectionLabel==='FAKE'?'#4ade80':'#e2e8f0'};border-radius:8px;padding:10px;cursor:pointer;text-align:center;background:#f8fafc" id="lblFeedReal">
            <input type="radio" name="feedLabel" value="REAL" style="margin-right:6px"${lastDetectionLabel==='FAKE'?' checked':''}>
            <span style="color:#22c55e;font-weight:600">真实照片</span>
          </label>
        </div>
        <textarea id="feedNote" placeholder="备注（可选）：如来源说明、判断依据…"
          style="width:100%;height:68px;padding:8px;border-radius:6px;border:1px solid #e2e8f0;background:#f8fafc;color:#1e293b;font-size:0.82rem;resize:none;box-sizing:border-box"
          maxlength="200"></textarea>
        <div style="display:flex;gap:10px;margin-top:12px">
          <button class="btn-secondary" id="btnFeedCancel" style="flex:1">取消</button>
          <button class="btn-detect" id="btnFeedSubmit" style="flex:1">提交反馈</button>
        </div>
        <p id="feedError" style="color:#f87171;font-size:0.82rem;margin:8px 0 0;min-height:16px"></p>
      </div>
    `);
    $('btnFeedCancel').addEventListener('click', closeActionModal);
    $('btnFeedSubmit').addEventListener('click', async () => {
      const btn = $('btnFeedSubmit');
      const errEl = $('feedError');
      const sel = document.querySelector('input[name="feedLabel"]:checked');
      if (!sel) { errEl.textContent = '请选择正确标签'; return; }
      const note = ($('feedNote').value || '').trim();
      btn.disabled = true;
      btn.textContent = '提交中…';
      try {
        const res = await fetch('/api/feedback', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', ...authHeaders() },
          body: JSON.stringify({ detection_id: lastDetectionId, correct_label: sel.value, note }),
        });
        const resp = await res.json();
        if (!res.ok) { errEl.textContent = resp.detail || '提交失败'; btn.disabled = false; btn.textContent = '提交反馈'; return; }
        actionModalContent.innerHTML = `
          <div style="text-align:center;padding:28px">
            <div style="font-size:1rem;font-weight:600;color:#22c55e;margin-bottom:14px">提交成功</div>
            <h3 style="color:#1e293b;margin:0 0 8px">感谢反馈</h3>
            <p style="color:#64748b;margin:0">您的反馈将帮助改进检测准确率</p>
            <button class="btn-detect" id="btnActionConfirm" style="margin-top:20px;width:100%">确定</button>
          </div>`;
        $('btnActionConfirm').addEventListener('click', closeActionModal);
      } catch(e) {
        errEl.textContent = '网络错误';
        btn.disabled = false;
        btn.textContent = '提交反馈';
      }
    });
  });

  // 2. 重新检测
  $('btnRedetect').addEventListener('click',()=>{
    openActionModal(`
      <div style="text-align:center; padding:20px;">
        <h3 style="color:#1e293b; margin:0 0 8px 0;">确认重新检测</h3>
        <p style="color:#64748b; margin:0 0 24px 0;">是否要重新检测当前图片？</p>
        <div style="display:flex; gap:12px; justify-content:center;">
          <button class="btn-secondary" id="btnActionCancel" style="flex:1;">取消</button>
          <button class="btn-detect" id="btnActionConfirm" style="flex:1;">确认</button>
        </div>
      </div>
    `);
    // 绑定按钮
    $('btnActionCancel').addEventListener('click', closeActionModal);
    $('btnActionConfirm').addEventListener('click', ()=>{
      closeActionModal();
      $('btnDetect').click();
    });
  });

  // 3. 分享给同事
  $('btnShare').addEventListener('click',()=>{
    const shareUrl = window.location.href;
    openActionModal(`
      <div style="text-align:center; padding:20px;">
        <h3 style="color:#1e293b; margin:0 0 8px 0;">分享链接</h3>
        <p style="color:#64748b; margin:0 0 16px 0;">复制以下链接分享给同事：</p>
        <input type="text" value="${shareUrl}" readonly style="width:100%; padding:10px; border-radius:6px; border:1px solid #e2e8f0; background:#f1f5f9; color:#1e293b; text-align:center; margin-bottom:16px;" onclick="this.select();" />
        <button class="btn-detect" id="btnActionConfirm" style="margin-top:8px;">确定</button>
      </div>
    `);
    $('btnActionConfirm').addEventListener('click', closeActionModal);
  });
});

/* ============================================================
   Admin Panel — embedded in main page
   ============================================================ */
let _adminDailyChart = null;
let _adminSceneChart = null;

/** Build prev/numbered/next pagination HTML inside container. */
function _renderPagination(container, currentPage, total, pageSize, fnName) {
  if (!container) return;
  const totalPages = Math.ceil(total / pageSize);
  if (totalPages <= 1) { container.innerHTML = ''; return; }
  const MAX_VIS = 5;
  let start = Math.max(1, currentPage - 2);
  let end   = Math.min(totalPages, start + MAX_VIS - 1);
  if (end - start < MAX_VIS - 1) start = Math.max(1, end - MAX_VIS + 1);
  let h = `<button class="page-btn" onclick="${fnName}(${Math.max(1,currentPage-1)})" ${currentPage===1?'disabled':''}>\u2039 \u4e0a\u9875</button>`;
  if (start > 1) h += `<button class="page-btn" onclick="${fnName}(1)">1</button>`;
  if (start > 2) h += '<span class="page-ellipsis">…</span>';
  for (let i = start; i <= end; i++)
    h += `<button class="page-btn ${i===currentPage?'active':''}" onclick="${fnName}(${i})">${i}</button>`;
  if (end < totalPages - 1) h += '<span class="page-ellipsis">…</span>';
  if (end < totalPages) h += `<button class="page-btn" onclick="${fnName}(${totalPages})">${totalPages}</button>`;
  h += `<button class="page-btn" onclick="${fnName}(${Math.min(totalPages,currentPage+1)})" ${currentPage===totalPages?'disabled':''}>\u4e0b\u9875 \u203a</button>`;
  container.innerHTML = h;
}

function openAdminPanel() {
  const rawUser = localStorage.getItem(AUTH_USER_KEY);
  if (!rawUser) { $('loginModal').hidden = false; return; }
  const u = JSON.parse(rawUser);
  if (u.role !== 'admin') { alert('权限不足：仅管理员可访问管理后台'); return; }
  switchToTab('history');
  switchHistoryTab('admin-panel');
}

// History sub-tab switching
function switchHistoryTab(tabName) {
  document.querySelectorAll('.history-tab-btn').forEach(b => b.classList.remove('active'));
  document.querySelectorAll('#tab-history > .history-pane').forEach(p => p.classList.remove('active'));
  const btn = document.querySelector(`.history-tab-btn[data-history-tab="${tabName}"]`);
  if (btn) btn.classList.add('active');
  const pane = $('history-' + tabName);
  if (pane) pane.classList.add('active');
  if (tabName === 'my-records') loadMyRecords(1);
  if (tabName === 'admin-panel') {
    // Load the currently active admin sub-tab
    const activeSubBtn = document.querySelector('.admin-sub-tab-btn.active');
    const subTab = activeSubBtn ? activeSubBtn.dataset.adminTab : 'dashboard';
    _loadAdminSubTab(subTab);
  }
}

// Admin sub-tab switching (within admin panel)
function switchAdminSubTab(tabName) {
  document.querySelectorAll('.admin-sub-tab-btn').forEach(b => b.classList.remove('active'));
  document.querySelectorAll('.admin-sub-pane').forEach(p => p.classList.remove('active'));
  const btn = document.querySelector(`.admin-sub-tab-btn[data-admin-tab="${tabName}"]`);
  if (btn) btn.classList.add('active');
  const pane = $('admin-sub-' + tabName);
  if (pane) pane.classList.add('active');
  _loadAdminSubTab(tabName);
}

function _loadAdminSubTab(tabName) {
  if (tabName === 'dashboard') loadAdminDashboard();
  else if (tabName === 'users') loadAdminUsers(1);
  else if (tabName === 'detections') loadAdminDetections(1);
  else if (tabName === 'feedback') loadAdminFeedback(1);
}

document.querySelectorAll('.history-tab-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    switchHistoryTab(btn.dataset.historyTab);
  });
});

document.querySelectorAll('.admin-sub-tab-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    switchAdminSubTab(btn.dataset.adminTab);
  });
});

// F4: Debounced search/filter bindings for admin tables
['adminUsersSearch', 'adminUsersRoleFilter'].forEach(id => {
  const el = $(id);
  if (!el) return;
  el.addEventListener('input', () => { clearTimeout(el._t); el._t = setTimeout(() => loadAdminUsers(1), 350); });
});
['adminDetectionsSearch', 'adminDetectionsLabelFilter'].forEach(id => {
  const el = $(id);
  if (!el) return;
  el.addEventListener('input', () => { clearTimeout(el._t); el._t = setTimeout(() => loadAdminDetections(1), 350); });
});

async function loadAdminDashboard() {
  try {
    const res = await fetch('/api/admin/stats', { headers: authHeaders() });
    if (!res.ok) throw new Error('HTTP ' + res.status);
    const data = await res.json();

    $('adminStatsCards').innerHTML = `
      <div class="admin-stat-card"><div class="admin-stat-num">${data.total_users}</div><div class="admin-stat-label">总用户数</div></div>
      <div class="admin-stat-card"><div class="admin-stat-num">${data.total_detections}</div><div class="admin-stat-label">总检测数</div></div>
      <div class="admin-stat-card"><div class="admin-stat-num">${data.today_detections}</div><div class="admin-stat-label">今日检测</div></div>
    `;

    if (data.daily_stats && data.daily_stats.length > 0 && typeof Chart !== 'undefined') {
      const ctx = $('adminDailyChart').getContext('2d');
      if (_adminDailyChart) _adminDailyChart.destroy();
      _adminDailyChart = new Chart(ctx, {
        type: 'line',
        data: {
          labels: data.daily_stats.map(d => d.date),
          datasets: [{
            label: '检测次数', data: data.daily_stats.map(d => d.count),
            borderColor: '#60a5fa', backgroundColor: 'rgba(96,165,250,0.1)',
            tension: 0.3, fill: true
          }]
        },
        options: {
          plugins: { legend: { labels: { color: '#64748b' } } },
          scales: {
            x: { ticks: { color: '#64748b' }, grid: { color: '#e2e8f0' } },
            y: { ticks: { color: '#64748b' }, grid: { color: '#e2e8f0' } }
          }
        }
      });
    }

    if (data.top_fake_scenes && data.top_fake_scenes.length > 0 && typeof Chart !== 'undefined') {
      const ctx2 = $('adminSceneChart').getContext('2d');
      if (_adminSceneChart) _adminSceneChart.destroy();
      _adminSceneChart = new Chart(ctx2, {
        type: 'bar',
        data: {
          labels: data.top_fake_scenes.map(s => s.source),
          datasets: [{
            label: '检测量', data: data.top_fake_scenes.map(s => s.total || s.fake_rate),
            backgroundColor: '#ef4444'
          }]
        },
        options: {
          plugins: { legend: { labels: { color: '#64748b' } } },
          scales: {
            x: { ticks: { color: '#64748b', maxRotation: 0, autoSkip: true }, grid: { color: '#e2e8f0' } },
            y: { ticks: { color: '#64748b' }, grid: { color: '#e2e8f0' } }
          }
        }
      });
    }
  } catch (e) {
    if (e.message && (e.message.includes('401') || e.message.includes('403'))) {
      clearAuth();
      $('loginModal').hidden = false;
      return;
    }
    const sc = $('adminStatsCards');
    if (sc) sc.innerHTML = '<div class="admin-stat-card"><div class="admin-stat-label" style="color:#f87171">\u6570\u636e\u52a0\u8f7d\u5931\u8d25\uff0c\u8bf7\u91cd\u8bd5</div></div>';
  }
}

function _roleBadgeHtml(r) {
  if (r === 'admin') return '<span class="admin-badge admin-badge--admin">管理员</span>';
  if (r === 'auditor') return '<span class="admin-badge admin-badge--auditor">审核员</span>';
  return '<span class="admin-badge admin-badge--user">用户</span>';
}

async function loadAdminUsers(page) {
  const searchEl = $('adminUsersSearch');
  const roleEl   = $('adminUsersRoleFilter');
  const search   = (searchEl && searchEl.value.trim()) || '';
  const role     = (roleEl   && roleEl.value)          || '';
  const params   = new URLSearchParams({ page, page_size: 10 });
  if (search) params.set('search', search);
  if (role)   params.set('role',   role);
  try {
    const res = await fetch(`/api/admin/users?${params}`, { headers: authHeaders() });
    if (!res.ok) throw new Error('HTTP ' + res.status);
    const data = await res.json();

    const totalEl = $('adminUsersTotal');
    if (totalEl) totalEl.textContent = `\u5171 ${data.total} \u6761`;

    const wrap = $('adminUsersTable');
    if (!wrap) return;
    if (!data.users || data.users.length === 0) {
      wrap.innerHTML = '<p style="color:#94a3b8;padding:20px;text-align:center">\u6682\u65e0\u6570\u636e</p>';
    } else {
      wrap.innerHTML = `
        <table class="admin-table">
          <thead><tr><th>ID</th><th>\u7528\u6237\u540d</th><th>\u89d2\u8272</th><th>\u6ce8\u518c\u65f6\u95f4</th></tr></thead>
          <tbody>${data.users.map(u => `<tr>
            <td>${u.id}</td>
            <td>${_escHtml(u.username)}</td>
            <td>${_roleBadgeHtml(u.role)}</td>
            <td>${new Date(u.created_at).toLocaleString()}</td>
          </tr>`).join('')}</tbody>
        </table>`;
    }
    _renderPagination($('adminUsersPagination'), page, data.total, 10, 'loadAdminUsers');
  } catch (e) {
    if (e.message && (e.message.includes('401') || e.message.includes('403'))) { clearAuth(); return; }
    const w = $('adminUsersTable');
    if (w) w.innerHTML = '<p style="color:#f87171;padding:16px">\u26a0\ufe0f \u52a0\u8f7d\u5931\u8d25</p>';
  }
}

async function loadAdminDetections(page) {
  const searchEl = $('adminDetectionsSearch');
  const labelEl  = $('adminDetectionsLabelFilter');
  const search   = (searchEl && searchEl.value.trim()) || '';
  const label    = (labelEl  && labelEl.value)         || '';
  const params   = new URLSearchParams({ page, page_size: 10 });
  if (search) params.set('search', search);
  if (label)  params.set('label',  label);
  try {
    const res = await fetch(`/api/admin/detections?${params}`, { headers: authHeaders() });
    if (!res.ok) throw new Error('HTTP ' + res.status);
    const data = await res.json();

    const totalEl = $('adminDetectionsTotal');
    if (totalEl) totalEl.textContent = `\u5171 ${data.total} \u6761`;

    const wrap = $('adminDetectionsTable');
    if (!wrap) return;
    if (!data.detections || data.detections.length === 0) {
      wrap.innerHTML = '<p style="color:#94a3b8;padding:20px;text-align:center">\u6682\u65e0\u6570\u636e</p>';
    } else {
      wrap.innerHTML = `
        <table class="admin-table">
          <thead><tr><th>ID</th><th>\u7528\u6237</th><th>\u6765\u6e90</th><th>\u7ed3\u679c</th><th>\u7f6e\u4fe1\u5ea6</th><th>\u65f6\u95f4</th><th>\u64cd\u4f5c</th></tr></thead>
          <tbody>${data.detections.map(d => `<tr>
            <td>${d.id}</td>
            <td>${_escHtml(String(d.user_id ?? '\u533f\u540d'))}</td>
            <td title="${_escHtml(d.image_url||'')}" style="max-width:140px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">
              ${d.image_url ? _escHtml(d.image_url.slice(0,35)) + '\u2026' : '\u672c\u5730\u4e0a\u4f20'}
            </td>
            <td><span class="admin-badge ${d.label==='FAKE'?'admin-badge--fake':'admin-badge--real'}">${d.label==='FAKE'?'AI\u751f\u6210':'\u771f\u5b9e'}</span></td>
            <td>${Math.round(d.confidence)}%</td>
            <td>${new Date(d.created_at).toLocaleString()}</td>
            <td>
              <button class="admin-stats-btn" onclick="openImageStats(${d.id})" title="\u67e5\u770b\u56fe\u7247\u7edf\u8ba1">\ud83d\udcca</button>
              <button class="admin-stats-btn" onclick="openFeedbackFromHistory(${d.id},'${d.label}')" title="\u6807\u8bb0\u8bef\u5224">\u26a0\ufe0f</button>
            </td>
          </tr>`).join('')}</tbody>
        </table>`;
    }
    _renderPagination($('adminDetectionsPagination'), page, data.total, 10, 'loadAdminDetections');
  } catch (e) {
    if (e.message && (e.message.includes('401') || e.message.includes('403'))) { clearAuth(); return; }
    const w = $('adminDetectionsTable');
    if (w) w.innerHTML = '<p style="color:#f87171;padding:16px">\u26a0\ufe0f \u52a0\u8f7d\u5931\u8d25</p>';
  }
}

/* ── Image-level statistics modal ─────────────────────────────────── */
async function openImageStats(detectionId) {
  openActionModal(`<div style="text-align:center;padding:28px"><div style="color:#3b82f6;font-size:1.5rem">\u23f3 加载中…</div></div>`);
  try {
    const res = await fetch(`/api/admin/image-stats/${detectionId}`, { headers: authHeaders() });
    if (!res.ok) throw new Error('HTTP ' + res.status);
    const d = await res.json();
    const fakeColor = '#f87171';
    const realColor = '#4ade80';
    const rateColor = d.fake_rate >= 70 ? fakeColor : d.fake_rate >= 40 ? '#f97316' : realColor;
    actionModalContent.innerHTML = `
      <div style="padding:20px">
        <h3 style="color:#1e293b;margin:0 0 14px;font-size:1rem">图片检测统计</h3>
        ${d.image_url ? `<p style="color:#64748b;font-size:0.78rem;margin:0 0 14px;word-break:break-all">${_escHtml(d.image_url.slice(0,90))}${d.image_url.length>90?'…':''}</p>` : ''}
        <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px;margin-bottom:14px">
          <div style="background:#f1f5f9;border-radius:8px;padding:12px;text-align:center">
            <div style="font-size:1.5rem;font-weight:700;color:#1e293b">${d.total_detections}</div>
            <div style="font-size:0.72rem;color:#64748b;margin-top:3px">检测次数</div>
          </div>
          <div style="background:#f1f5f9;border-radius:8px;padding:12px;text-align:center">
            <div style="font-size:1.5rem;font-weight:700;color:${fakeColor}">${d.fake_count}</div>
            <div style="font-size:0.72rem;color:#64748b;margin-top:3px">AI生成</div>
          </div>
          <div style="background:#f1f5f9;border-radius:8px;padding:12px;text-align:center">
            <div style="font-size:1.5rem;font-weight:700;color:${realColor}">${d.real_count}</div>
            <div style="font-size:0.72rem;color:#64748b;margin-top:3px">真实</div>
          </div>
        </div>
        <div style="background:#f1f5f9;border-radius:8px;padding:12px 14px;margin-bottom:10px">
          <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:7px">
            <span style="color:#64748b;font-size:0.85rem">AI生成率</span>
            <span style="font-size:1.1rem;font-weight:700;color:${rateColor}">${d.fake_rate}%</span>
          </div>
          <div style="background:#e2e8f0;border-radius:4px;height:7px;overflow:hidden">
            <div style="width:${d.fake_rate}%;height:100%;background:${rateColor};border-radius:4px"></div>
          </div>
        </div>
        <div style="background:#f1f5f9;border-radius:8px;padding:10px 14px;margin-bottom:14px;display:flex;justify-content:space-between;align-items:center">
          <span style="color:#64748b;font-size:0.85rem">用户误判反馈</span>
          <span style="color:#1e293b;font-weight:600">${d.feedback_count} 次</span>
        </div>
        ${d.recent_feedbacks && d.recent_feedbacks.length > 0 ? `
        <div style="margin-bottom:14px">
          <p style="color:#64748b;font-size:0.78rem;margin:0 0 6px">最近反馈：</p>
          ${d.recent_feedbacks.map(fb => `
            <div style="background:#f8fafc;border-radius:6px;padding:7px 10px;margin-bottom:4px;font-size:0.8rem;display:flex;justify-content:space-between;align-items:center">
              <span style="color:#64748b">${fb.reported_label}→<span style="color:${fb.correct_label==='FAKE'?fakeColor:realColor}">${fb.correct_label}</span>${fb.note?` &middot; <span style="color:#1e293b">${_escHtml((fb.note||'').slice(0,28))}</span>`:''}</span>
              <span style="color:#94a3b8;font-size:0.72rem">${new Date(fb.created_at).toLocaleDateString()}</span>
            </div>`).join('')}
        </div>` : ''}
        <button class="btn-detect" id="btnActionConfirm" style="width:100%">关闭</button>
      </div>`;
    $('btnActionConfirm').addEventListener('click', closeActionModal);
  } catch(e) {
    actionModalContent.innerHTML = `<div style="padding:24px;text-align:center">
      <p style="color:#ef4444">加载统计失败</p>
      <button class="btn-detect" id="btnActionConfirm" style="margin-top:14px">关闭</button>
    </div>`;
    $('btnActionConfirm').addEventListener('click', closeActionModal);
  }
}

/* ── Admin feedback list ──────────────────────────────────────────── */
async function loadAdminFeedback(page) {
  const params = new URLSearchParams({ page, page_size: 10 });
  try {
    const res = await fetch(`/api/admin/feedback?${params}`, { headers: authHeaders() });
    if (!res.ok) throw new Error('HTTP ' + res.status);
    const data = await res.json();

    const totalEl = $('adminFeedbackTotal');
    if (totalEl) totalEl.textContent = `\u5171 ${data.total} \u6761\u53cd\u9988`;

    const wrap = $('adminFeedbackTable');
    if (!wrap) return;
    if (!data.feedbacks || data.feedbacks.length === 0) {
      wrap.innerHTML = '<p style="color:#94a3b8;padding:24px;text-align:center">\u6682\u65e0\u53cd\u9988\u6570\u636e</p>';
    } else {
      wrap.innerHTML = `
        <table class="admin-table">
          <thead><tr>
            <th>ID</th><th>\u68c0\u6d4b ID</th><th>\u539f\u5224\u65ad</th><th>\u5e94\u4e3a</th><th>\u5907\u6ce8</th><th>\u96c6\u6210\u72b6\u6001</th><th>\u65f6\u95f4</th>
          </tr></thead>
          <tbody>${data.feedbacks.map(f => `<tr>
            <td>${f.id}</td>
            <td>${f.detection_id || '-'}</td>
            <td><span class="admin-badge ${f.reported_label==='FAKE'?'admin-badge--fake':'admin-badge--real'}">${f.reported_label==='FAKE'?'AI\u751f\u6210':'\u771f\u5b9e'}</span></td>
            <td><span class="admin-badge ${f.correct_label==='FAKE'?'admin-badge--fake':'admin-badge--real'}">${f.correct_label==='FAKE'?'AI\u751f\u6210':'\u771f\u5b9e'}</span></td>
            <td style="max-width:110px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap" title="${_escHtml(f.note||'')}">${_escHtml(f.note||'-')}</td>
            <td><span class="admin-badge ${f.used_in_training?'admin-badge--trained':'admin-badge--pending'}">${f.used_in_training?'\u5df2\u96c6\u6210':'\u5f85\u96c6\u6210'}</span></td>
            <td>${new Date(f.created_at).toLocaleString()}</td>
          </tr>`).join('')}</tbody>
        </table>`;
    }
    _renderPagination($('adminFeedbackPagination'), page, data.total, 10, 'loadAdminFeedback');
  } catch (e) {
    if (e.message && (e.message.includes('401') || e.message.includes('403'))) { clearAuth(); return; }
    const w = $('adminFeedbackTable');
    if (w) w.innerHTML = '<p style="color:#f87171;padding:16px">\u26a0\ufe0f \u52a0\u8f7d\u5931\u8d25</p>';
  }
}

// Bind integrate-training button (element always in DOM)
const _btnIntegrate = $('btnIntegrateTraining');
if (_btnIntegrate) {
  _btnIntegrate.addEventListener('click', async () => {
    const statusEl = $('integrateStatus');
    _btnIntegrate.disabled = true;
    _btnIntegrate.innerHTML = '集成中…';
    statusEl.textContent = '';
    try {
      const res = await fetch('/api/admin/feedback/integrate', { method: 'POST', headers: authHeaders() });
      const data = await res.json();
      statusEl.textContent = res.ok ? `\u2705 ${data.message}` : `\u274c ${data.detail || '\u5931\u8d25'}`;
      if (res.ok) loadAdminFeedback(1);
    } catch(e) {
      statusEl.textContent = '\u274c \u7f51\u7edc\u9519\u8bef';
    } finally {
      _btnIntegrate.disabled = false;
      _btnIntegrate.innerHTML = '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M20.25 7.5l-.625 10.632a2.25 2.25 0 01-2.247 2.118H6.622a2.25 2.25 0 01-2.247-2.118L3.75 7.5M10 11.25h4M3.375 7.5h17.25c.621 0 1.125-.504 1.125-1.125v-1.5c0-.621-.504-1.125-1.125-1.125H3.375c-.621 0-1.125.504-1.125 1.125v1.5c0 .621.504 1.125 1.125 1.125z"/></svg> 集成到训练集';
    }
  });
}

// ── Feedback from history records ────────────────────────────────────────────
function openFeedbackFromHistory(detectionId, currentLabel) {
  const detectedZh = currentLabel === 'FAKE' ? 'AI生成' : '真实照片';
  const detectedColor = currentLabel === 'FAKE' ? '#f87171' : '#4ade80';
  openActionModal(`
    <div style="padding:20px">
      <h3 style="color:#1e293b;margin:0 0 12px;font-size:1rem">标记误判</h3>
      <p style="color:#64748b;font-size:0.85rem;margin:0 0 16px">AI 判定为
        <strong style="color:${detectedColor}">${detectedZh}</strong>，您认为实际应该是：</p>
      <div style="display:flex;gap:10px;margin-bottom:14px">
        <label style="flex:1;border:2px solid ${currentLabel==='REAL'?'#f87171':'#e2e8f0'};border-radius:8px;padding:10px;cursor:pointer;text-align:center;background:#f8fafc">
          <input type="radio" name="feedLabelHist" value="FAKE" style="margin-right:6px"${currentLabel==='REAL'?' checked':''}>
          <span style="color:#f87171;font-weight:600">AI生成</span>
        </label>
        <label style="flex:1;border:2px solid ${currentLabel==='FAKE'?'#4ade80':'#e2e8f0'};border-radius:8px;padding:10px;cursor:pointer;text-align:center;background:#f8fafc">
          <input type="radio" name="feedLabelHist" value="REAL" style="margin-right:6px"${currentLabel==='FAKE'?' checked':''}>
          <span style="color:#22c55e;font-weight:600">真实照片</span>
        </label>
      </div>
      <textarea id="feedNoteHist" placeholder="备注（可选）：如来源说明、判断依据…"
        style="width:100%;height:68px;padding:8px;border-radius:6px;border:1px solid #e2e8f0;background:#f8fafc;color:#1e293b;font-size:0.82rem;resize:none;box-sizing:border-box"
        maxlength="200"></textarea>
      <div style="display:flex;gap:10px;margin-top:12px">
        <button class="btn-secondary" id="btnFeedCancelHist" style="flex:1">取消</button>
        <button class="btn-detect" id="btnFeedSubmitHist" style="flex:1">提交反馈</button>
      </div>
      <p id="feedErrorHist" style="color:#f87171;font-size:0.82rem;margin:8px 0 0;min-height:16px"></p>
    </div>
  `);
  $('btnFeedCancelHist').addEventListener('click', closeActionModal);
  $('btnFeedSubmitHist').addEventListener('click', async () => {
    const btn = $('btnFeedSubmitHist');
    const errEl = $('feedErrorHist');
    const sel = document.querySelector('input[name="feedLabelHist"]:checked');
    if (!sel) { errEl.textContent = '请选择正确标签'; return; }
    const note = ($('feedNoteHist').value || '').trim();
    btn.disabled = true;
    btn.textContent = '提交中…';
    try {
      const res = await fetch('/api/feedback', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...authHeaders() },
        body: JSON.stringify({ detection_id: detectionId, correct_label: sel.value, note }),
      });
      const resp = await res.json();
      if (!res.ok) { errEl.textContent = resp.detail || '提交失败'; btn.disabled = false; btn.textContent = '提交反馈'; return; }
      actionModalContent.innerHTML = `
        <div style="text-align:center;padding:28px">
          <div style="font-size:1rem;font-weight:600;color:#22c55e;margin-bottom:14px">提交成功</div>
          <h3 style="color:#1e293b;margin:0 0 8px">感谢反馈</h3>
          <p style="color:#64748b;margin:0">您的反馈将帮助改进检测准确率</p>
          <button class="btn-detect" id="btnActionConfirm" style="margin-top:20px;width:100%">确定</button>
        </div>`;
      $('btnActionConfirm').addEventListener('click', closeActionModal);
    } catch(e) {
      errEl.textContent = '网络错误';
      btn.disabled = false;
      btn.textContent = '提交反馈';
    }
  });
}

// ─────────────────────────────────────────────────────────────────────────────
// ─ AI Analysis Panel & Image Download Features ─
// ─────────────────────────────────────────────────────────────────────────────

// Generate session ID at page load
const sessionId = 'session_' + Date.now() + '_' + Math.random().toString(36).substring(2, 11);
let currentDetectionId = null;
let analysisHistory = [];  // 保存该检测的分析历史[{question, answer, timestamp}]

function resetAnalysisPanel() {
  const panel = $('analysisQuestion');
  if (panel) panel.value = '';
  const error = $('analysisError');
  if (error) error.hidden = true;
  analysisHistory = [];
  const container = $('chatContainer');
  if (container) container.innerHTML = '';
}

// 将历史记录渲染为对话气泡
function renderAnalysisHistory() {
  const container = $('chatContainer');
  if (!container) return;
  container.innerHTML = '';
  analysisHistory.forEach(item => {
    appendChatMessage('user', item.question);
    appendChatMessage('ai', item.answer);
  });
}

// HTML转义（用于用户消息气泡）
function escapeHtml(text) {
  const map = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;' };
  return text.replace(/[&<>"']/g, m => map[m]);
}

// 轻量 Markdown 渲染（用于 AI 回复气泡）
function renderMarkdown(text) {
  // 先转义原始 HTML，防止 XSS
  let out = text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');

  // 代码块 (```...```)
  out = out.replace(/```[\w]*\n?([\s\S]*?)```/g, (_, code) =>
    `<pre><code>${code.trim()}</code></pre>`
  );

  // 行内代码
  out = out.replace(/`([^`\n]+)`/g, '<code>$1</code>');

  // 标题
  out = out.replace(/^### (.+)$/gm, '<h3>$1</h3>');
  out = out.replace(/^## (.+)$/gm, '<h2>$1</h2>');
  out = out.replace(/^# (.+)$/gm, '<h2>$1</h2>');

  // 粗体 & 斜体
  out = out.replace(/\*\*\*(.+?)\*\*\*/g, '<strong><em>$1</em></strong>');
  out = out.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
  out = out.replace(/\*([^*\n]+)\*/g, '<em>$1</em>');

  // 无序列表（连续以 - / * / + 开头的行）
  out = out.replace(/((?:^[*\-+] .+\n?)+)/gm, block => {
    const items = block.trim().split('\n')
      .map(l => `<li>${l.replace(/^[*\-+] /, '')}</li>`).join('');
    return `<ul>${items}</ul>`;
  });

  // 有序列表
  out = out.replace(/((?:^\d+\. .+\n?)+)/gm, block => {
    const items = block.trim().split('\n')
      .map(l => `<li>${l.replace(/^\d+\. /, '')}</li>`).join('');
    return `<ol>${items}</ol>`;
  });

  // 段落（双换行）
  out = out.replace(/\n{2,}/g, '</p><p>');
  out = '<p>' + out + '</p>';

  // 修正：块级元素外层不套 <p>
  out = out.replace(/<p>(<(?:ul|ol|pre|h[1-6])[^>]*>)/g, '$1');
  out = out.replace(/(<\/(?:ul|ol|pre|h[1-6])>)<\/p>/g, '$1');

  // 段落内单换行 → <br>
  out = out.replace(/\n/g, '<br>');

  // 清除空段落
  out = out.replace(/<p>\s*<\/p>/g, '');
  out = out.replace(/<p><br><\/p>/g, '');

  return out;
}

// 向 chatContainer 追加一条消息并返回关键元素
function appendChatMessage(role, text, isStreaming = false) {
  const container = $('chatContainer');
  if (!container) return null;

  if (role === 'user') {
    const row = document.createElement('div');
    row.className = 'chat-msg-user';
    const bubble = document.createElement('div');
    bubble.className = 'chat-bubble-user';
    bubble.textContent = text;
    row.appendChild(bubble);
    container.appendChild(row);
    scrollChatToBottom();
    return row;
  }

  if (role === 'typing') {
    const row = document.createElement('div');
    row.className = 'chat-msg-ai chat-typing';
    row.innerHTML = `
      <div class="chat-avatar">AI</div>
      <div class="chat-bubble-ai">
        <div class="typing-dot"></div>
        <div class="typing-dot"></div>
        <div class="typing-dot"></div>
      </div>`;
    container.appendChild(row);
    scrollChatToBottom();
    return row;
  }

  if (role === 'ai') {
    const row = document.createElement('div');
    row.className = 'chat-msg-ai';
    const wrap = document.createElement('div');
    wrap.className = 'chat-bubble-ai-wrap';
    const bubble = document.createElement('div');
    bubble.className = 'chat-bubble-ai';
    if (isStreaming) {
      // 流式阶段显示纯文本，完成后替换为渲染后的 Markdown
      bubble.textContent = text;
    } else {
      bubble.innerHTML = renderMarkdown(text);
      addExpandButton(wrap, bubble);
    }
    wrap.appendChild(bubble);
    row.innerHTML = '<div class="chat-avatar">AI</div>';
    row.appendChild(wrap);
    container.appendChild(row);
    scrollChatToBottom();
    return { row, bubble, wrap };
  }

  return null;
}

// 若气泡内容过长则折叠并加"展开全文"按钮
function addExpandButton(wrap, bubble) {
  setTimeout(() => {
    if (bubble.scrollHeight > 200) {
      bubble.classList.add('is-collapsed');
      const btn = document.createElement('button');
      btn.className = 'btn-expand-msg';
      btn.textContent = '展开全文 ▼';
      btn.addEventListener('click', () => {
        if (bubble.classList.contains('is-collapsed')) {
          bubble.classList.remove('is-collapsed');
          btn.textContent = '收起 ▲';
        } else {
          bubble.classList.add('is-collapsed');
          btn.textContent = '展开全文 ▼';
        }
      });
      wrap.appendChild(btn);
    }
  }, 0);
}

function scrollChatToBottom() {
  const container = $('chatContainer');
  if (container) container.scrollTop = container.scrollHeight;
}

// 加载分析历史
async function loadAnalysisHistory(detectionId) {
  try {
    const response = await fetch(
      `/api/detection/${detectionId}/analysis-history?session_id=${encodeURIComponent(sessionId)}`
    );
    const data = await response.json();
    if (data.history && data.history.length > 0) {
      analysisHistory = data.history;
      renderAnalysisHistory();
    }
  } catch (e) {
    console.error('Failed to load analysis history:', e);
  }
}

// AI Analysis button click - SSE streaming
if ($('btnAnalyze')) {
  $('btnAnalyze').addEventListener('click', initiateAnalysis);
}

function initiateAnalysis() {
  const question = $('analysisQuestion').value.trim();
  if (!question) {
    showToast('请输入你的问题', 'error');
    return;
  }

  if (!currentDetectionId) {
    showToast('请先完成一次检测', 'error');
    return;
  }

  $('analysisQuestion').value = '';
  const error = $('analysisError');
  if (error) error.hidden = true;
  streamAnalysis(currentDetectionId, question);
}

function streamAnalysis(detectionId, question) {
  // 立即追加用户气泡
  appendChatMessage('user', question);

  // 显示打字动画气泡
  const typingRow = appendChatMessage('typing', '');

  const eventSource = new EventSource(
    `/api/detection/${detectionId}/analyze?question=${encodeURIComponent(question)}&session_id=${encodeURIComponent(sessionId)}`
  );

  let fullResponse = '';
  let aiBubble = null;
  let aiWrap = null;

  eventSource.onmessage = (event) => {
    const data = event.data;

    if (data === '[DONE]') {
      eventSource.close();
      // 移除打字动画，渲染最终 Markdown
      if (typingRow && typingRow.parentNode) typingRow.remove();
      if (aiBubble) {
        aiBubble.innerHTML = renderMarkdown(fullResponse);
        addExpandButton(aiWrap, aiBubble);
      } else {
        appendChatMessage('ai', fullResponse);
      }
      analysisHistory.push({ question, answer: fullResponse, timestamp: new Date().toISOString() });
      scrollChatToBottom();
      return;
    }

    try {
      const parsed = JSON.parse(data);
      if (parsed.error) {
        if (typingRow && typingRow.parentNode) typingRow.remove();
        const error = $('analysisError');
        if (error) { error.textContent = parsed.error; error.hidden = false; }
      } else if (parsed.chunk) {
        fullResponse += parsed.chunk;
        if (!aiBubble) {
          // 第一个 chunk：用 AI 气泡替换打字动画
          if (typingRow && typingRow.parentNode) typingRow.remove();
          const result = appendChatMessage('ai', fullResponse, true);
          aiBubble = result.bubble;
          aiWrap = result.wrap;
        } else {
          aiBubble.textContent = fullResponse;
        }
        scrollChatToBottom();
      }
    } catch (e) {
      fullResponse += data;
      if (!aiBubble) {
        if (typingRow && typingRow.parentNode) typingRow.remove();
        const result = appendChatMessage('ai', fullResponse, true);
        aiBubble = result.bubble;
        aiWrap = result.wrap;
      } else {
        aiBubble.textContent = fullResponse;
      }
      scrollChatToBottom();
    }
  };

  eventSource.onerror = () => {
    eventSource.close();
    if (typingRow && typingRow.parentNode) typingRow.remove();
    const error = $('analysisError');
    if (error) { error.hidden = false; error.textContent = '分析失败：网络连接异常'; }
  };
}


// Gallery image operations - add overlay buttons, checkboxes, and context menu
let selectedCards = new Set();  // 记录选中的卡片索引

function enhanceGalleryCards() {
  const cards = document.querySelectorAll('.gallery-card');

  cards.forEach((card, idx) => {
    // 删除现有的复选框（如果有）
    const existing = card.querySelector('.gallery-card__checkbox');
    if (existing) existing.remove();

    // 添加复选框
    const checkbox = document.createElement('input');
    checkbox.type = 'checkbox';
    checkbox.className = 'gallery-card__checkbox';
    checkbox.dataset.idx = idx;

    checkbox.addEventListener('change', (e) => {
      if (e.target.checked) {
        selectedCards.add(idx);
        card.classList.add('selected');
      } else {
        selectedCards.delete(idx);
        card.classList.remove('selected');
      }
      updateBatchDownloadBtn();
    });

    card.appendChild(checkbox);

    // Remove existing overlay if any
    const existing_overlay = card.querySelector('.gallery-overlay');
    if (existing_overlay) existing_overlay.remove();

    // Create overlay
    const overlay = document.createElement('div');
    overlay.className = 'gallery-overlay';
    overlay.innerHTML = `
      <button class="gallery-btn btn-copy-clip" title="复制图片">
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"></path>
          <rect x="8" y="2" width="8" height="4" rx="1" ry="1"></rect>
        </svg>
        复制
      </button>
      <button class="gallery-btn btn-download" title="下载图片">
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
          <polyline points="7 10 12 15 17 10"></polyline>
          <line x1="12" y1="15" x2="12" y2="3"></line>
        </svg>
        下载
      </button>
      <button class="gallery-btn btn-url-show" title="查看图片URL">
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M13.828 10.172a4 4 0 0 0-5.656 0l-4.243 4.243a4 4 0 1 0 5.656 5.656l1.102-1.101m-.758-4.899a4 4 0 0 0 5.656 0l4.243-4.243a4 4 0 0 0-5.656-5.656l-1.1 1.1"></path>
        </svg>
        URL
      </button>
    `;

    // Get original image URL from data attribute
    const img = card.querySelector('img');
    const imgUrl = img ? img.dataset.imgUrl || img.src : '';

    // Copy button handler
    overlay.querySelector('.btn-copy-clip').addEventListener('click', async (e) => {
      e.stopPropagation();
      await copyImageToClipboard(imgUrl);
    });

    // Download button handler
    overlay.querySelector('.btn-download').addEventListener('click', (e) => {
      e.stopPropagation();
      downloadSingleImage(imgUrl);
    });

    // URL button handler
    overlay.querySelector('.btn-url-show').addEventListener('click', (e) => {
      e.stopPropagation();
      showImageUrl(imgUrl);
    });

    // 右键菜单
    card.addEventListener('contextmenu', (e) => {
      e.preventDefault();
      showContextMenu(e.pageX, e.pageY, {
        url: imgUrl,
        cardElement: card,
        cardIndex: idx,
        selectedCount: selectedCards.size
      });
    });

    card.appendChild(overlay);
  });
}

// 复制图片到剪贴板
async function copyImageToClipboard(url) {
  try {
    if (!url) {
      showToast('无效的图片URL');
      return;
    }
    const blob = await fetch(`/api/image/download?url=${encodeURIComponent(url)}`).then(r => r.blob());
    await navigator.clipboard.write([
      new ClipboardItem({ 'image/png': blob })
    ]);
    showToast('已复制到剪贴板');
  } catch (err) {
    console.error('Copy error:', err);
    showToast('复制失败');
  }
}

// 下载单张图片
function downloadSingleImage(imgUrl) {
  if (imgUrl) {
    window.location.href = `/api/image/download?url=${encodeURIComponent(imgUrl)}`;
  } else {
    showToast('无效的图片URL');
  }
}

// 显示图片URL
function showImageUrl(imgUrl) {
  if (imgUrl) {
    const modal = $('actionModal');
    if (modal) {
      openActionModal(`
        <h3>图片原始 URL</h3>
        <p style="word-break: break-all; font-size: 0.85rem; color: #64748b;">
          <code>${escapeHtml(imgUrl)}</code>
        </p>
        <button class="btn-secondary" onclick="navigator.clipboard.writeText('${imgUrl.replace(/'/g, "\\'")}').then(() => showToast('URL已复制')).catch(() => showToast('复制失败'))">复制URL</button>
      `);
    }
  }
}

// 右键菜单实现
function showContextMenu(x, y, data) {
  const old = document.querySelector('.context-menu');
  if (old) old.remove();

  const menu = document.createElement('div');
  menu.className = 'context-menu';
  menu.style.left = x + 'px';
  menu.style.top = y + 'px';

  menu.innerHTML = `
    <button class="context-menu-item" data-action="copy">复制图片</button>
    <button class="context-menu-item" data-action="download">下载图片</button>
    <button class="context-menu-item" data-action="open">在新标签打开</button>
    <div class="divider"></div>
    <button class="context-menu-item" data-action="select-all">✓ 全选</button>
    <button class="context-menu-item" data-action="batch-download">批量下载 (${data.selectedCount})</button>
  `;

  menu.querySelectorAll('.context-menu-item').forEach(btn => {
    btn.addEventListener('click', () => {
      const action = btn.dataset.action;
      handleContextMenuAction(action, data);
      menu.remove();
      // 移除点击监听
      document.removeEventListener('click', closeMenu);
    });
  });

  document.body.appendChild(menu);

  // 点击其他地方关闭菜单
  const closeMenu = function(e) {
    if (!menu.contains(e.target)) {
      menu.remove();
      document.removeEventListener('click', closeMenu);
    }
  };

  setTimeout(() => {
    document.addEventListener('click', closeMenu);
  }, 0);
}

// 处理右键菜单操作
function handleContextMenuAction(action, data) {
  switch(action) {
    case 'copy':
      copyImageToClipboard(data.url);
      break;
    case 'download':
      downloadSingleImage(data.url);
      break;
    case 'open':
      window.open(data.url, '_blank');
      break;
    case 'select-all':
      selectAllGalleryCards();
      break;
    case 'batch-download':
      performBatchDownload();
      break;
  }
}

// 全选所有图片
function selectAllGalleryCards() {
  document.querySelectorAll('.gallery-card__checkbox').forEach(cb => {
    cb.checked = true;
    cb.dispatchEvent(new Event('change'));
  });
}

// 取消全选
function deselectAllGalleryCards() {
  document.querySelectorAll('.gallery-card__checkbox').forEach(cb => {
    cb.checked = false;
    cb.dispatchEvent(new Event('change'));
  });
}

// 批量下载
function performBatchDownload() {
  const cards = document.querySelectorAll('.gallery-card');
  const urls = Array.from(selectedCards).map(idx => {
    const img = cards[idx].querySelector('img');
    return img?.dataset.imgUrl || img?.src || '';
  }).filter(Boolean);

  if (urls.length === 0) {
    showToast('未选择任何图片');
    return;
  }

  try {
    const urlParam = JSON.stringify(urls);
    window.location.href = `/api/images/batch-download?urls=${encodeURIComponent(urlParam)}`;
  } catch (e) {
    showToast('批量下载失败：' + e.message);
  }
}

// 更新批量下载按钮状态
function updateBatchDownloadBtn() {
  // 可以根据需要添加更新UI的逻辑
}

// Monkey-patch the gallery update function to include enhanced cards
const originalGalleryUpdate = window.updateGallery || (() => {});
window.updateGallery = function() {
  originalGalleryUpdate.apply(this, arguments);
  setTimeout(enhanceGalleryCards, 100);
};

// Also enhance cards when URL detection completes
const originalUrlDetect = btnUrl ? btnUrl.onclick : null;
if (btnUrl) {
  btnUrl.addEventListener('click', async () => {
    // ... (original URL detection logic)
    // After gallery is rendered, enhance cards
    setTimeout(() => {
      enhanceGalleryCards();
    }, 500);
  }, { once: false });
}


// Toast notification
/* ============================================================
   My Records (检测历史 — 当前用户)
   ============================================================ */
async function loadMyRecords(page) {
  const searchEl = $('myRecordsSearch');
  const labelEl  = $('myRecordsLabelFilter');
  const search   = (searchEl && searchEl.value.trim()) || '';
  const label    = (labelEl  && labelEl.value)         || '';
  const params   = new URLSearchParams({ page, page_size: 10 });
  if (search) params.set('search', search);
  if (label)  params.set('label',  label);
  try {
    const res = await fetch(`/api/history?${params}`, { headers: authHeaders() });
    if (!res.ok) throw new Error('HTTP ' + res.status);
    const data = await res.json();

    const totalEl = $('myRecordsTotal');
    if (totalEl) totalEl.textContent = `共 ${data.total} 条`;

    const wrap = $('myRecordsTable');
    if (!wrap) return;
    if (!data.records || data.records.length === 0) {
      wrap.innerHTML = '<p style="color:#94a3b8;padding:24px;text-align:center">暂无检测记录</p>';
    } else {
      wrap.innerHTML = `
        <table class="admin-table">
          <thead><tr><th>ID</th><th>来源</th><th>结果</th><th>置信度</th><th>时间</th><th>操作</th></tr></thead>
          <tbody>${data.records.map(d => `<tr>
            <td>${d.id}</td>
            <td title="${_escHtml(d.image_url||'')}" style="max-width:180px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">
              ${d.image_url ? _escHtml(d.image_url.slice(0,40)) + '…' : '本地上传'}
            </td>
            <td><span class="admin-badge ${d.label==='FAKE'?'admin-badge--fake':'admin-badge--real'}">${d.label==='FAKE'?'AI生成':'真实'}</span></td>
            <td>${Math.round(d.confidence)}%</td>
            <td>${new Date(d.created_at).toLocaleString()}</td>
            <td><button class="admin-stats-btn" onclick="openFeedbackFromHistory(${d.id},'${d.label}')" title="标记误判">⚠️</button></td>
          </tr>`).join('')}</tbody>
        </table>`;
    }
    _renderPagination($('myRecordsPagination'), page, data.total, 10, 'loadMyRecords');
  } catch (e) {
    if (e.message && (e.message.includes('401') || e.message.includes('403'))) { clearAuth(); return; }
    const w = $('myRecordsTable');
    if (w) w.innerHTML = '<p style="color:#ef4444;padding:16px">加载失败</p>';
  }
}

// Debounced search/filter for my records
['myRecordsSearch', 'myRecordsLabelFilter'].forEach(id => {
  const el = $(id);
  if (!el) return;
  el.addEventListener('input', () => { clearTimeout(el._t); el._t = setTimeout(() => loadMyRecords(1), 350); });
});

/* ============================================================
   Floating Ball & FAQ
   ============================================================ */
let _faqData = [];
let _faqPage = 0;
const _FAQ_PER_PAGE = 5;

async function loadFaqData() {
  if (_faqData.length > 0) return;
  try {
    const res = await fetch('/static/faq/questions.json');
    if (res.ok) _faqData = await res.json();
  } catch (e) {
    console.warn('Failed to load FAQ data:', e);
  }
}

function renderFaqList() {
  const list = $('faqList');
  if (!list) return;
  const start = (_faqPage * _FAQ_PER_PAGE) % Math.max(_faqData.length, 1);
  const items = [];
  for (let i = 0; i < _FAQ_PER_PAGE && i < _faqData.length; i++) {
    items.push(_faqData[(start + i) % _faqData.length]);
  }
  list.innerHTML = items.map((item, idx) =>
    `<button class="faq-item" data-faq-idx="${idx}">${_escHtml(item.q)}</button>`
  ).join('');
  // Show faq list, hide answer
  $('faqList').hidden = false;
  const ans = $('faqAnswer');
  if (ans) ans.hidden = true;
}

// Floating ball toggle
if ($('floatingBall')) {
  $('floatingBall').addEventListener('click', async () => {
    const panel = $('floatingPanel');
    if (!panel) return;
    if (!panel.hidden) {
      panel.hidden = true;
      return;
    }
    await loadFaqData();
    renderFaqList();
    panel.hidden = false;
  });
}

if ($('floatingPanelClose')) {
  $('floatingPanelClose').addEventListener('click', () => {
    $('floatingPanel').hidden = true;
  });
}

// FAQ item click
if ($('floatingPanelBody')) {
  $('floatingPanelBody').addEventListener('click', (e) => {
    const item = e.target.closest('.faq-item');
    if (!item) return;
    const idx = parseInt(item.dataset.faqIdx);
    const start = (_faqPage * _FAQ_PER_PAGE) % Math.max(_faqData.length, 1);
    const realIdx = (start + idx) % _faqData.length;
    const faq = _faqData[realIdx];
    if (!faq) return;
    $('faqList').hidden = true;
    const ans = $('faqAnswer');
    ans.hidden = false;
    $('faqAnswerContent').innerHTML = `<h4>${_escHtml(faq.q)}</h4><p>${_escHtml(faq.a)}</p>`;
  });
}

if ($('faqBack')) {
  $('faqBack').addEventListener('click', () => {
    $('faqAnswer').hidden = true;
    $('faqList').hidden = false;
  });
}

if ($('faqRefresh')) {
  $('faqRefresh').addEventListener('click', () => {
    _faqPage++;
    renderFaqList();
  });
}

/* ============================================================
   News detection enhancements — Web Search & News Image buttons
   ============================================================ */

/* ── 联网新闻搜索 ──────────────────────────────────────────── */
(function initNewsSearch() {
  let _newsOffset = 0;
  const _newsCount = 10;

  function _extractKeyword(url) {
    // Prefer article title/summary extracted from the page itself
    if (_urlPageTitle) return _urlPageTitle.trim().slice(0, 100);
    if (_urlPageSummary) {
      // Take the first 8-10 meaningful words of the summary
      const words = _urlPageSummary.trim().split(/\s+/).slice(0, 10).join(' ');
      if (words.length > 5) return words.slice(0, 100);
    }
    // Fallback: parse URL path
    try {
      const u = new URL(url);
      const parts = u.pathname.replace(/\//g, ' ').replace(/[-_]/g, ' ').trim();
      return (parts || u.hostname.replace('www.', '')).slice(0, 60);
    } catch { return ''; }
  }

  function _formatDate(dateStr) {
    if (!dateStr) return '';
    try {
      const d = new Date(dateStr);
      const diff = Math.floor((Date.now() - d) / 1000);
      if (diff < 3600) return Math.floor(diff / 60) + ' 分钟前';
      if (diff < 86400) return Math.floor(diff / 3600) + ' 小时前';
      if (diff < 604800) return Math.floor(diff / 86400) + ' 天前';
      return d.toLocaleDateString('zh-CN');
    } catch { return ''; }
  }

  function _escHtmlLocal(s) {
    return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
  }

  function renderNewsResults(articles) {
    const el = $('newsSearchResults');
    if (!articles || articles.length === 0) {
      el.innerHTML = '<p style="color:#94a3b8;text-align:center;padding:20px">未找到相关新闻</p>';
      return;
    }
    el.innerHTML = articles.map(a => {
      // 兼容 Serper API 格式
      const title = a.title || a.name || '';
      const desc = a.snippet || a.description || '';
      const url = a.link || a.url || '#';
      const source = a.source || '';
      const dateStr = _formatDate(a.date || a.datePublished);
      const thumb = a.image || ''
        ? `<img class="news-card-thumb" src="${_escHtmlLocal(a.image)}" alt="" loading="lazy" onerror="this.style.display='none'">`
        : '';
      return `
        <a class="news-card" href="${_escHtmlLocal(url)}" target="_blank" rel="noopener">
          ${thumb}
          <div class="news-card-body">
            <div class="news-card-title">${_escHtmlLocal(title)}</div>
            <div class="news-card-desc">${_escHtmlLocal(desc)}</div>
            <div class="news-card-meta">
              ${source ? `<span class="news-card-source">${_escHtmlLocal(source)}</span>` : ''}
              ${dateStr ? `<span>${dateStr}</span>` : ''}
            </div>
          </div>
        </a>`;
    }).join('');
  }

  async function doNewsSearch(offset) {
    const keyword = ($('newsSearchKeyword').value || '').trim();
    if (!keyword) { showToast('请输入搜索关键词'); return; }
    const freshness = $('newsSearchFreshness').value;
    const statusEl = $('newsSearchStatus');
    const pagEl = $('newsSearchPagination');

    setStatus(statusEl, spinnerHTML() + ' 搜索中…');
    $('btnDoNewsSearch').disabled = true;

    try {
      const params = new URLSearchParams({ q: keyword, offset, count: _newsCount });
      const res = await fetch('/api/search/news?' + params);
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || `HTTP ${res.status}`);
      }
      const data = await res.json();
      const articles = data.news || data.value || [];  // Serper 用 'news'，Bing 用 'value'
      _newsOffset = offset;

      renderNewsResults(articles);
      statusEl.textContent = '';
      pagEl.hidden = false;
      $('newsSearchPageLabel').textContent = `第 ${Math.floor(offset / _newsCount) + 1} 页`;
      $('btnNewsSearchPrev').disabled = offset === 0;
      $('btnNewsSearchNext').disabled = articles.length < _newsCount;
    } catch (e) {
      setStatus(statusEl, '搜索失败：' + e.message, 'error');
      $('newsSearchPagination').hidden = true;
    } finally {
      $('btnDoNewsSearch').disabled = false;
    }
  }

  if ($('btnWebSearch')) {
    $('btnWebSearch').addEventListener('click', () => {
      const url = ($('urlInput') && $('urlInput').value.trim()) || '';
      const panel = $('newsSearchPanel');
      panel.hidden = false;
      // Pre-fill keyword from URL
      const kw = $('newsSearchKeyword');
      if (!kw.value && url) kw.value = _extractKeyword(url);
      kw.focus();
    });
  }

  if ($('btnCloseNewsSearch')) {
    $('btnCloseNewsSearch').addEventListener('click', () => {
      $('newsSearchPanel').hidden = true;
    });
  }

  if ($('btnDoNewsSearch')) {
    $('btnDoNewsSearch').addEventListener('click', () => doNewsSearch(0));
  }

  if ($('newsSearchKeyword')) {
    $('newsSearchKeyword').addEventListener('keydown', e => {
      if (e.key === 'Enter') doNewsSearch(0);
    });
  }

  if ($('btnNewsSearchPrev')) {
    $('btnNewsSearchPrev').addEventListener('click', () => {
      if (_newsOffset >= _newsCount) doNewsSearch(_newsOffset - _newsCount);
    });
  }

  if ($('btnNewsSearchNext')) {
    $('btnNewsSearchNext').addEventListener('click', () => doNewsSearch(_newsOffset + _newsCount));
  }
})();


/* ── 联网图片搜索 ───────────────────────────────────────── */

// 全局函数：从图片卡片触发图片搜索（以文章标题 + 图片类别为关键词）
// 包装函数：从图片卡片按钮触发搜索（读取按钮的 data-category）
function _searchFromCard(btn) {
  if (!btn) return;
  _openImageSearchForCard(btn.dataset.category || '');
}

function _openImageSearchForCard(category) {
  const modal = $('imageSearchModal');
  if (!modal) return;
  modal.hidden = false;
  const kw = $('imageSearchKeyword');
  if (kw) {
    let keyword = _urlPageTitle || '';
    if (category && keyword) {
      keyword = keyword + ' ' + category;
    } else if (category) {
      keyword = category;
    } else if (!keyword && _urlPageSummary) {
      keyword = _urlPageSummary.trim().split(/\s+/).slice(0, 10).join(' ');
    }
    kw.value = keyword.trim().slice(0, 100);
    // 自动触发搜索，不需要用户再手动点搜索按钮
    const btnSearch = $('btnDoImageSearch');
    if (btnSearch && kw.value) btnSearch.click();
    else kw.focus();
  }
}

(function initImageSearch() {
  let _imgOffset = 0;
  const _imgCount = 20;

  function _escHtmlLocal(s) {
    return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
  }

  function proxyUrl(url) {
    return '/api/search/proxy/image?url=' + encodeURIComponent(url);
  }

  // ── Image search ──
  function renderImageResults(items) {
    const el = $('imageSearchResults');
    if (!items || items.length === 0) {
      el.innerHTML = '<p style="color:#94a3b8;text-align:center;padding:20px;grid-column:1/-1">未找到相关图片</p>';
      return;
    }
    el.innerHTML = items.map((img, i) => {
      // 兼容 Serper (imageUrl/title) 和 Bing (contentUrl/name) 格式
      const imgName = img.title || img.name || '';
      const thumbUrl = img.imageUrl || img.thumbnailUrl || img.contentUrl || '';
      return `
        <div class="img-search-card" data-idx="${i}" title="${_escHtmlLocal(imgName)}">
          <img src="${_escHtmlLocal(proxyUrl(thumbUrl))}" alt="${_escHtmlLocal(imgName)}" loading="lazy"
               onerror="this.src='/static/img/placeholder.png'">
          <div class="img-search-card-overlay">
            <span class="img-search-card-name">${_escHtmlLocal(imgName)}</span>
          </div>
        </div>`;
    }).join('');

    // Click → open image in new tab
    el.querySelectorAll('.img-search-card').forEach((card, i) => {
      card.addEventListener('click', () => {
        const img = items[i];
        if (!img) return;
        const url = img.imageUrl || img.contentUrl || '';
        if (url) window.open(url, '_blank', 'noopener');
      });
    });
  }

  async function doImageSearch(offset) {
    const keyword = ($('imageSearchKeyword').value || '').trim();
    if (!keyword) { showToast('请输入搜索关键词'); return; }
    const size = $('imageSearchSize').value;
    const color = $('imageSearchColor').value;
    const statusEl = $('imageSearchStatus');
    const pagEl = $('imageSearchPagination');

    setStatus(statusEl, spinnerHTML() + ' 搜索中…');
    $('btnDoImageSearch').disabled = true;

    try {
      const params = new URLSearchParams({ q: keyword, offset, count: _imgCount });
      const res = await fetch('/api/search/images?' + params);
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || `HTTP ${res.status}`);
      }
      const data = await res.json();
      const items = data.images || data.value || [];  // Serper 用 'images'，Bing 用 'value'
      _imgOffset = offset;

      renderImageResults(items);
      statusEl.textContent = '';
      pagEl.hidden = false;
      $('imageSearchPageLabel').textContent = `第 ${Math.floor(offset / _imgCount) + 1} 页`;
      $('btnImageSearchPrev').disabled = offset === 0;
      $('btnImageSearchNext').disabled = items.length < _imgCount;
    } catch (e) {
      setStatus(statusEl, '搜索失败：' + e.message, 'error');
      $('imageSearchPagination').hidden = true;
    } finally {
      $('btnDoImageSearch').disabled = false;
    }
  }

  // Open modal
  if ($('btnNewsImage')) {
    $('btnNewsImage').addEventListener('click', () => {
      const url = ($('urlInput') && $('urlInput').value.trim()) || '';
      $('imageSearchModal').hidden = false;
      const kw = $('imageSearchKeyword');
      if (!kw.value) {
        // Prefer article title/summary; fallback to URL path
        if (_urlPageTitle) {
          kw.value = _urlPageTitle.trim().slice(0, 100);
        } else if (_urlPageSummary) {
          kw.value = _urlPageSummary.trim().split(/\s+/).slice(0, 10).join(' ').slice(0, 100);
        } else if (url) {
          try {
            const u = new URL(url);
            kw.value = u.pathname.replace(/\//g,' ').replace(/[-_]/g,' ').trim().slice(0, 60) || u.hostname;
          } catch {}
        }
      }
      kw.focus();
    });
  }

  if ($('btnImageSearchModalClose')) {
    $('btnImageSearchModalClose').addEventListener('click', () => {
      $('imageSearchModal').hidden = true;
    });
  }
  if ($('imageSearchModal')) {
    $('imageSearchModal').addEventListener('click', e => {
      if (e.target === $('imageSearchModal')) $('imageSearchModal').hidden = true;
    });
  }

  if ($('btnDoImageSearch')) {
    $('btnDoImageSearch').addEventListener('click', () => doImageSearch(0));
  }
  if ($('imageSearchKeyword')) {
    $('imageSearchKeyword').addEventListener('keydown', e => {
      if (e.key === 'Enter') doImageSearch(0);
    });
  }
  if ($('btnImageSearchPrev')) {
    $('btnImageSearchPrev').addEventListener('click', () => {
      if (_imgOffset >= _imgCount) doImageSearch(_imgOffset - _imgCount);
    });
  }
  if ($('btnImageSearchNext')) {
    $('btnImageSearchNext').addEventListener('click', () => doImageSearch(_imgOffset + _imgCount));
  }
})();

// ────────────────────────────────────────────────────────────────
function showToast(message) {
  const toast = document.createElement('div');
  toast.style.cssText = `
    position: fixed;
    bottom: 20px;
    right: 20px;
    background: #1e293b;
    color: #f1f5f9;
    padding: 12px 16px;
    border-radius: 6px;
    font-size: 0.88rem;
    box-shadow: 0 2px 8px rgba(0,0,0,0.15);
    z-index: 9999;
    animation: fadeSlideIn 0.2s ease-out;
  `;
  toast.textContent = message;
  document.body.appendChild(toast);
  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transition = 'opacity 0.2s';
    setTimeout(() => toast.remove(), 200);
  }, 3000);
}
// ════════════════════════════════════════════════════════════════
// 文本 AI 生成检测 (XAI) 功能
// ════════════════════════════════════════════════════════════════

(() => {
  const $ = (id) => document.getElementById(id);

  // 事件监听
  const btnDetectText = $('btnDetectText');
  const btnClearText = $('btnClearText');
  const btnBackToTextInput = $('btnBackToTextInput');
  const textInput = $('textInput');
  const textInputPanel = $('textInput').parentElement;
  const textResultPanel = $('textResultPanel');
  const textLoading = $('textLoading');

  if (btnDetectText) {
    btnDetectText.addEventListener('click', detectText);
  }

  if (btnClearText) {
    btnClearText.addEventListener('click', () => {
      textInput.value = '';
      textInput.focus();
    });
  }

  if (btnBackToTextInput) {
    btnBackToTextInput.addEventListener('click', () => {
      textInputPanel.style.display = 'block';
      textResultPanel.hidden = true;
    });
  }

  async function detectText() {
    const text = textInput.value.trim();
    if (!text) {
      showToast('请输入文本内容');
      return;
    }

    const xaiMethod = document.querySelector('input[name="xai-method"]:checked').value;

    textInputPanel.style.display = 'none';
    textLoading.style.display = 'flex';
    textResultPanel.hidden = true;

    try {
      const response = await fetch('/api/text/detect', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          text: text,
          xai_method: xaiMethod,
          num_features: 20
        })
      });

      if (!response.ok) {
        const err = await response.json().catch(() => ({}));
        throw new Error(err.detail || `HTTP ${response.status}`);
      }

      const result = await response.json();
      displayResult(result, xaiMethod);
    } catch (e) {
      showToast('检测失败：' + e.message);
      textInputPanel.style.display = 'block';
    } finally {
      textLoading.style.display = 'none';
    }
  }

  function displayResult(result, xaiMethod) {
    try {
      const label = result.label || 'UNKNOWN';
      const confidence = result.confidence || 0;
      const isFake = label === 'FAKE';

      // 更新结果卡片
      const badge = $('resultBadge');
      if (badge) {
        badge.className = 'result-badge ' + (isFake ? 'fake' : 'real');
        badge.textContent = isFake ? 'AI\n生成' : '真实\n文本';
      }

      const resultLabel = $('resultLabel');
      const resultConfidence = $('resultConfidence');
      if (resultLabel) resultLabel.textContent = result.label_zh || label;
      if (resultConfidence) resultConfidence.textContent = confidence.toFixed(1) + '%';

      // 处理解释
      if (result.explanations && result.explanations.lime) {
        displayLimeExplanation(result.explanations.lime);
      }
      if (result.explanations && result.explanations.shap) {
        displayShapExplanation(result.explanations.shap);
        const expShapBtn = $('expShapBtn');
        if (expShapBtn) expShapBtn.hidden = false;
      }

      // 高亮文本
      if (result.highlighted_html) {
        const highlightedText = $('highlightedText');
        if (highlightedText) highlightedText.innerHTML = result.highlighted_html;
      }

      // 确保至少显示 LIME 解释
      if (result.explanations && Object.keys(result.explanations).length === 0) {
        const limeContent = $('limeContent');
        if (limeContent && !limeContent.classList.contains('active')) {
          limeContent.classList.add('active');
        }
      }

      textResultPanel.hidden = false;
    } catch (e) {
      console.error('displayResult error:', e);
      showToast('显示结果时出错：' + e.message);
    }
  }

  function displayLimeExplanation(lime) {
    try {
      const fakeTokens = (lime.top_positive || []).slice(0, 10);
      const realTokens = (lime.top_negative || []).slice(0, 10);

      const fakeHtml = fakeTokens.map(t => 
        `<div class="keyword-tag positive">${(t.token || '').replace(/</g, '&lt;').replace(/>/g, '&gt;')} <span class="keyword-weight">${(t.weight || t.contribution || 0).toFixed(3)}</span></div>`
      ).join('') || '<div class="keyword-tag">无明显特征</div>';

      const realHtml = realTokens.map(t => 
        `<div class="keyword-tag negative">${(t.token || '').replace(/</g, '&lt;').replace(/>/g, '&gt;')} <span class="keyword-weight">${Math.abs(t.weight || t.contribution || 0).toFixed(3)}</span></div>`
      ).join('') || '<div class="keyword-tag">无明显特征</div>';

      const limeFakeKeywords = $('limeFakeKeywords');
      const limeRealKeywords = $('limeRealKeywords');
      const limeContent = $('limeContent');
      const expLimeBtn = $('expLimeBtn');

      if (limeFakeKeywords) limeFakeKeywords.innerHTML = fakeHtml;
      if (limeRealKeywords) limeRealKeywords.innerHTML = realHtml;
      if (limeContent) limeContent.classList.add('active');
      if (expLimeBtn) expLimeBtn.classList.add('active');
    } catch (e) {
      console.error('displayLimeExplanation error:', e);
    }
  }

  function displayShapExplanation(shap) {
    try {
      const tokens = (shap.tokens || []).slice(0, 15);
      const html = tokens.map(t => {
        const isPos = t.shap_value > 0;
        return `<div class="keyword-tag ${isPos ? 'positive' : 'negative'}">
        ${(t.token || '').replace(/</g, '&lt;').replace(/>/g, '&gt;')} <span class="keyword-weight">${Math.abs(t.shap_value || 0).toFixed(3)}</span>
      </div>`;
      }).join('') || '<div class="keyword-tag">无明显特征</div>';

      const shapKeywords = $('shapKeywords');
      if (shapKeywords) shapKeywords.innerHTML = html;
    } catch (e) {
      console.error('displayShapExplanation error:', e);
    }
  }
})();
