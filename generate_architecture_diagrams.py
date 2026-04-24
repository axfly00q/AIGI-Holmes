"""
AIGI-Holmes 多维度架构图生成脚本
生成以下图表:
  1. 前端实现逻辑图（宏观）
  2. 前端实现逻辑图（微观 - 单图检测流程）
  3. 后端算法设计图（宏观）
  4. 后端算法设计图（微观 - 检测算法流水线）
  5. 项目全局数据流图
"""

import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import matplotlib.patheffects as pe
import numpy as np

# ─────────────────────────────────────────────
# 全局配色（浅色系，白色背景）
# ─────────────────────────────────────────────
COLORS = {
    # 功能层
    "user":        "#D0E8FF",   # 浅蓝 - 用户
    "frontend":    "#E8F5E9",   # 浅绿 - 前端
    "api":         "#FFF3E0",   # 浅橙 - API网关
    "backend":     "#EDE7F6",   # 浅紫 - 后端服务
    "model":       "#FCE4EC",   # 浅粉 - AI模型
    "db":          "#E3F2FD",   # 浅蓝2 - 数据库
    "cache":       "#F3E5F5",   # 浅紫2 - 缓存
    "auth":        "#E8EAF6",   # 蓝紫 - 认证
    "xai":         "#E0F2F1",   # 青绿 - XAI解释
    "analyzer":    "#FFF8E1",   # 浅黄 - 分析器
    "report":      "#EFEBE9",   # 浅棕 - 报告
    "websocket":   "#E1F5FE",   # 天蓝 - WebSocket

    # 边框
    "border_blue":   "#90CAF9",
    "border_green":  "#A5D6A7",
    "border_orange": "#FFCC80",
    "border_purple": "#CE93D8",
    "border_pink":   "#F48FB1",
    "border_teal":   "#80CBC4",
    "border_amber":  "#FFE082",
    "border_brown":  "#BCAAA4",
    "border_sky":    "#81D4FA",
    "border_indigo": "#9FA8DA",

    # 箭头/线条
    "arrow": "#607D8B",
    "arrow_light": "#90A4AE",
}

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "architecture_diagrams")
os.makedirs(OUTPUT_DIR, exist_ok=True)


def save(fig, name):
    path = os.path.join(OUTPUT_DIR, name)
    fig.savefig(path, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"  ✓ 已保存: {path}")


def fancy_box(ax, x, y, w, h, text, facecolor, edgecolor,
              fontsize=9, text_color="#263238", radius=0.02,
              bold=False, multiline=False):
    """绘制圆角矩形 + 居中文字"""
    box = FancyBboxPatch(
        (x, y), w, h,
        boxstyle=f"round,pad=0.01,rounding_size={radius}",
        facecolor=facecolor, edgecolor=edgecolor, linewidth=1.4, zorder=3
    )
    ax.add_patch(box)
    weight = "bold" if bold else "normal"
    va = "center"
    ax.text(x + w / 2, y + h / 2, text,
            ha="center", va=va, fontsize=fontsize,
            color=text_color, weight=weight, zorder=4,
            multialignment="center",
            wrap=True)
    return box


def arrow(ax, x1, y1, x2, y2, color="#607D8B", lw=1.5, style="->", label=""):
    ax.annotate("",
                xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle=style, color=color,
                                lw=lw, connectionstyle="arc3,rad=0.0"),
                zorder=5)
    if label:
        mx, my = (x1 + x2) / 2, (y1 + y2) / 2
        ax.text(mx, my, label, fontsize=7, color=color,
                ha="center", va="bottom", zorder=6)


def arrow_curve(ax, x1, y1, x2, y2, rad=0.2, color="#607D8B", lw=1.5, label=""):
    ax.annotate("",
                xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle="->", color=color,
                                lw=lw,
                                connectionstyle=f"arc3,rad={rad}"),
                zorder=5)
    if label:
        mx, my = (x1 + x2) / 2 + rad * 0.5, (y1 + y2) / 2 + abs(rad) * 0.5
        ax.text(mx, my, label, fontsize=7, color=color,
                ha="center", va="bottom", zorder=6)


def section_bg(ax, x, y, w, h, color, alpha=0.12, label="", label_fs=9):
    rect = plt.Rectangle((x, y), w, h, facecolor=color, edgecolor=color,
                          alpha=alpha, zorder=1, linewidth=0)
    ax.add_patch(rect)
    if label:
        ax.text(x + 0.01, y + h - 0.02, label,
                fontsize=label_fs, color=color, alpha=0.85,
                va="top", weight="bold", zorder=2)


# ══════════════════════════════════════════════════════════
#  图1: 前端实现逻辑图（宏观视角）
# ══════════════════════════════════════════════════════════
def draw_frontend_macro():
    fig, ax = plt.subplots(figsize=(18, 12))
    ax.set_xlim(0, 18)
    ax.set_ylim(0, 12)
    ax.axis("off")
    ax.set_facecolor("white")
    fig.patch.set_facecolor("white")

    ax.text(9, 11.6, "AIGI-Holmes  前端实现逻辑图（宏观）",
            ha="center", va="top", fontsize=15, weight="bold", color="#1A237E")
    ax.text(9, 11.25, "HTML + 原生 JavaScript · 无框架 · REST API 通信",
            ha="center", va="top", fontsize=9, color="#607D8B")

    # ── 分区背景 ──
    section_bg(ax, 0.2, 0.3, 3.2, 10.5, "#42A5F5", label="  用户层")
    section_bg(ax, 3.7, 0.3, 10.4, 10.5, "#66BB6A", label="  前端页面层 (static/js/app.js  ~1000行)")
    section_bg(ax, 14.4, 0.3, 3.4, 10.5, "#FFA726", label="  后端API层")

    # ─── 用户操作节点 ───
    users = [
        (0.4, 8.8, "游客\nGuest"),
        (0.4, 6.8, "普通用户\nUser"),
        (0.4, 4.8, "审计员\nAuditor"),
        (0.4, 2.8, "管理员\nAdmin"),
    ]
    for (ux, uy, ut) in users:
        fancy_box(ax, ux, uy, 2.8, 1.1, ut,
                  COLORS["user"], COLORS["border_blue"], fontsize=9, bold=True)

    # ─── 认证区 ───
    fancy_box(ax, 3.9, 9.2, 3.0, 0.85, "登录 / 注册\nLogin · Register",
              COLORS["auth"], COLORS["border_indigo"], fontsize=8.5)
    fancy_box(ax, 7.2, 9.2, 3.0, 0.85, "JWT令牌存储\n(localStorage)",
              COLORS["auth"], COLORS["border_indigo"], fontsize=8.5)
    fancy_box(ax, 10.5, 9.2, 3.2, 0.85, "权限拦截器\nrequire_role()",
              COLORS["auth"], COLORS["border_indigo"], fontsize=8.5)

    # ─── 三大功能Tab ───
    tabs = [
        (3.9, 7.2, 9.8, 1.5, "Tab 1：单图检测\n上传图片 → ResNet50推理 → 置信度 + Grad-CAM热力图 + XAI说明",
         COLORS["frontend"], COLORS["border_green"]),
        (3.9, 5.3, 9.8, 1.5, "Tab 2：新闻URL检测\n输入URL → 抓取页面图片 → 批量推理 → CLIP分类\n→ 六维度综合评分 + Bing搜图验证",
         COLORS["analyzer"], COLORS["border_amber"]),
        (3.9, 3.4, 9.8, 1.5, "Tab 3：批量检测（Auditor/Admin）\n拖拽文件夹/多文件 → WebSocket连接\n→ XHR上传+进度条 → 结果卡片瀑布流",
         COLORS["websocket"], COLORS["border_sky"]),
    ]
    for (tx, ty, tw, th, tt, tc, tec) in tabs:
        fancy_box(ax, tx, ty, tw, th, tt, tc, tec, fontsize=8.5)

    # ─── 通用UI组件 ───
    ui_comps = [
        (3.9,  2.0, "历史记录\n(History Tab)"),
        (5.55, 2.0, "搜索功能\n(Search Tab)"),
        (7.2,  2.0, "报告导出\nPDF/CSV"),
        (8.85, 2.0, "反馈提交\n(Feedback)"),
        (10.5, 2.0, "管理面板\n(Admin Tab)"),
        (12.15,2.0, "暗色模式\n切换"),
    ]
    for (cx, cy, ct) in ui_comps:
        fancy_box(ax, cx, cy, 1.5, 0.85, ct,
                  COLORS["report"], COLORS["border_brown"], fontsize=7.5)

    # ─── 状态管理 ───
    fancy_box(ax, 3.9, 0.7, 9.8, 0.9,
              "全局状态：currentUser · authToken · activeTab · detectionHistory",
              COLORS["cache"], COLORS["border_purple"], fontsize=8)

    # ─── 后端API节点 ───
    apis = [
        (14.6, 9.2,  "POST /api/auth\n/register · /login · /refresh"),
        (14.6, 7.55, "POST /api/detect\n单图检测"),
        (14.6, 6.2,  "POST /api/detect-url\nURL检测"),
        (14.6, 4.85, "POST /api/detect-batch\n批量检测"),
        (14.6, 3.5,  "WS /api/ws/batch\nWebSocket"),
        (14.6, 2.15, "GET  /api/report\n报告 · 历史 · 搜索"),
        (14.6, 0.8,  "PATCH /api/auth/admin\n角色管理"),
    ]
    for (ax2, ay2, at) in apis:
        fancy_box(ax, ax2, ay2, 3.0, 1.0, at,
                  COLORS["api"], COLORS["border_orange"], fontsize=7.5)

    # ─── 连接箭头 ───
    # 用户 → 认证
    for uy in [9.35, 7.35, 5.35, 3.35]:
        arrow(ax, 3.2, uy, 3.9, 9.65, color="#78909C", lw=1.2)

    # 认证 → JWT
    arrow(ax, 6.9, 9.65, 7.2, 9.65, color=COLORS["arrow"])
    arrow(ax, 10.2, 9.65, 10.5, 9.65, color=COLORS["arrow"])

    # Tab → API
    arrow(ax, 13.7, 7.95, 14.6, 8.0, color=COLORS["arrow"])
    arrow(ax, 13.7, 6.05, 14.6, 6.7, color=COLORS["arrow"])
    arrow(ax, 13.7, 4.15, 14.6, 5.35, color=COLORS["arrow"])
    arrow(ax, 13.7, 4.15, 14.6, 4.0, color=COLORS["arrow"])

    # 状态 ↔ Tab
    for tx in [5.0, 8.8, 12.0]:
        arrow(ax, tx, 1.6, tx, 2.0, color=COLORS["arrow_light"], lw=1.0)

    # 图例
    legend_items = [
        (mpatches.Patch(facecolor=COLORS["user"],     edgecolor=COLORS["border_blue"]),   "用户角色"),
        (mpatches.Patch(facecolor=COLORS["auth"],     edgecolor=COLORS["border_indigo"]), "认证 / 权限"),
        (mpatches.Patch(facecolor=COLORS["frontend"], edgecolor=COLORS["border_green"]),  "核心检测功能"),
        (mpatches.Patch(facecolor=COLORS["analyzer"], edgecolor=COLORS["border_amber"]),  "URL分析功能"),
        (mpatches.Patch(facecolor=COLORS["websocket"],edgecolor=COLORS["border_sky"]),    "批量检测/WS"),
        (mpatches.Patch(facecolor=COLORS["api"],      edgecolor=COLORS["border_orange"]), "后端API端点"),
    ]
    handles, labels = zip(*legend_items)
    ax.legend(handles, labels, loc="lower right", fontsize=8,
              framealpha=0.9, edgecolor="#CFD8DC")

    save(fig, "01_frontend_macro.png")


# ══════════════════════════════════════════════════════════
#  图2: 前端实现逻辑图（微观 - 单图检测 & 批量检测交互流程）
# ══════════════════════════════════════════════════════════
def draw_frontend_micro():
    fig, axes = plt.subplots(1, 2, figsize=(20, 13))
    fig.patch.set_facecolor("white")
    fig.suptitle("AIGI-Holmes  前端实现逻辑图（微观）", fontsize=14,
                 weight="bold", color="#1A237E", y=0.98)

    # ──────────────────────────────────
    # 左图: 单图检测交互流程
    # ──────────────────────────────────
    ax = axes[0]
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 13)
    ax.axis("off")
    ax.set_facecolor("white")
    ax.set_title("单图检测交互流程 (app.js)", fontsize=11,
                 weight="bold", color="#2E7D32", pad=8)

    steps_left = [
        (2.5, 11.5, "用户拖拽/选择图片\ndropzone · input[type=file]",
         COLORS["user"], COLORS["border_blue"]),
        (2.5, 10.0, "文件格式验证\nJPEG / PNG / WebP / GIF / BMP",
         COLORS["frontend"], COLORS["border_green"]),
        (2.5,  8.5, "预览显示\nFileReader → img.src",
         COLORS["frontend"], COLORS["border_green"]),
        (2.5,  7.0, "调用 handleDetect()\n构建 FormData · POST /api/detect",
         COLORS["api"], COLORS["border_orange"]),
        (2.5,  5.5, "Loading动画\n禁用按钮，显示旋转图标",
         COLORS["frontend"], COLORS["border_green"]),
        (2.5,  4.0, "接收 JSON 响应\n{ label, confidence, probs,\nexplanation, cam_image, detection_id }",
         COLORS["backend"], COLORS["border_purple"]),
        (2.5,  2.5, "渲染结果\n标签徽章 · 置信度环形图\nGrad-CAM热力图 · XAI说明卡",
         COLORS["model"], COLORS["border_pink"]),
        (2.5,  1.0, "写入 detectionHistory[]\n更新历史记录Tab",
         COLORS["cache"], COLORS["border_purple"]),
    ]
    for i, (sx, sy, st, sc, sec) in enumerate(steps_left):
        fancy_box(ax, sx - 2.2, sy, 4.4, 1.1, st, sc, sec, fontsize=8)
        if i < len(steps_left) - 1:
            arrow(ax, sx, sy, sx, steps_left[i + 1][1] + 1.1,
                  color=COLORS["arrow"], lw=1.6)

    # 错误分支
    fancy_box(ax, 6.0, 7.0, 3.5, 1.1,
              "错误处理\n网络/格式错误 → showError()\n清除结果区",
              "#FFEBEE", "#EF9A9A", fontsize=7.5)
    arrow(ax, 4.7, 7.55, 6.0, 7.55, color="#EF5350", lw=1.2, label="失败")

    ax.text(0.3, 0.3, "① 用户交互层  ② DOM操作层  ③ Fetch API层",
            fontsize=7, color="#607D8B")

    # ──────────────────────────────────
    # 右图: 批量检测交互流程
    # ──────────────────────────────────
    ax2 = axes[1]
    ax2.set_xlim(0, 10)
    ax2.set_ylim(0, 13)
    ax2.axis("off")
    ax2.set_facecolor("white")
    ax2.set_title("批量检测交互流程 (WebSocket + XHR)", fontsize=11,
                  weight="bold", color="#1565C0", pad=8)

    steps_right = [
        (2.5, 11.5, "拖拽文件夹 / 选择多文件\ndropzone · folderInput(webkitdirectory)",
         COLORS["user"], COLORS["border_blue"]),
        (2.5, 10.0, "权限检查 updateBatchAccess()\n需 auditor 或 admin 角色",
         COLORS["auth"], COLORS["border_indigo"]),
        (2.5,  8.5, "文件过滤 _ACCEPTED_RE\n.jpg/.png/.webp/.pdf/.docx/.html/.txt",
         COLORS["frontend"], COLORS["border_green"]),
        (2.5,  7.0, "POST /api/detect-batch-init\n获取 jobId",
         COLORS["api"], COLORS["border_orange"]),
        (2.5,  5.5, "建立 WebSocket\nws://…/api/ws/batch/{jobId}",
         COLORS["websocket"], COLORS["border_sky"]),
        (2.5,  4.0, "XHR上传文件 + 上传进度条\nxhr.upload.onprogress → uploadProgressBar",
         COLORS["api"], COLORS["border_orange"]),
        (2.5,  2.5, "WS消息处理\nstart/item/result/item_skip/complete",
         COLORS["websocket"], COLORS["border_sky"]),
        (2.5,  1.0, "渲染结果卡片\nbatchGallery 网格 · skeleton → 真实卡片",
         COLORS["model"], COLORS["border_pink"]),
    ]
    for i, (sx, sy, st, sc, sec) in enumerate(steps_right):
        fancy_box(ax2, sx - 2.2, sy, 4.4, 1.1, st, sc, sec, fontsize=8)
        if i < len(steps_right) - 1:
            arrow(ax2, sx, sy, sx, steps_right[i + 1][1] + 1.1,
                  color=COLORS["arrow"], lw=1.6)

    # WS消息类型说明框
    ws_detail = (
        "WebSocket 消息类型:\n"
        "  start      → 初始化，设 totalImages\n"
        "  item       → 准备处理第N项\n"
        "  result     → 单项结果，更新进度条\n"
        "  item_skip  → 跳过（格式不支持）\n"
        "  complete   → 全部完成"
    )
    fancy_box(ax2, 5.0, 4.5, 4.5, 3.2, ws_detail,
              COLORS["websocket"], COLORS["border_sky"], fontsize=7.5)
    arrow(ax2, 4.7, 5.7, 5.0, 5.7, color=COLORS["border_sky"], lw=1.2)

    ax2.text(0.3, 0.3, "① 文件处理层  ② WebSocket层  ③ 进度可视化层",
             fontsize=7, color="#607D8B")

    plt.tight_layout(rect=[0, 0, 1, 0.96])
    save(fig, "02_frontend_micro.png")


# ══════════════════════════════════════════════════════════
#  图3: 后端算法设计图（宏观 - 服务分层架构）
# ══════════════════════════════════════════════════════════
def draw_backend_macro():
    fig, ax = plt.subplots(figsize=(18, 13))
    ax.set_xlim(0, 18)
    ax.set_ylim(0, 13)
    ax.axis("off")
    ax.set_facecolor("white")
    fig.patch.set_facecolor("white")

    ax.text(9, 12.65, "AIGI-Holmes  后端算法设计图（宏观）",
            ha="center", va="top", fontsize=15, weight="bold", color="#1A237E")
    ax.text(9, 12.25, "FastAPI · SQLAlchemy · Redis · ResNet50 · CLIP ViT-B/32",
            ha="center", va="top", fontsize=9, color="#607D8B")

    # ═══ 分区 ═══
    section_bg(ax, 0.2, 11.2, 17.6, 1.3, "#42A5F5", label="  API 网关层 (CORS · JWT验证 · 限速)")
    section_bg(ax, 0.2,  8.5, 17.6, 2.4, "#66BB6A", label="  路由层 (backend/routers/)")
    section_bg(ax, 0.2,  4.8, 17.6, 3.4, "#AB47BC", label="  服务层 / 算法层")
    section_bg(ax, 0.2,  0.3, 17.6, 4.2, "#FFA726", label="  数据层")

    # ─── API 网关 ───
    gw_items = [
        (0.5,  11.4, "FastAPI App\nmain.py"),
        (3.5,  11.4, "CORS\nMiddleware"),
        (6.5,  11.4, "JWT Auth\nDependency"),
        (9.5,  11.4, "Rate Limit\n(Redis)"),
        (12.5, 11.4, "静态文件\nStaticFiles"),
        (15.0, 11.4, "Jinja2\nTemplates"),
    ]
    for (gx, gy, gt) in gw_items:
        fancy_box(ax, gx, gy, 2.6, 0.85, gt,
                  COLORS["api"], COLORS["border_orange"], fontsize=8)

    # ─── 路由层 ───
    routes = [
        (0.4,  8.8, "auth.py\n/register /login /refresh\n/admin/users"),
        (2.9,  8.8, "detect.py\n/detect /detect-url\n/detect-batch"),
        (5.4,  8.8, "ws.py\n/ws/batch/{jobId}\nWebSocket"),
        (7.9,  8.8, "report.py\n/report/{id}\n/export"),
        (10.4, 8.8, "history.py\n/history\n(分页)"),
        (12.9, 8.8, "search.py\n/search\n全文搜索"),
        (15.4, 8.8, "feedback.py\nadmin.py\n附加功能"),
    ]
    for (rx, ry, rt) in routes:
        fancy_box(ax, rx, ry, 2.2, 1.6, rt,
                  COLORS["frontend"], COLORS["border_green"], fontsize=7.5)

    # ─── 服务/算法层 ───
    # AI模型组
    fancy_box(ax, 0.4, 5.1, 3.8, 2.9,
              "AI 推理引擎\n─────────────\nResNet50 (微调)\nFAKE vs REAL\n─────────────\nCLIP ViT-B/32\n图文一致性·内容分类",
              COLORS["model"], COLORS["border_pink"], fontsize=8, bold=False)

    # 分析器组
    fancy_box(ax, 4.5, 5.1, 4.0, 2.9,
              "六维度分析器\n─────────────\n人脸深伪检测  (CLIP+OpenCV)\n频率域分析    (FFT/PSD)\n边缘伪迹检测  (Laplacian)\n印章/签名检测 (HOG+CLIP)\nLogo检测     (CLIP零样本)\n图文一致性    (CLIP)",
              COLORS["analyzer"], COLORS["border_amber"], fontsize=7.5)

    # 综合评分
    fancy_box(ax, 8.8, 5.1, 3.2, 2.9,
              "综合评分引擎\ncomposite.py\n─────────────\n真实性    ×0.25\n置信度    ×0.20\n一致性    ×0.20\n印章      ×0.15\n频率域    ×0.10\n边缘      ×0.10",
              COLORS["backend"], COLORS["border_purple"], fontsize=7.5)

    # XAI
    fancy_box(ax, 12.3, 5.1, 2.8, 2.9,
              "XAI 解释引擎\n─────────────\nGrad-CAM\n热力图可视化\n─────────────\nLIME\nSHAP\n文本解释",
              COLORS["xai"], COLORS["border_teal"], fontsize=7.5)

    # 搜索/缓存
    fancy_box(ax, 15.4, 5.1, 2.2, 1.3,
              "反向图片搜索\nBing · Serper\nAPI",
              COLORS["cache"], COLORS["border_purple"], fontsize=7.5)
    fancy_box(ax, 15.4, 6.7, 2.2, 1.3,
              "Auth 模块\nbcrypt 哈希\nJWT令牌",
              COLORS["auth"], COLORS["border_indigo"], fontsize=7.5)

    # ─── 数据层 ───
    db_items = [
        (0.4,  2.4, "SQLite + SQLAlchemy\n异步引擎\naiosqlite",
         COLORS["db"], COLORS["border_blue"]),
        (3.8,  2.4, "DetectionRecord\n检测记录表",
         COLORS["db"], COLORS["border_blue"]),
        (6.8,  2.4, "User 表\n角色: guest/user\nauditor/admin",
         COLORS["db"], COLORS["border_blue"]),
        (9.8,  2.4, "FeedbackRecord\n用户反馈表",
         COLORS["db"], COLORS["border_blue"]),
        (12.8, 2.4, "Redis Cache\nTTL=300s\n哈希去重",
         COLORS["cache"], COLORS["border_purple"]),
        (15.4, 2.4, "JobStore\n批量任务\n状态管理",
         COLORS["report"], COLORS["border_brown"]),
    ]
    for (dx, dy, dt, dc, dec) in db_items:
        fancy_box(ax, dx, dy, 2.8, 1.5, dt, dc, dec, fontsize=7.5)

    # ─── 模型文件 ───
    fancy_box(ax, 0.4, 0.4, 5.0, 1.7,
              "模型权重文件\nfinetuned_fake_real_resnet50.pth\nSHA-256 指纹版本验证  MODEL_VERSION[:8]",
              COLORS["model"], COLORS["border_pink"], fontsize=8)
    fancy_box(ax, 5.7, 0.4, 4.5, 1.7,
              "CLIP 权重\nViT-B/32 (~350MB)\n懒加载 + 线程池预热\nCUDA / CPU 自动选择",
              COLORS["model"], COLORS["border_pink"], fontsize=8)
    fancy_box(ax, 10.5, 0.4, 4.0, 1.7,
              "Report 生成\nbackend/report/\nPDF · CSV · JSON 导出",
              COLORS["report"], COLORS["border_brown"], fontsize=8)
    fancy_box(ax, 14.8, 0.4, 3.0, 1.7,
              "Text 检测\nbackend/text_detect.py\nLLM 文本真实性\n分析 + XAI",
              COLORS["xai"], COLORS["border_teal"], fontsize=8)

    # ─── 层间连接 ───
    # 网关 → 路由
    for rx in [1.5, 4.0, 6.5, 9.0, 11.5, 14.0, 16.5]:
        arrow(ax, rx, 11.4, rx, 10.4, color=COLORS["arrow"], lw=1.3)

    # 路由 → 服务
    arrow(ax, 2.0, 8.8, 2.3, 7.0, color=COLORS["arrow"])
    arrow(ax, 4.0, 8.8, 4.0, 7.0, color=COLORS["arrow"])  # detect → ResNet50
    arrow(ax, 4.0, 8.8, 6.5, 7.0, color=COLORS["arrow"])  # detect → 分析器
    arrow(ax, 4.0, 8.8, 10.4, 7.0, color=COLORS["arrow_light"])  # detect → XAI
    arrow(ax, 8.0, 8.8, 10.4, 7.0, color=COLORS["arrow"])  # report → XAI
    arrow(ax, 6.5, 8.8, 10.4, 7.0, color=COLORS["arrow_light"])
    arrow(ax, 11.0, 8.8, 13.7, 7.0, color=COLORS["arrow"])
    arrow(ax, 13.5, 8.8, 16.5, 7.0, color=COLORS["arrow"])

    # 分析器 → 综合评分
    arrow(ax, 8.5, 6.5, 8.8, 6.5, color=COLORS["arrow"])

    # 服务 → 数据层
    for sx in [2.3, 5.5, 10.4, 14.7]:
        arrow(ax, sx, 5.1, sx, 3.9, color=COLORS["arrow_light"], lw=1.2)

    save(fig, "03_backend_macro.png")


# ══════════════════════════════════════════════════════════
#  图4: 后端算法设计图（微观 - 检测流水线）
# ══════════════════════════════════════════════════════════
def draw_backend_micro():
    fig, ax = plt.subplots(figsize=(20, 14))
    ax.set_xlim(0, 20)
    ax.set_ylim(0, 14)
    ax.axis("off")
    ax.set_facecolor("white")
    fig.patch.set_facecolor("white")

    ax.text(10, 13.65, "AIGI-Holmes  后端算法设计图（微观 — 检测流水线）",
            ha="center", va="top", fontsize=14, weight="bold", color="#1A237E")
    ax.text(10, 13.25, "单次图像检测的完整算法链路  ·  detect.py + backend/analyzers/ + backend/xai/",
            ha="center", va="top", fontsize=9, color="#607D8B")

    # ─── 第0层: 输入 ───
    section_bg(ax, 0.2, 12.0, 19.6, 1.3, "#42A5F5", alpha=0.1, label="  输入层", label_fs=8)
    fancy_box(ax, 1.0, 12.1, 3.5, 0.95, "原始图像\nPOST /api/detect\nUploadFile",
              COLORS["user"], COLORS["border_blue"], fontsize=8)
    fancy_box(ax, 5.0, 12.1, 3.5, 0.95, "图像URL\nPOST /api/detect-url\nasync_download_image",
              COLORS["user"], COLORS["border_blue"], fontsize=8)
    fancy_box(ax, 9.0, 12.1, 3.5, 0.95, "批量文件\nWebSocket jobId\nXHR multipart",
              COLORS["user"], COLORS["border_blue"], fontsize=8)
    fancy_box(ax, 13.0, 12.1, 3.5, 0.95, "Redis哈希缓存\nSHA-256 → 命中返回\nTTL 300s",
              COLORS["cache"], COLORS["border_purple"], fontsize=8)

    arrow(ax, 2.75, 12.1, 2.75, 10.5 + 1.25, color=COLORS["arrow"])
    arrow(ax, 6.75, 12.1, 2.75, 10.5 + 1.25, color=COLORS["arrow"])
    arrow(ax, 10.75, 12.1, 2.75, 10.5 + 1.25, color=COLORS["arrow"])
    arrow(ax, 14.75, 12.1, 14.75, 10.5 + 1.25, color=COLORS["border_purple"], lw=1.2,
          label="缓存命中")

    # ─── 第1层: 预处理 ───
    section_bg(ax, 0.2, 9.8, 19.6, 1.5, "#66BB6A", alpha=0.1, label="  预处理层", label_fs=8)
    preproc = [
        (0.5,  10.0, "PIL 格式验证\n图像完整性检查"),
        (3.5,  10.0, "Resize 224×224\ntorchvision.transforms"),
        (6.5,  10.0, "归一化\nmean=[0.485,0.456,0.406]\nstd=[0.229,0.224,0.225]"),
        (9.8,  10.0, "ToTensor\n→ torch.Tensor\n[1, 3, 224, 224]"),
        (13.0, 10.0, "SHA-256 哈希\n缓存键计算"),
    ]
    for i, (px, py, pt) in enumerate(preproc):
        fancy_box(ax, px, py, 2.8, 1.2, pt,
                  COLORS["frontend"], COLORS["border_green"], fontsize=7.5)
        if i < len(preproc) - 1:
            arrow(ax, px + 2.8, py + 0.6, preproc[i + 1][0], py + 0.6,
                  color=COLORS["arrow"])

    # ─── 第2层: 核心推理 ───
    section_bg(ax, 0.2, 7.2, 19.6, 2.3, "#AB47BC", alpha=0.1, label="  核心AI推理层", label_fs=8)

    # ResNet50
    fancy_box(ax, 0.5, 7.5, 5.5, 1.8,
              "ResNet50 (微调二分类)\n─────────────────────\n输入: [1,3,224,224]\n特征提取: Conv→BN→ReLU→Pooling×4\nfc层: 2048→2  (FAKE / REAL)\n输出: softmax概率 [p_fake, p_real]",
              COLORS["model"], COLORS["border_pink"], fontsize=8)

    # CLIP
    fancy_box(ax, 6.5, 7.5, 5.5, 1.8,
              "CLIP ViT-B/32\n─────────────────────\n图像编码器: Vision Transformer\n文本编码器: Transformer\n7类别零样本分类\n图文一致性打分 (余弦相似度)",
              COLORS["xai"], COLORS["border_teal"], fontsize=8)

    # Grad-CAM
    fancy_box(ax, 12.5, 7.5, 3.5, 1.8,
              "Grad-CAM\n─────────────────────\n钩子: layer4最后conv\n梯度权重叠加\n热力图 base64 PNG",
              COLORS["analyzer"], COLORS["border_amber"], fontsize=8)

    # LIME/SHAP
    fancy_box(ax, 16.3, 7.5, 3.2, 1.8,
              "XAI (LIME/SHAP)\n─────────────────────\n文本检测专用\n分段解释+合并\n高亮HTML生成",
              COLORS["report"], COLORS["border_brown"], fontsize=8)

    arrow(ax, 2.75, 10.0, 3.25, 9.3, color=COLORS["arrow"])
    arrow(ax, 2.75, 10.0, 9.25, 9.3, color=COLORS["arrow"])

    # ─── 第3层: 六维度分析器 ───
    section_bg(ax, 0.2, 4.3, 19.6, 2.6, "#FFA726", alpha=0.1, label="  六维度分析器层  (并发执行)", label_fs=8)

    analyzers = [
        (0.3,  4.5, "人脸深伪检测\nface_analyzer.py\nHaar Cascade\n+ CLIP Prompts\n加权: CLIP×0.55\n+信号×0.45"),
        (3.5,  4.5, "频率域分析\nfrequency_analyzer.py\n灰度FFT\nPSD径向分布\n1/f^α 拟合\nR²相关性"),
        (6.7,  4.5, "边缘伪迹检测\nedge_analyzer.py\nLaplacian方差\n块状边界\n不自然锐度"),
        (9.9,  4.5, "印章/签名检测\nseal_detector.py\nHOG特征\n+ CLIP零样本\n圆形印章识别"),
        (13.1, 4.5, "Logo检测\nlogo_analyzer.py\nCLIP零样本\n媒体机构Logo\n可信度评分"),
        (16.3, 4.5, "图文一致性\nclip_classify.py\n标题↔图像\n余弦相似度\n跨模态匹配"),
    ]
    for ax2x, ax2y, at in analyzers:
        fancy_box(ax, ax2x, ax2y, 2.9, 2.2, at,
                  COLORS["analyzer"], COLORS["border_amber"], fontsize=7)

    for ax2x, ax2y, _ in analyzers:
        arrow(ax, ax2x + 1.45, 4.5, ax2x + 1.45, 7.5, color=COLORS["arrow_light"], lw=1.1)
        arrow(ax, ax2x + 1.45, 4.5, 9.5, 3.0 + 1.1, color=COLORS["arrow_light"], lw=1.1)

    # ─── 第4层: 综合评分 & 输出 ───
    section_bg(ax, 0.2, 1.4, 19.6, 2.6, "#EF5350", alpha=0.08, label="  综合评分 & 响应层", label_fs=8)

    fancy_box(ax, 0.5, 1.6, 5.0, 2.2,
              "综合评分 composite.py\n─────────────────────\n真实性    × 0.25\n置信度    × 0.20\n一致性    × 0.20\n印章      × 0.15\n频率域    × 0.10\n边缘      × 0.10\n\n总分 0-100 → 可信/可疑/不可信",
              COLORS["backend"], COLORS["border_purple"], fontsize=7.5)

    fancy_box(ax, 6.0, 1.6, 4.5, 2.2,
              "说明生成\nexplanation builder\n─────────────\nlevel: credible/suspicious/unreliable\nsummary: 汇总描述\nclues: 检测线索列表\ndisclaimer: 免责声明",
              COLORS["xai"], COLORS["border_teal"], fontsize=7.5)

    fancy_box(ax, 11.0, 1.6, 4.0, 2.2,
              "数据持久化\n─────────────\nDetectionRecord → SQLite\n写入: label/confidence\nprobs_json/model_version\n缓存: Redis TTL=300s",
              COLORS["db"], COLORS["border_blue"], fontsize=7.5)

    fancy_box(ax, 15.5, 1.6, 4.0, 2.2,
              "JSON 响应\n─────────────\nlabel / label_zh\nconfidence (0-100)\nprobs []\nexplanation {}\ncam_image (base64)\ndetection_id",
              COLORS["frontend"], COLORS["border_green"], fontsize=7.5)

    arrow(ax, 3.0, 7.5, 3.0, 5.7, color=COLORS["arrow"])
    arrow(ax, 3.0, 4.5, 3.25, 3.8, color=COLORS["arrow"])
    arrow(ax, 5.5, 2.7, 6.0, 2.7, color=COLORS["arrow"])
    arrow(ax, 10.5, 2.7, 11.0, 2.7, color=COLORS["arrow"])
    arrow(ax, 15.0, 2.7, 15.5, 2.7, color=COLORS["arrow"])

    save(fig, "04_backend_micro.png")


# ══════════════════════════════════════════════════════════
#  图5: 项目全局数据流图
# ══════════════════════════════════════════════════════════
def draw_dataflow():
    fig, ax = plt.subplots(figsize=(22, 16))
    ax.set_xlim(0, 22)
    ax.set_ylim(0, 16)
    ax.axis("off")
    ax.set_facecolor("white")
    fig.patch.set_facecolor("white")

    ax.text(11, 15.65, "AIGI-Holmes  项目全局数据流图",
            ha="center", va="top", fontsize=16, weight="bold", color="#1A237E")
    ax.text(11, 15.2, "从用户输入到最终检测结果的完整数据流向",
            ha="center", va="top", fontsize=10, color="#607D8B")

    # ═════════════════════════
    #  竖向泳道
    # ═════════════════════════
    lanes = [
        (0.2,  3.5, "#E3F2FD", "用户层"),
        (3.9,  3.5, "#E8F5E9", "前端层"),
        (7.6,  3.5, "#FFF3E0", "API层"),
        (11.3, 3.5, "#EDE7F6", "算法层"),
        (15.0, 3.5, "#FCE4EC", "模型层"),
        (18.5, 3.5, "#E0F7FA", "数据层"),
    ]
    for lx, lw, lc, lt in lanes:
        rect = plt.Rectangle((lx, 0.3), lw, 14.7, facecolor=lc,
                              edgecolor="#CFD8DC", linewidth=0.8, alpha=0.35, zorder=0)
        ax.add_patch(rect)
        ax.text(lx + lw / 2, 14.7, lt, ha="center", va="bottom",
                fontsize=10, weight="bold", color="#37474F")

    # ═════════════════════════
    # 行1: 认证流程 (y~12)
    # ═════════════════════════
    ax.text(0.5, 13.85, "① 认证流", fontsize=9, color="#1A237E", weight="bold")
    fancy_box(ax, 0.4, 12.5, 3.0, 1.0, "用户\n(浏览器)", COLORS["user"], COLORS["border_blue"], fontsize=9)
    fancy_box(ax, 4.1, 12.5, 3.0, 1.0, "登录/注册表单\napp.js", COLORS["frontend"], COLORS["border_green"], fontsize=8.5)
    fancy_box(ax, 7.8, 12.5, 3.0, 1.0, "POST /api/auth\n/login", COLORS["api"], COLORS["border_orange"], fontsize=8.5)
    fancy_box(ax, 11.5, 12.5, 3.0, 1.0, "bcrypt验证\npasslib", COLORS["auth"], COLORS["border_indigo"], fontsize=8.5)
    fancy_box(ax, 15.2, 12.5, 3.0, 1.0, "JWT生成\naccess+refresh\n令牌", COLORS["auth"], COLORS["border_indigo"], fontsize=8)
    fancy_box(ax, 19.0, 12.5, 2.8, 1.0, "User表\nSQLite", COLORS["db"], COLORS["border_blue"], fontsize=8.5)
    for x1, x2 in [(3.4, 4.1), (7.1, 7.8), (10.8, 11.5), (14.5, 15.2), (18.2, 19.0)]:
        arrow(ax, x1, 13.0, x2, 13.0, color=COLORS["arrow"])
    arrow(ax, 18.2, 13.0, 4.1, 13.0, color="#EF5350", lw=1.2, label="JWT返回")

    # ═════════════════════════
    # 行2: 单图检测流程 (y~10)
    # ═════════════════════════
    ax.text(0.5, 11.75, "② 单图检测流", fontsize=9, color="#2E7D32", weight="bold")
    fancy_box(ax, 0.4, 10.3, 3.0, 1.1, "上传图片\n拖拽/选择", COLORS["user"], COLORS["border_blue"], fontsize=8.5)
    fancy_box(ax, 4.1, 10.3, 3.0, 1.1, "FormData构建\n预览·格式验证", COLORS["frontend"], COLORS["border_green"], fontsize=8)
    fancy_box(ax, 7.8, 10.3, 3.0, 1.1, "POST /api/detect\ncam=0|1", COLORS["api"], COLORS["border_orange"], fontsize=8.5)
    fancy_box(ax, 11.5, 10.3, 3.0, 1.1, "Redis缓存\nSHA-256命中检查", COLORS["cache"], COLORS["border_purple"], fontsize=8)
    fancy_box(ax, 15.2, 10.3, 3.0, 1.1, "ResNet50推理\nFAKE/REAL概率", COLORS["model"], COLORS["border_pink"], fontsize=8)
    fancy_box(ax, 19.0, 10.3, 2.8, 1.1, "DetectionRecord\n写入SQLite", COLORS["db"], COLORS["border_blue"], fontsize=8)

    for x1, x2 in [(3.4, 4.1), (7.1, 7.8), (10.8, 11.5), (14.5, 15.2), (18.2, 19.0)]:
        arrow(ax, x1, 10.85, x2, 10.85, color=COLORS["arrow"])
    # 缓存未命中 → 模型
    arrow(ax, 14.5, 10.65, 15.2, 10.65, color=COLORS["arrow"], label="未命中")
    # 缓存命中回路
    arrow_curve(ax, 12.0, 10.3, 4.1, 10.6, rad=-0.15, color="#9C27B0", lw=1.2, label="缓存命中")

    # Grad-CAM分支
    fancy_box(ax, 15.2, 8.8, 3.0, 1.1, "Grad-CAM\nlayer4热力图\nbase64编码", COLORS["xai"], COLORS["border_teal"], fontsize=8)
    arrow(ax, 16.7, 10.3, 16.7, 9.9, color=COLORS["arrow_light"], lw=1.2, label="cam=1")

    # 结果回流
    fancy_box(ax, 4.1, 8.8, 3.0, 1.1, "渲染结果\n标签+置信度\nCAM+XAI说明", COLORS["frontend"], COLORS["border_green"], fontsize=8)
    arrow(ax, 15.2, 9.35, 7.1, 9.35, color="#2196F3", lw=1.5, label="JSON响应")
    arrow(ax, 7.1, 9.35, 4.1 + 3.0, 9.35, color="#2196F3", lw=1.5)

    # ═════════════════════════
    # 行3: URL检测流程 (y~7)
    # ═════════════════════════
    ax.text(0.5, 8.35, "③ URL检测流", fontsize=9, color="#E65100", weight="bold")
    fancy_box(ax, 0.4, 7.0, 3.0, 1.0, "输入新闻URL\n文章链接", COLORS["user"], COLORS["border_blue"], fontsize=8.5)
    fancy_box(ax, 4.1, 7.0, 3.0, 1.0, "URL输入框\napp.js", COLORS["frontend"], COLORS["border_green"], fontsize=8.5)
    fancy_box(ax, 7.8, 7.0, 3.0, 1.0, "POST\n/api/detect-url", COLORS["api"], COLORS["border_orange"], fontsize=8.5)
    fancy_box(ax, 11.5, 7.0, 3.0, 1.0, "抓取页面\nhttpx异步\n提取所有图片URL", COLORS["backend"], COLORS["border_purple"], fontsize=7.5)
    fancy_box(ax, 15.2, 7.0, 3.0, 1.0, "并发推理\nResNet50批量\n+CLIP分类", COLORS["model"], COLORS["border_pink"], fontsize=8)
    fancy_box(ax, 19.0, 7.0, 2.8, 1.0, "六维度分析\n综合评分\ncomposite.py", COLORS["analyzer"], COLORS["border_amber"], fontsize=8)

    for x1, x2 in [(3.4, 4.1), (7.1, 7.8), (10.8, 11.5), (14.5, 15.2), (18.2, 19.0)]:
        arrow(ax, x1, 7.5, x2, 7.5, color=COLORS["arrow"])

    # Bing搜图分支
    fancy_box(ax, 19.0, 5.8, 2.8, 0.9, "Bing/Serper\n反向图片搜索\n验证真实性", COLORS["cache"], COLORS["border_purple"], fontsize=7.5)
    arrow(ax, 20.4, 7.0, 20.4, 6.7, color=COLORS["arrow_light"], lw=1.2)

    # 结果回流
    fancy_box(ax, 4.1, 5.8, 3.0, 0.9, "结果网格\n可信度徽章\n摘要说明", COLORS["frontend"], COLORS["border_green"], fontsize=8)
    arrow(ax, 19.0, 7.5, 7.1, 7.5, color="#2196F3", lw=1.2, label="JSON结果数组")
    arrow(ax, 7.1, 7.5, 7.1, 6.25, color="#2196F3", lw=1.2)
    arrow(ax, 7.1, 6.25, 7.1, 6.25, color="#2196F3", lw=1.2)
    arrow(ax, 7.1, 6.25, 4.1 + 3.0, 6.25, color="#2196F3", lw=1.2)

    # ═════════════════════════
    # 行4: 批量检测流程 (y~4.2)
    # ═════════════════════════
    ax.text(0.5, 5.35, "④ 批量检测流", fontsize=9, color="#1565C0", weight="bold")
    fancy_box(ax, 0.4, 4.0, 3.0, 1.0, "拖拽文件夹\n多文件", COLORS["user"], COLORS["border_blue"], fontsize=8.5)
    fancy_box(ax, 4.1, 4.0, 3.0, 1.0, "文件过滤·\nXHR上传\n+进度条", COLORS["frontend"], COLORS["border_green"], fontsize=8)
    fancy_box(ax, 7.8, 4.0, 3.0, 1.0, "POST init\nWS连接\n/ws/batch", COLORS["api"], COLORS["border_orange"], fontsize=8)
    fancy_box(ax, 11.5, 4.0, 3.0, 1.0, "JobStore\n任务队列\n状态跟踪", COLORS["backend"], COLORS["border_purple"], fontsize=8)
    fancy_box(ax, 15.2, 4.0, 3.0, 1.0, "逐项推理\ndetect_batch()\n异步线程池", COLORS["model"], COLORS["border_pink"], fontsize=8)
    fancy_box(ax, 19.0, 4.0, 2.8, 1.0, "WS推送\nresult消息\n实时返回", COLORS["websocket"], COLORS["border_sky"], fontsize=8)

    for x1, x2 in [(3.4, 4.1), (7.1, 7.8), (10.8, 11.5), (14.5, 15.2), (18.2, 19.0)]:
        arrow(ax, x1, 4.5, x2, 4.5, color=COLORS["arrow"])

    fancy_box(ax, 4.1, 2.8, 3.0, 0.85, "结果卡片\n瀑布流展示", COLORS["frontend"], COLORS["border_green"], fontsize=8)
    arrow(ax, 20.4, 4.0, 20.4, 3.25, color="#2196F3", lw=1.2)
    arrow(ax, 20.4, 3.25, 7.1, 3.25, color="#2196F3", lw=1.2, label="WS消息流")
    arrow(ax, 7.1, 3.25, 4.1 + 3.0, 3.25, color="#2196F3", lw=1.2)

    # ═════════════════════════
    # 底部公共组件
    # ═════════════════════════
    ax.text(0.5, 2.5, "⑤ 公共基础设施", fontsize=9, color="#880E4F", weight="bold")
    common = [
        (0.4,  0.5, 3.0, 1.7, "Redis缓存层\nget_cached_result\nset_cached_result\nTTL=300s",
         COLORS["cache"], COLORS["border_purple"]),
        (3.7,  0.5, 3.0, 1.7, "SQLite数据库\naiosqlite异步驱动\nBase.metadata.create_all\n启动时自动建表",
         COLORS["db"], COLORS["border_blue"]),
        (7.0,  0.5, 3.0, 1.7, "报告生成\nbackend/report/\nPDF·CSV·JSON\n多格式导出",
         COLORS["report"], COLORS["border_brown"]),
        (10.3, 0.5, 3.0, 1.7, "文本检测\ntext_detect.py\nLLM文本真实性\nXAI高亮解释",
         COLORS["xai"], COLORS["border_teal"]),
        (13.6, 0.5, 3.0, 1.7, "异常处理\nexceptions.py\nImageFormatError\n全局错误处理器",
         "#FFEBEE", "#EF9A9A"),
        (16.9, 0.5, 4.7, 1.7, "PyInstaller 打包\nAIGI_Holmes.spec\nOne-file EXE\nWindows安装包(Inno Setup)",
         COLORS["report"], COLORS["border_brown"]),
    ]
    for cx, cy, cw, ch, ct, cc, cec in common:
        fancy_box(ax, cx, cy, cw, ch, ct, cc, cec, fontsize=7.5)

    # 图例
    legend_items = [
        (mpatches.Patch(facecolor=COLORS["user"],      edgecolor=COLORS["border_blue"]),   "用户操作"),
        (mpatches.Patch(facecolor=COLORS["frontend"],  edgecolor=COLORS["border_green"]),  "前端处理"),
        (mpatches.Patch(facecolor=COLORS["api"],       edgecolor=COLORS["border_orange"]), "API路由"),
        (mpatches.Patch(facecolor=COLORS["model"],     edgecolor=COLORS["border_pink"]),   "AI模型"),
        (mpatches.Patch(facecolor=COLORS["cache"],     edgecolor=COLORS["border_purple"]), "缓存/认证"),
        (mpatches.Patch(facecolor=COLORS["db"],        edgecolor=COLORS["border_blue"]),   "数据库"),
        (mpatches.Patch(facecolor=COLORS["websocket"], edgecolor=COLORS["border_sky"]),    "WebSocket"),
        (mpatches.Patch(facecolor=COLORS["xai"],       edgecolor=COLORS["border_teal"]),   "XAI/分析器"),
    ]
    handles, labels = zip(*legend_items)
    ax.legend(handles, labels, loc="lower right", fontsize=8,
              framealpha=0.9, edgecolor="#CFD8DC", ncol=2)

    save(fig, "05_dataflow.png")


# ══════════════════════════════════════════════════════════
#  主入口
# ══════════════════════════════════════════════════════════
if __name__ == "__main__":
    # 确保中文字体可用
    import matplotlib.font_manager as fm
    cjk_fonts = [
        "Microsoft YaHei", "SimHei", "WenQuanYi Micro Hei",
        "Noto Sans CJK SC", "Source Han Sans CN",
        "DejaVu Sans",
    ]
    found = None
    for fname in cjk_fonts:
        matches = fm.findfont(fm.FontProperties(family=fname), fallback_to_default=False)
        if matches and "DejaVu" not in matches:
            found = fname
            break
    if found:
        plt.rcParams["font.family"] = found
        print(f"  使用字体: {found}")
    else:
        # 尝试系统字体
        plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "Arial Unicode MS", "DejaVu Sans"]
        plt.rcParams["axes.unicode_minus"] = False
        print("  使用系统后备字体")

    plt.rcParams["axes.unicode_minus"] = False

    print("开始生成架构图...")
    print("─" * 50)
    draw_frontend_macro()
    draw_frontend_micro()
    draw_backend_macro()
    draw_backend_micro()
    draw_dataflow()
    print("─" * 50)
    print(f"全部完成！图片保存在: {OUTPUT_DIR}")
