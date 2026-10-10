"""Metric Calculation Engine for Patchwise Benchmark Suite.

Implements precision, recall, F1 score, false-positive rate, and latency statistics
with explicit handling of zero denominators to avoid manufacturing numbers.
"""
import math
from typing import Dict, List, Optional


def calculate_precision(tp: int, fp: int) -> Optional[float]:
    """
    Precision = TP / (TP + FP).
    Returns None if (TP + FP) == 0 to handle zero denominator explicitly.
    """
    total = tp + fp
    if total <= 0:
        return None
    return round(tp / total, 4)


def calculate_recall(tp: int, fn: int) -> Optional[float]:
    """
    Recall = TP / (TP + FN).
    Returns None if (TP + FN) == 0 to handle zero denominator explicitly.
    """
    total = tp + fn
    if total <= 0:
        return None
    return round(tp / total, 4)


def calculate_f1(precision: Optional[float], recall: Optional[float]) -> Optional[float]:
    """
    F1 Score = 2 * (Precision * Recall) / (Precision + Recall).
    Returns None if precision or recall is None or if their sum is 0.
    """
    if precision is None or recall is None:
        return None
    sum_val = precision + recall
    if sum_val <= 0:
        return None
    return round(2 * (precision * recall) / sum_val, 4)


def calculate_false_positive_rate(fp: int, tn: int) -> Optional[float]:
    """
    FPR = FP / (FP + TN).
    Calculated across cases with ground-truth negative evaluation units.
    Returns None if (FP + TN) == 0.
    """
    total = fp + tn
    if total <= 0:
        return None
    return round(fp / total, 4)


def calculate_latency_statistics(latencies: List[float]) -> Dict[str, float]:
    """
    Calculates summary latency statistics: total, mean, median, and 95th percentile.
    """
    if not latencies:
        return {
            "total_ms": 0.0,
            "mean_ms": 0.0,
            "median_ms": 0.0,
            "p95_ms": 0.0,
        }

    sorted_lats = sorted(latencies)
    n = len(sorted_lats)
    total = sum(sorted_lats)
    mean = total / n

    # Median
    if n % 2 == 1:
        median = sorted_lats[n // 2]
    else:
        median = (sorted_lats[n // 2 - 1] + sorted_lats[n // 2]) / 2.0

    # P95 (nearest rank method)
    p95_index = max(0, math.ceil(0.95 * n) - 1)
    p95 = sorted_lats[p95_index]

    return {
        "total_ms": round(total, 2),
        "mean_ms": round(mean, 2),
        "median_ms": round(median, 2),
        "p95_ms": round(p95, 2),
    }
