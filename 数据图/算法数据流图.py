"""
AIGI-Holmes 项目算法设计与数据流图可视化
包含5张关键数据流图：
1. 整体系统架构与数据流
2. 单图检测算法数据流（ResNet50 + Grad-CAM）
3. CLIP多模态内容分类与图文一致性检测数据流
4. URL批量检测与实时进度推送数据流
5. 报告生成与导出工作流

作者: AIGI-Holmes Team
"""

import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import numpy as np
from matplotlib.patches import Rectangle
import matplotlib.lines as mlines

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

# ============================================================================
# 图1: 整体系统架构与数据流
# ============================================================================
def draw_overall_architecture():
    """绘制AIGI-Holmes整体系统架构图"""
    fig, ax = plt.subplots(figsize=(16, 10))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 10)
    ax.axis('off')
    
    # 标题
    ax.text(5, 9.5, 'AIGI-Holmes 系统整体架构与数据流', 
            fontsize=18, fontweight='bold', ha='center')
    
    # ===== 用户接口层 =====
    user_color = '#E8F4F8'
    user_y = 8.5
    # 桌面应用
    rect1 = FancyBboxPatch((0.5, user_y-0.4), 1.5, 0.8, 
                           boxstyle="round,pad=0.1", 
                           edgecolor='#1f77b4', facecolor=user_color, linewidth=2)
    ax.add_patch(rect1)
    ax.text(1.25, user_y, '桌面应用\n(PyWebView)', ha='center', va='center', fontsize=10, fontweight='bold')
    
    # 网页应用
    rect2 = FancyBboxPatch((2.5, user_y-0.4), 1.5, 0.8, 
                           boxstyle="round,pad=0.1", 
                           edgecolor='#1f77b4', facecolor=user_color, linewidth=2)
    ax.add_patch(rect2)
    ax.text(3.25, user_y, '网页应用\n(Flask/React)', ha='center', va='center', fontsize=10, fontweight='bold')
    
    # 移动应用
    rect3 = FancyBboxPatch((4.5, user_y-0.4), 1.5, 0.8, 
                           boxstyle="round,pad=0.1", 
                           edgecolor='#1f77b4', facecolor=user_color, linewidth=2)
    ax.add_patch(rect3)
    ax.text(5.25, user_y, 'API接口\n(REST)', ha='center', va='center', fontsize=10, fontweight='bold')
    
    # ===== 中间件层 =====
    middleware_color = '#FFF4E6'
    middleware_y = 7
    
    # FastAPI服务器
    rect_api = FancyBboxPatch((1.5, middleware_y-0.5), 3, 1, 
                              boxstyle="round,pad=0.1", 
                              edgecolor='#ff7f0e', facecolor=middleware_color, linewidth=2)
    ax.add_patch(rect_api)
    ax.text(3, middleware_y, 'FastAPI后端服务器\n(uvicorn localhost:7860)', 
            ha='center', va='center', fontsize=11, fontweight='bold')
    
    # 箭头: 用户界面 → FastAPI
    for x in [1.25, 3.25, 5.25]:
        arrow = FancyArrowPatch((x, user_y-0.5), (3, middleware_y+0.5),
                               arrowstyle='->', mutation_scale=20, 
                               color='#1f77b4', linewidth=2)
        ax.add_patch(arrow)
    
    # ===== 检测路由层 =====
    route_color = '#F0E6FF'
    route_y = 5.5
    
    # 单图检测
    rect_detect = FancyBboxPatch((0.3, route_y-0.35), 1.8, 0.7, 
                                boxstyle="round,pad=0.05", 
                                edgecolor='#2ca02c', facecolor=route_color, linewidth=1.5)
    ax.add_patch(rect_detect)
    ax.text(1.2, route_y, 'POST /api/detect\n单图检测', ha='center', va='center', fontsize=9)
    
    # URL批量检测
    rect_url = FancyBboxPatch((2.4, route_y-0.35), 1.8, 0.7, 
                             boxstyle="round,pad=0.05", 
                             edgecolor='#2ca02c', facecolor=route_color, linewidth=1.5)
    ax.add_patch(rect_url)
    ax.text(3.3, route_y, 'POST /api/detect-url\nURL检测', ha='center', va='center', fontsize=9)
    
    # WebSocket进度
    rect_ws = FancyBboxPatch((4.5, route_y-0.35), 1.8, 0.7, 
                            boxstyle="round,pad=0.05", 
                            edgecolor='#2ca02c', facecolor=route_color, linewidth=1.5)
    ax.add_patch(rect_ws)
    ax.text(5.4, route_y, 'WS /ws/detect\n实时进度', ha='center', va='center', fontsize=9)
    
    # 报告生成
    rect_report = FancyBboxPatch((6.6, route_y-0.35), 1.8, 0.7, 
                                boxstyle="round,pad=0.05", 
                                edgecolor='#2ca02c', facecolor=route_color, linewidth=1.5)
    ax.add_patch(rect_report)
    ax.text(7.5, route_y, 'POST /api/report\n报告生成', ha='center', va='center', fontsize=9)
    
    # 箭头: FastAPI → 路由
    for x in [1.2, 3.3, 5.4, 7.5]:
        arrow = FancyArrowPatch((3, middleware_y-0.5), (x, route_y+0.35),
                               arrowstyle='->', mutation_scale=15, 
                               color='#ff7f0e', linewidth=1.5)
        ax.add_patch(arrow)
    
    # ===== 算法核心层 =====
    algo_color = '#E6F3FF'
    algo_y = 3.8
    
    # ResNet50检测
    rect_resnet = FancyBboxPatch((0.2, algo_y-0.4), 1.8, 0.8, 
                                boxstyle="round,pad=0.05", 
                                edgecolor='#d62728', facecolor=algo_color, linewidth=2)
    ax.add_patch(rect_resnet)
    ax.text(1.1, algo_y, 'ResNet50\n微调模型\n(FAKE/REAL)', 
            ha='center', va='center', fontsize=9, fontweight='bold')
    
    # CLIP分类
    rect_clip = FancyBboxPatch((2.3, algo_y-0.4), 1.8, 0.8, 
                              boxstyle="round,pad=0.05", 
                              edgecolor='#d62728', facecolor=algo_color, linewidth=2)
    ax.add_patch(rect_clip)
    ax.text(3.2, algo_y, 'CLIP\n多模态分类\n(7个类别)', 
            ha='center', va='center', fontsize=9, fontweight='bold')
    
    # Grad-CAM
    rect_gradcam = FancyBboxPatch((4.4, algo_y-0.4), 1.8, 0.8, 
                                 boxstyle="round,pad=0.05", 
                                 edgecolor='#d62728', facecolor=algo_color, linewidth=2)
    ax.add_patch(rect_gradcam)
    ax.text(5.3, algo_y, 'Grad-CAM\n热力图生成\n可解释性', 
            ha='center', va='center', fontsize=9, fontweight='bold')
    
    # 豆包AI分析
    rect_doubao = FancyBboxPatch((6.5, algo_y-0.4), 1.8, 0.8, 
                                boxstyle="round,pad=0.05", 
                                edgecolor='#d62728', facecolor=algo_color, linewidth=2)
    ax.add_patch(rect_doubao)
    ax.text(7.4, algo_y, '豆包AI\n辅助分析\n自然语言', 
            ha='center', va='center', fontsize=9, fontweight='bold')
    
    # 箭头: 路由 → 算法
    arrow1 = FancyArrowPatch((1.2, route_y-0.38), (1.1, algo_y+0.4),
                            arrowstyle='->', mutation_scale=15, 
                            color='#2ca02c', linewidth=1.5)
    ax.add_patch(arrow1)
    
    arrow2 = FancyArrowPatch((3.3, route_y-0.38), (3.2, algo_y+0.4),
                            arrowstyle='->', mutation_scale=15, 
                            color='#2ca02c', linewidth=1.5)
    ax.add_patch(arrow2)
    
    arrow3 = FancyArrowPatch((5.4, route_y-0.38), (5.3, algo_y+0.4),
                            arrowstyle='->', mutation_scale=15, 
                            color='#2ca02c', linewidth=1.5)
    ax.add_patch(arrow3)
    
    arrow4 = FancyArrowPatch((7.5, route_y-0.38), (7.4, algo_y+0.4),
                            arrowstyle='->', mutation_scale=15, 
                            color='#2ca02c', linewidth=1.5)
    ax.add_patch(arrow4)
    
    # ===== 数据存储层 =====
    storage_color = '#FFE6E6'
    storage_y = 2
    
    # 数据库
    rect_db = FancyBboxPatch((1, storage_y-0.4), 2, 0.8, 
                            boxstyle="round,pad=0.05", 
                            edgecolor='#9467bd', facecolor=storage_color, linewidth=2)
    ax.add_patch(rect_db)
    ax.text(2, storage_y, '数据库\n(SQLite/PostgreSQL)', 
            ha='center', va='center', fontsize=10, fontweight='bold')
    
    # 缓存
    rect_cache = FancyBboxPatch((3.5, storage_y-0.4), 2, 0.8, 
                               boxstyle="round,pad=0.05", 
                               edgecolor='#9467bd', facecolor=storage_color, linewidth=2)
    ax.add_patch(rect_cache)
    ax.text(4.5, storage_y, '缓存系统\n(Redis)', 
            ha='center', va='center', fontsize=10, fontweight='bold')
    
    # 模型文件
    rect_models = FancyBboxPatch((6, storage_y-0.4), 2, 0.8, 
                                boxstyle="round,pad=0.05", 
                                edgecolor='#9467bd', facecolor=storage_color, linewidth=2)
    ax.add_patch(rect_models)
    ax.text(7, storage_y, '模型仓库\n(.pth weights)', 
            ha='center', va='center', fontsize=10, fontweight='bold')
    
    # 箭头: 算法 → 存储
    arrow_db = FancyArrowPatch((3, algo_y-0.4), (2, storage_y+0.4),
                              arrowstyle='<->', mutation_scale=15, 
                              color='#d62728', linewidth=1.5)
    ax.add_patch(arrow_db)
    
    arrow_cache = FancyArrowPatch((3.2, algo_y-0.4), (4.5, storage_y+0.4),
                                arrowstyle='<->', mutation_scale=15, 
                                color='#d62728', linewidth=1.5)
    ax.add_patch(arrow_cache)
    
    arrow_models = FancyArrowPatch((1.1, algo_y-0.4), (7, storage_y+0.4),
                                 arrowstyle='->', mutation_scale=15, 
                                 color='#d62728', linewidth=1.5)
    ax.add_patch(arrow_models)
    
    # ===== 数据流说明 =====
    flow_y = 0.5
    ax.text(0.3, flow_y, '数据流向:', fontsize=10, fontweight='bold')
    ax.plot([1.2, 1.5], [flow_y, flow_y], 'o-', color='#1f77b4', linewidth=2, markersize=5)
    ax.text(1.7, flow_y, '用户交互', fontsize=9, va='center')
    
    ax.plot([3, 3.3], [flow_y, flow_y], 'o-', color='#2ca02c', linewidth=2, markersize=5)
    ax.text(3.5, flow_y, '业务逻辑', fontsize=9, va='center')
    
    ax.plot([5, 5.3], [flow_y, flow_y], 'o-', color='#d62728', linewidth=2, markersize=5)
    ax.text(5.5, flow_y, '模型推理', fontsize=9, va='center')
    
    ax.plot([7, 7.3], [flow_y, flow_y], 'o-', color='#9467bd', linewidth=2, markersize=5)
    ax.text(7.5, flow_y, '数据存储', fontsize=9, va='center')
    
    plt.tight_layout()
    return fig


# ============================================================================
# 图2: 单图检测算法数据流（ResNet50 + Grad-CAM）
# ============================================================================
def draw_single_image_detection():
    """绘制单图检测算法的详细数据流图"""
    fig, ax = plt.subplots(figsize=(14, 10))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 10)
    ax.axis('off')
    
    # 标题
    ax.text(5, 9.7, '单图检测算法数据流 (ResNet50 + Grad-CAM)', 
            fontsize=16, fontweight='bold', ha='center')
    
    # ===== 第1阶段: 输入处理 =====
    stage1_y = 8.8
    # 输入框
    rect_input = FancyBboxPatch((0.5, stage1_y-0.4), 2, 0.8, 
                               boxstyle="round,pad=0.05", 
                               edgecolor='#1f77b4', facecolor='#E8F4F8', linewidth=2)
    ax.add_patch(rect_input)
    ax.text(1.5, stage1_y, '图片输入\n(PIL Image)', ha='center', va='center', fontsize=10, fontweight='bold')
    
    # 处理步骤
    processing_steps = [
        '1. RGB转换\n2. 缩放(224×224)'
    ]
    rect_proc1 = FancyBboxPatch((3, stage1_y-0.4), 2, 0.8, 
                               boxstyle="round,pad=0.05", 
                               edgecolor='#17becf', facecolor='#E6F7FF', linewidth=2)
    ax.add_patch(rect_proc1)
    ax.text(4, stage1_y, processing_steps[0], ha='center', va='center', fontsize=9)
    
    # 归一化
    rect_norm = FancyBboxPatch((5.5, stage1_y-0.4), 1.8, 0.8, 
                              boxstyle="round,pad=0.05", 
                              edgecolor='#17becf', facecolor='#E6F7FF', linewidth=2)
    ax.add_patch(rect_norm)
    ax.text(6.4, stage1_y, '张量化\nImageNet\n归一化', ha='center', va='center', fontsize=8)
    
    # 输出
    rect_tensor = FancyBboxPatch((7.8, stage1_y-0.4), 1.8, 0.8, 
                                boxstyle="round,pad=0.05", 
                                edgecolor='#2ca02c', facecolor='#E6FFE6', linewidth=2)
    ax.add_patch(rect_tensor)
    ax.text(8.7, stage1_y, '张量输出\n(1,3,224,224)', ha='center', va='center', fontsize=9)
    
    # 箭头: 输入处理链
    for i, (start, end) in enumerate([(1.5, 4), (4, 6.4), (6.4, 8.7)]):
        arrow = FancyArrowPatch((start+1, stage1_y), (end-1, stage1_y),
                               arrowstyle='->', mutation_scale=15, 
                               color='#1f77b4', linewidth=1.5)
        ax.add_patch(arrow)
    
    ax.text(5, stage1_y+0.7, '阶段1: 输入预处理', fontsize=11, fontweight='bold', 
            bbox=dict(boxstyle='round', facecolor='#FFFFCC', alpha=0.7))
    
    # ===== 第2阶段: 主干网络推理 =====
    stage2_y = 7.3
    
    # ResNet50主干
    rect_backbone = FancyBboxPatch((1, stage2_y-0.5), 3.5, 1, 
                                  boxstyle="round,pad=0.05", 
                                  edgecolor='#d62728', facecolor='#FFE6E6', linewidth=2)
    ax.add_patch(rect_backbone)
    ax.text(2.75, stage2_y, 'ResNet50 主干网络\n(预训练权重微调)\n\nconv1 → layer1/2/3/4', 
            ha='center', va='center', fontsize=10, fontweight='bold')
    
    # 特征提取
    rect_features = FancyBboxPatch((5, stage2_y-0.5), 2, 1, 
                                  boxstyle="round,pad=0.05", 
                                  edgecolor='#d62728', facecolor='#FFE6E6', linewidth=2)
    ax.add_patch(rect_features)
    ax.text(6, stage2_y, '中间特征\n(layer4输出)\n2048维\nshape:(1,2048,\n7,7)', 
            ha='center', va='center', fontsize=8)
    
    # FC层
    rect_fc = FancyBboxPatch((7.5, stage2_y-0.5), 2, 1, 
                            boxstyle="round,pad=0.05", 
                            edgecolor='#d62728', facecolor='#FFE6E6', linewidth=2)
    ax.add_patch(rect_fc)
    ax.text(8.5, stage2_y, '全连接层\n2048 → 2\n\n输出logits\n(1,2)', 
            ha='center', va='center', fontsize=9)
    
    # 箭头
    arrow = FancyArrowPatch((8.7, stage1_y-0.4), (2.75, stage2_y+0.5),
                           arrowstyle='->', mutation_scale=15, 
                           color='#d62728', linewidth=2)
    ax.add_patch(arrow)
    
    arrow1 = FancyArrowPatch((4.5, stage2_y), (5, stage2_y),
                            arrowstyle='->', mutation_scale=15, 
                            color='#d62728', linewidth=1.5)
    ax.add_patch(arrow1)
    
    arrow2 = FancyArrowPatch((7, stage2_y), (7.5, stage2_y),
                            arrowstyle='->', mutation_scale=15, 
                            color='#d62728', linewidth=1.5)
    ax.add_patch(arrow2)
    
    ax.text(5, stage2_y+0.8, '阶段2: 深度学习推理', fontsize=11, fontweight='bold',
            bbox=dict(boxstyle='round', facecolor='#FFFFCC', alpha=0.7))
    
    # ===== 第3阶段: 分类 =====
    stage3_y = 5.5
    
    # Softmax
    rect_softmax = FancyBboxPatch((1, stage3_y-0.4), 2.5, 0.8, 
                                 boxstyle="round,pad=0.05", 
                                 edgecolor='#ff7f0e', facecolor='#FFF4E6', linewidth=2)
    ax.add_patch(rect_softmax)
    ax.text(2.25, stage3_y, 'Softmax\n概率计算', ha='center', va='center', fontsize=10, fontweight='bold')
    
    # 结果输出
    rect_result = FancyBboxPatch((4, stage3_y-0.4), 3, 0.8, 
                                boxstyle="round,pad=0.05", 
                                edgecolor='#ff7f0e', facecolor='#FFF4E6', linewidth=2)
    ax.add_patch(rect_result)
    ax.text(5.5, stage3_y, 'FAKE: 45% | REAL: 55%\n置信度评估', 
            ha='center', va='center', fontsize=9)
    
    # 文本解释
    rect_explain = FancyBboxPatch((7.3, stage3_y-0.4), 2.3, 0.8, 
                                 boxstyle="round,pad=0.05", 
                                 edgecolor='#ff7f0e', facecolor='#FFF4E6', linewidth=2)
    ax.add_patch(rect_explain)
    ax.text(8.45, stage3_y, '规则化解释\n(置信度等级)', ha='center', va='center', fontsize=9)
    
    # 箭头
    arrow = FancyArrowPatch((9.5, stage2_y-0.5), (2.25, stage3_y+0.4),
                           arrowstyle='->', mutation_scale=15, 
                           color='#ff7f0e', linewidth=2)
    ax.add_patch(arrow)
    
    arrow1 = FancyArrowPatch((3.5, stage3_y), (4, stage3_y),
                            arrowstyle='->', mutation_scale=15, 
                            color='#ff7f0e', linewidth=1.5)
    ax.add_patch(arrow1)
    
    arrow2 = FancyArrowPatch((7, stage3_y), (7.3, stage3_y),
                            arrowstyle='->', mutation_scale=15, 
                            color='#ff7f0e', linewidth=1.5)
    ax.add_patch(arrow2)
    
    ax.text(5, stage3_y+0.7, '阶段3: 结果获取', fontsize=11, fontweight='bold',
            bbox=dict(boxstyle='round', facecolor='#FFFFCC', alpha=0.7))
    
    # ===== 第4阶段: Grad-CAM热力图 =====
    stage4_y = 3.8
    
    ax.text(5, stage4_y+0.8, '阶段4: Grad-CAM 可解释性分析（可选）', fontsize=11, fontweight='bold',
            bbox=dict(boxstyle='round', facecolor='#FFFFCC', alpha=0.7))
    
    # Grad-CAM步骤
    gradcam_steps = [
        ('layer4\n收集梯度', 1.5),
        ('计算权重\nW=∂L/∂A', 3.2),
        ('加权求和\nCAM=ΣwA', 4.9),
        ('ReLU激活\nmax(CAM,0)', 6.6),
        ('双线性\n插值224×224', 8.3)
    ]
    
    for i, (step, x) in enumerate(gradcam_steps):
        color = '#FFE6E6' if i % 2 == 0 else '#E6F7FF'
        rect = FancyBboxPatch((x-0.6, stage4_y-0.35), 1.2, 0.7, 
                             boxstyle="round,pad=0.03", 
                             edgecolor='#d62728', facecolor=color, linewidth=1.5)
        ax.add_patch(rect)
        ax.text(x, stage4_y, step, ha='center', va='center', fontsize=8)
        
        if i < len(gradcam_steps) - 1:
            arrow = FancyArrowPatch((x+0.6, stage4_y), (x+0.9, stage4_y),
                                   arrowstyle='->', mutation_scale=12, 
                                   color='#d62728', linewidth=1.5)
            ax.add_patch(arrow)
    
    # Grad-CAM输出
    rect_gradcam_out = FancyBboxPatch((1.5, stage4_y-1.2), 7, 0.6, 
                                     boxstyle="round,pad=0.05", 
                                     edgecolor='#d62728', facecolor='#FFE6E6', linewidth=2)
    ax.add_patch(rect_gradcam_out)
    ax.text(5, stage4_y-0.9, '热力图输出：overlay红色热力图到原图 → Base64 JPEG编码', 
            ha='center', va='center', fontsize=9, fontweight='bold')
    
    # ===== 第5阶段: 最终输出 =====
    stage5_y = 1.5
    
    output_items = [
        '标签\n(FAKE/REAL)',
        '置信度\n(0-100%)',
        '概率分布\n[p_fake, p_real]',
        '热力图\n(Base64)',
        '文本解释\n(规则库)'
    ]
    
    for i, item in enumerate(output_items):
        x = 1 + i * 1.8
        rect = FancyBboxPatch((x-0.7, stage5_y-0.35), 1.4, 0.7, 
                             boxstyle="round,pad=0.05", 
                             edgecolor='#2ca02c', facecolor='#E6FFE6', linewidth=2)
        ax.add_patch(rect)
        ax.text(x, stage5_y, item, ha='center', va='center', fontsize=8, fontweight='bold')
    
    # 箭头汇聚
    for i, item in enumerate(output_items):
        x = 1 + i * 1.8
        arrow = FancyArrowPatch((x, stage4_y-1.2), (x, stage5_y+0.35),
                               arrowstyle='->', mutation_scale=12, 
                               color='#2ca02c', linewidth=1.5)
        ax.add_patch(arrow)
    
    ax.text(5, stage5_y+1, '阶段5: 结构化输出', fontsize=11, fontweight='bold',
            bbox=dict(boxstyle='round', facecolor='#FFFFCC', alpha=0.7))
    
    # 调用处理函数说明
    ax.text(0.3, 0.3, '核心函数: detect_image() | 热力图函数: grad_cam_overlay()', 
            fontsize=9, style='italic',
            bbox=dict(boxstyle='round', facecolor='#CCCCCC', alpha=0.5))
    
    plt.tight_layout()
    return fig


# ============================================================================
# 图3: CLIP多模态分析数据流
# ============================================================================
def draw_clip_multimodal_flow():
    """绘制CLIP内容分类和图文一致性检测的数据流"""
    fig, ax = plt.subplots(figsize=(16, 10))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 10)
    ax.axis('off')
    
    # 标题
    ax.text(5, 9.7, 'CLIP 多模态分析数据流（内容分类 + 图文一致性检测）', 
            fontsize=16, fontweight='bold', ha='center')
    
    # ===== 左侧: 内容分类流程 =====
    ax.text(2.5, 9.1, '内容分类流程', fontsize=12, fontweight='bold',
            bbox=dict(boxstyle='round', facecolor='#FFE6CC', alpha=0.8))
    
    # 输入
    rect_img1 = FancyBboxPatch((0.5, 8.2), 1.5, 0.6, 
                              boxstyle="round,pad=0.05", 
                              edgecolor='#1f77b4', facecolor='#E8F4F8', linewidth=2)
    ax.add_patch(rect_img1)
    ax.text(1.25, 8.5, '图片输入', ha='center', va='center', fontsize=10, fontweight='bold')
    
    # 图像编码
    rect_img_enc = FancyBboxPatch((0.5, 7.2), 1.5, 0.6, 
                                 boxstyle="round,pad=0.05", 
                                 edgecolor='#2ca02c', facecolor='#E6FFE6', linewidth=2)
    ax.add_patch(rect_img_enc)
    ax.text(1.25, 7.5, 'CLIP\n图像编码器', ha='center', va='center', fontsize=9, fontweight='bold')
    
    arrow = FancyArrowPatch((1.25, 8.2), (1.25, 7.8),
                           arrowstyle='->', mutation_scale=15, 
                           color='#1f77b4', linewidth=2)
    ax.add_patch(arrow)
    
    # 特征向量
    rect_img_feat = FancyBboxPatch((0.2, 6.2), 2.1, 0.6, 
                                  boxstyle="round,pad=0.05", 
                                  edgecolor='#2ca02c', facecolor='#E6FFE6', linewidth=2)
    ax.add_patch(rect_img_feat)
    ax.text(1.25, 6.5, '图像特征\nfeature_img ∈ℝ512\n(单位向量)', 
            ha='center', va='center', fontsize=8)
    
    arrow = FancyArrowPatch((1.25, 7.2), (1.25, 6.8),
                           arrowstyle='->', mutation_scale=15, 
                           color='#2ca02c', linewidth=2)
    ax.add_patch(arrow)
    
    # 分类标签库
    categories = ['人物', '动物', '建筑', '风景', '食物', '交通', '其他']
    rect_labels = FancyBboxPatch((3.2, 7.5), 1.5, 1.3, 
                                boxstyle="round,pad=0.05", 
                                edgecolor='#ff7f0e', facecolor='#FFF4E6', linewidth=2)
    ax.add_patch(rect_labels)
    ax.text(3.95, 8.4, '7类标签\n+ 提示词', ha='center', va='center', fontsize=9, fontweight='bold')
    for i, cat in enumerate(categories):
        ax.text(3.95, 8.1-i*0.15, f'• {cat}', ha='center', va='center', fontsize=7)
    
    # 文本编码
    rect_text_enc = FancyBboxPatch((3.2, 6.2), 1.5, 0.6, 
                                  boxstyle="round,pad=0.05", 
                                  edgecolor='#ff7f0e', facecolor='#FFF4E6', linewidth=2)
    ax.add_patch(rect_text_enc)
    ax.text(3.95, 6.5, 'CLIP文本\n编码器×7', ha='center', va='center', fontsize=9, fontweight='bold')
    
    arrow = FancyArrowPatch((3.95, 7.5), (3.95, 6.8),
                           arrowstyle='->', mutation_scale=15, 
                           color='#ff7f0e', linewidth=2)
    ax.add_patch(arrow)
    
    # 文本特征
    rect_text_feat = FancyBboxPatch((3.2, 5.2), 1.5, 0.6, 
                                   boxstyle="round,pad=0.05", 
                                   edgecolor='#ff7f0e', facecolor='#FFF4E6', linewidth=2)
    ax.add_patch(rect_text_feat)
    ax.text(3.95, 5.5, '7维文本\n特征矩阵\n(7,512)', ha='center', va='center', fontsize=8)
    
    arrow = FancyArrowPatch((3.95, 6.2), (3.95, 5.8),
                           arrowstyle='->', mutation_scale=15, 
                           color='#ff7f0e', linewidth=2)
    ax.add_patch(arrow)
    
    # 余弦相似度
    rect_cosine1 = FancyBboxPatch((1.5, 4.8), 2.5, 0.8, 
                                 boxstyle="round,pad=0.05", 
                                 edgecolor='#d62728', facecolor='#FFE6E6', linewidth=2)
    ax.add_patch(rect_cosine1)
    ax.text(2.75, 5.2, '余弦相似度计算\nsim = img @ text.T\nshape: (7,)', 
            ha='center', va='center', fontsize=9, fontweight='bold')
    
    # 箭头汇聚
    arrow1 = FancyArrowPatch((1.25, 6.2), (2.2, 5.3),
                            arrowstyle='->', mutation_scale=15, 
                            color='#2ca02c', linewidth=1.5)
    ax.add_patch(arrow1)
    
    arrow2 = FancyArrowPatch((3.95, 5.2), (3.3, 5.3),
                            arrowstyle='->', mutation_scale=15, 
                            color='#ff7f0e', linewidth=1.5)
    ax.add_patch(arrow2)
    
    # 分类结果
    rect_class_result = FancyBboxPatch((0.8, 3.5), 3.5, 0.7, 
                                      boxstyle="round,pad=0.05", 
                                      edgecolor='#2ca02c', facecolor='#E6FFE6', linewidth=2)
    ax.add_patch(rect_class_result)
    ax.text(2.55, 3.85, '分类结果: argmax(sims) → category_label (e.g., "建筑")', 
            ha='center', va='center', fontsize=9, fontweight='bold')
    
    arrow = FancyArrowPatch((2.75, 4.8), (2.55, 4.2),
                           arrowstyle='->', mutation_scale=15, 
                           color='#d62728', linewidth=2)
    ax.add_patch(arrow)
    
    # ===== 右侧: 图文一致性流程 =====
    ax.text(7.5, 9.1, '图文一致性检测流程', fontsize=12, fontweight='bold',
            bbox=dict(boxstyle='round', facecolor='#E6F7FF', alpha=0.8))
    
    # 输入
    rect_img2 = FancyBboxPatch((5.8, 8.2), 1.5, 0.6, 
                              boxstyle="round,pad=0.05", 
                              edgecolor='#1f77b4', facecolor='#E8F4F8', linewidth=2)
    ax.add_patch(rect_img2)
    ax.text(6.55, 8.5, '图片+文本', ha='center', va='center', fontsize=10, fontweight='bold')
    
    # 图像编码（同左侧）
    arrow = FancyArrowPatch((6.55, 8.2), (6.55, 7.8),
                           arrowstyle='->', mutation_scale=15, 
                           color='#1f77b4', linewidth=2)
    ax.add_patch(arrow)
    
    rect_img_enc2 = FancyBboxPatch((5.8, 7.2), 1.5, 0.6, 
                                  boxstyle="round,pad=0.05", 
                                  edgecolor='#2ca02c', facecolor='#E6FFE6', linewidth=2)
    ax.add_patch(rect_img_enc2)
    ax.text(6.55, 7.5, 'CLIP\n图像编码器', ha='center', va='center', fontsize=9, fontweight='bold')
    
    # 特征向量
    rect_img_feat2 = FancyBboxPatch((5.5, 6.2), 2.1, 0.6, 
                                   boxstyle="round,pad=0.05", 
                                   edgecolor='#2ca02c', facecolor='#E6FFE6', linewidth=2)
    ax.add_patch(rect_img_feat2)
    ax.text(6.55, 6.5, '图像特征\nfeature_img\n(单位向量)', 
            ha='center', va='center', fontsize=8)
    
    arrow = FancyArrowPatch((6.55, 7.2), (6.55, 6.8),
                           arrowstyle='->', mutation_scale=15, 
                           color='#2ca02c', linewidth=2)
    ax.add_patch(arrow)
    
    # 对齐和不对齐提示词
    rect_prompts = FancyBboxPatch((8.3, 6.8), 1.5, 1.3, 
                                 boxstyle="round,pad=0.05", 
                                 edgecolor='#ff7f0e', facecolor='#FFF4E6', linewidth=2)
    ax.add_patch(rect_prompts)
    ax.text(9.05, 7.8, '7个提示词', ha='center', va='center', fontsize=9, fontweight='bold')
    ax.text(9.05, 7.4, '●4个对齐', ha='center', va='center', fontsize=8)
    ax.text(9.05, 7.1, '●3个不对齐', ha='center', va='center', fontsize=8)
    ax.text(9.05, 6.8, '(基线)', ha='center', va='center', fontsize=7, style='italic')
    
    # 文本编码
    rect_text_enc2 = FancyBboxPatch((8.3, 5.8), 1.5, 0.6, 
                                   boxstyle="round,pad=0.05", 
                                   edgecolor='#ff7f0e', facecolor='#FFF4E6', linewidth=2)
    ax.add_patch(rect_text_enc2)
    ax.text(9.05, 6.1, 'CLIP文本\n编码器×7', ha='center', va='center', fontsize=9, fontweight='bold')
    
    arrow = FancyArrowPatch((9.05, 6.8), (9.05, 6.4),
                           arrowstyle='->', mutation_scale=15, 
                           color='#ff7f0e', linewidth=2)
    ax.add_patch(arrow)
    
    # 相似度计算
    rect_cosine2 = FancyBboxPatch((6.8, 4.8), 2.5, 0.8, 
                                 boxstyle="round,pad=0.05", 
                                 edgecolor='#d62728', facecolor='#FFE6E6', linewidth=2)
    ax.add_patch(rect_cosine2)
    ax.text(8.05, 5.2, '相似度计算\nsim[0:4] 对齐均值\nsim[4:7] 不对齐均值', 
            ha='center', va='center', fontsize=8, fontweight='bold')
    
    arrow1 = FancyArrowPatch((6.55, 6.2), (7.5, 5.3),
                            arrowstyle='->', mutation_scale=15, 
                            color='#2ca02c', linewidth=1.5)
    ax.add_patch(arrow1)
    
    arrow2 = FancyArrowPatch((9.05, 5.8), (8.6, 5.3),
                            arrowstyle='->', mutation_scale=15, 
                            color='#ff7f0e', linewidth=1.5)
    ax.add_patch(arrow2)
    
    # 一致性评分
    rect_consistency = FancyBboxPatch((6.2, 3.5), 3.5, 0.7, 
                                     boxstyle="round,pad=0.05", 
                                     edgecolor='#2ca02c', facecolor='#E6FFE6', linewidth=2)
    ax.add_patch(rect_consistency)
    ax.text(8.05, 3.85, '一致性评分 gap_norm→[0,100]\'高度\'→\'不一致', 
            ha='center', va='center', fontsize=9, fontweight='bold')
    
    arrow = FancyArrowPatch((8.05, 4.8), (8.05, 4.2),
                           arrowstyle='->', mutation_scale=15, 
                           color='#d62728', linewidth=2)
    ax.add_patch(arrow)
    
    # ===== 底部: 综合流程说明 =====
    summary_y = 2.5
    ax.text(5, summary_y+0.5, '综合数据流总结', fontsize=12, fontweight='bold',
            bbox=dict(boxstyle='round', facecolor='#FFFFCC', alpha=0.8))
    
    # 流程框
    flow_text = '''图像 → CLIP ViT-B/32编码器 (512维特征)
    ↓
    ├─ 分支1: 7类标签 → Softmax概率 → 分类标签
    └─ 分支2: 4对齐+3不对齐文本 → 相似度计算 → 一致性评分'''
    
    rect_summary = FancyBboxPatch((1, summary_y-1.3), 8, 1.5, 
                                 boxstyle="round,pad=0.1", 
                                 edgecolor='#9467bd', facecolor='#F0E6FF', linewidth=2)
    ax.add_patch(rect_summary)
    ax.text(5, summary_y-0.55, flow_text, ha='center', va='center', fontsize=9, family='monospace')
    
    # 函数说明
    ax.text(0.3, 0.3, '核心函数: classify_image() | classify_text_image_consistency()', 
            fontsize=9, style='italic',
            bbox=dict(boxstyle='round', facecolor='#CCCCCC', alpha=0.5))
    
    plt.tight_layout()
    return fig


# ============================================================================
# 图4: URL批量检测与实时进度推送数据流
# ============================================================================
def draw_url_batch_detection_flow():
    """绘制URL批量检测和WebSocket实时进度推送的数据流"""
    fig, ax = plt.subplots(figsize=(16, 10))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 10)
    ax.axis('off')
    
    # 标题
    ax.text(5, 9.7, 'URL 批量检测与实时进度推送数据流', 
            fontsize=16, fontweight='bold', ha='center')
    
    # ===== 第1层: 用户交互 =====
    layer1_y = 8.8
    rect_user = FancyBboxPatch((1, layer1_y-0.4), 3.5, 0.8, 
                              boxstyle="round,pad=0.05", 
                              edgecolor='#1f77b4', facecolor='#E8F4F8', linewidth=2)
    ax.add_patch(rect_user)
    ax.text(2.75, layer1_y, '用户输入URL\n(新闻页面链接)', 
            ha='center', va='center', fontsize=10, fontweight='bold')
    
    rect_user2 = FancyBboxPatch((5.5, layer1_y-0.4), 3.5, 0.8, 
                               boxstyle="round,pad=0.05", 
                               edgecolor='#1f77b4', facecolor='#E8F4F8', linewidth=2)
    ax.add_patch(rect_user2)
    ax.text(7.25, layer1_y, 'POST /api/detect-url\n初始化检测任务', 
            ha='center', va='center', fontsize=10, fontweight='bold')
    
    ax.text(5, layer1_y+0.7, '第1层: 用户请求', fontsize=11, fontweight='bold',
            bbox=dict(boxstyle='round', facecolor='#FFFFCC', alpha=0.7))
    
    arrow = FancyArrowPatch((4.5, layer1_y), (5.5, layer1_y),
                           arrowstyle='->', mutation_scale=15, 
                           color='#1f77b4', linewidth=2)
    ax.add_patch(arrow)
    
    # ===== 第2层: 页面抓取与分析 =====
    layer2_y = 7.3
    
    steps_layer2 = [
        ('URL验证\nSSRF防护', 1),
        ('页面下载\nHTTP请求', 2.8),
        ('HTML解析\nBeautifulSoup', 4.6),
        ('图片提取\n<img>标签', 6.4),
        ('URL归一化\n检测重复', 8.2)
    ]
    
    for step, x in steps_layer2:
        rect = FancyBboxPatch((x-0.7, layer2_y-0.35), 1.4, 0.7, 
                             boxstyle="round,pad=0.05", 
                             edgecolor='#2ca02c', facecolor='#E6FFE6', linewidth=1.5)
        ax.add_patch(rect)
        ax.text(x, layer2_y, step, ha='center', va='center', fontsize=8)
        
        if x < 8.2:
            arrow = FancyArrowPatch((x+0.7, layer2_y), (x+1, layer2_y),
                                   arrowstyle='->', mutation_scale=12, 
                                   color='#2ca02c', linewidth=1.5)
            ax.add_patch(arrow)
    
    ax.text(5, layer2_y+0.7, '第2层: 页面爬取与图片收集', fontsize=11, fontweight='bold',
            bbox=dict(boxstyle='round', facecolor='#FFFFCC', alpha=0.7))
    
    arrow = FancyArrowPatch((7.25, layer1_y-0.4), (5, layer2_y+0.35),
                           arrowstyle='->', mutation_scale=15, 
                           color='#1f77b4', linewidth=2)
    ax.add_patch(arrow)
    
    # ===== 第3层: 异步并发下载 =====
    layer3_y = 5.8
    
    rect_pool = FancyBboxPatch((0.8, layer3_y-0.5), 3.5, 1, 
                              boxstyle="round,pad=0.05", 
                              edgecolor='#d62728', facecolor='#FFE6E6', linewidth=2)
    ax.add_patch(rect_pool)
    ax.text(2.55, layer3_y, '异步并发下载\n(asyncio.gather)\n\n最多5个并发流', 
            ha='center', va='center', fontsize=9, fontweight='bold')
    
    # 下载队列
    rect_queue = FancyBboxPatch((5, layer3_y-0.5), 4.2, 1, 
                               boxstyle="round,pad=0.05", 
                               edgecolor='#ff7f0e', facecolor='#FFF4E6', linewidth=2)
    ax.add_patch(rect_queue)
    ax.text(7.1, layer3_y+0.15, 'Image Queue\n(asyncio.Queue)', 
            ha='center', va='center', fontsize=9, fontweight='bold')
    ax.text(7.1, layer3_y-0.25, '[img1] [img2] [img3] ... [imgN]\n(内存缓冲)', 
            ha='center', va='center', fontsize=8, style='italic')
    
    arrow = FancyArrowPatch((8.9, layer2_y-0.35), (7.1, layer3_y+0.5),
                           arrowstyle='->', mutation_scale=15, 
                           color='#2ca02c', linewidth=2)
    ax.add_patch(arrow)
    
    arrow = FancyArrowPatch((4.3, layer3_y), (5, layer3_y),
                           arrowstyle='->', mutation_scale=15, 
                           color='#d62728', linewidth=2)
    ax.add_patch(arrow)
    
    ax.text(5, layer3_y+0.8, '第3层: 异步并发处理', fontsize=11, fontweight='bold',
            bbox=dict(boxstyle='round', facecolor='#FFFFCC', alpha=0.7))
    
    # ===== 第4层: 批量检测 =====
    layer4_y = 4
    
    rect_batch = FancyBboxPatch((1.5, layer4_y-0.5), 3, 1, 
                               boxstyle="round,pad=0.05", 
                               edgecolor='#d62728', facecolor='#FFE6E6', linewidth=2)
    ax.add_patch(rect_batch)
    ax.text(3, layer4_y, 'detect_batch()\n批量推理\n\n[img1...imgN]\n→ [result1...resultN]', 
            ha='center', va='center', fontsize=9, fontweight='bold')
    
    # 缓存检查
    rect_cache = FancyBboxPatch((5, layer4_y-0.5), 2.5, 1, 
                               boxstyle="round,pad=0.05", 
                               edgecolor='#17becf', facecolor='#E6F7FF', linewidth=2)
    ax.add_patch(rect_cache)
    ax.text(6.25, layer4_y, 'Redis缓存\n检查\n(哈希避免\n重复推理)', 
            ha='center', va='center', fontsize=8, fontweight='bold')
    
    # CLIP分类
    rect_clip2 = FancyBboxPatch((7.8, layer4_y-0.5), 1.8, 1, 
                               boxstyle="round,pad=0.05", 
                               edgecolor='#ff7f0e', facecolor='#FFF4E6', linewidth=2)
    ax.add_patch(rect_clip2)
    ax.text(8.7, layer4_y, 'CLIP\n分类\n+一致性\n检测', 
            ha='center', va='center', fontsize=8, fontweight='bold')
    
    arrow = FancyArrowPatch((7.1, layer3_y-0.5), (3, layer4_y+0.5),
                           arrowstyle='->', mutation_scale=15, 
                           color='#ff7f0e', linewidth=2)
    ax.add_patch(arrow)
    
    arrow = FancyArrowPatch((3, layer4_y-0.5), (6.25, layer4_y),
                           arrowstyle='<->', mutation_scale=15, 
                           color='#17becf', linewidth=1.5)
    ax.add_patch(arrow)
    
    arrow = FancyArrowPatch((6, layer4_y), (7.8, layer4_y),
                           arrowstyle='->', mutation_scale=15, 
                           color='#ff7f0e', linewidth=1.5)
    ax.add_patch(arrow)
    
    ax.text(5, layer4_y+0.8, '第4层: 模型推理与结果缓存', fontsize=11, fontweight='bold',
            bbox=dict(boxstyle='round', facecolor='#FFFFCC', alpha=0.7))
    
    # ===== 第5层: WebSocket实时推送 =====
    layer5_y = 2
    
    rect_ws_send = FancyBboxPatch((0.5, layer5_y-0.5), 4, 1, 
                                 boxstyle="round,pad=0.05", 
                                 edgecolor='#9467bd', facecolor='#F0E6FF', linewidth=2)
    ax.add_patch(rect_ws_send)
    ax.text(2.5, layer5_y, 'WebSocket\n实时推送进度事件\n\nEvent:\n{type, index, result}', 
            ha='center', va='center', fontsize=9, fontweight='bold')
    
    rect_client = FancyBboxPatch((5, layer5_y-0.5), 4.5, 1, 
                                boxstyle="round,pad=0.05", 
                                edgecolor='#9467bd', facecolor='#F0E6FF', linewidth=2)
    ax.add_patch(rect_client)
    ax.text(7.25, layer5_y, '前端客户端\n实时显示进度条\n\n进度: 3/20\n缩略图+标签+置信度', 
            ha='center', va='center', fontsize=9, fontweight='bold')
    
    arrow = FancyArrowPatch((4.5, layer4_y-0.5), (2.5, layer5_y+0.5),
                           arrowstyle='->', mutation_scale=15, 
                           color='#9467bd', linewidth=2)
    ax.add_patch(arrow)
    
    arrow = FancyArrowPatch((2.5, layer5_y-0.5), (7.25, layer5_y+0.5),
                           arrowstyle='->', mutation_scale=15, 
                           color='#9467bd', linewidth=2)
    ax.add_patch(arrow)
    
    ax.text(5, layer5_y+0.8, '第5层: 实时反馈与交互', fontsize=11, fontweight='bold',
            bbox=dict(boxstyle='round', facecolor='#FFFFCC', alpha=0.7))
    
    # ===== 最终状态 =====
    final_y = 0.3
    ax.text(5, final_y+0.5, '最终状态: {type: "complete", results: [...], overall_score: ...}', 
            fontsize=10, fontweight='bold', 
            bbox=dict(boxstyle='round', facecolor='#E6FFE6', alpha=0.8))
    
    plt.tight_layout()
    return fig


# ============================================================================
# 图5: 报告生成与导出工作流
# ============================================================================
def draw_report_generation_workflow():
    """绘制检测报告生成和PDF/Excel导出的工作流"""
    fig, ax = plt.subplots(figsize=(14, 10))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 10)
    ax.axis('off')
    
    # 标题
    ax.text(5, 9.7, '检测报告生成与多格式导出工作流', 
            fontsize=16, fontweight='bold', ha='center')
    
    # ===== 第1阶段: 检测数据聚合 =====
    stage1_y = 8.8
    
    ax.text(5, stage1_y+0.6, '阶段1: 检测数据聚合', fontsize=11, fontweight='bold',
            bbox=dict(boxstyle='round', facecolor='#FFFFCC', alpha=0.7))
    
    data_sources = [
        ('检测ID\n(detection_id)', 0.8),
        ('用户信息\n(user_id)', 2.3),
        ('检测结果\n(label/conf)', 3.8),
        ('CLIP分类\n(category)', 5.3),
        ('图文一致性\n(consistency)', 6.8),
        ('Grad-CAM\n热力图', 8.3)
    ]
    
    for source, x in data_sources:
        rect = FancyBboxPatch((x-0.5, stage1_y-0.35), 1, 0.7, 
                             boxstyle="round,pad=0.03", 
                             edgecolor='#1f77b4', facecolor='#E8F4F8', linewidth=1.5)
        ax.add_patch(rect)
        ax.text(x, stage1_y, source, ha='center', va='center', fontsize=7, fontweight='bold')
    
    # ===== 第2阶段: 数据库查询 =====
    stage2_y = 7.5
    
    ax.text(5, stage2_y+0.6, '阶段2: 数据库查询与聚合', fontsize=11, fontweight='bold',
            bbox=dict(boxstyle='round', facecolor='#FFFFCC', alpha=0.7))
    
    rect_db_query = FancyBboxPatch((1.5, stage2_y-0.5), 7, 1, 
                                  boxstyle="round,pad=0.05", 
                                  edgecolor='#ff7f0e', facecolor='#FFF4E6', linewidth=2)
    ax.add_patch(rect_db_query)
    ax.text(5, stage2_y+0.15, 'generate_report(detection_id) 数据库查询与合并', 
            ha='center', va='center', fontsize=10, fontweight='bold')
    ax.text(5, stage2_y-0.25, 'SELECT * FROM detection_records WHERE id=?', 
            ha='center', va='center', fontsize=9, style='italic', family='monospace')
    
    # 箭头
    for x in np.linspace(1.3, 8.5, 6):
        arrow = FancyArrowPatch((x, stage1_y-0.35), (5, stage2_y+0.5),
                               arrowstyle='->', mutation_scale=12, 
                               color='#1f77b4', linewidth=1, alpha=0.6)
        ax.add_patch(arrow)
    
    # ===== 第3阶段: 报告结构化 =====
    stage3_y = 6
    
    ax.text(5, stage3_y+0.6, '阶段3: 结构化报告生成', fontsize=11, fontweight='bold',
            bbox=dict(boxstyle='round', facecolor='#FFFFCC', alpha=0.7))
    
    report_sections = [
        ('基本信息\n检测ID/用户', 1.2),
        ('检测结果\n标签/置信度', 2.5),
        ('热力图\nGrad-CAM', 3.8),
        ('内容分类\nCLIP结果', 5.1),
        ('一致性评分\n图文匹配', 6.4),
        ('AI分析\n豆包总结', 7.7),
        ('时间戳\n审计日志', 8.8)
    ]
    
    for section, x in report_sections:
        rect = FancyBboxPatch((x-0.55, stage3_y-0.35), 1.1, 0.7, 
                             boxstyle="round,pad=0.03", 
                             edgecolor='#2ca02c', facecolor='#E6FFE6', linewidth=1.5)
        ax.add_patch(rect)
        ax.text(x, stage3_y, section, ha='center', va='center', fontsize=7, fontweight='bold')
        
        arrow = FancyArrowPatch((5, stage2_y-0.5), (x, stage3_y+0.35),
                               arrowstyle='->', mutation_scale=12, 
                               color='#ff7f0e', linewidth=1, alpha=0.6)
        ax.add_patch(arrow)
    
    # ===== 第4阶段: 导出格式分支 =====
    stage4_y = 4.5
    
    ax.text(5, stage4_y+0.8, '阶段4: 多格式导出', fontsize=11, fontweight='bold',
            bbox=dict(boxstyle='round', facecolor='#FFFFCC', alpha=0.7))
    
    # 中间处理
    rect_template = FancyBboxPatch((3.5, stage4_y+0.2), 3, 0.6, 
                                  boxstyle="round,pad=0.05", 
                                  edgecolor='#d62728', facecolor='#FFE6E6', linewidth=2)
    ax.add_patch(rect_template)
    ax.text(5, stage4_y+0.5, 'report_dict → 模板渲染', 
            ha='center', va='center', fontsize=10, fontweight='bold')
    
    arrow = FancyArrowPatch((5, stage3_y-0.35), (5, stage4_y+0.2),
                           arrowstyle='->', mutation_scale=15, 
                           color='#2ca02c', linewidth=2)
    ax.add_patch(arrow)
    
    # PDF导出
    rect_pdf = FancyBboxPatch((1, stage4_y-0.8), 2.5, 0.8, 
                             boxstyle="round,pad=0.05", 
                             edgecolor='#9467bd', facecolor='#F0E6FF', linewidth=2)
    ax.add_patch(rect_pdf)
    ax.text(2.25, stage4_y-0.4, 'PDF导出\n(reportlab/WeasyPrint)\n\n+ 水印\n+ 横幅', 
            ha='center', va='center', fontsize=9, fontweight='bold')
    
    arrow_pdf = FancyArrowPatch((4, stage4_y+0.2), (2.25, stage4_y),
                               arrowstyle='->', mutation_scale=15, 
                               color='#d62728', linewidth=2)
    ax.add_patch(arrow_pdf)
    
    # Excel导出
    rect_excel = FancyBboxPatch((4, stage4_y-0.8), 2.5, 0.8, 
                               boxstyle="round,pad=0.05", 
                               edgecolor='#9467bd', facecolor='#F0E6FF', linewidth=2)
    ax.add_patch(rect_excel)
    ax.text(5.25, stage4_y-0.4, 'Excel导出\n(openpyxl)\n\n+ 多Sheet\n+ 图表', 
            ha='center', va='center', fontsize=9, fontweight='bold')
    
    arrow_excel = FancyArrowPatch((5, stage4_y+0.2), (5.25, stage4_y),
                                 arrowstyle='->', mutation_scale=15, 
                                 color='#d62728', linewidth=2)
    ax.add_patch(arrow_excel)
    
    # JSON导出
    rect_json = FancyBboxPatch((7, stage4_y-0.8), 2.5, 0.8, 
                              boxstyle="round,pad=0.05", 
                              edgecolor='#9467bd', facecolor='#F0E6FF', linewidth=2)
    ax.add_patch(rect_json)
    ax.text(8.25, stage4_y-0.4, 'JSON导出\n(内部API)\n\n+ 结构化\n+ 机器可读', 
            ha='center', va='center', fontsize=9, fontweight='bold')
    
    arrow_json = FancyArrowPatch((6, stage4_y+0.2), (8.25, stage4_y),
                                arrowstyle='->', mutation_scale=15, 
                                color='#d62728', linewidth=2)
    ax.add_patch(arrow_json)
    
    # ===== 第5阶段: 文件输出与传输 =====
    stage5_y = 2.5
    
    ax.text(5, stage5_y+0.6, '阶段5: 文件输出与传输', fontsize=11, fontweight='bold',
            bbox=dict(boxstyle='round', facecolor='#FFFFCC', alpha=0.7))
    
    # 输出文件
    output_files = [
        ('report_ID.pdf\n(字节流)', 1.5),
        ('report_ID.xlsx\n(字节流)', 3.5),
        ('report_ID.json\n(字节流)', 5.5),
        ('缓存存储\nRedis/DB', 7.5)
    ]
    
    for file_type, x in output_files:
        rect = FancyBboxPatch((x-0.8, stage5_y-0.35), 1.6, 0.7, 
                             boxstyle="round,pad=0.05", 
                             edgecolor='#17becf', facecolor='#E6F7FF', linewidth=1.5)
        ax.add_patch(rect)
        ax.text(x, stage5_y, file_type, ha='center', va='center', fontsize=8, fontweight='bold')
    
    for x_from, x_to in [(2.25, 1.5), (5.25, 3.5), (8.25, 5.5)]:
        arrow = FancyArrowPatch((x_from, stage4_y-0.8), (x_to, stage5_y+0.35),
                               arrowstyle='->', mutation_scale=15, 
                               color='#9467bd', linewidth=1.5)
        ax.add_patch(arrow)
    
    # 全局缓存
    arrow_cache = FancyArrowPatch((5.25, stage4_y-0.8), (7.5, stage5_y+0.35),
                                arrowstyle='->', mutation_scale=15, 
                                color='#d62728', linewidth=1.5)
    ax.add_patch(arrow_cache)
    
    # ===== 第6阶段: 前端响应 =====
    stage6_y = 1
    
    ax.text(5, stage6_y+0.5, '阶段6: HTTP响应与下载', fontsize=11, fontweight='bold',
            bbox=dict(boxstyle='round', facecolor='#FFFFCC', alpha=0.7))
    
    rect_response = FancyBboxPatch((1, stage6_y-0.3), 8, 0.6, 
                                  boxstyle="round,pad=0.05", 
                                  edgecolor='#2ca02c', facecolor='#E6FFE6', linewidth=2)
    ax.add_patch(rect_response)
    ax.text(5, stage6_y, 'HTTP 200 + Content-Type (application/pdf|xlsx) + Content-Disposition (attachment)', 
            ha='center', va='center', fontsize=9, fontweight='bold')
    
    for x in [1.5, 3.5, 5.5]:
        arrow = FancyArrowPatch((x, stage5_y-0.35), (5, stage6_y+0.3),
                               arrowstyle='->', mutation_scale=12, 
                               color='#17becf', linewidth=1.5)
        ax.add_patch(arrow)
    
    # 函数说明
    ax.text(0.3, 0.1, '核心函数: generate_report() | export_pdf() | export_excel()', 
            fontsize=9, style='italic',
            bbox=dict(boxstyle='round', facecolor='#CCCCCC', alpha=0.5))
    
    plt.tight_layout()
    return fig


# ============================================================================
# 主函数: 生成所有图表
# ============================================================================
def main():
    """生成所有5张数据流图"""
    
    print("=" * 80)
    print("AIGI-Holmes 算法设计与数据流图生成")
    print("=" * 80)
    
    # 生成图表1
    print("\n[1/5] 生成整体系统架构图...")
    fig1 = draw_overall_architecture()
    fig1.savefig('01_整体系统架构与数据流.png', dpi=300, bbox_inches='tight')
    plt.close(fig1)
    print("✓ 已保存: 01_整体系统架构与数据流.png")
    
    # 生成图表2
    print("[2/5] 生成单图检测算法流程图...")
    fig2 = draw_single_image_detection()
    fig2.savefig('02_单图检测算法数据流.png', dpi=300, bbox_inches='tight')
    plt.close(fig2)
    print("✓ 已保存: 02_单图检测算法数据流.png")
    
    # 生成图表3
    print("[3/5] 生成CLIP多模态分析流程图...")
    fig3 = draw_clip_multimodal_flow()
    fig3.savefig('03_CLIP多模态分析数据流.png', dpi=300, bbox_inches='tight')
    plt.close(fig3)
    print("✓ 已保存: 03_CLIP多模态分析数据流.png")
    
    # 生成图表4
    print("[4/5] 生成URL批量检测流程图...")
    fig4 = draw_url_batch_detection_flow()
    fig4.savefig('04_URL批量检测与实时进度推送.png', dpi=300, bbox_inches='tight')
    plt.close(fig4)
    print("✓ 已保存: 04_URL批量检测与实时进度推送.png")
    
    # 生成图表5
    print("[5/5] 生成报告生成工作流图...")
    fig5 = draw_report_generation_workflow()
    fig5.savefig('05_检测报告生成与多格式导出.png', dpi=300, bbox_inches='tight')
    plt.close(fig5)
    print("✓ 已保存: 05_检测报告生成与多格式导出.png")
    
    print("\n" + "=" * 80)
    print("所有数据流图已生成完毕！")
    print("=" * 80)
    print("\n生成的文件列表:")
    print("  1. 01_整体系统架构与数据流.png          - 系统架构与核心数据流")
    print("  2. 02_单图检测算法数据流.png            - ResNet50+Grad-CAM检测流程")
    print("  3. 03_CLIP多模态分析数据流.png          - 内容分类与图文一致性检测")
    print("  4. 04_URL批量检测与实时进度推送.png     - 批量检测与WebSocket实时推送")
    print("  5. 05_检测报告生成与多格式导出.png      - 报告生成与PDF/Excel导出")
    print("\n所有图表均采用单调递进的颜色方案，易于理解数据流向。")
    print("=" * 80)


if __name__ == "__main__":
    main()
