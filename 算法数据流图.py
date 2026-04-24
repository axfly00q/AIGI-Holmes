"""
AIGI-Holmes 项目算法设计与数据流图可视化
包含5张关键数据流图：
1. 整体系统架构与数据流
2. 单图检测算法数据流（ResNet50 + Grad-CAM）
3. CLIP多模态内容分类与图文一致性检测数据流
4. 批量文件检测与实时进度推送数据流
5. 报告生成与PDF/Excel导出工作流
"""

import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import numpy as np


plt.rcParams["font.sans-serif"] = ["SimHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False


def draw_overall_architecture():
    fig, ax = plt.subplots(figsize=(16, 10))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 10)
    ax.axis("off")

    ax.text(5, 9.5, "AIGI-Holmes 系统整体架构与数据流", fontsize=18, fontweight="bold", ha="center")

    user_y = 8.5
    user_color = "#E8F4F8"
    rect1 = FancyBboxPatch((0.5, user_y - 0.4), 1.5, 0.8, boxstyle="round,pad=0.1", edgecolor="#1f77b4", facecolor=user_color, linewidth=2)
    rect2 = FancyBboxPatch((2.5, user_y - 0.4), 1.5, 0.8, boxstyle="round,pad=0.1", edgecolor="#1f77b4", facecolor=user_color, linewidth=2)
    rect3 = FancyBboxPatch((4.5, user_y - 0.4), 1.5, 0.8, boxstyle="round,pad=0.1", edgecolor="#1f77b4", facecolor=user_color, linewidth=2)
    ax.add_patch(rect1)
    ax.add_patch(rect2)
    ax.add_patch(rect3)
    ax.text(1.25, user_y, "桌面应用\n(PyWebView)", ha="center", va="center", fontsize=10, fontweight="bold")
    ax.text(3.25, user_y, "网页应用\n(HTML+原生JS)", ha="center", va="center", fontsize=10, fontweight="bold")
    ax.text(5.25, user_y, "API接口\n(REST)", ha="center", va="center", fontsize=10, fontweight="bold")

    middleware_y = 7
    rect_api = FancyBboxPatch((1.5, middleware_y - 0.5), 3, 1, boxstyle="round,pad=0.1", edgecolor="#ff7f0e", facecolor="#FFF4E6", linewidth=2)
    ax.add_patch(rect_api)
    ax.text(3, middleware_y, "FastAPI后端\n(uvicorn:7860 异步)", ha="center", va="center", fontsize=11, fontweight="bold")

    for x in [1.25, 3.25, 5.25]:
        ax.add_patch(FancyArrowPatch((x, user_y - 0.5), (3, middleware_y + 0.5), arrowstyle="->", mutation_scale=20, color="#1f77b4", linewidth=2))

    route_y = 5.5
    route_color = "#F0E6FF"
    nodes = [
        ((0.3, route_y - 0.35), "POST /api/detect\n单图检测", 1.2),
        ((2.4, route_y - 0.35), "POST /api/detect-url\nURL检测", 3.3),
        ((4.5, route_y - 0.35), "WS /ws/detect/{job_id}\n实时进度", 5.4),
        ((6.6, route_y - 0.35), "POST /api/report/generate\n报告生成", 7.5),
    ]
    for (xy, text, cx) in nodes:
        rect = FancyBboxPatch(xy, 1.8, 0.7, boxstyle="round,pad=0.05", edgecolor="#2ca02c", facecolor=route_color, linewidth=1.5)
        ax.add_patch(rect)
        ax.text(cx, route_y, text, ha="center", va="center", fontsize=9)
    for x in [1.2, 3.3, 5.4, 7.5]:
        ax.add_patch(FancyArrowPatch((3, middleware_y - 0.5), (x, route_y + 0.35), arrowstyle="->", mutation_scale=15, color="#ff7f0e", linewidth=1.5))

    algo_y = 3.8
    algo_color = "#E6F3FF"
    algo_nodes = [
        ((0.1, algo_y - 0.4, 1.5, 0.8), "ResNet50\n微调模型\n(FAKE/REAL)", 0.85),
        ((1.8, algo_y - 0.4, 1.5, 0.8), "CLIP\n多模态分类\n(7个类别)", 2.55),
        ((3.5, algo_y - 0.4, 1.5, 0.8), "Grad-CAM\n热力图生成\n可解释性", 4.25),
        ((5.2, algo_y - 0.4, 2.0, 0.8), "多维分析器\nseal/freq/edge\nface/logo", 6.2),
        ((7.4, algo_y - 0.4, 1.6, 0.8), "LLM分析\n辅助结论\n自然语言", 8.2),
    ]
    for (x, y, w, h), text, cx in algo_nodes:
        ec = "#17becf" if "多维分析器" in text else "#d62728"
        fc = "#E6F7FF" if "多维分析器" in text else algo_color
        rect = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.05", edgecolor=ec, facecolor=fc, linewidth=2)
        ax.add_patch(rect)
        ax.text(cx, algo_y, text, ha="center", va="center", fontsize=8, fontweight="bold")

    for rx, axx in [(1.2, 0.85), (3.3, 2.55), (5.4, 4.25), (5.4, 6.2), (7.5, 8.2)]:
        ax.add_patch(FancyArrowPatch((rx, route_y - 0.38), (axx, algo_y + 0.4), arrowstyle="->", mutation_scale=14, color="#2ca02c", linewidth=1.2))

    storage_y = 2
    storage = [
        ((0.8, storage_y - 0.4), 2, "数据库\n(SQLite+异步驱动)", 1.8),
        ((3.2, storage_y - 0.4), 2, "缓存系统\n(Redis + SHA-256)", 4.2),
        ((5.6, storage_y - 0.4), 2, "模型仓库\n(.pth权重文件)", 6.6),
        ((7.8, storage_y - 0.4), 1.8, "6维综合\n评分输出\n(0-100)", 8.7),
    ]
    for (xy, w, text, cx) in storage:
        rect = FancyBboxPatch(xy, w, 0.8, boxstyle="round,pad=0.05", edgecolor="#9467bd", facecolor="#FFE6E6", linewidth=2)
        if "6维综合" in text:
            rect = FancyBboxPatch(xy, w, 0.8, boxstyle="round,pad=0.05", edgecolor="#17becf", facecolor="#E6F7FF", linewidth=2)
        ax.add_patch(rect)
        ax.text(cx, storage_y, text, ha="center", va="center", fontsize=8 if "6维" in text else 9, fontweight="bold")

    ax.add_patch(FancyArrowPatch((2.55, algo_y - 0.4), (1.8, storage_y + 0.4), arrowstyle="<->", mutation_scale=15, color="#d62728", linewidth=1.5))
    ax.add_patch(FancyArrowPatch((3.0, algo_y - 0.4), (4.2, storage_y + 0.4), arrowstyle="<->", mutation_scale=15, color="#d62728", linewidth=1.5))
    ax.add_patch(FancyArrowPatch((0.85, algo_y - 0.4), (6.6, storage_y + 0.4), arrowstyle="->", mutation_scale=15, color="#d62728", linewidth=1.5))
    ax.add_patch(FancyArrowPatch((6.2, algo_y - 0.4), (8.7, storage_y + 0.4), arrowstyle="->", mutation_scale=15, color="#17becf", linewidth=1.5))

    ax.text(0.3, 0.5, "数据流向: 用户交互 → FastAPI路由 → 模型推理 → 数据存储 → 结果反馈", fontsize=9, fontweight="bold", bbox=dict(boxstyle="round", facecolor="#FFFFCC", alpha=0.8))
    plt.tight_layout()
    return fig


def draw_single_image_detection():
    fig, ax = plt.subplots(figsize=(14, 10))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 10)
    ax.axis("off")
    ax.text(5, 9.7, "单图检测算法数据流 (ResNet50 + Grad-CAM)", fontsize=16, fontweight="bold", ha="center")

    stage1_y = 8.8
    ax.add_patch(FancyBboxPatch((0.5, stage1_y - 0.4), 2, 0.8, boxstyle="round,pad=0.05", edgecolor="#1f77b4", facecolor="#E8F4F8", linewidth=2))
    ax.add_patch(FancyBboxPatch((3.0, stage1_y - 0.4), 2, 0.8, boxstyle="round,pad=0.05", edgecolor="#17becf", facecolor="#E6F7FF", linewidth=2))
    ax.add_patch(FancyBboxPatch((5.5, stage1_y - 0.4), 1.8, 0.8, boxstyle="round,pad=0.05", edgecolor="#17becf", facecolor="#E6F7FF", linewidth=2))
    ax.add_patch(FancyBboxPatch((7.8, stage1_y - 0.4), 1.8, 0.8, boxstyle="round,pad=0.05", edgecolor="#2ca02c", facecolor="#E6FFE6", linewidth=2))
    ax.text(1.5, stage1_y, "图片输入\n(PIL Image)", ha="center", va="center", fontsize=10, fontweight="bold")
    ax.text(4.0, stage1_y, "1. RGB转换\n2. 缩放(224×224)", ha="center", va="center", fontsize=9)
    ax.text(6.4, stage1_y, "张量化\nImageNet\n归一化", ha="center", va="center", fontsize=8)
    ax.text(8.7, stage1_y, "张量输出\n(1,3,224,224)", ha="center", va="center", fontsize=9)
    for s, e in [(2.5, 3.0), (5.0, 5.5), (7.3, 7.8)]:
        ax.add_patch(FancyArrowPatch((s, stage1_y), (e, stage1_y), arrowstyle="->", mutation_scale=15, color="#1f77b4", linewidth=1.5))
    ax.text(5, stage1_y + 0.7, "阶段1: 输入预处理", fontsize=11, fontweight="bold", bbox=dict(boxstyle="round", facecolor="#FFFFCC", alpha=0.7))

    stage2_y = 7.3
    ax.add_patch(FancyBboxPatch((1, stage2_y - 0.5), 3.5, 1, boxstyle="round,pad=0.05", edgecolor="#d62728", facecolor="#FFE6E6", linewidth=2))
    ax.add_patch(FancyBboxPatch((5, stage2_y - 0.5), 2, 1, boxstyle="round,pad=0.05", edgecolor="#d62728", facecolor="#FFE6E6", linewidth=2))
    ax.add_patch(FancyBboxPatch((7.5, stage2_y - 0.5), 2, 1, boxstyle="round,pad=0.05", edgecolor="#d62728", facecolor="#FFE6E6", linewidth=2))
    ax.text(2.75, stage2_y, "ResNet50 主干网络\n(预训练权重微调)\n\nconv1 → layer1/2/3/4", ha="center", va="center", fontsize=10, fontweight="bold")
    ax.text(6, stage2_y, "中间特征\n(layer4输出)\nshape:(1,2048,7,7)", ha="center", va="center", fontsize=8)
    ax.text(8.5, stage2_y, "全连接层\n2048 → 2\n\n输出logits\n(1,2)", ha="center", va="center", fontsize=9)
    ax.add_patch(FancyArrowPatch((8.7, stage1_y - 0.4), (2.75, stage2_y + 0.5), arrowstyle="->", mutation_scale=15, color="#d62728", linewidth=2))
    ax.add_patch(FancyArrowPatch((4.5, stage2_y), (5, stage2_y), arrowstyle="->", mutation_scale=15, color="#d62728", linewidth=1.5))
    ax.add_patch(FancyArrowPatch((7, stage2_y), (7.5, stage2_y), arrowstyle="->", mutation_scale=15, color="#d62728", linewidth=1.5))
    ax.text(5, stage2_y + 0.8, "阶段2: 深度学习推理", fontsize=11, fontweight="bold", bbox=dict(boxstyle="round", facecolor="#FFFFCC", alpha=0.7))

    stage3_y = 5.5
    ax.add_patch(FancyBboxPatch((1, stage3_y - 0.4), 2.5, 0.8, boxstyle="round,pad=0.05", edgecolor="#ff7f0e", facecolor="#FFF4E6", linewidth=2))
    ax.add_patch(FancyBboxPatch((4, stage3_y - 0.4), 3, 0.8, boxstyle="round,pad=0.05", edgecolor="#ff7f0e", facecolor="#FFF4E6", linewidth=2))
    ax.add_patch(FancyBboxPatch((7.3, stage3_y - 0.4), 2.3, 0.8, boxstyle="round,pad=0.05", edgecolor="#ff7f0e", facecolor="#FFF4E6", linewidth=2))
    ax.text(2.25, stage3_y, "Softmax\n概率计算", ha="center", va="center", fontsize=10, fontweight="bold")
    ax.text(5.5, stage3_y, "FAKE: 45% | REAL: 55%\n置信度评估", ha="center", va="center", fontsize=9)
    ax.text(8.45, stage3_y, "规则化解释\n(置信度等级)", ha="center", va="center", fontsize=9)
    ax.add_patch(FancyArrowPatch((9.5, stage2_y - 0.5), (2.25, stage3_y + 0.4), arrowstyle="->", mutation_scale=15, color="#ff7f0e", linewidth=2))
    ax.add_patch(FancyArrowPatch((3.5, stage3_y), (4, stage3_y), arrowstyle="->", mutation_scale=15, color="#ff7f0e", linewidth=1.5))
    ax.add_patch(FancyArrowPatch((7, stage3_y), (7.3, stage3_y), arrowstyle="->", mutation_scale=15, color="#ff7f0e", linewidth=1.5))
    ax.text(5, stage3_y + 0.7, "阶段3: 结果获取", fontsize=11, fontweight="bold", bbox=dict(boxstyle="round", facecolor="#FFFFCC", alpha=0.7))

    stage4_y = 3.8
    ax.text(5, stage4_y + 0.8, "阶段4: Grad-CAM 可解释性分析（可选）", fontsize=11, fontweight="bold", bbox=dict(boxstyle="round", facecolor="#FFFFCC", alpha=0.7))
    gradcam_steps = [("layer4\n收集梯度", 1.5), ("计算权重\nW=∂L/∂A", 3.2), ("加权求和\nCAM=ΣwA", 4.9), ("ReLU激活\nmax(CAM,0)", 6.6), ("双线性\n插值224×224", 8.3)]
    for i, (step, x) in enumerate(gradcam_steps):
        color = "#FFE6E6" if i % 2 == 0 else "#E6F7FF"
        ax.add_patch(FancyBboxPatch((x - 0.6, stage4_y - 0.35), 1.2, 0.7, boxstyle="round,pad=0.03", edgecolor="#d62728", facecolor=color, linewidth=1.5))
        ax.text(x, stage4_y, step, ha="center", va="center", fontsize=8)
        if i < len(gradcam_steps) - 1:
            ax.add_patch(FancyArrowPatch((x + 0.6, stage4_y), (x + 0.9, stage4_y), arrowstyle="->", mutation_scale=12, color="#d62728", linewidth=1.5))
    ax.add_patch(FancyBboxPatch((1.5, stage4_y - 1.2), 7, 0.6, boxstyle="round,pad=0.05", edgecolor="#d62728", facecolor="#FFE6E6", linewidth=2))
    ax.text(5, stage4_y - 0.9, "热力图输出：overlay热力图到原图 → Base64 JPEG编码", ha="center", va="center", fontsize=9, fontweight="bold")

    stage5_y = 1.5
    output_items = ["标签\n(FAKE/REAL)", "置信度\n(0-100%)", "概率分布\n[p_fake, p_real]", "热力图\n(Base64)", "文本解释\n(规则库)"]
    for i, item in enumerate(output_items):
        x = 1 + i * 1.8
        ax.add_patch(FancyBboxPatch((x - 0.7, stage5_y - 0.35), 1.4, 0.7, boxstyle="round,pad=0.05", edgecolor="#2ca02c", facecolor="#E6FFE6", linewidth=2))
        ax.text(x, stage5_y, item, ha="center", va="center", fontsize=8, fontweight="bold")
        ax.add_patch(FancyArrowPatch((x, stage4_y - 1.2), (x, stage5_y + 0.35), arrowstyle="->", mutation_scale=12, color="#2ca02c", linewidth=1.5))
    ax.text(5, stage5_y + 1, "阶段5: 结构化输出", fontsize=11, fontweight="bold", bbox=dict(boxstyle="round", facecolor="#FFFFCC", alpha=0.7))
    ax.text(0.3, 0.3, "核心函数: detect_image() | 热力图函数: grad_cam_overlay()", fontsize=9, style="italic", bbox=dict(boxstyle="round", facecolor="#CCCCCC", alpha=0.5))

    plt.tight_layout()
    return fig


def draw_clip_multimodal_flow():
    fig, ax = plt.subplots(figsize=(16, 10))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 10)
    ax.axis("off")

    ax.text(5, 9.7, "CLIP 多模态分析数据流（内容分类 + 图文一致性检测）", fontsize=16, fontweight="bold", ha="center")

    ax.text(2.5, 9.1, "内容分类流程", fontsize=12, fontweight="bold", bbox=dict(boxstyle="round", facecolor="#FFE6CC", alpha=0.8))
    ax.add_patch(FancyBboxPatch((0.5, 8.2), 1.5, 0.6, boxstyle="round,pad=0.05", edgecolor="#1f77b4", facecolor="#E8F4F8", linewidth=2))
    ax.add_patch(FancyBboxPatch((0.5, 7.2), 1.5, 0.6, boxstyle="round,pad=0.05", edgecolor="#2ca02c", facecolor="#E6FFE6", linewidth=2))
    ax.add_patch(FancyBboxPatch((0.2, 6.2), 2.1, 0.6, boxstyle="round,pad=0.05", edgecolor="#2ca02c", facecolor="#E6FFE6", linewidth=2))
    ax.text(1.25, 8.5, "图片输入", ha="center", va="center", fontsize=10, fontweight="bold")
    ax.text(1.25, 7.5, "CLIP\n图像编码器", ha="center", va="center", fontsize=9, fontweight="bold")
    ax.text(1.25, 6.5, "图像特征\nfeature_img ∈ R^512\n(单位向量)", ha="center", va="center", fontsize=8)
    ax.add_patch(FancyArrowPatch((1.25, 8.2), (1.25, 7.8), arrowstyle="->", mutation_scale=15, color="#1f77b4", linewidth=2))
    ax.add_patch(FancyArrowPatch((1.25, 7.2), (1.25, 6.8), arrowstyle="->", mutation_scale=15, color="#2ca02c", linewidth=2))

    categories = ["人物", "动物", "建筑", "风景", "食物", "交通", "其他"]
    ax.add_patch(FancyBboxPatch((3.2, 7.5), 1.5, 1.3, boxstyle="round,pad=0.05", edgecolor="#ff7f0e", facecolor="#FFF4E6", linewidth=2))
    ax.text(3.95, 8.4, "7类标签\n+ 提示词", ha="center", va="center", fontsize=9, fontweight="bold")
    for i, cat in enumerate(categories):
        ax.text(3.95, 8.1 - i * 0.15, f"• {cat}", ha="center", va="center", fontsize=7)

    ax.add_patch(FancyBboxPatch((3.2, 6.2), 1.5, 0.6, boxstyle="round,pad=0.05", edgecolor="#ff7f0e", facecolor="#FFF4E6", linewidth=2))
    ax.add_patch(FancyBboxPatch((3.2, 5.2), 1.5, 0.6, boxstyle="round,pad=0.05", edgecolor="#ff7f0e", facecolor="#FFF4E6", linewidth=2))
    ax.text(3.95, 6.5, "CLIP文本\n编码器×7", ha="center", va="center", fontsize=9, fontweight="bold")
    ax.text(3.95, 5.5, "7类文本\n特征矩阵\n(7,512)", ha="center", va="center", fontsize=8)
    ax.add_patch(FancyArrowPatch((3.95, 7.5), (3.95, 6.8), arrowstyle="->", mutation_scale=15, color="#ff7f0e", linewidth=2))
    ax.add_patch(FancyArrowPatch((3.95, 6.2), (3.95, 5.8), arrowstyle="->", mutation_scale=15, color="#ff7f0e", linewidth=2))

    ax.add_patch(FancyBboxPatch((1.5, 4.8), 2.5, 0.8, boxstyle="round,pad=0.05", edgecolor="#d62728", facecolor="#FFE6E6", linewidth=2))
    ax.text(2.75, 5.2, "余弦相似度计算\nsim = img @ text.T\nshape: (7,)", ha="center", va="center", fontsize=9, fontweight="bold")
    ax.add_patch(FancyArrowPatch((1.25, 6.2), (2.2, 5.3), arrowstyle="->", mutation_scale=15, color="#2ca02c", linewidth=1.5))
    ax.add_patch(FancyArrowPatch((3.95, 5.2), (3.3, 5.3), arrowstyle="->", mutation_scale=15, color="#ff7f0e", linewidth=1.5))

    ax.add_patch(FancyBboxPatch((0.8, 3.5), 3.5, 0.7, boxstyle="round,pad=0.05", edgecolor="#2ca02c", facecolor="#E6FFE6", linewidth=2))
    ax.text(2.55, 3.85, "分类结果: argmax(sims) → category_label", ha="center", va="center", fontsize=9, fontweight="bold")
    ax.add_patch(FancyArrowPatch((2.75, 4.8), (2.55, 4.2), arrowstyle="->", mutation_scale=15, color="#d62728", linewidth=2))

    ax.text(7.5, 9.1, "图文一致性检测流程", fontsize=12, fontweight="bold", bbox=dict(boxstyle="round", facecolor="#E6F7FF", alpha=0.8))
    ax.add_patch(FancyBboxPatch((5.8, 8.2), 1.5, 0.6, boxstyle="round,pad=0.05", edgecolor="#1f77b4", facecolor="#E8F4F8", linewidth=2))
    ax.add_patch(FancyBboxPatch((5.8, 7.2), 1.5, 0.6, boxstyle="round,pad=0.05", edgecolor="#2ca02c", facecolor="#E6FFE6", linewidth=2))
    ax.add_patch(FancyBboxPatch((5.5, 6.2), 2.1, 0.6, boxstyle="round,pad=0.05", edgecolor="#2ca02c", facecolor="#E6FFE6", linewidth=2))
    ax.text(6.55, 8.5, "图片+文本", ha="center", va="center", fontsize=10, fontweight="bold")
    ax.text(6.55, 7.5, "CLIP\n图像编码器", ha="center", va="center", fontsize=9, fontweight="bold")
    ax.text(6.55, 6.5, "图像特征\nfeature_img\n(单位向量)", ha="center", va="center", fontsize=8)
    ax.add_patch(FancyArrowPatch((6.55, 8.2), (6.55, 7.8), arrowstyle="->", mutation_scale=15, color="#1f77b4", linewidth=2))
    ax.add_patch(FancyArrowPatch((6.55, 7.2), (6.55, 6.8), arrowstyle="->", mutation_scale=15, color="#2ca02c", linewidth=2))

    ax.add_patch(FancyBboxPatch((8.3, 6.8), 1.5, 1.3, boxstyle="round,pad=0.05", edgecolor="#ff7f0e", facecolor="#FFF4E6", linewidth=2))
    ax.add_patch(FancyBboxPatch((8.3, 5.8), 1.5, 0.6, boxstyle="round,pad=0.05", edgecolor="#ff7f0e", facecolor="#FFF4E6", linewidth=2))
    ax.text(9.05, 7.8, "7个提示词", ha="center", va="center", fontsize=9, fontweight="bold")
    ax.text(9.05, 7.4, "●4个对齐", ha="center", va="center", fontsize=8)
    ax.text(9.05, 7.1, "●3个不对齐", ha="center", va="center", fontsize=8)
    ax.text(9.05, 6.8, "(基线)", ha="center", va="center", fontsize=7, style="italic")
    ax.text(9.05, 6.1, "CLIP文本\n编码器×7", ha="center", va="center", fontsize=9, fontweight="bold")
    ax.add_patch(FancyArrowPatch((9.05, 6.8), (9.05, 6.4), arrowstyle="->", mutation_scale=15, color="#ff7f0e", linewidth=2))

    ax.add_patch(FancyBboxPatch((6.8, 4.8), 2.5, 0.8, boxstyle="round,pad=0.05", edgecolor="#d62728", facecolor="#FFE6E6", linewidth=2))
    ax.text(8.05, 5.2, "相似度计算\nsim[0:4] 对齐均值\nsim[4:7] 不对齐均值", ha="center", va="center", fontsize=8, fontweight="bold")
    ax.add_patch(FancyArrowPatch((6.55, 6.2), (7.5, 5.3), arrowstyle="->", mutation_scale=15, color="#2ca02c", linewidth=1.5))
    ax.add_patch(FancyArrowPatch((9.05, 5.8), (8.6, 5.3), arrowstyle="->", mutation_scale=15, color="#ff7f0e", linewidth=1.5))

    ax.add_patch(FancyBboxPatch((6.2, 3.5), 3.5, 0.7, boxstyle="round,pad=0.05", edgecolor="#2ca02c", facecolor="#E6FFE6", linewidth=2))
    ax.text(8.05, 3.85, "一致性评分 gap_norm→[0,100]", ha="center", va="center", fontsize=9, fontweight="bold")
    ax.add_patch(FancyArrowPatch((8.05, 4.8), (8.05, 4.2), arrowstyle="->", mutation_scale=15, color="#d62728", linewidth=2))

    summary_y = 2.5
    ax.text(5, summary_y + 0.5, "综合数据流总结", fontsize=12, fontweight="bold", bbox=dict(boxstyle="round", facecolor="#FFFFCC", alpha=0.8))
    flow_text = "图像 → CLIP ViT-B/32编码器 (512维特征)\n分支1: 7类标签 → Softmax概率 → 分类标签\n分支2: 4对齐+3不对齐文本 → 相似度计算 → 一致性评分"
    ax.add_patch(FancyBboxPatch((1, summary_y - 1.3), 8, 1.5, boxstyle="round,pad=0.1", edgecolor="#9467bd", facecolor="#F0E6FF", linewidth=2))
    ax.text(5, summary_y - 0.55, flow_text, ha="center", va="center", fontsize=9)

    ax.text(0.3, 0.3, "核心函数: classify_image() | classify_text_image_consistency()", fontsize=9, style="italic", bbox=dict(boxstyle="round", facecolor="#CCCCCC", alpha=0.5))
    plt.tight_layout()
    return fig


def draw_url_batch_detection_flow():
    fig, ax = plt.subplots(figsize=(16, 10))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 10)
    ax.axis("off")

    ax.text(5, 9.7, "批量文件检测与实时进度推送数据流", fontsize=16, fontweight="bold", ha="center")

    layer1_y = 8.8
    ax.add_patch(FancyBboxPatch((1, layer1_y - 0.4), 3.5, 0.8, boxstyle="round,pad=0.05", edgecolor="#1f77b4", facecolor="#E8F4F8", linewidth=2))
    ax.add_patch(FancyBboxPatch((5.5, layer1_y - 0.4), 3.5, 0.8, boxstyle="round,pad=0.05", edgecolor="#1f77b4", facecolor="#E8F4F8", linewidth=2))
    ax.text(2.75, layer1_y, "用户上传文件\n(图片/文档, 最多50个)", ha="center", va="center", fontsize=10, fontweight="bold")
    ax.text(7.25, layer1_y, "POST /api/detect-batch-init\nPOST /api/detect-batch-run", ha="center", va="center", fontsize=10, fontweight="bold")
    ax.text(5, layer1_y + 0.7, "第1层: 用户请求", fontsize=11, fontweight="bold", bbox=dict(boxstyle="round", facecolor="#FFFFCC", alpha=0.7))
    ax.add_patch(FancyArrowPatch((4.5, layer1_y), (5.5, layer1_y), arrowstyle="->", mutation_scale=15, color="#1f77b4", linewidth=2))

    layer2_y = 7.3
    steps_layer2 = [("读取上传\nUploadFile", 1), ("类型判断\n图片/文档", 2.8), ("文档抽图\nextract_images", 4.6), ("图像标准化\nRGB转换", 6.4), ("构建items\nfilename/raw", 8.2)]
    for step, x in steps_layer2:
        ax.add_patch(FancyBboxPatch((x - 0.7, layer2_y - 0.35), 1.4, 0.7, boxstyle="round,pad=0.05", edgecolor="#2ca02c", facecolor="#E6FFE6", linewidth=1.5))
        ax.text(x, layer2_y, step, ha="center", va="center", fontsize=8)
        if x < 8.2:
            ax.add_patch(FancyArrowPatch((x + 0.7, layer2_y), (x + 1, layer2_y), arrowstyle="->", mutation_scale=12, color="#2ca02c", linewidth=1.5))
    ax.text(5, layer2_y + 0.7, "第2层: 文件预处理与图片收集", fontsize=11, fontweight="bold", bbox=dict(boxstyle="round", facecolor="#FFFFCC", alpha=0.7))
    ax.add_patch(FancyArrowPatch((7.25, layer1_y - 0.4), (5, layer2_y + 0.35), arrowstyle="->", mutation_scale=15, color="#1f77b4", linewidth=2))

    layer3_y = 5.8
    ax.add_patch(FancyBboxPatch((0.8, layer3_y - 0.5), 3.5, 1, boxstyle="round,pad=0.05", edgecolor="#d62728", facecolor="#FFE6E6", linewidth=2))
    ax.add_patch(FancyBboxPatch((5, layer3_y - 0.5), 4.2, 1, boxstyle="round,pad=0.05", edgecolor="#ff7f0e", facecolor="#FFF4E6", linewidth=2))
    ax.text(2.55, layer3_y, "创建后台任务\n(asyncio.create_task)\n\n绑定job_id与user_id", ha="center", va="center", fontsize=9, fontweight="bold")
    ax.text(7.1, layer3_y + 0.15, "Job Queue\n(asyncio.Queue)", ha="center", va="center", fontsize=9, fontweight="bold")
    ax.text(7.1, layer3_y - 0.25, "[start] [result] [item_skip] [complete]\n(事件流)", ha="center", va="center", fontsize=8, style="italic")
    ax.add_patch(FancyArrowPatch((8.9, layer2_y - 0.35), (7.1, layer3_y + 0.5), arrowstyle="->", mutation_scale=15, color="#2ca02c", linewidth=2))
    ax.add_patch(FancyArrowPatch((4.3, layer3_y), (5, layer3_y), arrowstyle="->", mutation_scale=15, color="#d62728", linewidth=2))
    ax.text(5, layer3_y + 0.8, "第3层: 异步任务编排", fontsize=11, fontweight="bold", bbox=dict(boxstyle="round", facecolor="#FFFFCC", alpha=0.7))

    layer4_y = 4
    ax.add_patch(FancyBboxPatch((1.5, layer4_y - 0.5), 3, 1, boxstyle="round,pad=0.05", edgecolor="#d62728", facecolor="#FFE6E6", linewidth=2))
    ax.add_patch(FancyBboxPatch((5, layer4_y - 0.5), 2.5, 1, boxstyle="round,pad=0.05", edgecolor="#17becf", facecolor="#E6F7FF", linewidth=2))
    ax.add_patch(FancyBboxPatch((7.8, layer4_y - 0.5), 1.8, 1, boxstyle="round,pad=0.05", edgecolor="#ff7f0e", facecolor="#FFF4E6", linewidth=2))
    ax.text(3, layer4_y, "detect_batch([single])\n逐项推理\n\n输出label/conf/probs\n+ explanation", ha="center", va="center", fontsize=9, fontweight="bold")
    ax.text(6.25, layer4_y, "Redis缓存\nget/set_cached_result\n(SHA-256键)", ha="center", va="center", fontsize=8, fontweight="bold")
    ax.text(8.7, layer4_y, "CLIP\nclassify_image\n+ 缩略图\nthumbnail", ha="center", va="center", fontsize=8, fontweight="bold")
    ax.add_patch(FancyArrowPatch((7.1, layer3_y - 0.5), (3, layer4_y + 0.5), arrowstyle="->", mutation_scale=15, color="#ff7f0e", linewidth=2))
    ax.add_patch(FancyArrowPatch((3, layer4_y - 0.5), (6.25, layer4_y), arrowstyle="<->", mutation_scale=15, color="#17becf", linewidth=1.5))
    ax.add_patch(FancyArrowPatch((6, layer4_y), (7.8, layer4_y), arrowstyle="->", mutation_scale=15, color="#ff7f0e", linewidth=1.5))
    ax.text(5, layer4_y + 0.8, "第4层: 模型推理与结果组装", fontsize=11, fontweight="bold", bbox=dict(boxstyle="round", facecolor="#FFFFCC", alpha=0.7))

    layer5_y = 2
    ax.add_patch(FancyBboxPatch((0.5, layer5_y - 0.5), 4, 1, boxstyle="round,pad=0.05", edgecolor="#9467bd", facecolor="#F0E6FF", linewidth=2))
    ax.add_patch(FancyBboxPatch((5, layer5_y - 0.5), 4.5, 1, boxstyle="round,pad=0.05", edgecolor="#9467bd", facecolor="#F0E6FF", linewidth=2))
    ax.text(2.5, layer5_y, "WebSocket /ws/detect/{job_id}\n实时推送进度事件\n\nEvent:\nstart/result/item_skip/complete", ha="center", va="center", fontsize=9, fontweight="bold")
    ax.text(7.25, layer5_y, "前端客户端\n实时显示任务进度\n\n已完成/总数\n卡片: 缩略图+标签+分类", ha="center", va="center", fontsize=9, fontweight="bold")
    ax.add_patch(FancyArrowPatch((4.5, layer4_y - 0.5), (2.5, layer5_y + 0.5), arrowstyle="->", mutation_scale=15, color="#9467bd", linewidth=2))
    ax.add_patch(FancyArrowPatch((2.5, layer5_y - 0.5), (7.25, layer5_y + 0.5), arrowstyle="->", mutation_scale=15, color="#9467bd", linewidth=2))
    ax.text(5, layer5_y + 0.8, "第5层: 实时反馈与交互", fontsize=11, fontweight="bold", bbox=dict(boxstyle="round", facecolor="#FFFFCC", alpha=0.7))
    ax.text(5, 0.8, "最终状态: {type: \"complete\", count: N}", fontsize=10, fontweight="bold", bbox=dict(boxstyle="round", facecolor="#E6FFE6", alpha=0.8))

    plt.tight_layout()
    return fig


def draw_report_generation_workflow():
    fig, ax = plt.subplots(figsize=(14, 10))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 10)
    ax.axis("off")
    ax.text(5, 9.7, "检测报告生成与PDF/Excel导出工作流", fontsize=16, fontweight="bold", ha="center")

    stage1_y = 8.8
    ax.text(5, stage1_y + 0.6, "阶段1: 检测数据聚合", fontsize=11, fontweight="bold", bbox=dict(boxstyle="round", facecolor="#FFFFCC", alpha=0.7))
    data_sources = [("检测ID\n(detection_id)", 0.8), ("检测结果\n(label/conf)", 2.3), ("概率明细\n(probs_json)", 3.8), ("图片来源\n(image_url)", 5.3), ("模型版本\n(model_version)", 6.8), ("时间戳\n(created_at)", 8.3)]
    for source, x in data_sources:
        ax.add_patch(FancyBboxPatch((x - 0.5, stage1_y - 0.35), 1, 0.7, boxstyle="round,pad=0.03", edgecolor="#1f77b4", facecolor="#E8F4F8", linewidth=1.5))
        ax.text(x, stage1_y, source, ha="center", va="center", fontsize=7, fontweight="bold")

    stage2_y = 7.5
    ax.text(5, stage2_y + 0.6, "阶段2: 数据库查询与聚合", fontsize=11, fontweight="bold", bbox=dict(boxstyle="round", facecolor="#FFFFCC", alpha=0.7))
    ax.add_patch(FancyBboxPatch((1.5, stage2_y - 0.5), 7, 1, boxstyle="round,pad=0.05", edgecolor="#ff7f0e", facecolor="#FFF4E6", linewidth=2))
    ax.text(5, stage2_y + 0.15, "generate_report(detection_id) 数据库查询与合并", ha="center", va="center", fontsize=10, fontweight="bold")
    ax.text(5, stage2_y - 0.25, "SELECT * FROM detection_records WHERE id=?", ha="center", va="center", fontsize=9, style="italic", family="monospace")
    for x in np.linspace(1.3, 8.5, 6):
        ax.add_patch(FancyArrowPatch((x, stage1_y - 0.35), (5, stage2_y + 0.5), arrowstyle="->", mutation_scale=12, color="#1f77b4", linewidth=1, alpha=0.6))

    stage3_y = 6
    ax.text(5, stage3_y + 0.6, "阶段3: 结构化报告生成", fontsize=11, fontweight="bold", bbox=dict(boxstyle="round", facecolor="#FFFFCC", alpha=0.7))
    report_sections = [("基本信息\nID/时间", 1.2), ("检测结果\n标签/置信度", 2.5), ("概率分布\nprobs[]", 3.8), ("结论摘要\nconclusion", 5.1), ("审核建议\nsuggestion", 6.4), ("模型与哈希\nversion/hash", 7.7), ("图片来源\nimage_url", 8.8)]
    for section, x in report_sections:
        ax.add_patch(FancyBboxPatch((x - 0.55, stage3_y - 0.35), 1.1, 0.7, boxstyle="round,pad=0.03", edgecolor="#2ca02c", facecolor="#E6FFE6", linewidth=1.5))
        ax.text(x, stage3_y, section, ha="center", va="center", fontsize=7, fontweight="bold")
        ax.add_patch(FancyArrowPatch((5, stage2_y - 0.5), (x, stage3_y + 0.35), arrowstyle="->", mutation_scale=12, color="#ff7f0e", linewidth=1, alpha=0.6))

    stage4_y = 4.5
    ax.text(5, stage4_y + 0.8, "阶段4: 导出接口与格式分支", fontsize=11, fontweight="bold", bbox=dict(boxstyle="round", facecolor="#FFFFCC", alpha=0.7))
    ax.add_patch(FancyBboxPatch((3.5, stage4_y + 0.2), 3, 0.6, boxstyle="round,pad=0.05", edgecolor="#d62728", facecolor="#FFE6E6", linewidth=2))
    ax.text(5, stage4_y + 0.5, "GET /api/report/{id}/export?format=pdf|excel", ha="center", va="center", fontsize=10, fontweight="bold")
    ax.add_patch(FancyArrowPatch((5, stage3_y - 0.35), (5, stage4_y + 0.2), arrowstyle="->", mutation_scale=15, color="#2ca02c", linewidth=2))

    ax.add_patch(FancyBboxPatch((1, stage4_y - 0.8), 2.5, 0.8, boxstyle="round,pad=0.05", edgecolor="#9467bd", facecolor="#F0E6FF", linewidth=2))
    ax.add_patch(FancyBboxPatch((4, stage4_y - 0.8), 2.5, 0.8, boxstyle="round,pad=0.05", edgecolor="#9467bd", facecolor="#F0E6FF", linewidth=2))
    ax.add_patch(FancyBboxPatch((7, stage4_y - 0.8), 2.5, 0.8, boxstyle="round,pad=0.05", edgecolor="#9467bd", facecolor="#F0E6FF", linewidth=2))
    ax.text(2.25, stage4_y - 0.4, "PDF导出\n(reportlab/WeasyPrint)\n\n+ 水印\n+ 横幅", ha="center", va="center", fontsize=9, fontweight="bold")
    ax.text(5.25, stage4_y - 0.4, "Excel导出\n(openpyxl)\n\n+ 多Sheet\n+ 样式", ha="center", va="center", fontsize=9, fontweight="bold")
    ax.text(8.25, stage4_y - 0.4, "POST /api/report/generate\n\n返回report_dict\n(结构化JSON)", ha="center", va="center", fontsize=9, fontweight="bold")
    ax.add_patch(FancyArrowPatch((4, stage4_y + 0.2), (2.25, stage4_y), arrowstyle="->", mutation_scale=15, color="#d62728", linewidth=2))
    ax.add_patch(FancyArrowPatch((5, stage4_y + 0.2), (5.25, stage4_y), arrowstyle="->", mutation_scale=15, color="#d62728", linewidth=2))
    ax.add_patch(FancyArrowPatch((6, stage4_y + 0.2), (8.25, stage4_y), arrowstyle="->", mutation_scale=15, color="#d62728", linewidth=2))

    stage5_y = 2.5
    ax.text(5, stage5_y + 0.6, "阶段5: 文件输出与传输", fontsize=11, fontweight="bold", bbox=dict(boxstyle="round", facecolor="#FFFFCC", alpha=0.7))
    output_files = [("report_ID.pdf\n(字节流)", 1.5), ("report_ID.xlsx\n(字节流)", 3.5), ("report_dict\n(JSON响应体)", 5.5), ("DetectionRecord\nSQLite存储", 7.5)]
    for file_type, x in output_files:
        ax.add_patch(FancyBboxPatch((x - 0.8, stage5_y - 0.35), 1.6, 0.7, boxstyle="round,pad=0.05", edgecolor="#17becf", facecolor="#E6F7FF", linewidth=1.5))
        ax.text(x, stage5_y, file_type, ha="center", va="center", fontsize=8, fontweight="bold")
    for x_from, x_to in [(2.25, 1.5), (5.25, 3.5), (8.25, 5.5)]:
        ax.add_patch(FancyArrowPatch((x_from, stage4_y - 0.8), (x_to, stage5_y + 0.35), arrowstyle="->", mutation_scale=15, color="#9467bd", linewidth=1.5))
    ax.add_patch(FancyArrowPatch((5, stage3_y - 0.35), (7.5, stage5_y + 0.35), arrowstyle="->", mutation_scale=15, color="#d62728", linewidth=1.5))

    stage6_y = 1
    ax.text(5, stage6_y + 0.5, "阶段6: HTTP响应与下载", fontsize=11, fontweight="bold", bbox=dict(boxstyle="round", facecolor="#FFFFCC", alpha=0.7))
    ax.add_patch(FancyBboxPatch((1, stage6_y - 0.3), 8, 0.6, boxstyle="round,pad=0.05", edgecolor="#2ca02c", facecolor="#E6FFE6", linewidth=2))
    ax.text(5, stage6_y, "HTTP 200 + PDF/XLSX附件下载 + JSON生成接口返回", ha="center", va="center", fontsize=9, fontweight="bold")
    for x in [1.5, 3.5]:
        ax.add_patch(FancyArrowPatch((x, stage5_y - 0.35), (5, stage6_y + 0.3), arrowstyle="->", mutation_scale=12, color="#17becf", linewidth=1.5))

    ax.text(0.3, 0.1, "核心函数: generate_report() | export_pdf() | export_excel()", fontsize=9, style="italic", bbox=dict(boxstyle="round", facecolor="#CCCCCC", alpha=0.5))
    plt.tight_layout()
    return fig


def main():
    print("=" * 80)
    print("AIGI-Holmes 算法设计与数据流图生成")
    print("=" * 80)

    fig1 = draw_overall_architecture()
    fig1.savefig("01_整体系统架构与数据流.png", dpi=300, bbox_inches="tight")
    plt.close(fig1)
    print("✓ 已保存: 01_整体系统架构与数据流.png")

    fig2 = draw_single_image_detection()
    fig2.savefig("02_单图检测算法数据流.png", dpi=300, bbox_inches="tight")
    plt.close(fig2)
    print("✓ 已保存: 02_单图检测算法数据流.png")

    fig3 = draw_clip_multimodal_flow()
    fig3.savefig("03_CLIP多模态分析数据流.png", dpi=300, bbox_inches="tight")
    plt.close(fig3)
    print("✓ 已保存: 03_CLIP多模态分析数据流.png")

    fig4 = draw_url_batch_detection_flow()
    fig4.savefig("04_URL批量检测与实时进度推送.png", dpi=300, bbox_inches="tight")
    plt.close(fig4)
    print("✓ 已保存: 04_URL批量检测与实时进度推送.png")

    fig5 = draw_report_generation_workflow()
    fig5.savefig("05_检测报告生成与多格式导出.png", dpi=300, bbox_inches="tight")
    plt.close(fig5)
    print("✓ 已保存: 05_检测报告生成与多格式导出.png")

    print("=" * 80)
    print("所有数据流图已生成完毕")
    print("=" * 80)


if __name__ == "__main__":
    main()
