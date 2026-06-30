#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成 AIGI-Holmes 五个核心模块数据流图 PDF
"""

import os
import re
from pathlib import Path
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm, inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle, Image
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from datetime import datetime

class DataflowPDFGenerator:
    def __init__(self, output_path):
        self.output_path = output_path
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()
        
    def _setup_custom_styles(self):
        """设置自定义样式"""
        # 标题样式
        self.styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#2563eb'),
            spaceAfter=30,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        ))
        
        # 章节标题
        self.styles.add(ParagraphStyle(
            name='SectionTitle',
            parent=self.styles['Heading2'],
            fontSize=16,
            textColor=colors.HexColor('#1976d2'),
            spaceAfter=12,
            spaceBefore=12,
            fontName='Helvetica-Bold'
        ))
        
        # 小标题
        self.styles.add(ParagraphStyle(
            name='SubsectionTitle',
            parent=self.styles['Heading3'],
            fontSize=12,
            textColor=colors.HexColor('#0d47a1'),
            spaceAfter=8,
            fontName='Helvetica-Bold'
        ))
        
        # 正文（修改名称避免冲突）
        self.styles.add(ParagraphStyle(
            name='CustomBody',
            parent=self.styles['BodyText'],
            fontSize=10,
            alignment=TA_JUSTIFY,
            spaceAfter=10,
            leading=14
        ))

    def generate(self):
        """生成 PDF 文档"""
        doc = SimpleDocTemplate(
            self.output_path,
            pagesize=landscape(A4),
            rightMargin=1*cm,
            leftMargin=1*cm,
            topMargin=1.5*cm,
            bottomMargin=1.5*cm,
            title="AIGI-Holmes 五个核心模块数据流图",
            author="AIGI-Holmes Team",
            subject="系统架构与数据流分析"
        )
        
        story = []
        
        # 标题页
        story.extend(self._create_title_page())
        story.append(PageBreak())
        
        # 目录
        story.extend(self._create_toc())
        story.append(PageBreak())
        
        # 内容
        story.extend(self._create_content())
        
        # 生成 PDF
        doc.build(story)
        print(f"✅ PDF 已生成: {self.output_path}")
        
    def _create_title_page(self):
        """创建标题页"""
        elements = []
        elements.append(Spacer(1, 2*cm))
        
        title = Paragraph(
            "AIGI-Holmes 数据流图文档",
            self.styles['CustomTitle']
        )
        elements.append(title)
        
        elements.append(Spacer(1, 1*cm))
        
        subtitle = Paragraph(
            "五个核心模块架构与数据处理流程",
            self.styles['SectionTitle']
        )
        elements.append(subtitle)
        
        elements.append(Spacer(1, 2*cm))
        
        # 项目信息
        info_text = f"""
        <font size=11>
        <b>项目名称：</b> AIGI-Holmes - AI生成图片检测系统<br/><br/>
        <b>文档日期：</b> {datetime.now().strftime('%Y年%m月%d日')}<br/><br/>
        <b>文档版本：</b> v1.0<br/><br/>
        <b>核心功能：</b> 面向新闻媒体核查场景的AI生成图片检测，采用微调ResNet-50和CLIP多模态分析
        </font>
        """
        elements.append(Paragraph(info_text, self.styles['CustomBody']))
        
        elements.append(Spacer(1, 3*cm))
        
        footer = Paragraph(
            "<i>本文档详细展示了系统的5大核心算法数据流</i>",
            self.styles['SectionTitle']
        )
        elements.append(footer)
        
        return elements
    
    def _create_toc(self):
        """创建目录"""
        elements = []
        
        title = Paragraph("目 录", self.styles['CustomTitle'])
        elements.append(title)
        elements.append(Spacer(1, 0.5*cm))
        
        toc_items = [
            "1. 整体系统架构与数据流",
            "2. 单图检测算法数据流",
            "3. CLIP多模态分析数据流",
            "4. URL批量检测与实时进度推送",
            "5. 检测报告生成与多格式导出工作流",
            "6. 模块间关系图",
            "7. 关键代码位置与数据流分析"
        ]
        
        for item in toc_items:
            p = Paragraph(f"<font size=11>{item}</font>", self.styles['CustomBody'])
            elements.append(p)
            elements.append(Spacer(1, 0.3*cm))
        
        return elements
    
    def _create_content(self):
        """创建主要内容"""
        elements = []
        
        # 模块1：整体系统架构
        elements.extend(self._create_section(
            "1. 整体系统架构与数据流",
            """
            系统采用分层架构设计，包含五个主要层级：
            <br/><br/>
            <b>• 用户接口层：</b> 桌面应用(PyWebView)、网页应用(Flask/React)、API接口(REST)<br/>
            <b>• 中间件层：</b> FastAPI后端服务器(uvicorn localhost:7860)<br/>
            <b>• 检测路由层：</b> 单图检测、URL批量检测、WebSocket实时进度、报告生成<br/>
            <b>• 算法核心层：</b> ResNet50微调、CLIP多模态分类、Grad-CAM热力图、豆包AI辅助分析<br/>
            <b>• 数据存储层：</b> SQLite/PostgreSQL、Redis缓存、模型仓库<br/>
            <br/>
            数据流向：用户交互 → FastAPI路由 → 模型推理 → 数据存储 → 结果反馈
            """
        ))
        elements.append(PageBreak())
        
        # 模块2：单图检测
        elements.extend(self._create_section(
            "2. 单图检测算法数据流",
            """
            单图检测包含五个处理阶段：<br/><br/>
            <b>阶段1：输入预处理</b><br/>
            • RGB转换与缩放至224×224<br/>
            • 张量化与ImageNet标准化<br/>
            • 输出Tensor shape: 1×3×224×224<br/><br/>
            
            <b>阶段2：深度学习推理</b><br/>
            • ResNet50主干网络推理<br/>
            • layer4特征提取 (1×2048×7×7)<br/>
            • 全连接层映射至2维logits<br/><br/>
            
            <b>阶段3：结果获取</b><br/>
            • Softmax概率计算与归一化<br/>
            • 置信度最高类别选取<br/>
            • 规则化分级解释<br/><br/>
            
            <b>阶段4：Grad-CAM可解释性</b><br/>
            • 梯度收集与权重计算<br/>
            • 特征加权求和<br/>
            • 双线性插值至原始分辨率<br/>
            • Base64热力图编码<br/><br/>
            
            <b>阶段5：结构化输出</b><br/>
            • 返回JSON格式结果<br/>
            • 包含标签、置信度、概率分布、解释、热力图
            """
        ))
        elements.append(PageBreak())
        
        # 模块3：CLIP多模态
        elements.extend(self._create_section(
            "3. CLIP多模态分析数据流",
            """
            采用OpenAI CLIP ViT-B/32模型，512维特征空间<br/><br/>
            <b>分支1：内容分类（7类）</b><br/>
            • 图像编码：Vision Transformer编码器<br/>
            • 提示词集合：人物、动物、建筑、风景、食物、交通、其他<br/>
            • 文本编码：7×512维特征矩阵（缓存复用）<br/>
            • 余弦相似度计算<br/>
            • Argmax分类选取<br/><br/>
            
            <b>分支2：图文一致性检测</b><br/>
            • 双层提示词策略<br/>
            • 对齐提示词×4 + 不对齐提示词×3<br/>
            • 相似度间隙计算：gap = aligned - unrelated<br/>
            • 间隙归一化：[-0.20, +0.20] → [0, 100]<br/>
            • 评级划分：高度/基本/不一致<br/><br/>
            
            <b>性能特点：</b><br/>
            • 零样本学习，无需训练数据<br/>
            • 首次加载~350MB，后续复用<br/>
            • 文本特征预计算，推理快速
            """
        ))
        elements.append(PageBreak())
        
        # 模块4：URL批量处理
        elements.extend(self._create_section(
            "4. URL批量检测与实时进度推送",
            """
            分为五层处理流程<br/><br/>
            <b>第1层：用户请求</b><br/>
            • POST /api/detect-url 初始化检测任务<br/><br/>
            
            <b>第2层：页面爬取与图片收集</b><br/>
            • SSRF安全防护（private IP黑名单）<br/>
            • HTTP页面下载<br/>
            • BeautifulSoup HTML解析<br/>
            • 图片URL提取与转换<br/>
            • SHA-256哈希去重<br/><br/>
            
            <b>第3层：异步并发处理</b><br/>
            • asyncio.Semaphore(5)并发限制<br/>
            • asyncio.Queue内存缓冲<br/>
            • 批量图片下载到内存<br/><br/>
            
            <b>第4层：检测推理与缓存</b><br/>
            • Redis缓存检查（三级优化）<br/>
            • 批量推理(detect_batch)利用GPU优势<br/>
            • CLIP分类与一致性检测<br/>
            • 结果缓存<br/><br/>
            
            <b>第5层：WebSocket实时反馈</b><br/>
            • 进度中间事件推送<br/>
            • 完成事件汇总<br/>
            • 推送延迟<100ms
            """
        ))
        elements.append(PageBreak())
        
        # 模块5：报告生成
        elements.extend(self._create_section(
            "5. 检测报告生成与多格式导出",
            """
            四阶段报告生成工作流<br/><br/>
            <b>第1阶段：检测数据聚合</b><br/>
            • 数据库查询检测记录<br/>
            • 聚合关键指标：总检测数、FAKE/REAL占比、平均置信度、分类分布、一致性统计<br/>
            • 结构化数据组织<br/><br/>
            
            <b>第2阶段：多格式并行生成</b><br/>
            • <b>PDF报告：</b> reportlab库生成，包含表格、图表、热力图（500KB-5MB）<br/>
            • <b>Excel表格：</b> openpyxl库生成，多Sheet包含摘要、详细记录、统计、热力图（100KB-2MB）<br/>
            • <b>JSON数据：</b> 原始数据导出，便于系统集成（50KB-500KB）<br/><br/>
            
            <b>第3阶段：文件生成完成</b><br/>
            • 保存至临时目录 /uploads/reports/{task_id}/<br/><br/>
            
            <b>第4阶段：下载与分享</b><br/>
            • 用户下载PDF/Excel/JSON<br/>
            • 可选生成短链接（7天有效期）
            """
        ))
        elements.append(PageBreak())
        
        # 模块间关系
        elements.extend(self._create_section(
            "6. 模块间关系与数据流向",
            """
            <b>核心结论：</b><br/><br/>
            系统采用模块化设计，各模块职责清晰，数据流向如下：<br/><br/>
            用户输入<br/>
            &nbsp;&nbsp;&nbsp;&nbsp;↓<br/>
            [系统架构层] 路由分发<br/>
            &nbsp;&nbsp;&nbsp;&nbsp;├─→ [单图检测] ResNet50推理 → CLIP分类 → Grad-CAM → 结果<br/>
            &nbsp;&nbsp;&nbsp;&nbsp;├─→ [URL批量] 爬取图片 → 并发处理 → WebSocket推送进度<br/>
            &nbsp;&nbsp;&nbsp;&nbsp;├─→ [CLIP多模态] 内容分类 + 一致性检测<br/>
            &nbsp;&nbsp;&nbsp;&nbsp;└─→ [报告生成] 数据聚合 → 多格式输出<br/>
            &nbsp;&nbsp;&nbsp;&nbsp;↓<br/>
            结果输出 (UI显示 / 下载导出 / API返回)<br/><br/>
            
            <b>设计特点：</b><br/>
            • 单图检测和URL批量处理共享ResNet50模型<br/>
            • URL批量处理复用单图检测模块<br/>
            • CLIP分类与一致性检测在多个流程中应用<br/>
            • 报告生成基于上游所有检测结果聚合<br/>
            • Redis缓存优化避免重复计算
            """
        ))
        elements.append(PageBreak())
        
        # 关键代码位置
        elements.extend(self._create_section(
            "7. 关键代码位置总览",
            """
            <b>单图检测模块</b><br/>
            • 文件：detect.py<br/>
            • 核心函数：detect_image()、_grad_cam()、grad_cam_overlay()<br/>
            • 关键操作：模型推理、梯度钩子、热力图生成<br/><br/>
            
            <b>CLIP分类模块</b><br/>
            • 文件：backend/clip_classify.py<br/>
            • 核心函数：classify_image()、classify_text_image_consistency()<br/>
            • 关键操作：特征编码、相似度计算、评分归一化<br/><br/>
            
            <b>URL批量处理模块</b><br/>
            • 文件：detect.py、backend/routers/ws.py<br/>
            • 核心函数：async_download_image()、ws_detect_progress()<br/>
            • 关键操作：页面爬取、并发下载、实时推送<br/><br/>
            
            <b>报告生成模块</b><br/>
            • 文件：backend/report/*.py<br/>
            • 核心函数：generate_pdf()、generate_excel()、generate_json()<br/>
            • 关键操作：数据聚合、文件生成、多格式输出<br/><br/>
            
            <b>系统架构</b><br/>
            • 文件：backend/main.py、backend/routers/*.py<br/>
            • 核心：FastAPI路由定义、中间件配置、CORS处理
            """
        ))
        
        return elements
    
    def _create_section(self, title, content):
        """创建章节"""
        elements = []
        
        heading = Paragraph(title, self.styles['SectionTitle'])
        elements.append(heading)
        elements.append(Spacer(1, 0.3*cm))
        
        body = Paragraph(content, self.styles['CustomBody'])
        elements.append(body)
        elements.append(Spacer(1, 0.5*cm))
        
        return elements


def main():
    """主函数"""
    output_path = r"d:\aigi修改\AIGI-Holmes-main\数据流图\五个核心模块数据流图.pdf"
    
    # 确保输出目录存在
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    print("🔧 开始生成PDF文档...")
    print(f"📍 输出路径: {output_path}")
    
    generator = DataflowPDFGenerator(output_path)
    generator.generate()
    
    # 显示文件信息
    file_size = os.path.getsize(output_path) / (1024 * 1024)
    print(f"📊 文件大小: {file_size:.2f} MB")
    print(f"✅ PDF生成完成！")


if __name__ == "__main__":
    main()
