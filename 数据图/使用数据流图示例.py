"""
AIGI-Holmes 数据流图使用示例
展示如何导入、显示和自定义数据流图

使用方式：
    python 使用数据流图示例.py
"""

import matplotlib.pyplot as plt
import matplotlib.image as mpimg
from matplotlib.gridspec import GridSpec
import os

def display_single_figure(figure_path, title=None):
    """
    显示单张数据流图
    
    Args:
        figure_path: 图片文件路径
        title: 图表标题
    """
    if not os.path.exists(figure_path):
        print(f"❌ 文件不存在: {figure_path}")
        return
    
    fig, ax = plt.subplots(figsize=(14, 10))
    img = mpimg.imread(figure_path)
    ax.imshow(img)
    ax.axis('off')
    if title:
        fig.suptitle(title, fontsize=16, fontweight='bold', y=0.98)
    plt.tight_layout()
    plt.show()


def display_all_figures_grid():
    """
    在一个 2×3 的网格中显示所有5张图表（最后一格为空）
    """
    figure_files = [
        '01_整体系统架构与数据流.png',
        '02_单图检测算法数据流.png',
        '03_CLIP多模态分析数据流.png',
        '04_URL批量检测与实时进度推送.png',
        '05_检测报告生成与多格式导出.png',
    ]
    
    figure_titles = [
        '①整体系统架构与数据流',
        '②单图检测算法数据流',
        '③CLIP多模态分析数据流',
        '④URL批量检测与实时进度推送',
        '⑤检测报告生成与多格式导出',
    ]
    
    # 检查文件是否存在
    missing_files = [f for f in figure_files if not os.path.exists(f)]
    if missing_files:
        print(f"❌ 缺少以下文件: {missing_files}")
        return
    
    # 创建 2×3 网格
    fig = plt.figure(figsize=(20, 14))
    gs = GridSpec(2, 3, figure=fig, hspace=0.3, wspace=0.2)
    
    for i, (figure_file, title) in enumerate(zip(figure_files, figure_titles)):
        if i < 5:
            row = i // 3
            col = i % 3
            ax = fig.add_subplot(gs[row, col])
            
            img = mpimg.imread(figure_file)
            ax.imshow(img)
            ax.axis('off')
            ax.set_title(title, fontsize=12, fontweight='bold', pad=10)
    
    # 第6个位置用于说明文字
    ax_text = fig.add_subplot(gs[1, 2])
    ax_text.axis('off')
    
    explanation = """
    AIGI-Holmes 核心算法总结
    
    ① 整体架构
    - 桌面/Web/API 三端支持
    - FastAPI 后端服务
    - 模型推理层
    - 数据存储层
    
    ② 单图检测
    - 预处理 → ResNet-50推理
    - Softmax 分类
    - Grad-CAM 热力图
    - 规则化解释
    
    ③ CLIP 多模态
    - 内容分类（7类）
    - 图文一致性评分
    - 双分支并行处理
    
    ④ URL 批量处理
    - 异步页面爬取
    - 并发图片下载
    - 批量推理优化
    - WebSocket 实时推送
    
    ⑤ 报告生成导出
    - 数据库聚合
    - PDF/Excel/JSON 格式
    - 多层级结构化输出
    """
    
    ax_text.text(0.05, 0.95, explanation, 
                transform=ax_text.transAxes,
                fontsize=10, 
                verticalalignment='top',
                family='monospace',
                bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
    
    plt.suptitle('AIGI-Holmes 项目算法设计与数据流全景图', 
                fontsize=18, fontweight='bold', y=0.995)
    
    plt.show()


def extract_specific_stage(figure_path, title=None):
    """
    提取并放大显示某个特定阶段的细节
    （这里作为示例，展示如何二次处理图表）
    """
    if not os.path.exists(figure_path):
        print(f"❌ 文件不存在: {figure_path}")
        return
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))
    
    # 原始图表
    img = mpimg.imread(figure_path)
    ax1.imshow(img)
    ax1.axis('off')
    ax1.set_title('完整数据流', fontsize=12, fontweight='bold')
    
    # 右侧显示处理说明
    ax2.axis('off')
    instructions = """
    数据流图使用指南
    
    ✓ 如何阅读这些图表：
    
    1. 颜色含义：
       • 蓝色 → 用户交互层
       • 橙色 → 业务逻辑层
       • 绿色 → 算法处理层
       • 红色 → 深度学习层
       • 紫色 → 数据存储层
    
    2. 形状含义：
       • 圆角矩形 → 数据或函数
       • 箭头 → 数据流向
       • 双箭头 ↔ → 双向交互
    
    3. 聚焦点：
       • 跟踪箭头理解数据流向
       • 识别瓶颈和优化点
       • 对应实际代码位置
    
    ✓ 典型应用场景：
    
    • 系统架构评审
    • 团队知识共享
    • 性能瓶颈分析
    • 功能需求讨论
    • 代码实现参考
    
    ✓ 相关文件：
    
    - 01_*.png: 系统整体视图
    - 02_*.png: 算法实现细节
    - 03_*.png: 多模态处理流程
    - 04_*.png: 异步并发设计
    - 05_*.png: 数据处理管道
    
    更多详情见：
    算法数据流图详细分析文档.md
    """
    
    ax2.text(0.05, 0.95, instructions,
            transform=ax2.transAxes,
            fontsize=9,
            verticalalignment='top',
            family='monospace',
            bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.7))
    
    plt.tight_layout()
    plt.show()


def generate_markdown_index():
    """
    生成 Markdown 索引文件，便于快速查阅
    """
    index_content = """# AIGI-Holmes 数据流图索引

## 5大核心数据流图

### 1. 整体系统架构与数据流
**文件**: `01_整体系统架构与数据流.png`

**目标**: 快速理解系统全貌

**关键内容**:
- 用户接口层 (桌面/Web/API)
- FastAPI 后端中间件
- 4大检测路由
- 4大算法核心
- 3层数据存储

---

### 2. 单图检测算法数据流
**文件**: `02_单图检测算法数据流.png`

**目标**: 深入理解ResNet-50检测与Grad-CAM热力图生成

**关键阶段**:
1. 输入预处理: RGB转换 → 缩放 224×224 → 张量化 → 归一化
2. ResNet-50推理: conv1 → layer1/2/3/4 → FC层
3. 结果获取: Softmax → 分类 → 规则化解释
4. Grad-CAM: 梯度收集 → 权重计算 → 特征融合 → ReLU → 双线性插值
5. 结构化输出: 标签 + 置信度 + 概率 + 热力图 + 文本解释

**对应函数**:
- `detect_image()`: 主检测函数
- `_grad_cam()`: Grad-CAM计算
- `grad_cam_overlay()`: 热力图叠加
- `explain_result()`: 文本解释

---

### 3. CLIP多模态分析数据流
**文件**: `03_CLIP多模态分析数据流.png`

**目标**: 理解CLIP ViT-B/32的多模态应用

**左分支-内容分类**:
- 图像编码 → 512维单位向量
- 7类提示词文本编码 → 7×512矩阵
- 余弦相似度 → argmax → 分类标签

**右分支-图文一致性**:
- 图像编码 (复用)
- 7个提示词 (4个对齐 + 3个基准)
- 相似度间隙计算 → 归一化评分 (0-100)
- 三级评价: 高度一致 / 基本一致 / 不一致

**对应函数**:
- `classify_image()`: 内容分类
- `classify_text_image_consistency()`: 一致性检测

---

### 4. URL批量检测与实时进度推送
**文件**: `04_URL批量检测与实时进度推送.png`

**目标**: 掌握异步并发架构与WebSocket实时反馈

**5大层级**:
1. 用户请求: URL输入 → API初始化
2. 页面爬取: URL验证 → HTML下载 → 图片提取
3. 异步处理: 5个并发 + asyncio.Queue缓冲
4. 模型推理: 缓存检查 → 批量推理 → CLIP分类
5. 实时反馈: WebSocket推送进度事件 → 前端实时显示

**对应函数**:
- `api_detect_url()`: URL检测API
- `async_fetch_page_content()`: 页面抓取
- `async_download_image()`: 异步下载
- `detect_batch()`: 批量推理
- `ws_detect_progress()`: WebSocket处理

---

### 5. 检测报告生成与多格式导出
**文件**: `05_检测报告生成与多格式导出.png`

**目标**: 理解数据聚合与多格式输出管道

**6大阶段**:
1. 数据聚合: 6大数据源汇总
2. 数据库查询: 联表查询 → 数据合并
3. 结构化生成: 7个报告模块
4. 多格式导出: PDF (reportlab) | Excel (openpyxl) | JSON
5. 文件输出: 字节流存储 + Redis缓存
6. HTTP响应: Content-Type头 + 自动下载

**对应函数**:
- `generate_report()`: 报告生成
- `export_pdf()`: PDF导出
- `export_excel()`: Excel导出
- `api_generate_report()`: 报告API

---

## 核心算法参数表

| 算法 | 模型 | 输入 | 输出 | 延迟 | GPU内存 |
|------|------|------|------|------|--------|
| 单图检测 | ResNet-50 | 图片(任意) | FAKE/REAL | 50ms | 200MB |
| Grad-CAM | Layer4 Hook | 图片+类别 | 热力图 | 100ms | 同上 |
| 内容分类 | CLIP ViT-B/32 | 图片 | 7类标签 | 80ms | 350MB |
| 图文一致性 | CLIP ViT-B/32 | 图片+文本 | 评分(0-100) | 120ms | 同上 |
| URL爬取 | BeautifulSoup | URL | 图片列表 | 1-5s | CPU |
| 批量推理 | ResNet-50 | 多图 | 结果列表 | 10ms/100 | 200MB |

---

## 代码位置速查表

### 主要文件
- [detect.py](detect.py): 单图检测, Grad-CAM, URL爬取
- [backend/clip_classify.py](backend/clip_classify.py): CLIP分类与一致性检测
- [backend/routers/detect.py](backend/routers/detect.py): 检测API
- [backend/routers/ws.py](backend/routers/ws.py): WebSocket实时推送
- [backend/report/generator.py](backend/report/generator.py): 报告生成
- [backend/report/exporter.py](backend/report/exporter.py): 格式导出

### 关键函数映射
```
detect_image()                  ← 02-单图检测
_grad_cam()                     ← 02-Grad-CAM
classify_image()                ← 03-内容分类
classify_text_image_consistency() ← 03-一致性检测
async_fetch_page_content()      ← 04-页面爬取
async_download_image()          ← 04-异步下载
detect_batch()                  ← 04-批量推理
ws_detect_progress()            ← 04-WebSocket推送
generate_report()               ← 05-报告生成
export_pdf() / export_excel()   ← 05-格式导出
```

---

## 常见问题 (FAQ)

### Q1: 如何在实际项目中应用这些图表?
**A**: 
- 系统架构评审: 使用图1讨论整体设计
- 性能优化: 使用图2-4识别瓶颈
- 新功能集成: 参考相关数据流加入接口
- 代码审查: 对照相关流程验证实现

### Q2: 更新功能后如何更新这些图表?
**A**: 修改 [算法数据流图.py](算法数据流图.py) 中的相应函数，重新运行脚本:
```bash
python 算法数据流图.py
```

### Q3: 如何自定义颜色和样式?
**A**: 编辑文件中的颜色常量:
```python
user_color = '#E8F4F8'  # 修改这些
algo_color = '#FFE6E6'
```

### Q4: 这些图表是否适合打印?
**A**: 是的,所有图表都以 DPI=300 生成，适合高质量打印和文档

---

## 快速开始

### 生成图表
```bash
python 算法数据流图.py
```

### 显示单张图表
```bash
python -c "from 使用数据流图示例 import display_single_figure;
display_single_figure('01_整体系统架构与数据流.png')"
```

### 显示所有图表网格
```bash
python -c "from 使用数据流图示例 import display_all_figures_grid;
display_all_figures_grid()"
```

---

**生成时间**: 2025年4月  
**项目**: AIGI-Holmes v2.0.0  
**格式**: PNG (DPI=300, A4适配)  
"""
    
    with open('数据流图索引.md', 'w', encoding='utf-8') as f:
        f.write(index_content)
    
    print("✓ 已生成索引文件: 数据流图索引.md")


def main():
    """主程序"""
    print("\n" + "="*80)
    print("AIGI-Holmes 数据流图使用示例")
    print("="*80 + "\n")
    
    options = """
请选择要执行的操作:

1. 显示单张图表 (选择文件)
2. 显示所有图表网格视图
3. 提取特定阶段细节
4. 生成 Markdown 索引
5. 退出

请输入选项 (1-5): """
    
    while True:
        try:
            choice = input(options).strip()
            
            if choice == '1':
                print("\n可用的数据流图:")
                figures = [
                    '01_整体系统架构与数据流.png',
                    '02_单图检测算法数据流.png',
                    '03_CLIP多模态分析数据流.png',
                    '04_URL批量检测与实时进度推送.png',
                    '05_检测报告生成与多格式导出.png',
                ]
                for i, fig in enumerate(figures, 1):
                    print(f"  {i}. {fig}")
                
                fig_choice = input("\n选择文件编号 (1-5): ").strip()
                if fig_choice in ['1', '2', '3', '4', '5']:
                    figure_path = figures[int(fig_choice)-1]
                    display_single_figure(figure_path, title=f"AIGI-Holmes {fig_choice}")
                else:
                    print("❌ 无效选择")
            
            elif choice == '2':
                print("\n生成网格视图...")
                display_all_figures_grid()
            
            elif choice == '3':
                print("\nAvailable figures:")
                figures = [
                    '01_整体系统架构与数据流.png',
                    '02_单图检测算法数据流.png',
                    '03_CLIP多模态分析数据流.png',
                    '04_URL批量检测与实时进度推送.png',
                    '05_检测报告生成与多格式导出.png',
                ]
                for i, fig in enumerate(figures, 1):
                    print(f"  {i}. {fig}")
                
                fig_choice = input("\n选择文件编号 (1-5): ").strip()
                if fig_choice in ['1', '2', '3', '4', '5']:
                    figure_path = figures[int(fig_choice)-1]
                    extract_specific_stage(figure_path)
                else:
                    print("❌ 无效选择")
            
            elif choice == '4':
                print("\n生成 Markdown 索引...")
                generate_markdown_index()
                print("✓ 完成！")
            
            elif choice == '5':
                print("\n👋 退出程序")
                break
            
            else:
                print("❌ 无效选择，请重试")
        
        except KeyboardInterrupt:
            print("\n\n👋 用户中断")
            break
        except Exception as e:
            print(f"❌ 错误: {e}")


if __name__ == "__main__":
    main()
