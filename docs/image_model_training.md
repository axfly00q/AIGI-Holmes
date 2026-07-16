# 图像检测模型训练与评估说明

## 为什么要改

旧 `finetune.py` 使用 Windows 专用路径，默认目录与仓库实际数据目录不一致；训练/验证集各类只有少量样本，没有独立测试集评估、随机种子、校准、混淆矩阵和模型来源记录。旧文档中的“95%”因此无法由仓库内实验复现。

新流水线保留 ResNet50 和现有 Grad-CAM，不更换产品架构，只补齐课程项目所需的实验闭环。

## 数据划分

- 数据源：CIFAKE 官方数据的 Hugging Face 镜像 `dragonintelligence/CIFAKE-image-dataset`。
- 官方训练集：100,000 张，按固定随机种子 42 划分为 90,000 张训练和 10,000 张验证。
- 官方测试集：20,000 张，只做最终评估，绝不参与训练、温度校准或阈值选择。
- 类别顺序：`FAKE=0`、`REAL=1`，与生产模型保持一致。

## 训练步骤

1. 使用 ImageNet 预训练的 ResNet50，先冻结骨干网络，只训练二分类头。
2. 可选解冻 `layer4` 做低学习率微调。
3. 每轮记录训练损失/准确率和验证集 Accuracy、Macro-F1、分类别指标、ROC-AUC、ECE、混淆矩阵与推理耗时。
4. 以验证集 Macro-F1 保存最佳候选权重。
5. 在验证集上选择温度缩放参数，并按 90% 条件精度目标选择三态灰区阈值。
6. 在未参与任何选择的官方测试集上报告最终结果。
7. 使用 `--activate` 时，先将当前权重复制到 `models/archive/`，再激活候选权重。

## 三态规则

最终结论只使用温度校准后的 ResNet50 `FAKE` 概率：

- 风险不高于低阈值：较可能为真实照片；
- 风险不低于高阈值：较可能由 AI 生成；
- 两个阈值之间：证据不足，暂无法判断。

印章、频域、边缘、人脸、Logo、EXIF 和图文一致性都属于辅助信号。它们可帮助人工核查，但不会参与或覆盖三态结论。

## 运行命令

```bash
pip install -r requirements-dev.txt

# 完整评估当前权重
HF_HOME=.cache/huggingface venv/bin/python scripts/image_model_pipeline.py evaluate

# 完整训练、校准、测试并激活；激活前自动备份旧权重
HF_HOME=.cache/huggingface venv/bin/python scripts/image_model_pipeline.py train --activate
```

输出文件位于 `resources/image_detector/`：

- `metadata.yaml`：权重哈希、温度、阈值、数据划分与测试集指标；
- `evaluation_baseline.yaml`：改造前旧权重的测试结果；
- `evaluation_current.yaml`：当前激活权重的测试结果；
- `training_history.yaml`：每轮训练与验证结果；
- `model_card.md`：对外展示的模型说明和使用边界。

本轮实际执行按用户要求以架构改造为主：完成 90,000 张训练和 10,000 张验证后，最终测试缩减为 1,000 张类别均衡样本。完整 20,000 张测试能力仍保留在脚本中，但当前模型卡只报告抽样结果。

## 课程验收建议

课程标准采用 Accuracy 和 Macro-F1 为主指标，同时必须展示混淆矩阵、FAKE/REAL 各自 Precision/Recall、ROC-AUC 和 ECE。项目目标线可记录为 Accuracy ≥ 90%、Macro-F1 ≥ 90%，但本次功能交付不会为了达到目标线而隐藏或修改真实实验结果。

CIFAKE 图像只有 32×32。即使达到课程目标，也只能说明模型适配该数据集，不能宣称在真实新闻图片、未知生成器或平台压缩图片上具有同等准确率。
