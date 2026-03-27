import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

fig, ax = plt.subplots(figsize=(16, 12))
ax.set_xlim(0, 16)
ax.set_ylim(0, 12)
ax.axis('off')
fig.patch.set_facecolor('white')

def draw_box(ax, x, y, w, h, text, color='#dae8fc', edge='#6c8ebf', fs=10, bold=False):
    rect = mpatches.FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.15",
                                     facecolor=color, edgecolor=edge, linewidth=2)
    ax.add_patch(rect)
    weight = 'bold' if bold else 'normal'
    ax.text(x + w/2, y + h/2, text, ha='center', va='center', fontsize=fs,
            fontweight=weight, fontfamily='SimHei')

def draw_arrow(ax, x1, y1, x2, y2, color='#333'):
    ax.annotate('', xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle='->', color=color, lw=2))

# 标题
ax.text(8, 11.6, 'Trainer 统一调度器数据流', ha='center', fontsize=16, fontweight='bold', fontfamily='SimHei')
ax.text(8, 11.2, 'Baselines_AIGI/networks/trainer.py + options/', ha='center', fontsize=10, color='gray')

# ① 参数解析
draw_box(ax, 4, 10.2, 8, 0.7, '① 参数解析 (Options)\nbase_options.py + train_options.py\n--trainmode  --modelname  --lr  --optim  --dataroot', '#dae8fc', '#6c8ebf', 10)

# ② 数据加载
draw_box(ax, 4, 8.8, 8, 0.7, '② 数据加载 & 增强\nDataset→DataLoader | Resize + RandomFlip + GaussianBlur + JPEG + Normalize', '#d5e8d4', '#82b366', 10)
draw_arrow(ax, 8, 10.2, 8, 9.5, '#6c8ebf')

# ③ Trainer init
draw_box(ax, 5, 7.5, 6, 0.6, '③ Trainer.__init__()\n根据 trainmode 选择模型 & 冻结策略', '#fff2cc', '#d6b656', 11, True)
draw_arrow(ax, 8, 8.8, 8, 8.1, '#82b366')

# 菱形
diamond = mpatches.FancyBboxPatch((7.2, 6.5), 1.6, 0.6, boxstyle="round,pad=0.1",
                                    facecolor='#fff2cc', edgecolor='#d6b656', linewidth=2)
ax.add_patch(diamond)
ax.text(8, 6.8, 'trainmode?', ha='center', va='center', fontsize=10, fontweight='bold', fontfamily='SimHei')
draw_arrow(ax, 8, 7.5, 8, 7.1, '#d6b656')

# 四个分支
draw_box(ax, 0.3, 4.8, 3.2, 1.2,
         'trainmode = NPR\n──────────\n模型: resnet50(use_low_level=npr)\n预处理: NPR残差提取\nBackbone: conv1→layer1→layer2→fc\n全部可训练',
         '#f8cecc', '#b85450', 8)
draw_box(ax, 4, 4.8, 3.2, 1.2,
         'trainmode = CNNDetection\n──────────\n模型: resnet50_new\n预处理: 无(直接RGB)\nBackbone: 标准ResNet50全层\n全部可训练',
         '#f8cecc', '#b85450', 8)
draw_box(ax, 8, 4.8, 3.5, 1.2,
         'trainmode = rine\n──────────\n模型: Model(CLIP+Hook)\nBackbone: CLIP ViT(冻结)\n可训练: alpha+proj1+proj2+head\n核心: 多层Hook+自适应加权',
         '#d5e8d4', '#82b366', 8)
draw_box(ax, 12, 4.8, 3.5, 1.2,
         'trainmode = lora\n──────────\n模型: CLIPModel+LoRA注入\nBackbone: CLIP(大部分冻结)\n可训练: lora_A/lora_B + FC\n来源: swift/tuners/lora.py',
         '#e1d5e7', '#9673a6', 8)

# 菱形到四分支
draw_arrow(ax, 7.2, 6.8, 1.9, 6.0, '#b85450')
draw_arrow(ax, 7.5, 6.5, 5.6, 6.0, '#b85450')
draw_arrow(ax, 8.5, 6.5, 9.7, 6.0, '#82b366')
draw_arrow(ax, 8.8, 6.8, 13.7, 6.0, '#9673a6')

# 分支标签
ax.text(3.5, 6.6, 'NPR', fontsize=9, fontweight='bold', color='#b85450', fontfamily='SimHei')
ax.text(6.2, 6.2, 'CNNDet', fontsize=9, fontweight='bold', color='#b85450', fontfamily='SimHei')
ax.text(9.2, 6.2, 'rine', fontsize=9, fontweight='bold', color='#82b366', fontfamily='SimHei')
ax.text(12, 6.6, 'lora', fontsize=9, fontweight='bold', color='#9673a6', fontfamily='SimHei')

# ④ 统一训练循环
draw_box(ax, 3, 2.8, 10, 1.2,
         '④ 统一训练循环 (train_epoch)\nfor batch in DataLoader:\n    output = model(images)\n    loss = BCEWithLogitsLoss(output, label)\n    optimizer.zero_grad()  →  loss.backward()  →  optimizer.step()',
         '#fff2cc', '#d6b656', 10)

for bx in [1.9, 5.6, 9.7, 13.7]:
    draw_arrow(ax, bx, 4.8, 8, 4.0, '#666')

# ⑤ Optimizer
draw_box(ax, 3.5, 1.3, 9, 0.7,
         '⑤ Optimizer: Adam / SGD (filter requires_grad)\n+ adjust_learning_rate 衰减',
         '#e1d5e7', '#9673a6', 10)
draw_arrow(ax, 8, 2.8, 8, 2.0, '#d6b656')

# ⑥ 输出
draw_box(ax, 4.5, 0.1, 7, 0.6,
         '⑥ 输出: save checkpoint (best_model.pth) | metrics: Acc / AUC / F1',
         '#dae8fc', '#6c8ebf', 11, True)
draw_arrow(ax, 8, 1.3, 8, 0.7, '#9673a6')

plt.tight_layout()
plt.savefig('Trainer_dataflow.png', dpi=200, bbox_inches='tight', facecolor='white')
plt.show()
print('已保存: Trainer_dataflow.png')
