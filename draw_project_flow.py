import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.lines as mlines

fig, ax = plt.subplots(figsize=(22, 28))
ax.set_xlim(0, 22)
ax.set_ylim(0, 28)
ax.axis('off')
fig.patch.set_facecolor('white')

# ========== 工具函数 ==========
def box(ax, x, y, w, h, text, fc='#dae8fc', ec='#6c8ebf', fs=10, bold=False, alpha=1.0):
    r = mpatches.FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.18",
                                  facecolor=fc, edgecolor=ec, linewidth=2, alpha=alpha)
    ax.add_patch(r)
    wt = 'bold' if bold else 'normal'
    ax.text(x + w/2, y + h/2, text, ha='center', va='center', fontsize=fs,
            fontweight=wt, fontfamily='SimHei', linespacing=1.4)

def arrow(ax, x1, y1, x2, y2, color='#333', lw=2, style='->', ls='-'):
    ax.annotate('', xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle=style, color=color, lw=lw, linestyle=ls))

def dashed_rect(ax, x, y, w, h, ec='#999', label=''):
    r = mpatches.FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.25",
                                  facecolor='#fafafa', edgecolor=ec, linewidth=2, linestyle='--', alpha=0.5)
    ax.add_patch(r)
    if label:
        ax.text(x + 0.3, y + h - 0.35, label, fontsize=11, fontweight='bold',
                color='#666', fontfamily='SimHei')

def section_title(ax, x, y, text, fs=13):
    ax.text(x, y, text, fontsize=fs, fontweight='bold', fontfamily='SimHei',
            color='#333', bbox=dict(boxstyle='round,pad=0.3', facecolor='#e8e8e8', edgecolor='#999'))

# ==================== 大标题 ====================
ax.text(11, 27.4, 'AIGI-Holmes 项目完整数据流图', ha='center', fontsize=22, fontweight='bold', fontfamily='SimHei')
ax.text(11, 26.9, 'AI 生成图像识别系统 — 全模块架构与数据流', ha='center', fontsize=12, color='gray', fontfamily='SimHei')

# ==================== 第一层：数据集 ====================
section_title(ax, 0.5, 26.2, 'Layer 1: 数据集')
box(ax, 7, 25.3, 8, 0.9, 'Dataset  data/train  data/val\nFAKE (AI生成图) / REAL (真实照片)\nJPG/PNG 图像文件', '#dae8fc', '#6c8ebf', 11, True)

# ==================== 第二层   数据增强 ====================
section_title(ax, 0.5, 24.5, 'Layer 2: 数据增强与预处理')

# 系统A增强
box(ax, 1, 23.2, 5.5, 1.0,
    '系统A: finetune.py 增强\nResize(224) + RandomFlip\nRandomRotation(15) + ColorJitter\nToTensor + Normalize', '#fff2cc', '#d6b656', 9)

# 系统B增强
box(ax, 8, 23.2, 5.5, 1.0,
    '系统B: Baselines 增强\nResize(cropSize) + RandomFlip\nGaussianBlur(prob) + JPEG(prob)\nToTensor + Normalize', '#fff2cc', '#d6b656', 9)

# 系统C
box(ax, 15.5, 23.2, 5.5, 1.0,
    '系统C: swift/llm\nLLM SFT 数据预处理\nTokenizer + Template\n多模态图文对齐', '#e1d5e7', '#9673a6', 9)

arrow(ax, 11, 25.3, 3.75, 24.2, '#6c8ebf')
arrow(ax, 11, 25.3, 10.75, 24.2, '#6c8ebf')
arrow(ax, 11, 25.3, 18.25, 24.2, '#6c8ebf')

# ==================== 第三层：DataLoader ====================
box(ax, 1.5, 21.8, 4.5, 0.6, 'DataLoader (batch=8)', '#f5f5f5', '#999', 10)
box(ax, 8.5, 21.8, 4.5, 0.6, 'DataLoader (batch=opt.batch)', '#f5f5f5', '#999', 10)
box(ax, 16, 21.8, 4.5, 0.6, 'DataLoader (LLM batch)', '#f5f5f5', '#999', 10)

arrow(ax, 3.75, 23.2, 3.75, 22.4, '#d6b656')
arrow(ax, 10.75, 23.2, 10.75, 22.4, '#d6b656')
arrow(ax, 18.25, 23.2, 18.25, 22.4, '#d6b656')

# ==================== 第四层：模型选择（核心） ====================
section_title(ax, 0.5, 21.0, 'Layer 3: 模型架构 (核心)')

# ---- 系统A: finetune.py ----
dashed_rect(ax, 0.5, 17.5, 5.5, 3.2, '#6c8ebf', '系统A: finetune.py')
box(ax, 1, 19.5, 4.5, 0.8, 'ResNet50 (pretrained)\nBackbone 全部冻结\nrequires_grad=False', '#dae8fc', '#6c8ebf', 9)
box(ax, 1.5, 18.3, 3.5, 0.7, 'FC (可训练)\n2048 -> 2\n唯一训练参数', '#d5e8d4', '#82b366', 9, True)
arrow(ax, 3.25, 19.5, 3.25, 19.0, '#6c8ebf')
arrow(ax, 3.75, 21.8, 3.25, 20.3, '#999')

# ---- 系统B: Baselines_AIGI ----
dashed_rect(ax, 6.5, 13.0, 8.5, 7.7, '#d6b656', '系统B: Baselines_AIGI (Trainer)')

# Trainer 调度
box(ax, 7.5, 19.6, 6.5, 0.8, 'Trainer.__init__(opt)\nnetworks/trainer.py\n根据 trainmode 分发模型', '#fff2cc', '#d6b656', 10, True)
arrow(ax, 10.75, 21.8, 10.75, 20.4, '#999')

# trainmode 菱形
diamond = mpatches.FancyBboxPatch((9.8, 18.6), 1.9, 0.6, boxstyle="round,pad=0.1",
                                    facecolor='#fff2cc', edgecolor='#d6b656', linewidth=2)
ax.add_patch(diamond)
ax.text(10.75, 18.9, 'trainmode?', ha='center', va='center', fontsize=10, fontweight='bold', fontfamily='SimHei')
arrow(ax, 10.75, 19.6, 10.75, 19.2, '#d6b656')

# NPR 分支
box(ax, 6.8, 16.2, 3.5, 2.0,
    'trainmode = NPR\n--------\nNPR 预处理 (核心)\nx - interpolate(x,0.5) * 2/3\n提取像素级上采样指纹\n+\nResNet50 (layer1+layer2)\nconv1-bn1-relu-maxpool\nlayer1-layer2-avgpool-fc',
    '#f8cecc', '#b85450', 8)

# RINE 分支
box(ax, 10.8, 16.2, 3.8, 2.0,
    'trainmode = rine\n--------\nCLIP ViT-L/14 (冻结)\nHook 所有 ln_2 层输出\nproj1: 1024->128 投影\nalpha: 可学习层权重\nsoftmax加权聚合\nproj2 + head 分类\n输出: (logit, embedding)',
    '#d5e8d4', '#82b366', 8)

# CNNDetection 分支
box(ax, 7, 13.5, 3.3, 2.1,
    'trainmode=CNNDetection\n--------\nresnet50_new\n直接用 RGB 图像\n标准 ResNet50 全层\n全部可训练',
    '#ffe6cc', '#d79b00', 8)

# LoRA 分支
box(ax, 11, 13.5, 3.5, 2.1,
    'trainmode = lora\n--------\nCLIPModel + LoRA\nswift/tuners/lora.py\n注入 lora_A / lora_B\n只训练 lora 参数 + fc\n大部分 CLIP 冻结',
    '#e1d5e7', '#9673a6', 8)

# 菱形到分支箭头
arrow(ax, 9.8, 18.9, 8.5, 18.2, '#b85450')
arrow(ax, 11.7, 18.6, 12.7, 18.2, '#82b366')
arrow(ax, 9.8, 18.7, 8.5, 15.6, '#d79b00')
arrow(ax, 11.7, 18.7, 12.7, 15.6, '#9673a6')

# 分支标签
ax.text(8.3, 18.5, 'NPR', fontsize=8, fontweight='bold', color='#b85450', fontfamily='SimHei')
ax.text(12.8, 18.5, 'rine', fontsize=8, fontweight='bold', color='#82b366', fontfamily='SimHei')
ax.text(7.8, 15.9, 'CNNDet', fontsize=8, fontweight='bold', color='#d79b00', fontfamily='SimHei')
ax.text(13.2, 15.9, 'lora', fontsize=8, fontweight='bold', color='#9673a6', fontfamily='SimHei')

# ---- 系统C: swift LLM ----
dashed_rect(ax, 15.5, 17.5, 5.5, 3.2, '#9673a6', '系统C: swift/ LLM微调')
box(ax, 16, 19.3, 4.5, 1.0,
    'swift/llm/sft.py 入口\nswift/llm/tuner.py 选微调方式\nLoRA / Adapter / Prompt\nReFT / ResTuning', '#e1d5e7', '#9673a6', 9)
box(ax, 16, 18.0, 4.5, 0.8,
    'swift/trainers/trainers.py\nSeq2SeqTrainer\ncompute_loss + prediction_step', '#e1d5e7', '#9673a6', 9)
arrow(ax, 18.25, 19.3, 18.25, 18.8, '#9673a6')
arrow(ax, 18.25, 21.8, 18.25, 20.3, '#999')

# ==================== 第五层：损失函数 ====================
section_title(ax, 0.5, 12.2, 'Layer 4: 损失函数')

box(ax, 1, 11.2, 4.5, 0.7, '系统A: CrossEntropyLoss\noutput(2类) vs label', '#dae8fc', '#6c8ebf', 10)
box(ax, 7, 11.2, 7.5, 0.7, '系统B: BCEWithLogitsLoss\noutput.squeeze(1) vs label.float()', '#fff2cc', '#d6b656', 10)
box(ax, 16, 11.2, 4.5, 0.7, '系统C: LM CrossEntropy\nnext token prediction', '#e1d5e7', '#9673a6', 10)

arrow(ax, 3.25, 17.5, 3.25, 11.9, '#6c8ebf')
arrow(ax, 8.5, 13.5, 10.75, 11.9, '#d6b656')
arrow(ax, 12.7, 13.5, 10.75, 11.9, '#9673a6')
arrow(ax, 18.25, 18.0, 18.25, 11.9, '#9673a6')

# ==================== 第六层：优化器 ====================
section_title(ax, 0.5, 10.3, 'Layer 5: 优化器')

box(ax, 1, 9.3, 4.5, 0.7, '系统A: Adam\nonly model.fc.parameters()\nlr=0.001', '#dae8fc', '#6c8ebf', 9)
box(ax, 7, 9.3, 7.5, 0.7, '系统B: Adam / SGD (opt.optim)\nfilter(requires_grad) + adjust_lr * 0.9 衰减', '#fff2cc', '#d6b656', 9)
box(ax, 16, 9.3, 4.5, 0.7, '系统C: AdamW\n+ LR Scheduler\n+ Gradient Accumulation', '#e1d5e7', '#9673a6', 9)

arrow(ax, 3.25, 11.2, 3.25, 10.0, '#6c8ebf')
arrow(ax, 10.75, 11.2, 10.75, 10.0, '#d6b656')
arrow(ax, 18.25, 11.2, 18.25, 10.0, '#9673a6')

# ==================== 第七层：训练循环 ====================
section_title(ax, 0.5, 8.5, 'Layer 6: 训练循环')

box(ax, 1, 7.0, 4.5, 1.2,
    '系统A 训练循环\nfor epoch in range(5):\n  for images,labels in loader:\n    output = model(images)\n    loss = criterion(output, labels)\n    loss.backward()\n    optimizer.step()',
    '#dae8fc', '#6c8ebf', 8)

box(ax, 7, 7.0, 7.5, 1.2,
    '系统B 训练循环 (trainer.optimize_parameters)\nself.forward()  # output = model(input)\nif rine: loss = loss_fn(output[0].squeeze(1), label)\nelse:    loss = loss_fn(output.squeeze(1), label)\noptimizer.zero_grad()\nloss.backward() + optimizer.step()',
    '#fff2cc', '#d6b656', 8)

box(ax, 16, 7.0, 4.5, 1.2,
    '系统C 训练循环\nSeq2SeqTrainer.train()\ncompute_loss(model, inputs)\nloss.backward()\noptimizer.step()\nscheduler.step()',
    '#e1d5e7', '#9673a6', 8)

arrow(ax, 3.25, 9.3, 3.25, 8.2, '#6c8ebf')
arrow(ax, 10.75, 9.3, 10.75, 8.2, '#d6b656')
arrow(ax, 18.25, 9.3, 18.25, 8.2, '#9673a6')

# ==================== 第八层：输出 ====================
section_title(ax, 0.5, 6.2, 'Layer 7: 输出与保存')

box(ax, 1, 5.0, 4.5, 0.8,
    '系统A 输出\nfinetuned_fake_real_resnet50.pth\nsoftmax -> FAKE/REAL + 置信度',
    '#dae8fc', '#6c8ebf', 9)

box(ax, 7, 5.0, 7.5, 0.8,
    '系统B 输出\ncheckpoints/best_model.pth\nAcc / AUC / F1 评估指标',
    '#fff2cc', '#d6b656', 9)

box(ax, 16, 5.0, 4.5, 0.8,
    '系统C 输出\nLoRA adapter weights\nswift/llm/infer.py 推理\nswift/llm/deploy.py 部署',
    '#e1d5e7', '#9673a6', 9)

arrow(ax, 3.25, 7.0, 3.25, 5.8, '#6c8ebf')
arrow(ax, 10.75, 7.0, 10.75, 5.8, '#d6b656')
arrow(ax, 18.25, 7.0, 18.25, 5.8, '#9673a6')

# ==================== 最终输出 ====================
box(ax, 5, 3.5, 12, 0.9,
    '最终目标: 输入一张照片 -> 判断 FAKE (AI生成) / REAL (真实照片)\n系统A: 快速原型验证  |  系统B: 多方法对比实验 (NPR/CNNDet/RINE/LoRA)  |  系统C: LLM多模态识别',
    '#d5e8d4', '#82b366', 11, True)

arrow(ax, 3.25, 5.0, 9, 4.4, '#6c8ebf')
arrow(ax, 10.75, 5.0, 11, 4.4, '#d6b656')
arrow(ax, 18.25, 5.0, 13, 4.4, '#9673a6')

# ==================== 辅助工具层 ====================
section_title(ax, 0.5, 2.8, 'Layer 8: 辅助工具')

box(ax, 1, 1.5, 4.5, 0.8,
    'swift/aigc/diffusers/\nAIGC图像生成\nSD / SDXL / ControlNet\n生成 FAKE 训练数据',
    '#ffe6cc', '#d79b00', 9)

box(ax, 7, 1.5, 4.5, 0.8,
    'tools/merge_lora_weights\nLoRA权重合并到基模型\n部署时不需要额外加载',
    '#ffe6cc', '#d79b00', 9)

box(ax, 13, 1.5, 4.5, 0.8,
    'logits-processor-zoo/\nLLM 解码后处理\n控制生成输出格式',
    '#ffe6cc', '#d79b00', 9)

box(ax, 18.5, 1.5, 3, 0.8,
    'scripts/ examples/\n运行脚本\n示例代码',
    '#f5f5f5', '#999', 9)

# ==================== 图例 ====================
box(ax, 0.5, 0.1, 2.5, 0.6, '系统A\nfinetune.py', '#dae8fc', '#6c8ebf', 9, True)
box(ax, 3.5, 0.1, 2.5, 0.6, '系统B\nBaselines_AIGI', '#fff2cc', '#d6b656', 9, True)
box(ax, 6.5, 0.1, 2.5, 0.6, '系统C\nswift/LLM', '#e1d5e7', '#9673a6', 9, True)
box(ax, 9.5, 0.1, 2.5, 0.6, '核心输出\n识别结果', '#d5e8d4', '#82b366', 9, True)
box(ax, 12.5, 0.1, 2.5, 0.6, '辅助工具', '#ffe6cc', '#d79b00', 9, True)

ax.text(16, 0.4, '图例', fontsize=12, fontweight='bold', fontfamily='SimHei')

plt.tight_layout()
plt.savefig('Project_Full_Dataflow.png', dpi=150, bbox_inches='tight', facecolor='white')
plt.show()
print('已保存: Project_Full_Dataflow.png')