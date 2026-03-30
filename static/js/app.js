/* global */
'use strict';

// ── Helpers ──────────────────────────────────────────────────────────────────

function $(id) { return document.getElementById(id); }

function setStatus(el, msg, type) {
  el.textContent = msg;
  el.className = 'status-msg' + (type ? ' ' + type : '');
}

function spinnerHTML() {
  return '<span class="spinner"></span>';
}

// ── Auth ────────────────────────────────────────────────────────────────────────

const AUTH_KEY      = 'aigi_token';
const AUTH_USER_KEY = 'aigi_user';

function getToken() { return localStorage.getItem(AUTH_KEY); }
function authHeaders() {
  const t = getToken();
  return t ? { 'Authorization': 'Bearer ' + t } : {};
}
function saveAuth(tokens, username, role) {
  localStorage.setItem(AUTH_KEY, tokens.access_token);
  localStorage.setItem(AUTH_USER_KEY, JSON.stringify({ username, role }));
  updateAuthBar();
}
function clearAuth() {
  localStorage.removeItem(AUTH_KEY);
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
  } else {
    $('authGuest').hidden = false;
    $('authUser').hidden  = true;
  }
  updateBatchAccess();
  // hide report download on logout
  if (!raw && $('reportDownload')) $('reportDownload').hidden = true;
}

$('btnShowLogin').addEventListener('click',  () => { $('loginModal').hidden = false; });
$('btnModalClose').addEventListener('click', () => { $('loginModal').hidden = true;  });
$('btnLogout').addEventListener('click',     () => { clearAuth(); });

// Modal tab switching
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
  if (!username || !password) { setStatus($('loginStatus'), '⚠️ 请填写用户名和密码', 'error'); return; }
  const r = await fetch('/api/auth/login', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password }),
  });
  const d = await r.json();
  if (!r.ok) { setStatus($('loginStatus'), '❌ ' + (d.message || '登录失败'), 'error'); return; }
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
  if (!username || !password) { setStatus($('registerStatus'), '⚠️ 请填写用户名和密码', 'error'); return; }
  const r = await fetch('/api/auth/register', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password }),
  });
  const d = await r.json();
  if (!r.ok) { setStatus($('registerStatus'), '❌ ' + (d.message || '注册失败'), 'error'); return; }
  const role = JSON.parse(atob(d.access_token.split('.')[1])).role;
  saveAuth(d, username, role);
  $('loginModal').hidden = true;
  $('regUser').value = '';
  $('regPass').value = '';
  setStatus($('registerStatus'), '', '');
});

// Allow Enter to submit login / register
$('loginPass').addEventListener('keydown',   e => { if (e.key === 'Enter') $('btnLogin').click(); });
$('regPass').addEventListener('keydown',     e => { if (e.key === 'Enter') $('btnRegister').click(); });

updateAuthBar();

// ── Role management modal ─────────────────────────────────────────────────────

function openRoleModal() {
  // 重置到 step1 状态，防止残留
  $('roleStep1').hidden  = false;
  $('roleStep2').hidden  = true;
  $('rolePass').value    = '';
  $('roleTargetUser').value = '';
  $('roleSelect').value  = 'user';
  $('rolePassError').hidden = true;
  setStatus($('roleStatus'), '', '');
  $('roleModal').hidden  = false;
}

function closeRoleModal() {
  $('roleModal').hidden = true;
}

$('btnShowRole').addEventListener('click', openRoleModal);
$('btnRoleModalClose').addEventListener('click', closeRoleModal);

// 点击遮罩层关闭 roleModal
$('roleModal').addEventListener('click', e => {
  if (e.target === $('roleModal')) closeRoleModal();
});

// Step 1: 验证密码
$('btnRoleUnlock').addEventListener('click', () => {
  if ($('rolePass').value === 'aigi') {
    $('rolePassError').hidden = true;
    $('roleStep1').hidden = true;
    $('roleStep2').hidden = false;
  } else {
    $('rolePassError').hidden = false;
    $('rolePass').value = '';
    $('rolePass').focus();
  }
});
$('rolePass').addEventListener('keydown', e => {
  if (e.key === 'Enter') $('btnRoleUnlock').click();
});

// Step 2: 修改角色
$('btnRoleChange').addEventListener('click', async () => {
  const targetUsername = $('roleTargetUser').value.trim();
  const newRole = $('roleSelect').value;
  if (!targetUsername) {
    setStatus($('roleStatus'), '⚠️ 请输入目标用户名', 'error');
    return;
  }

  $('btnRoleChange').disabled = true;
  $('btnRoleChange').textContent = '修改中…';

  try {
    const r = await fetch(`/api/auth/admin/users/${encodeURIComponent(targetUsername)}/role`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json', ...authHeaders() },
      body: JSON.stringify({ role: newRole }),
    });
    const d = await r.json();

    if (!r.ok) {
      const msg = d.detail || d.message || '修改失败';
      setStatus($('roleStatus'), '❌ ' + msg, 'error');
    } else {
      setStatus($('roleStatus'), `✅ 已将 ${d.username} 的角色改为 ${d.role}`, 'success');
      // 若修改的是当前登录用户自己，同步更新 localStorage 和 auth-bar
      const rawUser = localStorage.getItem(AUTH_USER_KEY);
      if (rawUser) {
        const currentUser = JSON.parse(rawUser);
        if (currentUser.username === d.username) {
          currentUser.role = d.role;
          localStorage.setItem(AUTH_USER_KEY, JSON.stringify(currentUser));
          updateAuthBar();
        }
      }
      $('roleTargetUser').value = '';
    }
  } catch (err) {
    setStatus($('roleStatus'), '❌ 网络错误：' + err.message, 'error');
  } finally {
    $('btnRoleChange').disabled = false;
    $('btnRoleChange').textContent = '修改角色';
  }
});
$('roleTargetUser').addEventListener('keydown', e => {
  if (e.key === 'Enter') $('btnRoleChange').click();
});



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

// ── Tab switching ─────────────────────────────────────────────────────────────

document.querySelectorAll('.tab-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.tab-pane').forEach(p => p.classList.remove('active'));
    btn.classList.add('active');
    $('tab-' + btn.dataset.tab).classList.add('active');
  });
});

// ── Tab 1 — Upload & Detect ───────────────────────────────────────────────────

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
  // Reset result card
  hideResultCard();
}

function clearUpload() {
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
  // Reset cam overlay
  const camOvl = $('camOverlay');
  camOvl.src = '';
  camOvl.classList.remove('visible');
  $('btnCamToggle').hidden = true;
  $('btnCamToggle').classList.remove('active');
  hideResultCard();
}

function hideResultCard() {
  $('resultCard').style.display = 'none';
  $('resultEmpty').style.display = 'flex';
  // Reset panel to center-align for empty state
  $('resultPanel') && ($('resultPanel').style.alignItems = 'center');
  const rp = document.querySelector('.result-panel');
  if (rp) { rp.style.alignItems = 'center'; rp.style.justifyContent = 'center'; }
}

// File input
fileInput.addEventListener('change', e => {
  const file = e.target.files[0];
  if (file) showPreview(file);
});

// Click on drop zone (when no image)
dropZone.addEventListener('click', () => {
  if (!selectedFile) fileInput.click();
});

// Drag & drop
dropZone.addEventListener('dragover', e => {
  e.preventDefault();
  dropZone.classList.add('drag-over');
});
dropZone.addEventListener('dragleave', () => dropZone.classList.remove('drag-over'));
dropZone.addEventListener('drop', e => {
  e.preventDefault();
  dropZone.classList.remove('drag-over');
  const file = e.dataTransfer.files[0];
  if (file && file.type.startsWith('image/')) showPreview(file);
});

// Re-upload
btnReupload.addEventListener('click', e => { e.stopPropagation(); fileInput.click(); });

// Clear
btnClear.addEventListener('click', e => { e.stopPropagation(); clearUpload(); });

// Cam toggle
$('btnCamToggle').addEventListener('click', e => {
  e.stopPropagation();
  const camOvl = $('camOverlay');
  const btn = $('btnCamToggle');
  const show = !camOvl.classList.contains('visible');
  camOvl.classList.toggle('visible', show);
  btn.classList.toggle('active', show);
  btn.textContent = show ? '🌡️ 原图' : '🌡️ 热力图';
});

// ── Render result card ────────────────────────────────────────────────────────

function renderResult(data) {
  const isReal = data.label === 'REAL';
  const cls    = isReal ? 'real' : 'fake';

  // Verdict
  const verdict = $('verdict');
  verdict.className = 'verdict ' + cls;
  $('verdictIcon').textContent = isReal ? '📷' : '🤖';
  $('verdictLabel').textContent = data.label_zh;

  // Confidence
  const conf = Math.round(data.confidence);
  $('confValue').textContent = conf + '%';
  const bar = $('confBar');
  bar.className = 'progress-bar ' + cls;
  // Trigger width animation (set 0 first then update)
  bar.style.width = '0%';
  requestAnimationFrame(() => {
    requestAnimationFrame(() => { bar.style.width = conf + '%'; });
  });

  // Probability rows
  const probRows = $('probRows');
  probRows.innerHTML = '';
  (data.probs || []).forEach(p => {
    const rowCls = p.label === 'REAL' ? 'real' : 'fake';
    const score = Math.round(p.score);
    probRows.insertAdjacentHTML('beforeend', `
      <div class="prob-row">
        <div class="prob-row-header">
          <span class="prob-row-label">${p.label_zh}</span>
          <span class="prob-row-score">${score}%</span>
        </div>
        <div class="prob-track">
          <div class="prob-fill ${rowCls}" style="width:0%" data-score="${score}"></div>
        </div>
      </div>
    `);
  });

  // Animate prob bars
  requestAnimationFrame(() => {
    requestAnimationFrame(() => {
      probRows.querySelectorAll('.prob-fill').forEach(el => {
        el.style.width = el.dataset.score + '%';
      });
    });
  });

  // ── Explanation section ──
  const explain = data.explanation;
  const explainSection = $('explainSection');
  if (explain) {
    const levelEl = $('explainLevel');
    levelEl.textContent = explain.level;
    levelEl.className = 'explain-level ' + cls;
    $('explainSummary').textContent = explain.summary;

    const cluesList = $('explainClues');
    cluesList.innerHTML = '';
    (explain.clues || []).forEach(c => {
      const li = document.createElement('li');
      li.textContent = c;
      cluesList.appendChild(li);
    });
    cluesList.style.display = (explain.clues && explain.clues.length) ? '' : 'none';

    $('explainDisclaimer').textContent = explain.disclaimer || '';
    explainSection.style.display = '';
  } else {
    explainSection.style.display = 'none';
  }

  // ── Grad-CAM overlay ──
  const camOvl = $('camOverlay');
  const camBtn = $('btnCamToggle');
  if (data.cam_image) {
    camOvl.src = data.cam_image;
    camBtn.hidden = false;
    camBtn.classList.remove('active');
    camOvl.classList.remove('visible');
  } else {
    camOvl.src = '';
    camBtn.hidden = true;
  }

  // Show card
  $('resultEmpty').style.display = 'none';
  const card = $('resultCard');
  card.style.display = 'flex';
  const rp = document.querySelector('.result-panel');
  if (rp) { rp.style.alignItems = 'flex-start'; rp.style.justifyContent = 'flex-start'; }
}

// ── Detect button ─────────────────────────────────────────────────────────────

btnDetect.addEventListener('click', async () => {
  if (!selectedFile) return;

  btnDetect.disabled = true;
  btnDetect.classList.add('loading');
  btnDetect.innerHTML = spinnerHTML() + '检测中…';
  setStatus(uploadStatus, '', '');

  const fd = new FormData();
  fd.append('image', selectedFile);

  try {
    const resp = await fetch('/api/detect?cam=1', { method: 'POST', body: fd, headers: authHeaders() });
    const data = await resp.json();

    if (!resp.ok || data.error) {
      setStatus(uploadStatus, '❌ ' + (data.error || '检测失败'), 'error');
    } else {
      renderResult(data);
      setStatus(uploadStatus, '✅ 检测完成', 'success');
      const rd = $('reportDownload');
      if (data.detection_id && getToken()) {
        rd.hidden = false;
        $('btnDownloadPdf').onclick   = () => downloadReport(data.detection_id, 'pdf');
        $('btnDownloadExcel').onclick = () => downloadReport(data.detection_id, 'excel');
      } else {
        rd.hidden = true;
      }
    }
  } catch (err) {
    setStatus(uploadStatus, '❌ 网络错误：' + err.message, 'error');
  } finally {
    btnDetect.classList.remove('loading');
    btnDetect.innerHTML = '开始检测';
    btnDetect.disabled = false;
  }
});

// ── Tab 2 — URL Detection ─────────────────────────────────────────────────────

const urlInput    = $('urlInput');
const btnUrl      = $('btnUrl');
const urlStatus   = $('urlStatus');
const gallery     = $('gallery');
const reportSection = $('reportSection');
const reportBody  = $('reportBody');

function buildGalleryCard(item) {
  const cls = item.label === 'REAL' ? 'real' : 'fake';
  const miniBars = (item.probs || []).map(p => {
    const pCls = p.label === 'REAL' ? 'real' : 'fake';
    return `
      <div class="mini-row">
        <span class="mini-label">${p.label_zh}</span>
        <div class="mini-track">
          <div class="mini-fill ${pCls}" style="width:0%" data-score="${Math.round(p.score)}"></div>
        </div>
        <span class="mini-score">${Math.round(p.score)}%</span>
      </div>`;
  }).join('');

  return `
    <div class="gallery-card">
      <img class="gallery-card__img" src="${item.thumbnail}" alt="图片 ${item.index}" loading="lazy" />
      <div class="gallery-card__body">
        <span class="gallery-card__badge ${cls}">${item.label_zh}</span>
        <p class="gallery-card__conf">置信度：<span>${Math.round(item.confidence)}%</span></p>
        <div class="gallery-card__mini-bars">${miniBars}</div>
      </div>
    </div>`;
}

function buildReportRow(item) {
  const cls = item.label === 'REAL' ? 'real' : 'fake';
  return `
    <div class="report-row">
      <span class="report-row__index">图${item.index}</span>
      <span class="report-row__badge ${cls}">${item.label_zh}</span>
      <span class="report-row__conf">${Math.round(item.confidence)}%</span>
      <span class="report-row__url">${item.url}</span>
    </div>`;
}

btnUrl.addEventListener('click', async () => {
  const url = urlInput.value.trim();
  if (!url) { setStatus(urlStatus, '⚠️ 请输入 URL', 'error'); return; }

  btnUrl.disabled = true;
  btnUrl.classList.add('loading');
  btnUrl.innerHTML = spinnerHTML() + '检测中…';
  gallery.innerHTML = '';
  reportSection.hidden = true;
  reportBody.innerHTML = '';
  setStatus(urlStatus, '', '');

  try {
    const resp = await fetch('/api/detect-url', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url }),
    });
    const data = await resp.json();

    if (!resp.ok || data.error) {
      setStatus(urlStatus, '❌ ' + (data.error || '检测失败'), 'error');
    } else {
      setStatus(urlStatus, `✅ 共检测 ${data.count} 张图片`, 'success');

      // Render gallery
      gallery.innerHTML = data.results.map(buildGalleryCard).join('');

      // Animate mini bars
      requestAnimationFrame(() => {
        requestAnimationFrame(() => {
          gallery.querySelectorAll('.mini-fill').forEach(el => {
            el.style.width = el.dataset.score + '%';
          });
        });
      });

      // Render report
      reportBody.innerHTML = data.results.map(buildReportRow).join('');
      reportSection.hidden = false;
    }
  } catch (err) {
    setStatus(urlStatus, '❌ 网络错误：' + err.message, 'error');
  } finally {
    btnUrl.classList.remove('loading');
    btnUrl.innerHTML = '抓取并检测';
    btnUrl.disabled = false;
  }
});

// Allow pressing Enter in URL input
urlInput.addEventListener('keydown', e => {
  if (e.key === 'Enter') btnUrl.click();
});

// ── Tab 3 — Batch Detection ───────────────────────────────────────────────────────

function updateBatchAccess() {
  const raw  = localStorage.getItem(AUTH_USER_KEY);
  const role = raw ? JSON.parse(raw).role : null;
  const allowed = role === 'auditor' || role === 'admin';
  const hint = $('batchAuthHint');
  const btn  = $('btnBatch');
  if (!raw) {
    hint.hidden = false;
    hint.querySelector('p').textContent = '⚠️ 批量检测需要登录后使用。';
    btn.disabled = true;
  } else if (!allowed) {
    hint.hidden = false;
    hint.querySelector('p').innerHTML = '⚠️ 批量检测需要 <strong>auditor</strong> 或 <strong>admin</strong> 角色，当前账号无权限。';
    btn.disabled = true;
  } else {
    hint.hidden  = true;
    btn.disabled = $('batchInput').files.length === 0;
  }
}

const batchInput = $('batchInput');
batchInput.addEventListener('change', () => {
  const raw  = localStorage.getItem(AUTH_USER_KEY);
  const role = raw ? JSON.parse(raw).role : null;
  const allowed = role === 'auditor' || role === 'admin';
  $('btnBatch').disabled = !allowed || batchInput.files.length === 0;
});

$('btnBatch').addEventListener('click', async () => {
  const files = [...batchInput.files].slice(0, 20);
  if (!files.length) return;

  const fd = new FormData();
  files.forEach(f => fd.append('images', f));

  const btn   = $('btnBatch');
  const bGall = $('batchGallery');
  btn.disabled = true;
  btn.classList.add('loading');
  btn.innerHTML = spinnerHTML() + '检测中…';
  bGall.innerHTML = '';
  setStatus($('batchStatus'), '', '');

  try {
    const r = await fetch('/api/detect-batch', {
      method: 'POST',
      body: fd,
      headers: authHeaders(),
    });
    const d = await r.json();
    if (!r.ok) {
      setStatus($('batchStatus'), '❌ ' + (d.message || '检测失败'), 'error');
    } else {
      setStatus($('batchStatus'), `✅ 共检测 ${d.count} 张图片`, 'success');
      bGall.innerHTML = d.results.map((item, i) =>
        buildGalleryCard({ ...item, index: i + 1, thumbnail: '', url: files[i] ? files[i].name : '' })
      ).join('');
      requestAnimationFrame(() => {
        requestAnimationFrame(() => {
          bGall.querySelectorAll('.mini-fill').forEach(el => {
            el.style.width = el.dataset.score + '%';
          });
        });
      });
    }
  } catch (e) {
    setStatus($('batchStatus'), '❌ 网络错误：' + e.message, 'error');
  } finally {
    btn.classList.remove('loading');
    btn.innerHTML = '开始批量检测';
    updateBatchAccess();
  }
});
