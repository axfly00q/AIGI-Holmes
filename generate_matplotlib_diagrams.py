#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成 AIGI-Holmes 五个核心模块的 matplotlib PNG 可视化图片。"""

from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

COLORS = {
    "bg": "#f8fafc",
    "text": "#1f2937",
    "blue_fill": "#dbeafe",
    "blue_edge": "#2563eb",
    "orange_fill": "#ffedd5",
    "orange_edge": "#ea580c",
    "green_fill": "#dcfce7",
    "green_edge": "#16a34a",
    "purple_fill": "#ede9fe",
    "purple_edge": "#7c3aed",
    "pink_fill": "#fce7f3",
    "pink_edge": "#db2777",
    "gray_fill": "#e2e8f0",
    "gray_edge": "#475569",
    "yellow_fill": "#fef3c7",
    "yellow_edge": "#d97706",
}


class DiagramGenerator:
    def __init__(self, output_dir: str):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _canvas(self, width: float, height: float, title: str):
        fig, ax = plt.subplots(figsize=(width, height))
        fig.patch.set_facecolor(COLORS["bg"])
        ax.set_facecolor(COLORS["bg"])
        ax.axis("off")
        ax.set_xlim(0, 16)
        ax.set_ylim(0, 10)
        ax.text(8, 9.55, title, ha="center", va="center", fontsize=18, fontweight="bold", color=COLORS["text"])
        return fig, ax

    def _box(self, ax, x, y, w, h, text, fill, edge, fontsize=10, bold=True):
        patch = FancyBboxPatch(
            (x - w / 2, y - h / 2),
            w,
            h,
            boxstyle="round,pad=0.08,rounding_size=0.08",
            linewidth=1.8,
            edgecolor=edge,
            facecolor=fill,
        )
        ax.add_patch(patch)
        ax.text(
            x,
            y,
            text,
            ha="center",
            va="center",
            fontsize=fontsize,
            fontweight="bold" if bold else "normal",
            color=COLORS["text"],
        )

    def _arrow(self, ax, x1, y1, x2, y2, color, lw=2.0):
        ax.annotate(
            "",
            xy=(x2, y2),
            xytext=(x1, y1),
            arrowprops={"arrowstyle": "->", "lw": lw, "color": color},
        )

    def _save(self, fig, name: str):
        target = self.output_dir / name
        fig.tight_layout()
        fig.savefig(target, dpi=300, bbox_inches="tight", facecolor="white")
        plt.close(fig)
        print(f"已生成: {target}")

    def generate_overview(self):
        fig, ax = self._canvas(16, 9, "AIGI-Holmes 五模块总体数据流总览")

        self._box(ax, 2.0, 7.8, 2.2, 0.9, "用户输入\n图片 / URL / 批量文件", COLORS["gray_fill"], COLORS["gray_edge"])
        self._box(ax, 5.0, 7.8, 2.2, 0.9, "接口层\nFastAPI 路由", COLORS["blue_fill"], COLORS["blue_edge"])
        self._box(ax, 8.0, 7.8, 2.4, 0.9, "detect.py\n核心能力聚合", COLORS["yellow_fill"], COLORS["yellow_edge"])
        self._box(ax, 11.2, 7.8, 2.4, 0.9, "数据库 / 缓存\n记录与复用", COLORS["pink_fill"], COLORS["pink_edge"])
        self._box(ax, 14.2, 7.8, 2.2, 0.9, "前端 / 报告\n页面展示与导出", COLORS["green_fill"], COLORS["green_edge"])

        for start, end in [(3.1, 3.9), (6.1, 6.8), (9.2, 10.0), (12.4, 13.1)]:
            self._arrow(ax, start, 7.8, end, 7.8, COLORS["gray_edge"], 2.4)

        modules = [
            (2.2, 4.8, "模块1\n模型加载", COLORS["blue_fill"], COLORS["blue_edge"]),
            (5.0, 4.8, "模块2\n单图检测", COLORS["orange_fill"], COLORS["orange_edge"]),
            (7.8, 4.8, "模块3\nURL处理", COLORS["green_fill"], COLORS["green_edge"]),
            (10.6, 4.8, "模块4\n批量检测", COLORS["purple_fill"], COLORS["purple_edge"]),
            (13.4, 4.8, "模块5\n结果可视化", COLORS["pink_fill"], COLORS["pink_edge"]),
        ]
        for x, y, text, fill, edge in modules:
            self._box(ax, x, y, 2.1, 1.0, text, fill, edge, fontsize=11)
            self._arrow(ax, 8.0, 7.25, x, 5.35, COLORS["gray_edge"], 1.8)

        self._box(ax, 8.0, 2.0, 11.8, 1.0, "整体链路：用户输入 -> 路由分发 -> 核心模块协同 -> 写库 / 缓存 -> 页面展示与报告导出", COLORS["gray_fill"], COLORS["gray_edge"], fontsize=11)
        self._save(fig, "00_五模块总体数据流总览.png")

    def generate_model_loading(self):
        fig, ax = self._canvas(16, 10, "模块1 模型加载模块数据流图")

        steps = [
            (2.2, 7.2, "导入 detect.py"),
            (5.0, 7.2, "确定 BASE_DIR\n兼容普通运行与打包环境"),
            (8.0, 7.2, "选择 DEVICE\nCPU 或 GPU"),
            (11.0, 7.2, "构建 ResNet50\n替换 fc 为 2 分类"),
            (13.8, 7.2, "加载 .pth 权重\nmodel.eval()"),
        ]
        for i, (x, y, text) in enumerate(steps):
            self._box(ax, x, y, 2.2, 1.0, text, COLORS["blue_fill"], COLORS["blue_edge"])
            if i < len(steps) - 1:
                self._arrow(ax, x + 1.1, y, steps[i + 1][0] - 1.1, y, COLORS["blue_edge"])

        lower = [
            (4.6, 4.6, "构建 _transform\nResize -> ToTensor -> Normalize"),
            (8.0, 4.6, "读取权重文件摘要\n计算 SHA-256"),
            (11.4, 4.6, "生成 MODEL_VERSION\n供写库与报告使用"),
        ]
        for x, y, text in lower:
            self._box(ax, x, y, 2.8, 1.0, text, COLORS["yellow_fill"], COLORS["yellow_edge"])

        self._arrow(ax, 13.8, 6.7, 4.6, 5.1, COLORS["gray_edge"], 1.8)
        self._arrow(ax, 13.8, 6.7, 8.0, 5.1, COLORS["gray_edge"], 1.8)
        self._arrow(ax, 8.0, 4.1, 11.4, 4.1, COLORS["yellow_edge"], 2.0)

        self._box(ax, 8.0, 1.8, 8.8, 1.0, "输出：_model、DEVICE、_transform、MODEL_VERSION，为单图检测、批量检测与报告模块共用", COLORS["gray_fill"], COLORS["gray_edge"])
        self._save(fig, "01_模型加载模块数据流.png")

    def generate_single_detection(self):
        fig, ax = self._canvas(16, 10, "模块2 单图检测模块数据流图")

        top = [
            (2.0, 7.6, "上传图片\nUploadFile"),
            (4.6, 7.6, "读取 raw bytes\n校验空文件"),
            (7.2, 7.6, "查询 Redis 缓存\n未请求 cam 时优先复用"),
            (9.8, 7.6, "PIL 打开图片\n转内部图像对象"),
            (12.4, 7.6, "_run_detect\n线程池调用 detect_image"),
        ]
        for i, (x, y, text) in enumerate(top):
            self._box(ax, x, y, 2.2, 1.0, text, COLORS["orange_fill"], COLORS["orange_edge"])
            if i < len(top) - 1:
                self._arrow(ax, x + 1.1, y, top[i + 1][0] - 1.1, y, COLORS["orange_edge"])

        middle = [
            (3.3, 4.8, "detect_image\nRGB -> Resize -> Normalize"),
            (6.2, 4.8, "ResNet50 前向推理\nSoftmax 概率"),
            (9.1, 4.8, "排序取 top1\n生成 label / confidence"),
            (12.0, 4.8, "explain_result\n输出中文解释"),
        ]
        for i, (x, y, text) in enumerate(middle):
            self._box(ax, x, y, 2.4, 1.0, text, COLORS["yellow_fill"], COLORS["yellow_edge"])
            if i < len(middle) - 1:
                self._arrow(ax, x + 1.2, y, middle[i + 1][0] - 1.2, y, COLORS["yellow_edge"])

        self._arrow(ax, 12.4, 7.0, 3.3, 5.35, COLORS["gray_edge"], 1.8)

        self._box(ax, 5.2, 2.1, 3.0, 1.0, "可选：grad_cam_overlay\n生成 base64 热力图", COLORS["green_fill"], COLORS["green_edge"])
        self._box(ax, 10.8, 2.1, 3.0, 1.0, "_save_record 写库\n返回 detection_id", COLORS["pink_fill"], COLORS["pink_edge"])
        self._arrow(ax, 12.0, 4.25, 5.2, 2.65, COLORS["green_edge"], 1.8)
        self._arrow(ax, 12.0, 4.25, 10.8, 2.65, COLORS["pink_edge"], 1.8)

        self._box(ax, 8.0, 0.8, 10.2, 0.9, "输出：label、label_zh、confidence、probs、explanation、可选 cam_image、detection_id", COLORS["gray_fill"], COLORS["gray_edge"], fontsize=11)
        self._save(fig, "02_单图检测模块数据流.png")

    def generate_url_processing(self):
        fig, ax = self._canvas(16, 10, "模块3 URL 处理模块数据流图")

        row1 = [
            (2.2, 7.6, "输入新闻 URL"),
            (5.0, 7.6, "协议校验\n仅 http / https"),
            (8.0, 7.6, "validate_public_url\nSSRF 安全过滤"),
            (11.0, 7.6, "httpx 抓取 HTML"),
            (13.8, 7.6, "解析页面内容"),
        ]
        for i, (x, y, text) in enumerate(row1):
            self._box(ax, x, y, 2.2, 1.0, text, COLORS["green_fill"], COLORS["green_edge"])
            if i < len(row1) - 1:
                self._arrow(ax, x + 1.1, y, row1[i + 1][0] - 1.1, y, COLORS["green_edge"])

        self._box(ax, 5.0, 4.8, 2.6, 1.0, "_ImgSrcParser\n提取 img/source/meta 图像地址", COLORS["yellow_fill"], COLORS["yellow_edge"])
        self._box(ax, 8.0, 4.8, 2.6, 1.0, "_TextContentParser\n提取标题、摘要、正文", COLORS["yellow_fill"], COLORS["yellow_edge"])
        self._box(ax, 11.0, 4.8, 2.6, 1.0, "urljoin + 去重\n最多保留 10 张图片", COLORS["yellow_fill"], COLORS["yellow_edge"])

        self._arrow(ax, 13.8, 7.0, 5.0, 5.35, COLORS["gray_edge"], 1.8)
        self._arrow(ax, 13.8, 7.0, 8.0, 5.35, COLORS["gray_edge"], 1.8)
        self._arrow(ax, 13.8, 7.0, 11.0, 5.35, COLORS["gray_edge"], 1.8)

        self._box(ax, 4.2, 2.2, 2.6, 1.0, "async_download_image\n下载并过滤无效图片", COLORS["orange_fill"], COLORS["orange_edge"])
        self._box(ax, 8.0, 2.2, 2.6, 1.0, "_run_detect\n调用单图检测能力", COLORS["orange_fill"], COLORS["orange_edge"])
        self._box(ax, 11.8, 2.2, 3.0, 1.0, "CLIP 分类 + 图文一致性\nclassify_image / consistency", COLORS["purple_fill"], COLORS["purple_edge"])
        self._arrow(ax, 11.0, 4.25, 4.2, 2.75, COLORS["orange_edge"], 1.8)
        self._arrow(ax, 4.2, 1.7, 8.0, 1.7, COLORS["orange_edge"], 2.0)
        self._arrow(ax, 8.0, 1.7, 11.8, 1.7, COLORS["purple_edge"], 2.0)

        self._box(ax, 8.0, 0.55, 11.5, 0.8, "输出：results、page_title、page_summary、dimensions、overall_score，并逐图写入数据库", COLORS["gray_fill"], COLORS["gray_edge"], fontsize=11)
        self._save(fig, "03_URL处理模块数据流.png")

    def generate_batch_processing(self):
        fig, ax = self._canvas(16, 10, "模块4 批量检测模块数据流图")

        self._box(ax, 2.5, 7.8, 2.5, 1.0, "前端调用\n/api/detect-batch-init", COLORS["purple_fill"], COLORS["purple_edge"])
        self._box(ax, 6.0, 7.8, 2.5, 1.0, "create_job\n创建 asyncio.Queue", COLORS["purple_fill"], COLORS["purple_edge"])
        self._box(ax, 9.5, 7.8, 2.5, 1.0, "返回 job_id\n建立任务上下文", COLORS["purple_fill"], COLORS["purple_edge"])
        self._box(ax, 13.0, 7.8, 2.5, 1.0, "上传 files 到\n/api/detect-batch-run", COLORS["purple_fill"], COLORS["purple_edge"])
        for start, end in [(3.75, 4.75), (7.25, 8.25), (10.75, 11.75)]:
            self._arrow(ax, start, 7.8, end, 7.8, COLORS["purple_edge"])

        self._box(ax, 3.2, 4.9, 2.7, 1.0, "_process_batch_run\n统一组织 items", COLORS["yellow_fill"], COLORS["yellow_edge"])
        self._box(ax, 7.0, 4.9, 2.7, 1.0, "图片直读 或\nextract_images_from_file", COLORS["yellow_fill"], COLORS["yellow_edge"])
        self._box(ax, 10.8, 4.9, 2.7, 1.0, "查 Redis 缓存\n否则 detect_batch([img])", COLORS["orange_fill"], COLORS["orange_edge"])
        self._box(ax, 14.0, 4.9, 2.0, 1.0, "生成 category\n和 thumbnail", COLORS["orange_fill"], COLORS["orange_edge"])

        self._arrow(ax, 13.0, 7.2, 3.2, 5.45, COLORS["gray_edge"], 1.8)
        self._arrow(ax, 3.2, 4.35, 7.0, 4.35, COLORS["yellow_edge"], 2.0)
        self._arrow(ax, 7.0, 4.35, 10.8, 4.35, COLORS["orange_edge"], 2.0)
        self._arrow(ax, 10.8, 4.35, 14.0, 4.35, COLORS["orange_edge"], 2.0)

        self._box(ax, 4.6, 1.9, 2.9, 1.0, "queue.put start / result / complete", COLORS["green_fill"], COLORS["green_edge"])
        self._box(ax, 11.2, 1.9, 3.3, 1.0, "ws_detect_progress\n消费队列并 send_json", COLORS["green_fill"], COLORS["green_edge"])
        self._arrow(ax, 14.0, 4.35, 4.6, 2.45, COLORS["green_edge"], 1.8)
        self._arrow(ax, 4.6, 1.35, 11.2, 1.35, COLORS["green_edge"], 2.0)

        self._box(ax, 8.0, 0.45, 11.2, 0.75, "输出：批量检测实时事件流，前端可逐张渲染结果卡片与进度状态", COLORS["gray_fill"], COLORS["gray_edge"], fontsize=11)
        self._save(fig, "04_批量检测模块数据流.png")

    def generate_visualization(self):
        fig, ax = self._canvas(16, 10, "模块5 结果可视化模块数据流图")

        self._box(ax, 2.2, 7.6, 2.3, 1.0, "模型输出 result" , COLORS["pink_fill"], COLORS["pink_edge"])
        self._box(ax, 5.2, 7.6, 2.4, 1.0, "explain_result\n生成中文解释", COLORS["pink_fill"], COLORS["pink_edge"])
        self._box(ax, 8.2, 7.6, 2.4, 1.0, "grad_cam_overlay\n可解释性热力图", COLORS["green_fill"], COLORS["green_edge"])
        self._box(ax, 11.2, 7.6, 2.4, 1.0, "_save_record\n写入 DetectionRecord", COLORS["pink_fill"], COLORS["pink_edge"])
        self._box(ax, 14.0, 7.6, 2.0, 1.0, "generate_report\n构造 report dict", COLORS["pink_fill"], COLORS["pink_edge"])
        for start, end in [(3.35, 4.0), (6.4, 7.0), (9.4, 10.0), (12.4, 13.0)]:
            self._arrow(ax, start, 7.6, end, 7.6, COLORS["pink_edge"])

        self._box(ax, 5.0, 4.5, 2.7, 1.0, "输出 explanation\nlevel / summary / clues", COLORS["yellow_fill"], COLORS["yellow_edge"])
        self._box(ax, 8.2, 4.5, 2.7, 1.0, "输出 cam_image\nbase64 JPEG", COLORS["yellow_fill"], COLORS["yellow_edge"])
        self._box(ax, 11.4, 4.5, 2.7, 1.0, "export_pdf\n导出 PDF 报告", COLORS["blue_fill"], COLORS["blue_edge"])
        self._box(ax, 14.0, 4.5, 2.0, 1.0, "export_excel\n导出 Excel", COLORS["blue_fill"], COLORS["blue_edge"])

        self._arrow(ax, 5.2, 7.05, 5.0, 5.05, COLORS["yellow_edge"], 1.8)
        self._arrow(ax, 8.2, 7.05, 8.2, 5.05, COLORS["green_edge"], 1.8)
        self._arrow(ax, 14.0, 7.05, 11.4, 5.05, COLORS["blue_edge"], 1.8)
        self._arrow(ax, 14.0, 7.05, 14.0, 5.05, COLORS["blue_edge"], 1.8)

        self._box(ax, 8.0, 1.6, 11.6, 1.0, "输出：页面可读解释、Grad-CAM 可视化图片、数据库记录，以及 PDF / Excel 导出能力", COLORS["gray_fill"], COLORS["gray_edge"], fontsize=11)
        self._save(fig, "05_结果可视化模块数据流.png")

    def generate_all(self):
        print(f"输出目录: {self.output_dir}")
        self.generate_overview()
        self.generate_model_loading()
        self.generate_single_detection()
        self.generate_url_processing()
        self.generate_batch_processing()
        self.generate_visualization()
        print("全部 PNG 已生成完成")


def main():
    output_dir = r"d:\aigi修改\AIGI-Holmes-main\数据流图\matplotlib图表"
    DiagramGenerator(output_dir).generate_all()


if __name__ == "__main__":
    main()
