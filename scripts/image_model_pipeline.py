#!/usr/bin/env python3
"""Reproducible CIFAKE training, calibration and evaluation for AIGI-Holmes.

The production architecture remains ResNet50 so the existing Grad-CAM target
layer and saved-state format remain compatible.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import shutil
import time
from datetime import datetime, timezone
from pathlib import Path

_ROOT_EARLY = Path(__file__).resolve().parents[1]
os.environ.setdefault("HF_HOME", str(_ROOT_EARLY / ".cache" / "huggingface"))
os.environ.setdefault("TORCH_HOME", str(_ROOT_EARLY / ".cache" / "torch"))

import numpy as np
import torch
import torch.nn as nn
import torchvision.models as models
import torchvision.transforms as transforms
import yaml
from datasets import load_dataset
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from torch.optim import AdamW
from torch.utils.data import DataLoader, Dataset


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_WEIGHTS = ROOT / "finetuned_fake_real_resnet50.pth"
ARTIFACT_DIR = ROOT / "resources" / "image_detector"
CLASSES = ["FAKE", "REAL"]
SEED = 42


def seed_everything(seed: int = SEED) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)


def select_device(requested: str) -> torch.device:
    if requested != "auto":
        return torch.device(requested)
    if torch.cuda.is_available():
        return torch.device("cuda")
    if torch.backends.mps.is_available():
        return torch.device("mps")
    return torch.device("cpu")


class CIFAKEDataset(Dataset):
    def __init__(self, split, transform):
        self.split = split
        self.transform = transform

    def __len__(self) -> int:
        return len(self.split)

    def __getitem__(self, index: int):
        item = self.split[index]
        return self.transform(item["image"].convert("RGB")), int(item["label"])


def transforms_for_training():
    normalize = transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
    train_tf = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.RandomHorizontalFlip(),
        transforms.RandomRotation(10),
        transforms.ColorJitter(brightness=0.15, contrast=0.15, saturation=0.1),
        transforms.ToTensor(),
        normalize,
    ])
    eval_tf = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        normalize,
    ])
    return train_tf, eval_tf


def load_cifake(validation_size: int = 10_000):
    dataset = load_dataset("dragonintelligence/CIFAKE-image-dataset")
    label_names = dataset["train"].features["label"].names
    if label_names != CLASSES or len(dataset["train"]) != 100_000 or len(dataset["test"]) != 20_000:
        raise RuntimeError(
            f"Unexpected CIFAKE schema/counts: labels={label_names}, "
            f"train={len(dataset['train'])}, test={len(dataset['test'])}"
        )
    split = dataset["train"].train_test_split(
        test_size=validation_size,
        seed=SEED,
        stratify_by_column="label",
    )
    return split["train"], split["test"], dataset["test"]


def make_model(*, pretrained: bool, weights_path: Path | None = None) -> nn.Module:
    weights = models.ResNet50_Weights.IMAGENET1K_V2 if pretrained else None
    model = models.resnet50(weights=weights)
    model.fc = nn.Linear(model.fc.in_features, len(CLASSES))
    if weights_path is not None:
        model.load_state_dict(torch.load(weights_path, map_location="cpu"))
    return model


def make_loader(split, transform, batch_size: int, shuffle: bool, workers: int, max_items: int | None = None):
    if max_items and max_items < len(split):
        # CIFAKE's stored rows are class-grouped, so a plain prefix would be
        # single-class.  Select an equal number from each class for smoke tests.
        labels = np.asarray(split["label"])
        per_class = max_items // len(CLASSES)
        indices = np.concatenate([
            np.flatnonzero(labels == class_index)[:per_class]
            for class_index in range(len(CLASSES))
        ])
        split = split.select(indices.tolist())
    return DataLoader(
        CIFAKEDataset(split, transform),
        batch_size=batch_size,
        shuffle=shuffle,
        num_workers=workers,
        pin_memory=torch.cuda.is_available(),
    )


def collect_logits(model, loader, device):
    model.eval()
    logits, labels = [], []
    started = time.perf_counter()
    with torch.inference_mode():
        for batch_index, (images, target) in enumerate(loader, 1):
            logits.append(model(images.to(device)).cpu())
            labels.append(target)
            if batch_index % 25 == 0 or batch_index == len(loader):
                print(f"evaluation_batch={batch_index}/{len(loader)}", flush=True)
    elapsed = time.perf_counter() - started
    return torch.cat(logits), torch.cat(labels), elapsed


def expected_calibration_error(y_true: np.ndarray, fake_prob: np.ndarray, bins: int = 15) -> float:
    predicted = (fake_prob < 0.5).astype(int)  # class 1 is REAL
    confidence = np.maximum(fake_prob, 1.0 - fake_prob)
    correct = predicted == y_true
    ece = 0.0
    for low, high in zip(np.linspace(0, 1, bins + 1)[:-1], np.linspace(0, 1, bins + 1)[1:]):
        mask = (confidence > low) & (confidence <= high)
        if mask.any():
            ece += mask.mean() * abs(correct[mask].mean() - confidence[mask].mean())
    return float(ece)


def metrics_from_logits(logits: torch.Tensor, labels: torch.Tensor, temperature: float, elapsed: float) -> dict:
    probs = torch.softmax(logits / temperature, dim=1).numpy()
    y_true = labels.numpy()
    y_pred = probs.argmax(axis=1)
    fake_prob = probs[:, 0]
    return {
        "samples": int(len(y_true)),
        "accuracy": round(float(accuracy_score(y_true, y_pred)), 6),
        "macro_f1": round(float(f1_score(y_true, y_pred, average="macro")), 6),
        "macro_precision": round(float(precision_score(y_true, y_pred, average="macro")), 6),
        "macro_recall": round(float(recall_score(y_true, y_pred, average="macro")), 6),
        "roc_auc_fake": round(float(roc_auc_score((y_true == 0).astype(int), fake_prob)), 6),
        "ece_15_bins": round(expected_calibration_error(y_true, fake_prob), 6),
        "confusion_matrix_rows_true_fake_real": confusion_matrix(y_true, y_pred, labels=[0, 1]).tolist(),
        "per_class": classification_report(y_true, y_pred, target_names=CLASSES, output_dict=True, zero_division=0),
        "inference_seconds": round(elapsed, 3),
        "inference_ms_per_image": round(elapsed / max(1, len(y_true)) * 1000, 3),
    }


def calibrate_temperature(logits: torch.Tensor, labels: torch.Tensor) -> float:
    loss = nn.CrossEntropyLoss()
    candidates = np.geomspace(0.25, 4.0, 120)
    values = [float(loss(logits / float(t), labels)) for t in candidates]
    return round(float(candidates[int(np.argmin(values))]), 6)


def calibrate_thresholds(logits: torch.Tensor, labels: torch.Tensor, temperature: float, target_precision: float = 0.90):
    fake_prob = torch.softmax(logits / temperature, dim=1)[:, 0].numpy() * 100
    y = labels.numpy()
    low = 35.0
    high = 65.0
    for threshold in np.arange(10.0, 50.1, 0.5):
        selected = fake_prob <= threshold
        if selected.sum() >= 100 and (y[selected] == 1).mean() >= target_precision:
            low = float(threshold)
    for threshold in np.arange(50.0, 90.1, 0.5):
        selected = fake_prob >= threshold
        if selected.sum() >= 100 and (y[selected] == 0).mean() >= target_precision:
            high = float(threshold)
            break
    if high <= low:
        low, high = 35.0, 65.0
    decisive = (fake_prob <= low) | (fake_prob >= high)
    decisive_pred = np.where(fake_prob >= high, 0, 1)
    return {
        "authentic_max": low,
        "ai_min": high,
        "target_conditional_precision": target_precision,
        "validation_decisive_coverage": round(float(decisive.mean()), 6),
        "validation_decisive_accuracy": round(float((decisive_pred[decisive] == y[decisive]).mean()), 6),
    }


def run_epoch(model, loader, device, optimizer=None):
    training = optimizer is not None
    model.train(training)
    if training:
        # Frozen BatchNorm layers must not silently update running statistics.
        for module in model.modules():
            if isinstance(module, nn.BatchNorm2d) and not any(
                parameter.requires_grad for parameter in module.parameters()
            ):
                module.eval()
    criterion = nn.CrossEntropyLoss(label_smoothing=0.05 if training else 0.0)
    total_loss = total_correct = total = 0
    context = torch.enable_grad() if training else torch.inference_mode()
    with context:
        for batch_index, (images, labels) in enumerate(loader, 1):
            images, labels = images.to(device), labels.to(device)
            if training:
                optimizer.zero_grad(set_to_none=True)
            output = model(images)
            loss = criterion(output, labels)
            if training:
                loss.backward()
                optimizer.step()
            total_loss += loss.item() * len(labels)
            total_correct += int((output.argmax(1) == labels).sum())
            total += len(labels)
            if training and (batch_index % 100 == 0 or batch_index == len(loader)):
                print(f"training_batch={batch_index}/{len(loader)}", flush=True)
    return {"loss": total_loss / total, "accuracy": total_correct / total}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_yaml(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")


def train(args) -> None:
    seed_everything()
    device = select_device(args.device)
    print(f"device={device}; loading official CIFAKE dataset", flush=True)
    train_split, val_split, test_split = load_cifake(args.validation_size)
    train_tf, eval_tf = transforms_for_training()
    train_loader = make_loader(train_split, train_tf, args.batch_size, True, args.workers, args.max_train)
    val_loader = make_loader(val_split, eval_tf, args.batch_size, False, args.workers, args.max_validation)

    model = make_model(pretrained=True).to(device)
    for param in model.parameters():
        param.requires_grad = False
    for param in model.fc.parameters():
        param.requires_grad = True

    history = []
    best_f1 = -1.0
    candidate = ARTIFACT_DIR / "resnet50_cifake_candidate.pth"
    optimizer = AdamW(model.fc.parameters(), lr=args.head_lr, weight_decay=1e-4)

    stages = [("head", args.head_epochs, optimizer)]
    for stage, epochs, stage_optimizer in stages:
        for epoch in range(1, epochs + 1):
            train_stats = run_epoch(model, train_loader, device, stage_optimizer)
            val_logits, val_labels, elapsed = collect_logits(model, val_loader, device)
            val_metrics = metrics_from_logits(val_logits, val_labels, 1.0, elapsed)
            row = {"stage": stage, "epoch": epoch, "train": train_stats, "validation": val_metrics}
            history.append(row)
            print(json.dumps({"stage": stage, "epoch": epoch, "train_acc": train_stats["accuracy"], "val_f1": val_metrics["macro_f1"]}), flush=True)
            if val_metrics["macro_f1"] > best_f1:
                best_f1 = val_metrics["macro_f1"]
                torch.save(model.state_dict(), candidate)

    if args.finetune_epochs:
        model.load_state_dict(torch.load(candidate, map_location=device))
        finetune_loader = make_loader(
            train_split,
            train_tf,
            args.finetune_batch_size,
            True,
            args.workers,
            args.max_train,
        )
        for param in model.layer4.parameters():
            param.requires_grad = True
        optimizer = AdamW(
            [{"params": model.layer4.parameters(), "lr": args.finetune_lr}, {"params": model.fc.parameters(), "lr": args.head_lr / 5}],
            weight_decay=1e-4,
        )
        for epoch in range(1, args.finetune_epochs + 1):
            train_stats = run_epoch(model, finetune_loader, device, optimizer)
            val_logits, val_labels, elapsed = collect_logits(model, val_loader, device)
            val_metrics = metrics_from_logits(val_logits, val_labels, 1.0, elapsed)
            history.append({"stage": "layer4", "epoch": epoch, "train": train_stats, "validation": val_metrics})
            print(json.dumps({"stage": "layer4", "epoch": epoch, "train_acc": train_stats["accuracy"], "val_f1": val_metrics["macro_f1"]}), flush=True)
            if val_metrics["macro_f1"] > best_f1:
                best_f1 = val_metrics["macro_f1"]
                torch.save(model.state_dict(), candidate)

    model.load_state_dict(torch.load(candidate, map_location=device))
    val_logits, val_labels, _ = collect_logits(model, val_loader, device)
    temperature = calibrate_temperature(val_logits, val_labels)
    thresholds = calibrate_thresholds(val_logits, val_labels, temperature)
    test_loader = make_loader(test_split, eval_tf, args.batch_size, False, args.workers)
    test_logits, test_labels, elapsed = collect_logits(model, test_loader, device)
    test_metrics = metrics_from_logits(test_logits, test_labels, temperature, elapsed)

    if args.activate:
        archive = ROOT / "models" / "archive"
        archive.mkdir(parents=True, exist_ok=True)
        if DEFAULT_WEIGHTS.exists():
            backup = archive / f"resnet50_legacy_{sha256(DEFAULT_WEIGHTS)[:12]}.pth"
            if not backup.exists():
                shutil.copy2(DEFAULT_WEIGHTS, backup)
        shutil.copy2(candidate, DEFAULT_WEIGHTS)

    metadata = {
        "result_version": "2.0",
        "release_status": "active" if args.activate else "candidate",
        "architecture": "ResNet50",
        "dataset": "CIFAKE (official 100000 train / 20000 test)",
        "dataset_source": "dragonintelligence/CIFAKE-image-dataset",
        "split_seed": SEED,
        "validation_size": args.validation_size,
        "temperature": temperature,
        "thresholds": {"authentic_max": thresholds["authentic_max"], "ai_min": thresholds["ai_min"]},
        "threshold_calibration": thresholds,
        "weights_sha256": sha256(DEFAULT_WEIGHTS if args.activate else candidate),
        "test_metrics": test_metrics,
        "trained_at": datetime.now(timezone.utc).isoformat(),
    }
    write_yaml(ARTIFACT_DIR / "metadata.yaml", metadata)
    write_yaml(ARTIFACT_DIR / "training_history.yaml", {"history": history})
    write_yaml(ARTIFACT_DIR / "evaluation_current.yaml", test_metrics)
    (ARTIFACT_DIR / "model_card.md").write_text(model_card(metadata), encoding="utf-8")
    print(yaml.safe_dump(metadata, allow_unicode=True, sort_keys=False), flush=True)


def model_card(metadata: dict) -> str:
    m = metadata["test_metrics"]
    t = metadata["thresholds"]
    return f"""# AIGI-Holmes 图像检测模型卡

- 架构：ResNet50（保留 Grad-CAM 兼容性）
- 数据集：CIFAKE，官方训练集 100,000 张；官方测试集 20,000 张
- 测试集用途：仅最终评估，不参与训练、阈值或温度校准
- Accuracy：{m['accuracy']:.4f}
- Macro-F1：{m['macro_f1']:.4f}
- ROC-AUC（FAKE）：{m['roc_auc_fake']:.4f}
- ECE（15 bins）：{m['ece_15_bins']:.4f}
- 灰区阈值：AI 风险 ≤ {t['authentic_max']:.1f}% 为较可能真实；≥ {t['ai_min']:.1f}% 为较可能 AI；其余为证据不足
- 权重 SHA-256：`{metadata['weights_sha256']}`

## 使用边界

模型只学习 CIFAKE 的 32×32 图像分布，不能把课程数据集成绩等同于真实新闻场景性能。输出是风险提示，不是真伪证明。印章、频域、边缘、人脸、Logo 与 EXIF 分析仅作为辅助信号展示，不参与三态结论。
"""


def evaluate(args) -> None:
    seed_everything()
    device = select_device(args.device)
    _, eval_tf = transforms_for_training()
    _, _, test_split = load_cifake(args.validation_size)
    loader = make_loader(test_split, eval_tf, args.batch_size, False, args.workers, args.max_eval)
    model = make_model(pretrained=False, weights_path=Path(args.weights)).to(device)
    logits, labels, elapsed = collect_logits(model, loader, device)
    metrics = metrics_from_logits(logits, labels, args.temperature, elapsed)
    output = Path(args.output)
    write_yaml(output, {"weights": str(args.weights), "weights_sha256": sha256(Path(args.weights)), **metrics})
    print(yaml.safe_dump(metrics, allow_unicode=True, sort_keys=False), flush=True)


def parse_args():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="mode", required=True)
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--device", default="auto")
    common.add_argument("--batch-size", type=int, default=64)
    common.add_argument("--workers", type=int, default=0)
    common.add_argument("--validation-size", type=int, default=10_000)

    train_parser = sub.add_parser("train", parents=[common])
    train_parser.add_argument("--head-epochs", type=int, default=3)
    train_parser.add_argument("--finetune-epochs", type=int, default=1)
    train_parser.add_argument("--head-lr", type=float, default=1e-3)
    train_parser.add_argument("--finetune-lr", type=float, default=2e-5)
    train_parser.add_argument("--finetune-batch-size", type=int, default=32)
    train_parser.add_argument("--activate", action="store_true")
    train_parser.add_argument("--max-train", type=int, help="Smoke-test limit; omit for the full training split")
    train_parser.add_argument("--max-validation", type=int, help="Smoke-test limit; omit for the full validation split")

    eval_parser = sub.add_parser("evaluate", parents=[common])
    eval_parser.add_argument("--weights", default=str(DEFAULT_WEIGHTS))
    eval_parser.add_argument("--temperature", type=float, default=1.0)
    eval_parser.add_argument("--max-eval", type=int)
    eval_parser.add_argument("--output", default=str(ARTIFACT_DIR / "evaluation_baseline.yaml"))
    return parser.parse_args()


if __name__ == "__main__":
    arguments = parse_args()
    train(arguments) if arguments.mode == "train" else evaluate(arguments)
