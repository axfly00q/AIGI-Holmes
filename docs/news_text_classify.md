# 新闻文本分类模块运行说明

本文档只覆盖第二轮“正式模型 + 系统验收”交付，不包含课程报告和 PPT。

## 1. 训练正式模型

默认流程优先使用 NLPCC2017，若 8 类不完整或 macro F1 未达到 0.80，则自动尝试 THUCNews；如果二者都无法单独覆盖固定 8 类，则自动使用 hybrid 方案：NLPCC2017 提供已覆盖类别，HuggingFace 上的 THUCNews/cnews 镜像只补齐缺失类别。

```bash
venv/bin/python scripts/train_news_text_classifier.py \
  --source auto \
  --max-per-class 2500 \
  --min-per-class 50 \
  --epochs 8 \
  --target-macro-f1 0.80
```

如果本机代理端口不是常见的 `7890`，不要写死端口，按实际 HTTP 代理端口显式传入：

```bash
venv/bin/python scripts/train_news_text_classifier.py \
  --source auto \
  --proxy http://127.0.0.1:实际端口 \
  --max-per-class 2500 \
  --min-per-class 50 \
  --epochs 8 \
  --target-macro-f1 0.80
```

也可以把已经下载好的 THUCNews 或同结构 8 类数据放在：

```text
data/news_text_classify/
```

再执行：

```bash
venv/bin/python scripts/train_news_text_classifier.py --source local --max-per-class 2500
```

训练产物会写入：

```text
resources/news_text_classify/artifacts/
```

正式产物包括 `nb.joblib`、`lr.joblib`、`svm.joblib`、`textcnn.pt`、`metadata.yaml`、`metrics_full.yaml`。完整训练数据不提交项目，`data/` 目录保持忽略。

当前正式模型包状态：

- 数据来源：`NLPCC2017+HF-THUCNews-cnews`
- 训练样本：8 类各 2500 条，共 20000 条
- 默认模型：TextCNN
- 测试集 accuracy：0.8113
- 测试集 macro F1：0.8124
- 模型包体积：约 15.0MB

第三轮新增了数据清洗统计、输入策略对比、TextCNN 小范围调参和训练历史记录。若希望冲击更高指标，可使用 0.82 目标重新训练：

```bash
venv/bin/python scripts/train_news_text_classifier.py \
  --source hybrid \
  --max-per-class 2500 \
  --min-per-class 50 \
  --epochs 8 \
  --target-macro-f1 0.82 \
  --keep-candidates
```

本机最近一次 0.82 目标尝试得到的候选结果为 best macro F1 `0.8053`，低于当前正式 TextCNN `0.8124`，因此未替换正式模型包。答辩时可如实说明：当前混合数据源存在类别来源差异，简单清洗和轻量调参未带来稳定提升，后续提升方向是补充同源 8 类数据或引入更强文本模型。

如果需要显式跑 hybrid：

```bash
venv/bin/python scripts/train_news_text_classifier.py \
  --source hybrid \
  --proxy http://127.0.0.1:7890 \
  --max-per-class 2500 \
  --min-per-class 50 \
  --epochs 8 \
  --target-macro-f1 0.80
```

## 2. 启动系统

为避免占用原有 `7860` 服务，验收新版本使用 `7861`：

```bash
env AIGI_SKIP_BACKGROUND_PRELOAD=1 \
  venv/bin/python -m uvicorn backend.main:app \
  --host 127.0.0.1 \
  --port 7861
```

浏览器访问：

```text
http://127.0.0.1:7861/app
```

## 3. 验收路径

1. 打开“新闻文本分类”页签。
2. 查看模型指标表，确认 `training_summary.formal=true` 且最佳模型 macro F1 不低于 0.80。
3. 输入标题和正文，执行单条预测，检查类别、置信度、概率条、关键词。
4. 上传包含 `title,content` 两列的 CSV，检查批量分类结果和 CSV 下载。
5. 登录临时测试账号后再预测，进入“检测历史 - 新闻分类记录”，检查分页、类别筛选和标题搜索。
6. 在“新闻检测”页完成 URL 提取后点击“新闻文本分类”，确认不会拖慢原 URL 检测流程。
7. 回归检查图片上传、URL 图片检测、批量图片检测和原文本检测。

新增课程化实验面板对应接口：

```text
GET /api/text-classify/experiments
```

该接口返回模型对比、各类别 precision/recall/F1、混淆矩阵、类别分布、弱项类别、Top 混淆类别对、输入策略和训练历史。前端“新闻文本分类”页会自动读取并渲染为实验分析面板。

## 4. 当前数据源说明

NLPCC2017 的可公开数据中缺少“教育”类，不能直接满足本项目固定 8 类要求。THUCNews/cnews 镜像包含教育类，但不包含军事、汽车两类。因此正式训练默认采用 hybrid 方案：NLPCC2017 作为主数据源，THUCNews/cnews 仅补齐教育类。`metadata.yaml` 会记录该来源，避免把混合来源误写成单一数据集。
