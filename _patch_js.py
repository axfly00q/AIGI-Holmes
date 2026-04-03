"""Patch static/js/app.js with auth headers and report download logic."""
import re, sys

src = open('static/js/app.js', encoding='utf-8').read()

# ── 1. Add auth headers to /api/detect fetch ─────────────────────────────────
old1 = "    const resp = await fetch('/api/detect', { method: 'POST', body: fd });\n    const data = await resp.json();\n\n    if (!resp.ok || data.error) {\n      setStatus(uploadStatus, '❌ ' + (data.error || '检测失败'), 'error');\n    } else {\n      renderResult(data);\n      setStatus(uploadStatus, '✅ 检测完成', 'success');\n    }"
new1 = "    const resp = await fetch('/api/detect', { method: 'POST', body: fd, headers: authHeaders() });\n    const data = await resp.json();\n\n    if (!resp.ok || data.error) {\n      setStatus(uploadStatus, '❌ ' + (data.error || '检测失败'), 'error');\n    } else {\n      renderResult(data);\n      setStatus(uploadStatus, '✅ 检测完成', 'success');\n      const rd = $('reportDownload');\n      if (data.detection_id && getToken()) {\n        rd.hidden = false;\n        $('btnDownloadPdf').onclick   = () => downloadReport(data.detection_id, 'pdf');\n        $('btnDownloadExcel').onclick = () => downloadReport(data.detection_id, 'excel');\n      } else {\n        rd.hidden = true;\n      }\n    }"

if old1 in src:
    src = src.replace(old1, new1, 1)
    print("✅ Patch 1 applied: /api/detect auth + report download")
else:
    print("❌ Patch 1 NOT found – check whitespace")
    sys.exit(1)

# ── 2. Hide reportDownload in clearUpload() ───────────────────────────────────
# Find clearUpload and add $('reportDownload').hidden = true; before hideResultCard
old2 = "function clearUpload() {\n  selectedFile = null;\n  uploadPreview.src = '';\n  uploadPreview.hidden = true;\n  uploadFileName.textContent = '';\n  uploadStatus.textContent = '';\n  uploadStatus.className = 'status-msg';\n  hideResultCard();\n}"
new2 = "function clearUpload() {\n  selectedFile = null;\n  uploadPreview.src = '';\n  uploadPreview.hidden = true;\n  uploadFileName.textContent = '';\n  uploadStatus.textContent = '';\n  uploadStatus.className = 'status-msg';\n  $('reportDownload').hidden = true;\n  hideResultCard();\n}"

if old2 in src:
    src = src.replace(old2, new2, 1)
    print("✅ Patch 2 applied: clearUpload hides reportDownload")
else:
    # Try without the hideResultCard line
    print("ℹ️  Patch 2 exact block not found, trying looser match...")
    m = re.search(r'(function clearUpload\(\) \{[^}]{10,200}?uploadStatus\.className[^\n]*\n)(  hideResultCard\(\);)', src, re.DOTALL)
    if m:
        src = src[:m.start()] + m.group(0).replace('  hideResultCard();', "  $('reportDownload').hidden = true;\n  hideResultCard();", 1) + src[m.end():]
        print("✅ Patch 2 applied (regex)")
    else:
        print("❌ Patch 2 NOT found")

open('static/js/app.js', 'w', encoding='utf-8').write(src)
print("Done — file saved.")
