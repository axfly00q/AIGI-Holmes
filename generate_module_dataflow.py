"""
AIGI-Holmes 四大核心模块数据流图
使用 matplotlib 绘制，分别保存为 PNG 图片
"""

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch
import numpy as np
import os

# 设置中文字体
plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "数据流图", "matplotlib图表")
os.makedirs(OUTPUT_DIR, exist_ok=True)


# ─── 通用绘图工具 ──────────────────────────────────────────────────────────────

def draw_box(ax, x, y, w, h, text, facecolor="#4A90D9",
             style="round,pad=0.1", textcolor="white", fontsize=9,
             edgecolor="#2C5F8A", linewidth=1.5, alpha=1.0):
    """在 ax 上绘制带圆角的矩形节点"""
    box = FancyBboxPatch((x - w / 2, y - h / 2), w, h,
                         boxstyle=style,
                         facecolor=facecolor, edgecolor=edgecolor,
                         linewidth=linewidth, alpha=alpha, zorder=3)
    ax.add_patch(box)
    ax.text(x, y, text, ha="center", va="center",
            fontsize=fontsize, color=textcolor,
            fontweight="bold", zorder=4, wrap=True,
            multialignment="center")


def draw_diamond(ax, x, y, w, h, text, facecolor="#F5A623",
                 textcolor="white", fontsize=8.5, edgecolor="#C87D0E"):
    """绘制菱形判断节点"""
    dx, dy = w / 2, h / 2
    diamond = plt.Polygon(
        [[x, y + dy], [x + dx, y], [x, y - dy], [x - dx, y]],
        closed=True, facecolor=facecolor, edgecolor=edgecolor,
        linewidth=1.5, zorder=3
    )
    ax.add_patch(diamond)
    ax.text(x, y, text, ha="center", va="center",
            fontsize=fontsize, color=textcolor, fontweight="bold", zorder=4)


def arrow(ax, x1, y1, x2, y2, label="", color="#555555", lw=1.5):
    """绘制带箭头的连接线"""
    ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle="-|>", color=color,
                                lw=lw, mutation_scale=14),
                zorder=2)
    if label:
        mx, my = (x1 + x2) / 2, (y1 + y2) / 2
        ax.text(mx + 0.05, my, label, fontsize=7.5, color="#333333",
                ha="left", va="center", style="italic", zorder=5)


def set_canvas(ax, title, xlim, ylim, bg="#F8FBFF"):
    """设置画布背景和标题"""
    ax.set_xlim(*xlim)
    ax.set_ylim(*ylim)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_facecolor(bg)
    ax.set_title(title, fontsize=14, fontweight="bold", pad=14,
                 color="#1A1A2E")


# ─── 模块1：单张照片检测 ──────────────────────────────────────────────────────

def draw_single_detect():
    fig, ax = plt.subplots(figsize=(14, 6))
    fig.patch.set_facecolor("#FAFBFC")
    set_canvas(ax, "单张照片检测  数据流图", (-0.5, 13.5), (-1.5, 1.5))

    # 淡色方案
    C_USER   = "#B4A7D6"
    C_FE     = "#7FA3C8"
    C_GATE   = "#F5D5A8"
    C_CACHE  = "#A8D5BA"
    C_MODEL  = "#F4B4B4"
    C_DB     = "#B8B8D1"
    C_OUT    = "#90D5A8"

    # ── 节点定义 (x, y, w, h, text, color) ──
    nodes = [
        # (x, y, w, h, text, facecolor)
        (0.5, 0, 1.2, 0.6, "用 户\n上传图片", C_USER),
        (1.8, 0, 1.2, 0.6, "前端校验\n格式检查", C_FE),
        (3.0, 0, 1.0, 0.6, "格式\n合法？", C_GATE),
        (4.2, 0, 1.4, 0.6, "Redis\n缓存查询", C_CACHE),
        (5.8, 0, 1.0, 0.6, "缓存\n命中？", C_GATE),
        (6.8, -0.9, 1.4, 0.6, "缓存结果\n直接返回", C_CACHE),
        (7.2, 0.9, 1.4, 0.6, "ResNet50\n推理", C_MODEL),
        (8.6, 0.9, 1.2, 0.6, "Grad-CAM\n热力图", C_MODEL),
        (9.8, 0.9, 1.4, 0.6, "写入\n缓存", C_CACHE),
        (11.4, 0.9, 1.4, 0.6, "写入\nSQLite DB", C_DB),
        (12.8, 0, 2.0, 0.7, "返回结果\nlabel·confidence·probs", C_OUT),
        (2.2, -0.95, 1.0, 0.5, "错误返回", "#F0C4C4"),
    ]

    for i, n in enumerate(nodes):
        x, y, w, h, text, fc = n
        if "？" in text:
            draw_diamond(ax, x, y, w, h, text, facecolor=fc)
        else:
            draw_box(ax, x, y, w, h, text, facecolor=fc)

    # ── 箭头 ──
    arrows = [
        (1.1, 0, 1.4, 0),
        (2.4, 0, 2.5, 0),
        # 格式不合法 → 错误
        (3.0, -0.3, 2.2, -0.7),
        # 合法 → 缓存查询
        (3.5, 0, 3.95, 0),
        # 缓存查询 → 缓存命中判断
        (4.9, 0, 5.3, 0),
        # 缓存命中 → 返回
        (6.0, -0.35, 6.8, -0.6),
        # 缓存未命中 → ResNet
        (6.3, 0.3, 7.2, 0.6),
        # ResNet → Grad-CAM
        (7.9, 0.9, 8.0, 0.9),
        # Grad-CAM → 写缓存
        (8.8, 0.9, 9.8, 0.9),
        # 写缓存 → 写DB
        (10.7, 0.9, 11.4, 0.9),
        # 写DB → 返回结果
        (11.8, 0.6, 12.4, 0.35),
        # 缓存命中返回 → 最终返回
        (6.8, -0.65, 12.0, -0.2),
    ]
    for a_ in arrows:
        arrow(ax, *a_)

    # 标注判断分支文字
    ax.text(2.9, -0.55, "x 非法", fontsize=7, color="#E74C3C")
    ax.text(3.3,  0.25, "√ 合法", fontsize=7, color="#27AE60")
    ax.text(5.7, -0.55, "命中", fontsize=7, color="#27AE60")
    ax.text(6.0,  0.25, "未命中", fontsize=7, color="#E74C3C")

    # 图例
    legend_items = [
        mpatches.Patch(facecolor=C_USER, label="用户输入"),
        mpatches.Patch(facecolor=C_FE, label="前端/接口层"),
        mpatches.Patch(facecolor=C_CACHE, label="缓存层"),
        mpatches.Patch(facecolor=C_MODEL, label="AI模型"),
        mpatches.Patch(facecolor=C_DB, label="数据库"),
        mpatches.Patch(facecolor=C_OUT, label="输出结果"),
    ]
    ax.legend(handles=legend_items, loc="lower center", fontsize=7,
              framealpha=0.8, edgecolor="#D0D0D0", ncol=6)

    plt.tight_layout()
    out = os.path.join(OUTPUT_DIR, "01_单张照片检测数据流图.png")
    plt.savefig(out, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"已保存: {out}")

    plt.tight_layout()
    out = os.path.join(OUTPUT_DIR, "01_单张照片检测数据流图.png")
    plt.savefig(out, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"已保存: {out}")


# ─── 模块2：URL批量检测 ──────────────────────────────────────────────────────

def draw_url_batch():
    fig, ax = plt.subplots(figsize=(15, 6.5))
    fig.patch.set_facecolor("#FAFBFC")
    set_canvas(ax, "URL 批量检测  数据流图", (-0.5, 14.5), (-1.8, 1.8))

    # 淡色方案
    C_USER  = "#B4A7D6"
    C_NET   = "#7FA3C8"
    C_PARSE = "#8FB8D8"
    C_LOOP  = "#B4A3D6"
    C_MODEL = "#F0B8B8"
    C_CLIP  = "#E8C9A0"
    C_ANA   = "#A8D5C4"
    C_SCORE = "#F0C8C0"
    C_DB    = "#B8B8D1"
    C_OUT   = "#A8D5B8"

    # ── 节点 ──
    draw_box(ax, 0.5, 0, 1.1, 0.6, "输入URL\n校验前缀", C_USER)
    draw_box(ax, 1.8, 0, 1.1, 0.6, "抓取页面\nBeautifulSoup", C_PARSE)
    draw_box(ax, 3.0, 0, 1.1, 0.6, "提取图片URL\n列表提取", C_PARSE)
    draw_diamond(ax, 4.0, 0, 1.0, 0.55, "img为空？", C_SCORE)
    draw_box(ax, 2.2, -1.3, 0.8, 0.5, "返回错误", "#F0C4C4")

    # 循环处理区
    draw_box(ax, 5.0, 0, 1.1, 0.6, "循环：下载\n异步处理", C_LOOP)

    # 并行处理框
    bg = FancyBboxPatch((5.8, -0.45), 4.2, 1.0,
                        boxstyle="round,pad=0.08",
                        facecolor="#F5F8FA", edgecolor="#C8D8E4",
                        linewidth=1.0, zorder=1)
    ax.add_patch(bg)
    ax.text(8.0, 0.3, "并行推理", fontsize=7.5, ha="center", color="#5A7FA8", style="italic")

    draw_box(ax, 6.3, 0, 1.0, 0.5, "ResNet50", C_MODEL)
    draw_box(ax, 7.4, 0, 0.9, 0.5, "CLIP", C_CLIP)
    draw_box(ax, 8.2, 0, 0.9, 0.5, "五项分析", C_ANA)
    draw_box(ax, 9.0, -0.45, 0.9, 0.45, "缩略图", "#C8D8E4")

    # 聚合和输出
    draw_box(ax, 10.5, 0, 1.2, 0.6, "聚合结果\n列表", C_LOOP)
    draw_box(ax, 11.8, 0, 1.2, 0.6, "综合评分\n维度分析", C_SCORE)
    draw_box(ax, 13.1, 0, 1.2, 0.6, "写入SQLite\nDB", C_DB)
    draw_box(ax, 14.2, -0.2, 1.4, 0.7, "返回结果\ncount·results", C_OUT)

    # ── 箭头 ──
    straight = [
        (1.05, 0, 1.35, 0),
        (2.35, 0, 2.65, 0),
        (3.55, 0, 3.5, 0),
        # 无图 → 错误
        (4.0, -0.25, 2.6, -1.05),
        # 有图 → 循环
        (4.45, 0, 4.55, 0),
        # 循环 → 并行框
        (5.55, 0, 5.8, 0),
        # 并行处理各项
        (6.3, 0, 6.3, 0),
        (7.4, 0, 7.4, 0),
        (8.2, -0.2, 8.2, -0.2),
        # 聚合
        (9.35, -0.15, 10.1, -0.15),
        (10.5, 0, 11.2, 0),
        (12.4, 0, 12.7, 0),
        (13.7, 0, 13.7, 0),
    ]
    for a_ in straight:
        arrow(ax, *a_)

    # 回环（循环）
    ax.annotate("", xy=(5.0, -0.55), xytext=(10.5, -0.55),
                arrowprops=dict(arrowstyle="-|>", color="#B4A3D6",
                                connectionstyle="arc3,rad=0.35",
                                lw=1.2, mutation_scale=10),
                zorder=2)
    ax.text(7.75, -1.05, "重复每张图", fontsize=6.5, color="#8875A8", ha="center")

    ax.text(3.8, 0.35, "无", fontsize=7, color="#E74C3C")
    ax.text(4.5, 0.3, "有", fontsize=7, color="#27AE60")

    legend_items = [
        mpatches.Patch(facecolor=C_USER, label="输入"),
        mpatches.Patch(facecolor=C_PARSE, label="页面解析"),
        mpatches.Patch(facecolor=C_LOOP, label="循环/聚合"),
        mpatches.Patch(facecolor=C_MODEL, label="ResNet"),
        mpatches.Patch(facecolor=C_CLIP, label="CLIP"),
        mpatches.Patch(facecolor=C_ANA, label="分析器"),
        mpatches.Patch(facecolor=C_DB, label="数据库"),
        mpatches.Patch(facecolor=C_OUT, label="输出"),
    ]
    ax.legend(handles=legend_items, loc="lower center", fontsize=6.5,
              framealpha=0.8, edgecolor="#D0D0D0", ncol=8)

    plt.tight_layout()
    out = os.path.join(OUTPUT_DIR, "02_URL批量检测数据流图.png")
    plt.savefig(out, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"已保存: {out}")



# ─── 模块3：AI智能解读报告 ──────────────────────────────────────────────────

def draw_ai_report():
    fig, ax = plt.subplots(figsize=(14, 5.5))
    fig.patch.set_facecolor("#FAFBFC")
    set_canvas(ax, "AI 智能解读报告  数据流图", (-0.5, 13.5), (-1.2, 1.2))

    # 淡色方案
    C_USER  = "#B4A7D6"
    C_AUTH  = "#E8C9A0"
    C_DB    = "#B8B8D1"
    C_PROM  = "#B4A3D6"
    C_API   = "#F0B8B8"
    C_HIST  = "#A8D5BA"
    C_OUT   = "#A8D5B8"

    draw_box(ax, 0.5, 0, 1.1, 0.6, "输入提问\n选择记录", C_USER)
    draw_box(ax, 1.7, 0, 1.0, 0.6, "JWT认证\n校验用户", C_AUTH)
    draw_box(ax, 2.85, 0, 1.0, 0.6, "查询DB\n获取记录", C_DB)
    draw_box(ax, 4.0, 0, 1.0, 0.6, "加载对话\n历史", C_HIST)
    
    # Prompt构建展示框
    tip = FancyBboxPatch((5.05, -0.55), 1.8, 1.15,
                         boxstyle="round,pad=0.08",
                         facecolor="#F5F8FA", edgecolor="#C8D8E4",
                         linewidth=0.8, zorder=1)
    ax.add_patch(tip)
    ax.text(5.95, 0.15,
            "构建 System\nPrompt",
            ha="center", va="center", fontsize=7, color="#5A7FA8",
            fontweight="bold", zorder=4)

    draw_box(ax, 7.0, 0, 1.2, 0.6, "调用豆包\nAI API", C_API)
    draw_box(ax, 8.4, 0, 1.2, 0.6, "流式推送\nSSE", C_OUT)
    draw_box(ax, 9.8, 0, 1.2, 0.6, "追加历史\n多轮对话", C_HIST)
    
    # 错误处理
    draw_box(ax, 2.85, -1.0, 1.0, 0.4, "404错误", "#F0C4C4")

    # ── 箭头 ──
    for x1, x2 in [(1.05, 1.2), (2.2, 2.35), (2.85, 3.5),
                   (4.5, 5.05), (6.95, 6.1), (7.6, 7.8),
                   (9.0, 9.8)]:
        arrow(ax, x1, 0, x2, 0)

    # 记录不存在 → 404
    arrow(ax, 2.85, -0.3, 2.85, -0.8)

    # 流式回环（历史更新）
    ax.annotate("", xy=(9.8, -0.5), xytext=(8.4, -0.5),
                arrowprops=dict(arrowstyle="-|>", color="#A8D5BA",
                                connectionstyle="arc3,rad=-0.25",
                                lw=1.0, mutation_scale=9), zorder=2)
    ax.text(9.1, -0.75, "更新", fontsize=6.5, color="#7CAB8A", ha="center")

    legend_items = [
        mpatches.Patch(facecolor=C_USER, label="用户"),
        mpatches.Patch(facecolor=C_AUTH, label="认证"),
        mpatches.Patch(facecolor=C_DB, label="数据库"),
        mpatches.Patch(facecolor=C_HIST, label="历史管理"),
        mpatches.Patch(facecolor=C_PROM, label="Prompt"),
        mpatches.Patch(facecolor=C_API, label="豆包API"),
        mpatches.Patch(facecolor=C_OUT, label="输出"),
    ]
    ax.legend(handles=legend_items, loc="lower center", fontsize=7,
              framealpha=0.8, edgecolor="#D0D0D0", ncol=7)

    plt.tight_layout()
    out = os.path.join(OUTPUT_DIR, "03_AI智能解读报告数据流图.png")
    plt.savefig(out, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"已保存: {out}")


# ─── 模块4：多格式报告导出 ──────────────────────────────────────────────────

def draw_export_report():
    fig, ax = plt.subplots(figsize=(14.5, 5.5))
    fig.patch.set_facecolor("#FAFBFC")
    set_canvas(ax, "多格式报告导出  数据流图", (-0.5, 13.8), (-1.3, 1.3))

    # 淡色方案
    C_USER  = "#B4A7D6"
    C_AUTH  = "#E8C9A0"
    C_GATE  = "#F5D5A8"
    C_DB    = "#B8B8D1"
    C_BUILD = "#7FA3C8"
    C_PDF   = "#F0B8B8"
    C_EXCEL = "#A8D5BA"
    C_OUT   = "#A8D5B8"

    draw_box(ax, 0.5, 0, 1.1, 0.6, "请求导出\n报告", C_USER)
    draw_box(ax, 1.7, 0, 1.0, 0.6, "JWT\n认证", C_AUTH)
    draw_box(ax, 2.85, 0, 1.0, 0.6, "格式校验\npdf/excel？", C_GATE)
    draw_box(ax, 4.0, 0, 1.0, 0.6, "查询DB\n获取记录", C_DB)
    draw_box(ax, 5.2, 0, 1.2, 0.6, "构建报告\n字典", C_BUILD)

    # 分支判断菱形
    draw_diamond(ax, 6.5, 0, 1.0, 0.55, "格式\n类型？", C_GATE)

    # PDF 分支
    draw_box(ax, 7.5, 0.8, 1.0, 0.5, "PDF\n导出", C_PDF)
    draw_box(ax, 8.5, 0.8, 1.0, 0.5, "WeasyPrint\n渲染", C_PDF)

    # Excel 分支
    draw_box(ax, 7.5, -0.8, 1.0, 0.5, "Excel\n导出", C_EXCEL)
    draw_box(ax, 8.5, -0.8, 1.0, 0.5, "openpyxl\n生成", C_EXCEL)

    # 合并输出
    draw_box(ax, 11.0, 0, 1.3, 0.6, "响应头\n设置", C_OUT)
    draw_box(ax, 12.4, 0, 1.5, 0.7, "返回文件\ndownload", C_OUT)

    # 错误处理
    draw_box(ax, 2.85, -1.1, 0.9, 0.4, "422错误", "#F0C4C4")
    draw_box(ax, 4.0, -1.1, 0.9, 0.4, "404错误", "#F0C4C4")

    # ── 箭头 ──
    # 主流程
    for x1, x2 in [(1.05, 1.2), (2.2, 2.35), (2.85, 3.5),
                   (4.5, 4.6), (5.8, 6.0)]:
        arrow(ax, x1, 0, x2, 0)

    # 格式不合法 → 422错误
    arrow(ax, 2.85, -0.3, 2.85, -0.9)

    # DB 无记录 → 404错误
    arrow(ax, 4.0, -0.3, 4.0, -0.9)

    # 分支 PDF
    arrow(ax, 6.75, 0.25, 7.5, 0.55)
    ax.text(6.9, 0.4, "PDF", fontsize=7, color="#E74C3C", fontweight="bold")

    # 分支 Excel
    arrow(ax, 6.75, -0.25, 7.5, -0.55)
    ax.text(6.9, -0.4, "Excel", fontsize=7, color="#27AE60", fontweight="bold")

    # 各分支内部流
    arrow(ax, 8.0, 0.8, 8.5, 0.8)
    arrow(ax, 8.0, -0.8, 8.5, -0.8)

    # 合并到响应头
    arrow(ax, 9.0, 0.5, 10.2, 0.3)
    arrow(ax, 9.0, -0.5, 10.2, -0.3)
    arrow(ax, 10.65, 0, 11.65, 0)
    arrow(ax, 11.65, 0, 12.15, 0)

    legend_items = [
        mpatches.Patch(facecolor=C_USER, label="用户请求"),
        mpatches.Patch(facecolor=C_AUTH, label="认证"),
        mpatches.Patch(facecolor=C_DB, label="数据库"),
        mpatches.Patch(facecolor=C_BUILD, label="构建"),
        mpatches.Patch(facecolor=C_PDF, label="PDF"),
        mpatches.Patch(facecolor=C_EXCEL, label="Excel"),
        mpatches.Patch(facecolor=C_OUT, label="输出"),
    ]
    ax.legend(handles=legend_items, loc="lower center", fontsize=6.5,
              framealpha=0.8, edgecolor="#D0D0D0", ncol=7)

    plt.tight_layout()
    out = os.path.join(OUTPUT_DIR, "04_多格式报告导出数据流图.png")
    plt.savefig(out, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"已保存: {out}")


# ─── 入口 ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("正在生成四大模块数据流图...")
    draw_single_detect()
    draw_url_batch()
    draw_ai_report()
    draw_export_report()
    print("\n全部完成！图片已保存至:", OUTPUT_DIR)
