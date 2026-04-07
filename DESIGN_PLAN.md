# AIGI-Holmes 前端设计修改计划

> 生成日期：2026-04-07
> 范围：`static/css/style.css`（1744行）、`templates/index.html`（425行）、`templates/admin.html`

---

## 执行优先顺序

| 步骤 | 文件 | 内容 | 影响规模 |
|------|------|------|---------|
| 1 | style.css | 全站色彩：橙 `#ff6b00` → 蓝 `#2563eb` | ~23处 |
| 2 | style.css | 按钮风格重设计 + 新增CSS类 | ~60行 |
| 3 | style.css | Tab按钮SVG对齐补充 | 2处 |
| 4 | index.html | 全部Emoji → SVG线型图标 | ~20处 |
| 5 | index.html | 内联样式 → CSS类 | ~14处 |
| 6 | admin.html | 深色主题统一 + 色彩替换 + Emoji清除 | ~10处 |

---

## 颜色对照表

| 用途 | 旧色 | 新色 |
|------|------|------|
| 主色 accent | `#ff6b00` | `#2563eb` |
| 主色 hover | `#e05e00` / `#e05f00` | `#1d4ed8` |
| 主色 active tint（深色背景） | `#2a1f14` | `#162040` |
| admin 渐变色1 | `#1e3c72` | 删除渐变 |
| admin 渐变色2 | `#2a5298` | `#1e2028`（平色） |
| admin stat-number | `#2a5298` | `#2563eb` |
| admin page-btn active | `#2a5298` | `#2563eb` |
| admin chart borderColor | `'#2a5298'` | `'#2563eb'` |
| admin chart rgba | `rgba(42,82,152,0.1)` | `rgba(37,99,235,0.1)` |

---

## 步骤 1：style.css 色彩替换（精确位置）

对 style.css 中以下选择器做 `#ff6b00` → `#2563eb` 替换：

| 选择器 | 属性 | 旧值 → 新值 |
|--------|------|------------|
| `.tab-btn.active` | `color` / `border-bottom-color` | `#ff6b00` → `#2563eb` |
| `.drop-zone:hover, .drop-zone.drag-over` | `border-color` | `#ff6b00` → `#2563eb` |
| `.btn-cam-toggle.active` | `border-color` / `color` | `#ff6b00` → `#2563eb` |
| `.btn-cam-toggle.active` | `background` | `#2a1f14` → `#162040` |
| `.progress-bar` | `background` | `#ff6b00` → `#2563eb` |
| `.btn-detect` | `background` | `#ff6b00` → `#2563eb` |
| `.btn-detect:hover:not(:disabled)` | `background` | `#e05e00` → `#1d4ed8` |
| `.btn-secondary:hover` | `border-color` / `color` | `#ff6b00` → `#2563eb` |
| `.url-input:focus` | `border-color` | `#ff6b00` → `#2563eb` |
| `.btn-url` | `background` | `#ff6b00` → `#2563eb` |
| `.btn-url:hover:not(:disabled)` | `background` | `#e05e00` → `#1d4ed8` |
| `.spinner` | `border-top-color` | `#ff6b00` → `#2563eb` |
| `.modal-tab-btn.active` | `color` / `border-bottom-color` | `#ff6b00` → `#2563eb` |
| `.modal-form input:focus` | `border-color` | `#ff6b00` → `#2563eb` |
| `.batch-landing:hover/.drag-over` | `border-color` | `#ff6b00` → `#2563eb` |
| `.role-select:focus` | `border-color` | `#ff6b00` → `#2563eb` |
| `.batch-progress-fill` | `background` | `#ff6b00` → `#2563eb` |
| `.quick-action-btn:hover` | `border-color` | `#ff6b00` → `#2563eb` |
| `.admin-search-input:focus` | `border-color` | `#ff6b00` → `#2563eb` |
| `.admin-filter-select:focus` | `border-color` | `#ff6b00` → `#2563eb` |
| `.admin-tab-btn.active` | `background` | `#ff6b00` → `#2563eb` |
| `.admin-pagination .page-btn.active` | `background` / `border-color` | `#ff6b00` → `#2563eb` |
| `.url-score-fg` / `.url-consistency-fill` | `stroke` / `background` | `#ff6b00` → `#2563eb` |

---

## 步骤 2：style.css 按钮风格重设计

### 2.1 `.btn-secondary` 改为 Outlined 蓝色风格

当前为灰色边框，改为蓝色 outlined：

```css
.btn-secondary {
  background: transparent;
  border: 1px solid #2563eb;
  color: #2563eb;
  border-radius: 8px;
  padding: 8px 20px;
  font-size: 0.9rem;
  cursor: pointer;
  transition: background 0.15s, color 0.15s;
}
.btn-secondary:hover {
  background: #2563eb;
  color: #fff;
}
```

### 2.2 新增 CSS 类（追加到 style.css 末尾）

```css
/* ── Quick Actions Block ─────── */
.quick-actions {
  margin-top: 16px;
  padding: 12px;
  border: 1px solid #2e3340;
  border-radius: 10px;
  background: #1e2028;
}
.quick-actions__title {
  color: #e4e6ed;
  margin: 0 0 10px 0;
  font-size: 0.9rem;
  font-weight: 600;
}
.quick-actions__row {
  display: flex;
  gap: 8px;
}
.btn-misjudge {
  flex: 1; padding: 10px; border: none; border-radius: 6px;
  background: #ca8a04; color: #fff; cursor: pointer;
  font-size: 0.88rem; display: inline-flex;
  align-items: center; gap: 6px; justify-content: center;
  transition: background 0.15s;
}
.btn-misjudge:hover { background: #a16207; }
.btn-redetect {
  flex: 1; padding: 10px; border: none; border-radius: 6px;
  background: #2563eb; color: #fff; cursor: pointer;
  font-size: 0.88rem; display: inline-flex;
  align-items: center; gap: 6px; justify-content: center;
  transition: background 0.15s;
}
.btn-redetect:hover { background: #1d4ed8; }
.btn-share {
  flex: 1; padding: 10px; border: none; border-radius: 6px;
  background: #059669; color: #fff; cursor: pointer;
  font-size: 0.88rem; display: inline-flex;
  align-items: center; gap: 6px; justify-content: center;
  transition: background 0.15s;
}
.btn-share:hover { background: #047857; }
.url-radar-chart { width: 100%; height: 240px; }
.integrate-status-text { font-size: 0.82rem; color: #8b90a0; }
#loginForm, #registerForm, #roleStep1, #roleStep2 {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
```

---

## 步骤 3：style.css Tab 和 Summary SVG 对齐

在现有 `.tab-btn` 和 `.explain-toggle` 规则后追加：

```css
/* SVG 对齐补充 */
.tab-btn { display: inline-flex; align-items: center; gap: 6px; }
.explain-toggle { display: flex; align-items: center; gap: 6px; }
```

---

## 步骤 4：index.html — 全部 Emoji → SVG

### SVG 统一规范
- `viewBox="0 0 24 24"`, `fill="none"`, `stroke="currentColor"`
- `stroke-width="1.5"`, `stroke-linecap="round"`, `stroke-linejoin="round"`
- 风格：Heroicons outline

### 替换清单

**1. Header Logo `🔍`（行15）**
```html
<span class="header-logo">
  <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
    <circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/>
  </svg>
</span>
```

**2. Tab 上传图片 `📤`（行38）**
```html
<button class="tab-btn active" role="tab" data-tab="upload">
  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
    <path d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5"/>
  </svg>
  上传图片
</button>
```

**3. Tab 新闻URL `🌐`（行39）**
```html
<button class="tab-btn" role="tab" data-tab="url">
  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
    <path d="M13.19 8.688a4.5 4.5 0 011.242 7.244l-4.5 4.5a4.5 4.5 0 01-6.364-6.364l1.757-1.757m13.35-.622l1.757-1.757a4.5 4.5 0 00-6.364-6.364l-4.5 4.5a4.5 4.5 0 001.242 7.244"/>
  </svg>
  新闻 URL 检测
</button>
```

**4. Tab 批量检测 `📁`（行40）**
```html
<button class="tab-btn" role="tab" data-tab="batch">
  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
    <path d="M2.25 12.75V12A2.25 2.25 0 014.5 9.75h15A2.25 2.25 0 0121.75 12v.75m-8.69-6.44l-2.12-2.12a1.5 1.5 0 00-1.061-.44H4.5A2.25 2.25 0 002.25 6v12a2.25 2.25 0 002.25 2.25h15A2.25 2.25 0 0021.75 18V9a2.25 2.25 0 00-2.25-2.25h-5.379a1.5 1.5 0 01-1.06-.44z"/>
  </svg>
  批量检测
</button>
```

**5. 热力图按钮 `🌡️`（行61）**
```html
<button class="btn-cam-toggle" id="btnCamToggle" title="显示/隐藏热力图" hidden>
  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
    <path d="M15.362 5.214A8.252 8.252 0 0112 21 8.25 8.25 0 016.038 7.047 8.287 8.287 0 009 9.601a8.983 8.983 0 013.361-6.867 8.21 8.21 0 003 2.48z"/>
    <path d="M12 18a3.75 3.75 0 00.495-7.467 5.99 5.99 0 00-1.925 3.546 5.974 5.974 0 01-2.133-1A3.75 3.75 0 0012 18z"/>
  </svg>
  热力图
</button>
```

**6. 管理后台按钮 `🛡️`（行29）**
```html
<button class="btn-secondary btn-sm" id="btnAdminPanel" hidden title="管理后台">
  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
    <path d="M9 12.75L11.25 15 15 9.75m-3-7.036A11.959 11.959 0 013.598 6 11.99 11.99 0 003 9.749c0 5.592 3.824 10.29 9 11.623 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.571-.598-3.751h-.152c-3.196 0-6.1-1.248-8.25-3.285z"/>
  </svg>
  管理后台
</button>
```

**7. 下载PDF `📄`（行100）**
```html
<button class="btn-report" id="btnDownloadPdf">
  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
    <path d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m.75 12l3 3m0 0l3-3m-3 3v-6m-1.5-9H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z"/>
  </svg>
  PDF
</button>
```

**8. 下载Excel `📊`（行101）**
```html
<button class="btn-report" id="btnDownloadExcel">
  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
    <path d="M3.375 19.5h17.25m-17.25 0a1.125 1.125 0 01-1.125-1.125M3.375 19.5h1.5C5.496 19.5 6 18.996 6 18.375m-3.75.125v-9.75A1.125 1.125 0 013.375 7.5h1.5m0 10.875h1.875a1.125 1.125 0 001.125-1.125V8.625a1.125 1.125 0 00-1.125-1.125H6"/>
  </svg>
  Excel
</button>
```

**9. 快捷操作区（行106-113）— 整块替换**
```html
<div id="quickActions" class="quick-actions" hidden>
  <p class="quick-actions__title">快捷操作</p>
  <div class="quick-actions__row">
    <button id="btnMarkMisjudge" class="btn-misjudge">
      <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
        <path d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z"/>
      </svg>
      标记误判
    </button>
    <button id="btnRedetect" class="btn-redetect">
      <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
        <path d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0l3.181 3.183a8.25 8.25 0 0013.803-3.7M4.031 9.865a8.25 8.25 0 0113.803-3.7l3.181 3.182m0-4.991v4.99"/>
      </svg>
      重新检测
    </button>
    <button id="btnShare" class="btn-share">
      <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
        <path d="M7.217 10.907a2.25 2.25 0 100 2.186m0-2.186c.18.324.283.696.283 1.093s-.103.77-.283 1.093m0-2.186l9.566-5.314m-9.566 7.5l9.566 5.314m0 0a2.25 2.25 0 103.935 2.186 2.25 2.25 0 00-3.935-2.186zm0-12.814a2.25 2.25 0 103.933-2.185 2.25 2.25 0 00-3.933 2.185z"/>
      </svg>
      分享同事
    </button>
  </div>
</div>
```

**10. 检测依据 summary `📝`（行123）**
```html
<summary class="explain-toggle">
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
    <path d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z"/>
  </svg>
  检测依据
</summary>
```

**11. URL 新闻摘要图标 `📰`（行144）**
```html
<span class="url-summary-icon">
  <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
    <path d="M12 7.5h1.5m-1.5 3h1.5m-7.5 3h7.5m-7.5 3h7.5m3-9h3.375c.621 0 1.125.504 1.125 1.125V18a2.25 2.25 0 01-2.25 2.25M16.5 7.5V18a2.25 2.25 0 002.25 2.25M16.5 7.5V4.875c0-.621-.504-1.125-1.125-1.125H4.125C3.504 3.75 3 4.254 3 4.875V18a2.25 2.25 0 002.25 2.25h13.5M6 7.5h3v3H6V7.5z"/>
  </svg>
</span>
```

**12. URL分享按钮 `🔗`（行193）**
```html
<button class="quick-action-btn" id="btnUrlShare">
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
    <path d="M7.217 10.907a2.25 2.25 0 100 2.186m0-2.186c.18.324.283.696.283 1.093s-.103.77-.283 1.093m0-2.186l9.566-5.314m-9.566 7.5l9.566 5.314m0 0a2.25 2.25 0 103.935 2.186 2.25 2.25 0 00-3.935-2.186zm0-12.814a2.25 2.25 0 103.933-2.185 2.25 2.25 0 00-3.933 2.185z"/>
  </svg>
  分享链接
</button>
```

**13. URL回到顶部 `⬆`（行196）**
```html
<button class="quick-action-btn" id="btnUrlScrollTop">
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
    <path d="M4.5 10.5L12 3m0 0l7.5 7.5M12 3v18"/>
  </svg>
  回到顶部
</button>
```

**14. 可视化报告标题 `📊`（行204）**
```html
<h3 class="report-title">
  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
    <path d="M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v6.75C7.5 20.496 6.996 21 6.375 21h-2.25A1.125 1.125 0 013 19.875v-6.75zM9.75 8.625c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125v11.25c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V8.625zM16.5 4.125c0-.621.504-1.125 1.125-1.125h2.25C20.496 3 21 3.504 21 4.125v15.75c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V4.125z"/>
  </svg>
  可视化检测报告
</h3>
```

**15. 导出PDF `📄`（行206）**
```html
<button class="btn-report" id="btnUrlExportPdf">
  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
    <path d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m.75 12l3 3m0 0l3-3m-3 3v-6m-1.5-9H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z"/>
  </svg>
  导出PDF
</button>
```

**16. Admin 弹窗标题 `🛡️`（行356）**
```html
<h2>
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
    <path d="M9 12.75L11.25 15 15 9.75m-3-7.036A11.959 11.959 0 013.598 6 11.99 11.99 0 003 9.749c0 5.592 3.824 10.29 9 11.623 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.571-.598-3.751h-.152c-3.196 0-6.1-1.248-8.25-3.285z"/>
  </svg>
  管理后台
</h2>
```

**17. 仪表盘趋势图标题 `📈`（行370）**
```html
<h3>
  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
    <path d="M2.25 18L9 11.25l4.306 4.307a11.95 11.95 0 015.814-5.519l2.74-1.22m0 0l-5.94-2.28m5.94 2.28l-2.28 5.941"/>
  </svg>
  近7天检测量趋势
</h3>
```

**18. 仪表盘Top5标题 `🔥`（行374）**
```html
<h3>
  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
    <path d="M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v6.75C7.5 20.496 6.996 21 6.375 21h-2.25A1.125 1.125 0 013 19.875v-6.75zM9.75 8.625c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125v11.25c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V8.625zM16.5 4.125c0-.621.504-1.125 1.125-1.125h2.25C20.496 3 21 3.504 21 4.125v15.75c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V4.125z"/>
  </svg>
  Top 5 来源
</h3>
```

**19. 集成训练集按钮 `📦`（行411）**
```html
<button class="admin-btn-action" id="btnIntegrateTraining">
  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
    <path d="M20.25 7.5l-.625 10.632a2.25 2.25 0 01-2.247 2.118H6.622a2.25 2.25 0 01-2.247-2.118L3.75 7.5M10 11.25h4M3.375 7.5h17.25c.621 0 1.125-.504 1.125-1.125v-1.5c0-.621-.504-1.125-1.125-1.125H3.375c-.621 0-1.125.504-1.125 1.125v1.5c0 .621.504 1.125 1.125 1.125z"/>
  </svg>
  集成到训练集
</button>
```

**20. 搜索框 placeholder 中的 Emoji（行381、396）**
```html
<!-- 旧 placeholder="🔍 搜索用户名…" -->
<!-- 新 -->
placeholder="搜索用户名…"
placeholder="搜索来源 URL…"
```

**21. 密码错误提示 `❌`（行326）**
```html
<!-- 旧 -->
<p class="role-error-msg" id="rolePassError" hidden>❌ 密码错误，请重新输入</p>
<!-- 新 -->
<p class="role-error-msg" id="rolePassError" hidden>密码错误，请重新输入</p>
```
在 CSS 中为 `.role-error-msg::before { content: "✕ "; }` 提供视觉符号。

---

## 步骤 5：index.html 内联样式清理

### 5.1 `#quickActions`（行106-113）— 已在步骤4 #9 整块替换

### 5.2 `#urlRadarChart`（行170）
```html
<!-- 旧 -->
<div id="urlRadarChart" style="width:100%;height:240px;"></div>
<!-- 新 -->
<div id="urlRadarChart" class="url-radar-chart"></div>
```

### 5.3 `#integrateStatus`（行412）
```html
<!-- 旧 -->
<span id="integrateStatus" style="font-size:0.82rem;color:#8b90a0;"></span>
<!-- 新 -->
<span id="integrateStatus" class="integrate-status-text"></span>
```

### 5.4 登录/注册表单间距（行304-312）
去掉 `style="margin-top:10px"` / `style="margin-top:14px"` 共4处。
CSS flex+gap 已在步骤2新增类中处理（`#loginForm, #registerForm { gap: 10px; }`）。

### 5.5 角色管理表单间距（行325、331、336）
去掉 `style="margin-top:14px"` / `style="margin-top:10px"` 共3处。
依赖步骤2中 `#roleStep1, #roleStep2 { gap: 10px; }` 处理。

---

## 步骤 6：admin.html 修改（内联 `<style>` 块内）

### 6.1 Header 背景渐变 → 纯深色
旧：`background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);`
新：`background: #1e2028;`

### 6.2 `.nav a.active` hover 背景
旧：`background: rgba(255,255,255,0.2);`
新：`background: rgba(37,99,235,0.25); color: #60a5fa;`

### 6.3 `.stat-number` 颜色
旧：`color: #2a5298;`
新：`color: #2563eb;`

### 6.4 分页 `.page-btn.active`
旧：`background: #2a5298; border-color: #2a5298;`
新：`background: #2563eb; border-color: #2563eb;`

### 6.5 Chart.js 颜色（JS 内）
旧：`borderColor: '#2a5298'` / `backgroundColor: 'rgba(42, 82, 152, 0.1)'`
新：`borderColor: '#2563eb'` / `backgroundColor: 'rgba(37, 99, 235, 0.1)'`

### 6.6 移除标题 Emoji
- `📊 AIGI-Holmes 后台管理` → `AIGI-Holmes 后台管理`
- `📈 近7天检测量趋势` → `近7天检测量趋势`
- `🔥 造假率 Top 5 来源` → `Top 5 来源`
- `👥 用户列表` → `用户列表`
- `📋 检测记录` → `检测记录`

---

## 变更影响汇总

| 文件 | 类型 | 数量 |
|------|------|------|
| style.css | 色彩替换 | 23处 |
| style.css | 按钮重设计 + 新增类 | ~60行 |
| style.css | Tab/Summary flex对齐 | 2处 |
| index.html | Emoji → SVG | 21处 |
| index.html | inline style 清理 | 10处 |
| admin.html | 色彩/渐变/Emoji | 10处 |

---

## 注意事项

1. **语义颜色保留**：`fake: #ef4444`（红）和 `real: #22c55e`（绿）不在替换范围内
2. **`.batch-progress-fill--detect`**：当前已是 `#3b82f6`，可统一改为 `#2563eb`
3. **卡通图片**：经代码核查，当前 UI HTML 中无静态 AI 卡通图片嵌入，图片全部为用户上传或 API 返回的动态内容。用户提及的"AI味"主要来自 Emoji 图标和橙色配色，已通过本方案解决。
4. **app.js 不需要修改**：所有变更仅涉及 CSS 和 HTML 文件
