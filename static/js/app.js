/* global */
'use strict';

function $(id) { return document.getElementById(id); }
function setStatus(el, msg, type) {
  el.textContent = msg;
  el.className = 'status-msg' + (type ? ' ' + type : '');
}
function spinnerHTML() { return '<span class="spinner"></span>'; }

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
  } else {
    $('rolePassError').hidden = false;
    $('rolePass').value = '';
    $('rolePass').focus();
  }
});
$('rolePass').addEventListener('keydown', e => { if (e.key === 'Enter') $('btnRoleUnlock').click(); });

$('btnRoleChange').addEventListener('click', async () => {
  const targetUsername = $('roleTargetUser').value.trim();
  const newRole = $('roleSelect').value;
  if (!targetUsername) { setStatus($('roleStatus'), '⚠️ 请输入目标用户名', 'error'); return; }
  $('btnRoleChange').disabled = true;
  $('btnRoleChange').textContent = '修改中…';
  try {
    const r = await fetch(`/api/auth/admin/users/${encodeURIComponent(targetUsername)}/role`, {
      method: 'PATCH', headers: { 'Content-Type': 'application/json', ...authHeaders() },
      body: JSON.stringify({ role: newRole }),
    });
    const d = await r.json();
    if (!r.ok) { setStatus($('roleStatus'), '❌ ' + (d.detail || d.message || '修改失败'), 'error');
    } else {
      setStatus($('roleStatus'), `✅ 已将 ${d.username} 的角色改为 ${d.role}`, 'success');
      const rawUser = localStorage.getItem(AUTH_USER_KEY);
      if (rawUser) {
        const cu = JSON.parse(rawUser);
        if (cu.username === d.username) { cu.role = d.role; localStorage.setItem(AUTH_USER_KEY, JSON.stringify(cu)); updateAuthBar(); }
      }
      $('roleTargetUser').value = '';
    }
  } catch (err) { setStatus($('roleStatus'), '❌ 网络错误', 'error');
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

document.querySelectorAll('.tab-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.tab-pane').forEach(p => p.classList.remove('active'));
    btn.classList.add('active');
    $('tab-' + btn.dataset.tab).classList.add('active');
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
  const camOvl = $('camOverlay');
  camOvl.src = ''; camOvl.classList.remove('visible');
  $('btnCamToggle').hidden = true; $('btnCamToggle').classList.remove('active');
  hideResultCard();
}

function hideResultCard() {
  $('resultCard').style.display = 'none';
  $('resultEmpty').style.display = 'flex';
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
  btn.textContent = show ? '🌡️ 原图' : '🌡️ 热力图';
});

function renderResult(data) {
  const isReal = data.label === 'REAL';
  const cls = isReal ? 'real' : 'fake';
  const v = $('verdict');
  v.className = 'verdict ' + cls;
  $('verdictIcon').textContent = isReal ? '📷' : '🤖';
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
  if(exp){
    const lev = $('explainLevel');
    lev.textContent=exp.level;
    lev.className='explain-level '+cls;
    $('explainSummary').textContent=exp.summary;
    const clist = $('explainClues'); clist.innerHTML='';
    (exp.clues||[]).forEach(x=>{const li=document.createElement('li');li.textContent=x;clist.appendChild(li);});
    clist.style.display=exp.clues?.length?'':'none';
    $('explainDisclaimer').textContent=exp.disclaimer||'';
    es.style.display='';
  }else{es.style.display='none';}
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
      setStatus(uploadStatus,'❌ 检测失败','error');
    }else{
      renderResult(data);
      setStatus(uploadStatus,'✅ 检测完成','success');
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
    }
  }catch(e){
    setStatus(uploadStatus,'❌ 网络错误','error');
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

function buildGalleryCard(it){
  const c=it.label==='REAL'?'real':'fake';
  const mb=(it.probs||[]).map(p=>{
    const pc=p.label==='REAL'?'real':'fake';
    const s=Math.round(p.score);
    return `<div class="mini-row"><span class="mini-label">${p.label_zh}</span><div class="mini-track"><div class="mini-fill ${pc}" style="width:0%" data-score="${s}"></div></div><span class="mini-score">${s}%</span></div>`;
  }).join('');
  return `<div class="gallery-card"><img class="gallery-card__img" src="${it.thumbnail}" alt="图"/><div class="gallery-card__body"><span class="gallery-card__badge ${c}">${it.label_zh}</span><p class="gallery-card__conf">置信度：<span>${Math.round(it.confidence)}%</span></p><div class="gallery-card__mini-bars">${mb}</div></div></div>`;
}
function buildReportRow(it){
  const c=it.label==='REAL'?'real':'fake';
  return `<div class="report-row"><span class="report-row__index">图${it.index}</span><span class="report-row__badge ${c}">${it.label_zh}</span><span class="report-row__conf">${Math.round(it.confidence)}%</span><span class="report-row__url">${it.url}</span></div>`;
}

btnUrl.addEventListener('click',async ()=>{
  const u=urlInput.value.trim();
  if(!u){setStatus(urlStatus,'⚠️ 请输入URL','error');return;}
  btnUrl.disabled=true;
  btnUrl.classList.add('loading');
  btnUrl.innerHTML=spinnerHTML()+'检测中…';
  gallery.innerHTML='';
  reportSection.hidden=true;
  try{
    const res=await fetch('/api/detect-url',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({url:u})});
    const d=await res.json();
    if(!res.ok||d.error){setStatus(urlStatus,`❌ ${d.detail||d.message||'请求失败'}`,'error');
    }else{
      setStatus(urlStatus,`✅ 检测 ${d.count} 张`,'success');
      gallery.innerHTML=d.results.map(buildGalleryCard).join('');
      requestAnimationFrame(()=>{requestAnimationFrame(()=>{
        gallery.querySelectorAll('.mini-fill').forEach(x=>x.style.width=x.dataset.score+'%');
      });});
      reportBody.innerHTML=d.results.map(buildReportRow).join('');
      reportSection.hidden=false;
    }
  }catch(e){setStatus(urlStatus,'❌ 网络错误','error');
  }finally{btnUrl.classList.remove('loading');btnUrl.innerHTML='抓取并检测';btnUrl.disabled=false;}
});
urlInput.addEventListener('keydown',e=>{if(e.key==='Enter')btnUrl.click();});

function updateBatchAccess(){
  const raw=localStorage.getItem(AUTH_USER_KEY);
  const role=raw?JSON.parse(raw).role:null;
  const allow=role==='auditor'||role==='admin';
  const hint=$('batchAuthHint');
  if(!raw){hint.hidden=false;hint.querySelector('p').textContent='⚠️ 批量检测需要登录';
  }else if(!allow){hint.hidden=false;hint.querySelector('p').innerHTML='⚠️ 需要 auditor / admin';
  }else{hint.hidden=true;}
}

/* ── Batch detection — WebSocket + drag-drop (方案C 沉浸收缩式) ───── */
let _batchWs=null;
let _batchRunning=false;
let _batchIndexOffset=0;  // 累计索引偏移，多次批次骨架卡片 ID 不冲突

const _ACCEPTED_RE = /\.(jpe?g|png|webp|gif|bmp|pdf|docx?|html?|txt)$/i;

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

  // Folder input — filter out system files
  folderInput.addEventListener('change',()=>{
    const filtered=[...folderInput.files].filter(f=>_ACCEPTED_RE.test(f.name));
    if(filtered.length) handleBatchFiles(filtered);
    folderInput.value='';
  });

  // Cancel button
  $('btnBatchCancel').addEventListener('click',resetBatchZone);
}

async function handleBatchFiles(fileList){
  const raw=localStorage.getItem(AUTH_USER_KEY);
  const role=raw?JSON.parse(raw).role:null;
  if(role!=='auditor'&&role!=='admin'){
    setStatus($('batchStatus'),'⚠️ 需要 auditor / admin 权限','error');
    return;
  }
  if(_batchRunning)return;
  _batchRunning=true;

  const files=[...fileList].filter(f=>_ACCEPTED_RE.test(f.name)||f.type.startsWith('image/')).slice(0,200);
  if(!files.length){_batchRunning=false;return;}

  // 记录本批起始索引偏移（不清空 gallery，实现堆叠）
  const indexOffset=_batchIndexOffset;

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
    setStatus($('batchStatus'),'❌ 初始化失败','error');
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
  const sourceGroups={};  // source filename -> details element

  ws.onmessage=function(e){
    const d=JSON.parse(e.data);
    const g=$('batchGallery');

    if(d.type==='start'){
      totalImages=d.total;
      $('detectLabel').textContent=`检测进度 0/${totalImages}`;

    }else if(d.type==='item'){
      // Insert skeleton card（使用全局偏移确保 ID 唯一）
      const skeletonId='skel-'+(d.index+indexOffset);
      const card=`<div class="gallery-card skeleton-card" id="${skeletonId}"><div class="skeleton-block skeleton-img"></div><div class="gallery-card__body"><div class="skeleton-block skeleton-line"></div><div class="skeleton-block skeleton-line short"></div></div></div>`;

      if(d.source){
        // Grouped under a source file
        let group=sourceGroups[d.source];
        if(!group){
          group=document.createElement('details');
          group.className='batch-source-group';
          group.open=true;
          const summary=document.createElement('summary');
          summary.textContent='📄 '+d.source;
          group.appendChild(summary);
          const inner=document.createElement('div');
          inner.className='gallery batch-source-gallery';
          group.appendChild(inner);
          g.appendChild(group);
          sourceGroups[d.source]=group;
        }
        group.querySelector('.batch-source-gallery').insertAdjacentHTML('beforeend',card);
      }else{
        g.insertAdjacentHTML('beforeend',card);
      }

    }else if(d.type==='result'){
      doneImages++;
      $('detectLabel').textContent=`检测进度 ${doneImages}/${totalImages}`;
      const pct=totalImages?Math.round(doneImages/totalImages*100):0;
      $('detectProgressBar').style.width=pct+'%';

      const r=d.result;
      const cardHtml=buildGalleryCard({...r, index:d.index+indexOffset+1, url:d.filename});
      const skel=document.getElementById('skel-'+(d.index+indexOffset));
      if(skel){
        skel.outerHTML=cardHtml;
      }
      // Animate mini-fill bars
      requestAnimationFrame(()=>{requestAnimationFrame(()=>{
        g.querySelectorAll('.mini-fill').forEach(x=>{
          if(!x.style.width||x.style.width==='0%') x.style.width=x.dataset.score+'%';
        });
      });});

    }else if(d.type==='item_skip'){
      const skipCard=`<div class="gallery-card skip-card"><div class="gallery-card__body"><span class="gallery-card__badge" style="background:#2e3340;color:#8b90a0">⏭️ 跳过</span><p class="gallery-card__conf">${d.filename||''}</p><p style="font-size:0.82rem;color:#8b90a0;margin:4px 0 0">${d.reason||''}</p></div></div>`;
      g.insertAdjacentHTML('beforeend',skipCard);

    }else if(d.type==='complete'){
      $('detectProgressBar').classList.add('complete');
      _batchIndexOffset+=totalImages;  // 累加，供下一批使用
      setStatus($('batchStatus'),`✅ 本批检测完成 ${d.count} 张，累计 ${_batchIndexOffset} 张`,'success');
      _batchRunning=false;
      _batchWs=null;
    }
  };

  ws.onerror=function(){
    if(_batchRunning){
      setStatus($('batchStatus'),'❌ WebSocket 连接失败','error');
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
    $('uploadLabel').textContent='上传完成 ✓';
    $('uploadProgressBar').style.width='100%';
  };
  xhr.onerror=function(){
    setStatus($('batchStatus'),'❌ 上传失败','error');
    resetBatchZone();
  };
  // 等 WebSocket 建立后再发送文件，避免缓存命中时处理完成早于 WS 连接（403 竞态）
  ws.onopen=function(){ xhr.send(fd); };
}

function resetBatchZone(){
  _batchRunning=false;
  _batchIndexOffset=0;  // 点×彻底重置时才清零
  if(_batchWs){try{_batchWs.close();}catch(e){}_batchWs=null;}
  $('batchLanding').hidden=false;
  $('batchBar').hidden=true;
  $('batchGallery').innerHTML='';
  setStatus($('batchStatus'),'','');
  // Reset file inputs
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
  // 1. 标记为误判
  $('btnMarkMisjudge').addEventListener('click',()=>{
    openActionModal(`
      <div style="text-align:center; padding:20px;">
        <div style="font-size:48px; color:#28a745; margin-bottom:16px;">✅</div>
        <h3 style="color:#fff; margin:0 0 8px 0;">操作成功</h3>
        <p style="color:#aaa; margin:0;">已成功标记为误判</p>
        <button class="btn-detect" id="btnActionConfirm" style="margin-top:24px;">确定</button>
      </div>
    `);
    // 绑定确定按钮
    $('btnActionConfirm').addEventListener('click', closeActionModal);
  });

  // 2. 重新检测
  $('btnRedetect').addEventListener('click',()=>{
    openActionModal(`
      <div style="text-align:center; padding:20px;">
        <h3 style="color:#fff; margin:0 0 8px 0;">确认重新检测</h3>
        <p style="color:#aaa; margin:0 0 24px 0;">是否要重新检测当前图片？</p>
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
        <h3 style="color:#fff; margin:0 0 8px 0;">分享链接</h3>
        <p style="color:#aaa; margin:0 0 16px 0;">复制以下链接分享给同事：</p>
        <input type="text" value="${shareUrl}" readonly style="width:100%; padding:10px; border-radius:6px; border:1px solid #444; background:#2a2a2a; color:#fff; text-align:center; margin-bottom:16px;" onclick="this.select();" />
        <button class="btn-detect" id="btnActionConfirm" style="margin-top:8px;">确定</button>
      </div>
    `);
    $('btnActionConfirm').addEventListener('click', closeActionModal);
  });
});