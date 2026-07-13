#!/usr/bin/env python3
"""Train news text classification models for AIGI-Holmes.

The default ``auto`` mode is conservative:
1. try NLPCC2017 first;
2. if the dataset is incomplete or the best macro F1 is below target, try THUCNews;
3. if neither public source alone covers the fixed 8 labels, try a hybrid source:
   NLPCC2017 for covered labels and HuggingFace THUCNews/cnews only for missing labels;
4. only replace the shipped artifact directory after a formal candidate succeeds.

Use ``--source seed`` only for the lightweight offline demo artifact.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import random
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time
import urllib.request
import zipfile
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import joblib
import numpy as np
import torch
from sklearn.feature_extraction.text import CountVectorizer, TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score
from sklearn.model_selection import train_test_split
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import FeatureUnion, Pipeline
from sklearn.svm import LinearSVC
from torch import nn
from torch.utils.data import DataLoader, TensorDataset
import yaml

from backend.news_text_classify.constants import (
    CATEGORY_ALIASES,
    CATEGORY_LABELS,
    DEFAULT_MODEL_VERSION,
    MODEL_DISPLAY_NAMES,
)
from backend.news_text_classify.service import build_model_input
from backend.news_text_classify.textcnn import TextCNN, encode_chars
from backend.news_text_classify.tokenization import jieba_tokens


NLPCC_GIT_URL = "https://github.com/FudanNLP/nlpcc2017_news_headline_categorization.git"
NLPCC_ZIP_URLS = [
    "https://github.com/FudanNLP/nlpcc2017_news_headline_categorization/archive/refs/heads/master.zip",
    "https://codeload.github.com/FudanNLP/nlpcc2017_news_headline_categorization/zip/refs/heads/master",
]
THUCNEWS_URLS = [
    "http://thuctc.thunlp.org/source/THUCNews.zip",
    "https://thuctc.thunlp.org/source/THUCNews.zip",
]
HF_THUCNEWS_REPO = "spiritx2023/ThuCnews"
HF_THUCNEWS_FILES = ["cnews.train.txt", "cnews.val.txt", "cnews.test.txt"]


@dataclass
class Candidate:
    source: str
    rows: list[dict[str, str]]
    counts: dict[str, int]
    warnings: list[str]
    cleaning_stats: dict | None = None
    source_counts: dict[str, int] | None = None


@dataclass
class TrainingRun:
    source: str
    artifact_dir: Path
    metrics: dict
    best_model: str
    best_macro_f1: float
    total_samples: int
    counts: dict[str, int]
    warnings: list[str]


def clean_text(value: object, limit: int | None = None) -> str:
    text = " ".join(str(value or "").replace("\ufeff", "").split())
    return text[:limit] if limit else text


def infer_title_and_content(text: object) -> tuple[str, str]:
    """Create title-like input from either a headline or a full news article."""
    clean = clean_text(text, 3000)
    if not clean:
        return "", ""
    if len(clean) <= 140:
        return clean, ""
    cut = 80
    for mark in ("。", "！", "？", "；"):
        idx = clean.find(mark)
        if 20 <= idx <= 120:
            cut = idx + 1
            break
    return clean[:cut], clean[:1000]


def normalize_label(label: object) -> str | None:
    value = clean_text(label)
    if not value:
        return None
    if value in CATEGORY_LABELS:
        return value
    lowered = value.lower()
    return CATEGORY_ALIASES.get(value) or CATEGORY_ALIASES.get(lowered)


def read_labeled_csv(path: Path) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    with path.open("r", encoding="utf-8-sig", newline="", errors="ignore") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            label = normalize_label(
                row.get("category")
                or row.get("label")
                or row.get("class")
                or row.get("class_label")
                or row.get("news_label")
            )
            title = clean_text(
                row.get("title")
                or row.get("headline")
                or row.get("content")
                or row.get("text"),
                300,
            )
            content = clean_text(row.get("content") or row.get("body") or row.get("article"), 3000)
            if label and title:
                rows.append({"category": label, "title": title, "content": content})
    return rows


def parse_labeled_json(obj: dict) -> dict[str, str] | None:
    label = normalize_label(
        obj.get("category")
        or obj.get("label")
        or obj.get("class")
        or obj.get("class_label")
        or obj.get("news_label")
    )
    title = clean_text(
        obj.get("title")
        or obj.get("headline")
        or obj.get("sentence")
        or obj.get("text")
        or obj.get("content"),
        300,
    )
    content = clean_text(obj.get("content") or obj.get("body") or obj.get("article"), 3000)
    if label and title:
        return {"category": label, "title": title, "content": content}
    return None


def parse_labeled_line(line: str) -> dict[str, str] | None:
    raw = str(line or "").strip().replace("\ufeff", "")
    if not raw:
        return None
    try:
        obj = json.loads(raw)
        if isinstance(obj, dict):
            parsed = parse_labeled_json(obj)
            if parsed:
                return parsed
    except Exception:
        pass

    for sep in ("\t", "|||", "\u0001", "####", ","):
        if sep not in raw:
            continue
        parts = [clean_text(p) for p in raw.split(sep) if clean_text(p)]
        if len(parts) < 2:
            continue
        first_label = normalize_label(parts[0])
        last_label = normalize_label(parts[-1])
        if first_label:
            return {"category": first_label, "title": parts[1][:300], "content": " ".join(parts[2:])[:3000]}
        if last_label:
            return {"category": last_label, "title": parts[0][:300], "content": " ".join(parts[1:-1])[:3000]}
    line = clean_text(raw)
    if not line:
        return None
    parts = [clean_text(p) for p in line.split(" ") if clean_text(p)]
    if len(parts) >= 2:
        first_label = normalize_label(parts[0])
        if first_label:
            return {"category": first_label, "title": " ".join(parts[1:])[:300], "content": ""}
    return None


def read_dataset_dir(data_dir: Path) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    if not data_dir.exists():
        return rows

    # THUCNews-style: one directory per class, each article in a .txt file.
    for subdir in data_dir.rglob("*"):
        if not subdir.is_dir():
            continue
        label = normalize_label(subdir.name)
        if not label:
            continue
        for path in subdir.rglob("*.txt"):
            try:
                text = path.read_text(encoding="utf-8", errors="ignore").strip()
            except Exception:
                continue
            if not text:
                continue
            first_line = clean_text(text.splitlines()[0], 300)
            rows.append({"category": label, "title": first_line, "content": clean_text(text, 3000)})

    # NLPCC/csv/json/jsonl-style mixed files.
    for path in data_dir.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in {".csv", ".txt", ".json", ".jsonl"}:
            continue
        if path.suffix.lower() == ".csv":
            try:
                rows.extend(read_labeled_csv(path))
                continue
            except Exception:
                pass
        try:
            with path.open("r", encoding="utf-8", errors="ignore") as fh:
                for line in fh:
                    item = parse_labeled_line(line)
                    if item:
                        rows.append(item)
        except Exception:
            continue
    return dedupe_rows(rows)


def dedupe_rows(rows: Iterable[dict[str, str]]) -> list[dict[str, str]]:
    seen: set[tuple[str, str]] = set()
    cleaned: list[dict[str, str]] = []
    for row in rows:
        label = normalize_label(row.get("category"))
        title = clean_text(row.get("title"), 300)
        content = clean_text(row.get("content"), 3000)
        source = clean_text(row.get("_source") or row.get("source"))
        if not label or not title:
            continue
        key = (label, title)
        if key in seen:
            continue
        seen.add(key)
        cleaned.append({"category": label, "title": title, "content": content, "_source": source})
    return cleaned


def clean_training_rows(rows: Iterable[dict[str, str]]) -> tuple[list[dict[str, str]], dict]:
    stats = {
        "before": 0,
        "after": 0,
        "dropped_empty": 0,
        "dropped_short": 0,
        "dropped_duplicate": 0,
    }
    seen: set[tuple[str, str]] = set()
    cleaned: list[dict[str, str]] = []
    for row in rows:
        stats["before"] += 1
        label = normalize_label(row.get("category"))
        title = clean_text(row.get("title"), 300)
        content = clean_text(row.get("content"), 3000)
        source = clean_text(row.get("_source") or row.get("source"))
        if not label or not title:
            stats["dropped_empty"] += 1
            continue
        compact = (title + content).replace(" ", "")
        if len(compact) < 6:
            stats["dropped_short"] += 1
            continue
        key = (label, title.replace(" ", ""), content[:120].replace(" ", ""))
        if key in seen:
            stats["dropped_duplicate"] += 1
            continue
        seen.add(key)
        cleaned.append({"category": label, "title": title, "content": content, "_source": source})
    stats["after"] = len(cleaned)
    return cleaned, stats


def dataset_counts(rows: list[dict[str, str]]) -> dict[str, int]:
    counter = Counter(row["category"] for row in rows if row.get("category") in CATEGORY_LABELS)
    return {label: int(counter.get(label, 0)) for label in CATEGORY_LABELS}


def validate_candidate(source: str, rows: list[dict[str, str]], min_per_class: int) -> Candidate:
    rows = [
        {**row, "_source": row.get("_source") or source}
        for row in rows
    ]
    rows, cleaning_stats = clean_training_rows(rows)
    counts = dataset_counts(rows)
    source_counts = dict(Counter(row.get("_source") or source for row in rows))
    warnings: list[str] = []
    missing = [label for label, count in counts.items() if count <= 0]
    low = [f"{label}:{count}" for label, count in counts.items() if 0 < count < min_per_class]
    if missing:
        warnings.append(f"缺少类别: {', '.join(missing)}")
    if low:
        warnings.append(f"部分类别样本少于 {min_per_class}: {', '.join(low)}")
    return Candidate(
        source=source,
        rows=rows,
        counts=counts,
        warnings=warnings,
        cleaning_stats=cleaning_stats,
        source_counts=source_counts,
    )


def ensure_formal_candidate(candidate: Candidate, min_per_class: int) -> None:
    missing = [label for label, count in candidate.counts.items() if count <= 0]
    low = [label for label, count in candidate.counts.items() if count < min_per_class]
    if missing:
        raise SystemExit(f"{candidate.source} 数据不满足 8 类要求，{'; '.join(candidate.warnings)}")
    if low:
        raise SystemExit(f"{candidate.source} 数据量不足，{'; '.join(candidate.warnings)}")


def run_command(cmd: list[str], cwd: Path | None = None) -> None:
    subprocess.run(cmd, cwd=str(cwd or ROOT), check=True)


def has_dataset_files(path: Path) -> bool:
    if not path.exists():
        return False
    return any(
        item.is_file() and item.suffix.lower() in {".csv", ".txt", ".json", ".jsonl"}
        for item in path.rglob("*")
    )


def try_clone_nlpcc(target_dir: Path) -> None:
    if has_dataset_files(target_dir):
        return
    if target_dir.exists():
        shutil.rmtree(target_dir)
    target_dir.parent.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env.setdefault("GIT_HTTP_VERSION", "HTTP/1.1")
    proxy = env.get("AIGI_DOWNLOAD_PROXY") or env.get("HTTPS_PROXY") or env.get("HTTP_PROXY")
    cmd = ["git", "-c", "http.version=HTTP/1.1"]
    if proxy:
        cmd.extend(["-c", f"http.proxy={proxy}", "-c", f"https.proxy={proxy}"])
    cmd.extend(["clone", "--depth", "1", NLPCC_GIT_URL, str(target_dir)])
    subprocess.run(
        cmd,
        check=True,
        env=env,
        timeout=90,
    )


def download_file(url: str, target: Path, timeout: int = 60) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(url, headers={"User-Agent": "AIGI-Holmes-news-classifier/1.0"})
    proxy = os.environ.get("AIGI_DOWNLOAD_PROXY") or os.environ.get("HTTPS_PROXY") or os.environ.get("HTTP_PROXY")
    opener = urllib.request.build_opener(
        urllib.request.ProxyHandler({"http": proxy, "https": proxy}) if proxy else urllib.request.ProxyHandler({})
    )
    with opener.open(request, timeout=timeout) as resp:
        with target.open("wb") as fh:
            shutil.copyfileobj(resp, fh)


def unpack_archive(archive_path: Path, target_dir: Path) -> None:
    target_dir.mkdir(parents=True, exist_ok=True)
    if zipfile.is_zipfile(archive_path):
        with zipfile.ZipFile(archive_path) as zf:
            zf.extractall(target_dir)
        return
    if tarfile.is_tarfile(archive_path):
        with tarfile.open(archive_path) as tf:
            tf.extractall(target_dir)
        return
    raise ValueError(f"无法识别压缩包格式: {archive_path}")


def unpack_nested_archives(target_dir: Path) -> None:
    if not target_dir.exists():
        return
    for archive_path in list(target_dir.rglob("*")):
        if not archive_path.is_file():
            continue
        suffixes = "".join(archive_path.suffixes).lower()
        if suffixes.endswith(".tar.gz") or suffixes.endswith(".tgz") or archive_path.suffix.lower() == ".zip":
            extract_marker = archive_path.with_suffix(archive_path.suffix + ".extracted")
            if extract_marker.exists():
                continue
            try:
                unpack_archive(archive_path, archive_path.parent)
                extract_marker.write_text("ok\n", encoding="utf-8")
            except Exception as exc:
                print(f"[WARN] nested archive extract failed: {archive_path}: {exc}")


def try_download_archives(urls: list[str], target_dir: Path, archive_name: str) -> None:
    if has_dataset_files(target_dir):
        return
    if target_dir.exists():
        shutil.rmtree(target_dir)
    with tempfile.TemporaryDirectory(prefix="news-dataset-") as tmp:
        archive_path = Path(tmp) / archive_name
        last_error: Exception | None = None
        for url in urls:
            try:
                print(f"[INFO] downloading {url}")
                download_file(url, archive_path)
                unpack_archive(archive_path, target_dir)
                unpack_nested_archives(target_dir)
                return
            except Exception as exc:
                last_error = exc
                print(f"[WARN] download failed: {url}: {exc}")
        if last_error:
            raise last_error


def load_nlpcc(data_dir: Path, min_per_class: int) -> Candidate:
    target = data_dir / "nlpcc2017"
    errors: list[str] = []
    if not (target.exists() and any(target.rglob("*"))):
        try:
            try_clone_nlpcc(target)
        except Exception as exc:
            errors.append(f"git clone 失败: {exc}")
            try:
                try_download_archives(NLPCC_ZIP_URLS, target, "nlpcc2017.zip")
            except Exception as zip_exc:
                errors.append(f"zip 下载失败: {zip_exc}")
    unpack_nested_archives(target)
    candidate = validate_candidate("NLPCC2017", read_dataset_dir(target), min_per_class)
    candidate.warnings.extend(errors)
    return candidate


def load_thucnews(data_dir: Path, min_per_class: int) -> Candidate:
    target = data_dir / "THUCNews"
    errors: list[str] = []
    if not (target.exists() and any(target.rglob("*"))):
        try:
            try_download_archives(THUCNEWS_URLS, target, "THUCNews.zip")
        except Exception as exc:
            errors.append(f"THUCNews 下载失败: {exc}")
    candidate = validate_candidate("THUCNews", read_dataset_dir(target), min_per_class)
    candidate.warnings.extend(errors)
    return candidate


def ensure_hf_thucnews(data_dir: Path) -> tuple[Path, list[str]]:
    target = data_dir / "hf_thucnews"
    warnings: list[str] = []
    if all((target / name).exists() for name in HF_THUCNEWS_FILES):
        return target, warnings
    try:
        from huggingface_hub import hf_hub_download
    except Exception as exc:
        warnings.append(f"HuggingFace 数据工具不可用: {exc}")
        return target, warnings

    target.mkdir(parents=True, exist_ok=True)
    for name in HF_THUCNEWS_FILES:
        try:
            cached = Path(hf_hub_download(repo_id=HF_THUCNEWS_REPO, filename=name, repo_type="dataset"))
            shutil.copy2(cached, target / name)
        except Exception as exc:
            warnings.append(f"HuggingFace THUCNews 文件下载失败 {name}: {exc}")
    return target, warnings


def load_hf_thucnews(data_dir: Path, min_per_class: int) -> Candidate:
    target, warnings = ensure_hf_thucnews(data_dir)
    candidate = validate_candidate("HF-THUCNews-cnews", read_dataset_dir(target), min_per_class)
    candidate.warnings.extend(warnings)
    return candidate


def load_hybrid(data_dir: Path, min_per_class: int) -> Candidate:
    nlpcc = load_nlpcc(data_dir, min_per_class)
    thuc = load_hf_thucnews(data_dir, min_per_class)
    combined: list[dict[str, str]] = []
    warnings: list[str] = []
    nlpcc_counts = nlpcc.counts
    thuc_counts = thuc.counts
    supplement_labels = [label for label, count in nlpcc_counts.items() if count < min_per_class]

    for row in nlpcc.rows:
        if row["category"] in CATEGORY_LABELS:
            combined.append({**row, "_source": "NLPCC2017"})
    for row in thuc.rows:
        if row["category"] in supplement_labels:
            combined.append({**row, "_source": "HF-THUCNews-cnews"})

    warnings.append(
        "hybrid source: NLPCC2017 provides covered labels; HF-THUCNews/cnews supplements "
        + ", ".join(supplement_labels or ["none"])
    )
    for label in supplement_labels:
        warnings.append(
            f"{label}: NLPCC={nlpcc_counts.get(label, 0)}, HF-THUCNews={thuc_counts.get(label, 0)}"
        )
    warnings.extend(f"NLPCC: {warning}" for warning in nlpcc.warnings)
    warnings.extend(f"HF-THUCNews: {warning}" for warning in thuc.warnings)
    candidate = validate_candidate("NLPCC2017+HF-THUCNews-cnews", combined, min_per_class)
    candidate.warnings = warnings + candidate.warnings
    return candidate


def load_local(data_dir: Path, min_per_class: int) -> Candidate:
    return validate_candidate("local_dataset", read_dataset_dir(data_dir), min_per_class)


def load_seed(seed_csv: Path, min_per_class: int) -> Candidate:
    return validate_candidate("seed_samples", read_labeled_csv(seed_csv), min_per_class=1)


def balance_rows(rows: list[dict[str, str]], max_per_class: int, seed: int) -> list[dict[str, str]]:
    buckets: dict[str, list[dict[str, str]]] = {label: [] for label in CATEGORY_LABELS}
    for row in rows:
        if row["category"] in buckets:
            buckets[row["category"]].append(row)
    missing = [label for label, values in buckets.items() if not values]
    if missing:
        raise SystemExit(f"缺少类别: {', '.join(missing)}")
    balanced: list[dict[str, str]] = []
    rng = random.Random(seed)
    for label in CATEGORY_LABELS:
        values = buckets[label]
        rng.shuffle(values)
        balanced.extend(values[:max_per_class] if max_per_class else values)
    rng.shuffle(balanced)
    return balanced


def build_strategy_input(row: dict[str, str], strategy: str) -> str:
    return build_model_input(row["title"], row.get("content", ""), strategy)


def make_texts(rows: list[dict[str, str]], strategy: str) -> tuple[list[str], list[str]]:
    texts = [build_strategy_input(row, strategy) for row in rows]
    labels = [row["category"] for row in rows]
    return texts, labels


def split_rows(rows: list[dict[str, str]], seed: int) -> tuple:
    labels = [row["category"] for row in rows]
    counts = Counter(labels)
    stratify = labels if min(counts.values()) >= 3 else None
    train_rows, temp_rows = train_test_split(
        rows, test_size=0.3, random_state=seed, stratify=stratify
    )
    temp_labels = [row["category"] for row in temp_rows]
    temp_counts = Counter(temp_labels)
    temp_stratify = temp_labels if min(temp_counts.values()) >= 2 else None
    val_rows, test_rows = train_test_split(
        temp_rows, test_size=0.5, random_state=seed, stratify=temp_stratify
    )
    return train_rows, val_rows, test_rows


def feature_union() -> FeatureUnion:
    return FeatureUnion(
        [
            (
                "char_tfidf",
                TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 4), max_features=40000),
            ),
            (
                "word_tfidf",
                TfidfVectorizer(
                    tokenizer=jieba_tokens,
                    token_pattern=None,
                    lowercase=False,
                    ngram_range=(1, 2),
                    max_features=20000,
                ),
            ),
            (
                "char_count",
                CountVectorizer(analyzer="char", ngram_range=(1, 2), max_features=10000),
            ),
        ]
    )


def select_input_strategy(
    train_rows: list[dict[str, str]],
    val_rows: list[dict[str, str]],
    seed: int,
) -> tuple[str, list[dict]]:
    strategies = ["title_only", "title_plus_summary", "title_weighted_content"]
    results: list[dict] = []
    train_y = [row["category"] for row in train_rows]
    val_y = [row["category"] for row in val_rows]
    for strategy in strategies:
        train_x, _ = make_texts(train_rows, strategy)
        val_x, _ = make_texts(val_rows, strategy)
        pipe = Pipeline([
            ("features", feature_union()),
            ("clf", LogisticRegression(max_iter=1200, class_weight="balanced", random_state=seed)),
        ])
        pipe.fit(train_x, train_y)
        pred = pipe.predict(val_x)
        results.append({
            "strategy": strategy,
            "accuracy": round(float(accuracy_score(val_y, pred)), 4),
            "macro_f1": round(float(f1_score(val_y, pred, labels=CATEGORY_LABELS, average="macro", zero_division=0)), 4),
        })
    results.sort(key=lambda item: item["macro_f1"], reverse=True)
    return results[0]["strategy"], results


def train_classic(
    train_x: list[str],
    train_y: list[str],
    test_x: list[str],
    test_y: list[str],
    export_x: list[str],
    export_y: list[str],
    out_dir: Path,
) -> dict:
    models = {
        "nb": MultinomialNB(alpha=0.08),
        "lr": LogisticRegression(max_iter=1500, class_weight="balanced"),
        "svm": LinearSVC(class_weight="balanced"),
    }
    metrics = {}
    for key, clf in models.items():
        print(f"[INFO] training {MODEL_DISPLAY_NAMES[key]}")
        pipe = Pipeline([("features", feature_union()), ("clf", clf)])
        pipe.fit(train_x, train_y)
        pred = pipe.predict(test_x)
        metrics[key] = evaluate(test_y, pred)

        export_pipe = Pipeline([("features", feature_union()), ("clf", clf)])
        export_pipe.fit(export_x, export_y)
        joblib.dump(export_pipe, out_dir / f"{key}.joblib", compress=3)
    return metrics


def build_vocab(texts: list[str], max_vocab: int = 8000) -> dict[str, int]:
    counter = Counter(ch for text in texts for ch in text)
    vocab = {"<PAD>": 0, "<UNK>": 1}
    for ch, _ in counter.most_common(max_vocab - 2):
        vocab[ch] = len(vocab)
    return vocab


def train_textcnn_once(
    train_x: list[str],
    train_y: list[str],
    eval_x: list[str],
    eval_y: list[str],
    config: dict,
    seed: int,
) -> tuple[TextCNN, dict[str, int], dict, list[dict]]:
    torch.manual_seed(seed)
    np.random.seed(seed)
    random.seed(seed)
    label_to_id = {label: idx for idx, label in enumerate(CATEGORY_LABELS)}
    max_len = int(config["max_len"])
    vocab = build_vocab(train_x, int(config.get("max_vocab", 8000)))
    x_train = torch.tensor([encode_chars(text, vocab, max_len) for text in train_x], dtype=torch.long)
    y_train = torch.tensor([label_to_id[y] for y in train_y], dtype=torch.long)
    x_eval = torch.tensor([encode_chars(text, vocab, max_len) for text in eval_x], dtype=torch.long)

    generator = torch.Generator()
    generator.manual_seed(seed)
    loader = DataLoader(
        TensorDataset(x_train, y_train),
        batch_size=int(config.get("batch_size", 128)),
        shuffle=True,
        generator=generator,
    )
    model = TextCNN(
        vocab_size=len(vocab),
        num_classes=len(CATEGORY_LABELS),
        embed_dim=int(config["embed_dim"]),
        num_filters=int(config["num_filters"]),
        kernel_sizes=tuple(config.get("kernel_sizes", (2, 3, 4))),
        dropout=float(config["dropout"]),
    )
    opt = torch.optim.Adam(model.parameters(), lr=float(config["lr"]))
    loss_fn = nn.CrossEntropyLoss()
    history: list[dict] = []
    for epoch in range(1, max(1, int(config["epochs"])) + 1):
        model.train()
        total_loss = 0.0
        for xb, yb in loader:
            opt.zero_grad()
            loss = loss_fn(model(xb), yb)
            loss.backward()
            opt.step()
            total_loss += float(loss.item()) * len(xb)
        model.eval()
        with torch.no_grad():
            pred_ids = torch.argmax(model(x_eval), dim=1).tolist()
        pred = [CATEGORY_LABELS[i] for i in pred_ids]
        history.append({
            "epoch": epoch,
            "loss": round(total_loss / max(1, len(train_x)), 4),
            "val_accuracy": round(float(accuracy_score(eval_y, pred)), 4),
            "val_macro_f1": round(float(f1_score(eval_y, pred, labels=CATEGORY_LABELS, average="macro", zero_division=0)), 4),
        })

    model.eval()
    with torch.no_grad():
        pred_ids = torch.argmax(model(x_eval), dim=1).tolist()
    pred = [CATEGORY_LABELS[i] for i in pred_ids]
    return model, vocab, evaluate(eval_y, pred), history


def train_textcnn(
    train_x: list[str],
    train_y: list[str],
    val_x: list[str],
    val_y: list[str],
    test_x: list[str],
    test_y: list[str],
    export_x: list[str],
    export_y: list[str],
    out_dir: Path,
    epochs: int,
    seed: int,
) -> dict:
    print("[INFO] training TextCNN")
    base_epochs = max(1, epochs)
    tune_pairs = list(zip(train_x, train_y))
    rng = random.Random(seed)
    rng.shuffle(tune_pairs)
    if len(tune_pairs) > 8000:
        tune_pairs = tune_pairs[:8000]
    tune_train_x = [item[0] for item in tune_pairs]
    tune_train_y = [item[1] for item in tune_pairs]
    configs = [
        # Do not silently cut a requested eight-epoch experiment down to five
        # epochs: the previous candidate was still improving at its final epoch.
        {"max_len": 128, "embed_dim": 64, "num_filters": 64, "kernel_sizes": (2, 3, 4), "dropout": 0.25, "lr": 0.002, "epochs": base_epochs},
        {"max_len": 160, "embed_dim": 80, "num_filters": 80, "kernel_sizes": (2, 3, 4), "dropout": 0.30, "lr": 0.0015, "epochs": base_epochs + 2},
    ]
    trials: list[dict] = []
    best_config = configs[0]
    best_score = -1.0
    for idx, config in enumerate(configs, start=1):
        _, _, val_metric, history = train_textcnn_once(tune_train_x, tune_train_y, val_x, val_y, config, seed + idx)
        trial = {
            "config": {
                key: list(value) if isinstance(value, tuple) else value
                for key, value in config.items()
            },
            "val_accuracy": val_metric["accuracy"],
            "val_macro_f1": val_metric["macro_f1"],
            "history": history,
        }
        trials.append(trial)
        if float(val_metric["macro_f1"]) > best_score:
            best_score = float(val_metric["macro_f1"])
            best_config = config

    train_all_x = train_x + val_x
    train_all_y = train_y + val_y
    model, vocab, metric, history = train_textcnn_once(train_all_x, train_all_y, test_x, test_y, best_config, seed + 31)
    metric["training_history"] = history
    metric["tuning_trials"] = trials
    metric["selected_config"] = {
        key: list(value) if isinstance(value, tuple) else value
        for key, value in best_config.items()
    }

    torch.save(
        {
            "vocab": vocab,
            "label_order": CATEGORY_LABELS,
            "max_len": int(best_config["max_len"]),
            "config": {
                "embed_dim": int(best_config["embed_dim"]),
                "num_filters": int(best_config["num_filters"]),
                "kernel_sizes": tuple(best_config.get("kernel_sizes", (2, 3, 4))),
                "dropout": float(best_config["dropout"]),
            },
            "model_state": model.state_dict(),
        },
        out_dir / "textcnn.pt",
    )
    return metric


def evaluate(y_true: list[str], y_pred: list[str]) -> dict:
    return {
        "accuracy": round(float(accuracy_score(y_true, y_pred)), 4),
        "macro_f1": round(float(f1_score(y_true, y_pred, labels=CATEGORY_LABELS, average="macro", zero_division=0)), 4),
        "classification_report": classification_report(
            y_true,
            y_pred,
            labels=CATEGORY_LABELS,
            zero_division=0,
            output_dict=True,
        ),
        "confusion_matrix": confusion_matrix(y_true, y_pred, labels=CATEGORY_LABELS).tolist(),
    }


def best_metric(metrics: dict) -> tuple[str, float]:
    ranked = sorted(metrics.items(), key=lambda item: item[1]["macro_f1"], reverse=True)
    return ranked[0][0], float(ranked[0][1]["macro_f1"])


def artifact_size_mb(path: Path) -> float:
    total = 0
    for item in path.rglob("*"):
        if item.is_file():
            total += item.stat().st_size
    return round(total / 1024 / 1024, 2)


def existing_best_macro_f1(artifact_dir: Path) -> float | None:
    """Read the shipped model score so a weaker candidate cannot replace it."""
    metadata_path = artifact_dir / "metadata.yaml"
    if not metadata_path.exists():
        return None
    try:
        metadata = yaml.safe_load(metadata_path.read_text(encoding="utf-8")) or {}
        score = metadata.get("training_summary", {}).get("best_macro_f1")
        return float(score) if score is not None else None
    except (OSError, TypeError, ValueError, yaml.YAMLError) as exc:
        print(f"[WARN] could not read current model score: {exc}")
        return None


def write_metadata(
    out_dir: Path,
    metrics: dict,
    candidate: Candidate,
    total: int,
    target_macro_f1: float,
    max_per_class: int,
    formal: bool,
    selected_input_strategy: str,
    input_strategy_metrics: list[dict],
) -> None:
    default_model, best_f1 = best_metric(metrics)
    status = "passed" if best_f1 >= target_macro_f1 else "below_target"
    note = (
        "formal training artifact generated from public news classification data."
        if formal
        else "seed_samples is a lightweight bundled demo artifact; use NLPCC2017/THUCNews data for course-grade metrics."
    )
    meta = {
        "model_version": DEFAULT_MODEL_VERSION,
        "default_model": default_model,
        "label_order": CATEGORY_LABELS,
        "training_summary": {
            "source": candidate.source,
            "total_samples": total,
            "class_counts": candidate.counts,
            "source_counts": candidate.source_counts or {},
            "cleaning_stats": candidate.cleaning_stats or {},
            "max_per_class": max_per_class,
            "target_macro_f1": target_macro_f1,
            "best_model": default_model,
            "best_macro_f1": round(best_f1, 4),
            "selected_input_strategy": selected_input_strategy,
            "input_strategy_metrics": input_strategy_metrics,
            "status": status,
            "formal": formal,
            "warnings": candidate.warnings,
            "trained_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "note": note,
        },
        "models": {
            key: {
                "name": MODEL_DISPLAY_NAMES[key],
                "accuracy": values["accuracy"],
                "macro_f1": values["macro_f1"],
            }
            for key, values in metrics.items()
        },
    }
    (out_dir / "metrics_full.yaml").write_text(yaml.safe_dump(metrics, allow_unicode=True, sort_keys=False), encoding="utf-8")
    (out_dir / "metadata.yaml").write_text(yaml.safe_dump(meta, allow_unicode=True, sort_keys=False), encoding="utf-8")


def train_candidate(
    candidate: Candidate,
    out_dir: Path,
    max_per_class: int,
    epochs: int,
    seed: int,
    target_macro_f1: float,
    formal: bool,
) -> TrainingRun:
    out_dir.mkdir(parents=True, exist_ok=True)
    rows = balance_rows(candidate.rows, max_per_class, seed)
    candidate.counts = dataset_counts(rows)
    candidate.source_counts = dict(Counter(row.get("_source") or candidate.source for row in rows))
    train_rows, val_rows, test_rows = split_rows(rows, seed)
    selected_strategy, strategy_metrics = select_input_strategy(train_rows, val_rows, seed)
    print(f"[INFO] selected input strategy: {selected_strategy}")
    train_x, train_y = make_texts(train_rows, selected_strategy)
    val_x, val_y = make_texts(val_rows, selected_strategy)
    test_x, test_y = make_texts(test_rows, selected_strategy)
    texts, labels = make_texts(rows, selected_strategy)
    train_all_x = train_x + val_x
    train_all_y = train_y + val_y

    metrics = train_classic(train_all_x, train_all_y, test_x, test_y, texts, labels, out_dir)
    metrics["textcnn"] = train_textcnn(train_x, train_y, val_x, val_y, test_x, test_y, texts, labels, out_dir, epochs, seed)
    write_metadata(
        out_dir,
        metrics,
        candidate,
        len(rows),
        target_macro_f1,
        max_per_class,
        formal,
        selected_strategy,
        strategy_metrics,
    )
    default_model, best_f1 = best_metric(metrics)
    return TrainingRun(
        source=candidate.source,
        artifact_dir=out_dir,
        metrics=metrics,
        best_model=default_model,
        best_macro_f1=best_f1,
        total_samples=len(rows),
        counts=candidate.counts,
        warnings=candidate.warnings,
    )


def replace_artifacts(candidate_dir: Path, final_dir: Path) -> None:
    final_dir.mkdir(parents=True, exist_ok=True)
    for name in ("nb.joblib", "lr.joblib", "svm.joblib", "textcnn.pt", "metadata.yaml", "metrics_full.yaml"):
        src = candidate_dir / name
        if not src.exists():
            raise SystemExit(f"候选模型缺少产物: {src}")
        shutil.copy2(src, final_dir / name)


def print_summary(run: TrainingRun) -> None:
    print("Training complete.")
    print(f"source={run.source} samples={run.total_samples} best={run.best_model} macro_f1={run.best_macro_f1:.4f}")
    print(f"artifact_size={artifact_size_mb(run.artifact_dir):.2f}MB")
    print("class_counts:", ", ".join(f"{k}:{v}" for k, v in run.counts.items()))
    for key, values in sorted(run.metrics.items(), key=lambda item: item[1]["macro_f1"], reverse=True):
        print(f"{key}: accuracy={values['accuracy']:.4f}, macro_f1={values['macro_f1']:.4f}")
    for warning in run.warnings:
        print(f"[WARN] {warning}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", choices=["auto", "nlpcc", "thucnews", "hybrid", "local", "seed"], default="auto")
    parser.add_argument("--data-dir", default=str(ROOT / "data" / "news_text_classify"))
    parser.add_argument("--seed-csv", default=str(ROOT / "resources" / "news_text_classify" / "seed_samples.csv"))
    parser.add_argument("--out-dir", default=str(ROOT / "resources" / "news_text_classify" / "artifacts"))
    parser.add_argument("--max-per-class", type=int, default=2500)
    parser.add_argument("--min-per-class", type=int, default=50)
    parser.add_argument("--epochs", type=int, default=8)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--target-macro-f1", type=float, default=0.80)
    parser.add_argument(
        "--min-improvement",
        type=float,
        default=0.0,
        help="Require this margin over the current shipped macro F1 before replacing artifacts.",
    )
    parser.add_argument(
        "--baseline-macro-f1",
        type=float,
        default=None,
        help="Optional protected baseline score, useful when recovering from an older artifact.",
    )
    parser.add_argument("--proxy", default="", help="Optional download proxy, e.g. http://127.0.0.1:7890")
    parser.add_argument("--keep-candidates", action="store_true")
    args = parser.parse_args()

    random.seed(args.seed)
    np.random.seed(args.seed)
    if args.proxy:
        os.environ["AIGI_DOWNLOAD_PROXY"] = args.proxy
    data_dir = Path(args.data_dir)
    final_dir = Path(args.out_dir)
    formal = args.source != "seed"
    current_best = existing_best_macro_f1(final_dir)
    if args.baseline_macro_f1 is not None:
        current_best = max(current_best or float("-inf"), args.baseline_macro_f1)
    replacement_target = args.target_macro_f1
    if args.min_improvement > 0 and current_best is not None:
        replacement_target = max(replacement_target, current_best + args.min_improvement)
        print(
            "[INFO] current shipped macro F1="
            f"{current_best:.4f}; replacement requires >= {replacement_target:.4f}"
        )

    candidate_loaders = {
        "nlpcc": lambda: load_nlpcc(data_dir, args.min_per_class),
        "thucnews": lambda: load_thucnews(data_dir, args.min_per_class),
        "hybrid": lambda: load_hybrid(data_dir, args.min_per_class),
        "local": lambda: load_local(data_dir, args.min_per_class),
        "seed": lambda: load_seed(Path(args.seed_csv), args.min_per_class),
    }
    order = ["nlpcc", "thucnews", "hybrid"] if args.source == "auto" else [args.source]
    tmp_root = final_dir.parent / "_candidate_artifacts"
    tmp_root.mkdir(parents=True, exist_ok=True)

    last_error: str | None = None
    selected: TrainingRun | None = None
    try:
        for source in order:
            print(f"[INFO] preparing {source}")
            candidate = candidate_loaders[source]()
            if source != "seed":
                try:
                    ensure_formal_candidate(candidate, args.min_per_class)
                except SystemExit as exc:
                    last_error = str(exc)
                    print(f"[WARN] {last_error}")
                    continue
            candidate_dir = tmp_root / source
            if candidate_dir.exists():
                shutil.rmtree(candidate_dir)
            run = train_candidate(
                candidate,
                candidate_dir,
                args.max_per_class,
                args.epochs,
                args.seed,
                replacement_target,
                formal=(source != "seed"),
            )
            print_summary(run)
            if source == "seed" or run.best_macro_f1 >= replacement_target:
                selected = run
                break
            last_error = (
                f"{run.source} best macro F1={run.best_macro_f1:.4f} "
                f"低于替换门槛 {replacement_target:.4f}"
            )
            print(f"[WARN] {last_error}")

        if selected is None:
            raise SystemExit(last_error or "没有可用的正式新闻分类数据。")

        replace_artifacts(selected.artifact_dir, final_dir)
        print(f"[INFO] final artifacts written to {final_dir}")
        print_summary(selected)
    finally:
        if not args.keep_candidates and tmp_root.exists():
            shutil.rmtree(tmp_root)


if __name__ == "__main__":
    main()
