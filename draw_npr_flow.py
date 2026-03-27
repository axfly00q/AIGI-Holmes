import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

fig, ax = plt.subplots(figsize=(14, 10))
ax.set_xlim(0, 14)
ax.set_ylim(0, 10)
ax.axis('off')
fig.patch.set_facecolor('white')

def draw_box(ax, x, y, w, h, text, color='#dae8fc', edge='#6c8ebf', fs=10, bold=False):
    rect = mpatches.FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.15",
                                     facecolor=color, edgecolor=edge, linewidth=2)
    ax.add_patch(rect)
    weight = 'bold' if bold else 'normal'
    ax.text(x + w/2, y + h/2, text, ha='center', va='center', fontsize=fs,
            fontweight=weight, wrap=True, fontfamily='SimHei')

def draw_arrow(ax, x1, y1, x2, y2, color='#333333'):
    ax.annotate('', xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle='->', color=color, lw=2))

# 标题
ax.text(7, 9.6, 'NPR 预处理数据流 (Neighboring Pixel Residual)', ha='center', va='center',
        fontsize=16, fontweight='bold', fontfamily='SimHei')
ax.text(7, 9.2, 'swift/new_models/resnet.py  L242-247', ha='center', va='center',
        fontsize=10, color='gray', fontfamily='SimHei')

# 节点
draw_box(ax, 5.5, 8.2, 3, 0.7, '输入图像 x\n(B, 3, H, W)', '#dae8fc', '#6c8ebf', 11, True)
draw_box(ax, 5.2, 7.0, 3.6, 0.7, '① 奇偶裁剪\n保证 H, W 可被 2 整除', '#fff2cc', '#d6b656', 10)
draw_box(ax, 1.5, 5.3, 4, 0.9, '② 最近邻下采样 ×0.5\nF.interpolate(x, 0.5, nearest)\n→ (B, 3, H/2, W/2)', '#f8cecc', '#b85450', 9)
draw_box(ax, 1.5, 3.8, 4, 0.9, '③ 最近邻上采样 ×2\nF.interpolate(x_half, 2.0, nearest)\n→ (B, 3, H, W)  高频已丢失', '#f8cecc', '#b85450', 9)
draw_box(ax, 8.5, 5.3, 3.5, 0.9, '原始 x 保留\n(B, 3, H, W)\n含完整高频信息', '#dae8fc', '#6c8ebf', 10)
draw_box(ax, 4, 2.3, 6, 0.8, '④ 求残差  NPR = (x − x_reconstructed) × 2/3\n(B, 3, H, W)', '#d5e8d4', '#82b366', 11, True)
draw_box(ax, 4.2, 1.0, 5.6, 0.8, '⑤ 送入 ResNet CNN\nconv1→bn1→relu→maxpool→layer1→layer2→avgpool→fc', '#e1d5e7', '#9673a6', 9)
draw_box(ax, 5, -0.1, 4, 0.7, '输出 logit → BCELoss → FAKE / REAL', '#dae8fc', '#6c8ebf', 11, True)

# 箭头
draw_arrow(ax, 7, 8.2, 7, 7.7, '#6c8ebf')
draw_arrow(ax, 5.5, 7.0, 3.5, 6.2, '#b85450')
draw_arrow(ax, 8.5, 7.0, 10, 6.2, '#6c8ebf')
draw_arrow(ax, 3.5, 5.3, 3.5, 4.7, '#b85450')
draw_arrow(ax, 3.5, 3.8, 6, 3.1, '#b85450')
draw_arrow(ax, 10, 5.3, 8.5, 3.1, '#6c8ebf')
draw_arrow(ax, 7, 2.3, 7, 1.8, '#82b366')
draw_arrow(ax, 7, 1.0, 7, 0.6, '#9673a6')

# 减号
ax.text(6.5, 3.5, '−', ha='center', va='center', fontsize=28, fontweight='bold', color='#333')

# 注释框
note_rect = mpatches.FancyBboxPatch((10.5, 1.5), 3.2, 1.8, boxstyle="round,pad=0.15",
                                      facecolor='#ffe6cc', edgecolor='#d79b00', linewidth=1.5)
ax.add_patch(note_rect)
ax.text(12.1, 2.4, '核心思想\n─────────────\n真实照片: NPR ≈ 随机噪声\nAI生成图: NPR ≈ 规律残差\n\nNPR 提取 AI 图像独有的\n像素级上采样指纹',
        ha='center', va='center', fontsize=8.5, fontfamily='SimHei')

plt.tight_layout()
plt.savefig('NPR_dataflow.png', dpi=200, bbox_inches='tight', facecolor='white')
plt.show()
print('已保存: NPR_dataflow.png')