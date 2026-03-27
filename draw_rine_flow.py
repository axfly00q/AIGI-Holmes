import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

fig, ax = plt.subplots(figsize=(14, 14))
ax.set_xlim(0, 14)
ax.set_ylim(0, 14)
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
ax.text(7, 13.6, 'RINE 多层聚合模型数据流', ha='center', fontsize=16, fontweight='bold', fontfamily='SimHei')
ax.text(7, 13.2, 'Baselines_AIGI/models.py — class Model', ha='center', fontsize=10, color='gray')

# 输入
draw_box(ax, 5, 12.3, 4, 0.6, '输入图像 x  (B, 3, 224, 224)', '#dae8fc', '#6c8ebf', 11, True)

# CLIP 大框
clip_rect = mpatches.FancyBboxPatch((1, 8.5), 12, 3.3, boxstyle="round,pad=0.2",
                                      facecolor='#f5f5f5', edgecolor='#999999', linewidth=2, linestyle='--')
ax.add_patch(clip_rect)
ax.text(7, 11.5, 'CLIP ViT-L/14  (冻结 requires_grad=False)  with torch.no_grad()',
        ha='center', fontsize=11, color='#666', fontfamily='SimHei', fontweight='bold')

# Transformer Blocks
draw_box(ax, 1.5, 10.0, 3, 0.8, 'Transformer Block 1\nln_1→Attn→ln_2→MLP', '#fff2cc', '#d6b656', 9)
draw_box(ax, 5.5, 10.0, 3, 0.8, 'Transformer Block 2\nln_1→Attn→ln_2→MLP', '#fff2cc', '#d6b656', 9)
ax.text(9.3, 10.4, '· · ·', ha='center', fontsize=20, fontweight='bold', color='#999')
draw_box(ax, 9.8, 10.0, 3, 0.8, 'Transformer Block N\nln_1→Attn→ln_2→MLP', '#fff2cc', '#d6b656', 9)

# Hooks
draw_box(ax, 1.8, 8.8, 2.4, 0.7, 'Hook ①\nln_2 output\nh1: (B,seq,1024)', '#f8cecc', '#b85450', 8)
draw_box(ax, 5.8, 8.8, 2.4, 0.7, 'Hook ②\nln_2 output\nh2: (B,seq,1024)', '#f8cecc', '#b85450', 8)
draw_box(ax, 10.1, 8.8, 2.4, 0.7, 'Hook N\nln_2 output\nhN: (B,seq,1024)', '#f8cecc', '#b85450', 8)

# Hook 虚线箭头
for bx in [3.0, 7.0, 11.3]:
    ax.annotate('', xy=(bx, 9.5), xytext=(bx, 10.0),
                arrowprops=dict(arrowstyle='->', color='#b85450', lw=1.5, linestyle='--'))

draw_arrow(ax, 7, 12.3, 7, 11.8, '#6c8ebf')

# Stack
draw_box(ax, 3.5, 7.3, 7, 0.8, 'torch.stack([h1...hN], dim=2)\ng: (B, seq, N, 1024) → 取[0,:,:,:] → (seq, N, 1024)', '#d5e8d4', '#82b366', 10)

for sx in [3.0, 7.0, 11.3]:
    draw_arrow(ax, sx, 8.8, 7, 8.1, '#b85450')

# proj1
draw_box(ax, 3, 5.9, 8, 0.8, 'proj1 (特征投影)\nDropout→[Linear(1024→128)→ReLU→Dropout] ×2\n输出: g\'  (seq, N, 128)', '#e1d5e7', '#9673a6', 10)
draw_arrow(ax, 7, 7.3, 7, 6.7, '#82b366')

# alpha
draw_box(ax, 2.5, 4.3, 9, 1.0, '⭐ Alpha 注意力加权聚合 (核心创新)\nalpha: nn.Parameter(1, N, 128) — 可学习参数\nw = softmax(alpha, dim=1)    z = sum(w × g\', dim=1)\n输出: z (seq, 128) — 多层融合后的特征', '#fff2cc', '#d6b656', 10, True)
draw_arrow(ax, 7, 5.9, 7, 5.3, '#9673a6')

# proj2
draw_box(ax, 3, 3.0, 8, 0.7, 'proj2 (二次投影)\nDropout→[Linear(128→128)→ReLU→Dropout] ×2\n输出: z\'  (seq, 128)', '#e1d5e7', '#9673a6', 10)
draw_arrow(ax, 7, 4.3, 7, 3.7, '#d6b656')

# head
draw_box(ax, 3.5, 1.5, 7, 0.9, 'head (分类头)\nLinear(128→128)→ReLU→DO→Linear(128→128)→ReLU→DO→Linear(128→1)\n输出: p (seq, 1) — FAKE/REAL logit', '#f8cecc', '#b85450', 10)
draw_arrow(ax, 7, 3.0, 7, 2.4, '#9673a6')

# 输出
draw_box(ax, 4, 0.2, 6, 0.7, 'return (p, z)\np→BCEWithLogitsLoss→反向传播\nz→特征嵌入 (可用于t-SNE可视化)', '#dae8fc', '#6c8ebf', 10, True)
draw_arrow(ax, 7, 1.5, 7, 0.9, '#b85450')

plt.tight_layout()
plt.savefig('RINE_dataflow.png', dpi=200, bbox_inches='tight', facecolor='white')
plt.show()
print('已保存: RINE_dataflow.png')