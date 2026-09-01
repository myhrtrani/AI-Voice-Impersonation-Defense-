"""
Calibrated scoring utilities: train a lightweight logistic calibrator on window-level features
and provide aggregation strategies (max, mean, EWMA, hybrid).
"""
from typing import List, Dict, Any, Optional
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
import joblib


class Calibrator:
    def __init__(self):
        self.scaler: Optional[StandardScaler] = None
        self.clf: Optional[LogisticRegression] = None

    def fit(self, X: List[List[float]], y: List[int]):
        self.scaler = StandardScaler().fit(X)
        Xs = self.scaler.transform(X)
        self.clf = LogisticRegression(max_iter=2000).fit(Xs, y)

    def predict_window_probs(self, X: List[List[float]]) -> List[float]:
        if self.clf is None or self.scaler is None:
            raise RuntimeError("Calibrator not trained")
        Xs = self.scaler.transform(X)
        probs = self.clf.predict_proba(Xs)[:, 1].tolist()
        return probs

    def save(self, path: str):
        joblib.dump({'scaler': self.scaler, 'clf': self.clf}, path)

    def load(self, path: str):
        data = joblib.load(path)
        self.scaler = data['scaler']
        self.clf = data['clf']


# Aggregation helpers

def agg_max(probs: List[float]) -> float:
    return float(np.max(probs)) if probs else 0.0


def agg_mean(probs: List[float]) -> float:
    return float(np.mean(probs)) if probs else 0.0


def agg_ewma(probs: List[float], alpha: float = 0.35) -> float:
    if not probs:
        return 0.0
    s = probs[0]
    for p in probs[1:]:
        s = alpha * p + (1.0 - alpha) * s
    return float(s)


def agg_hybrid(probs: List[float], alpha: float = 0.35, max_thresh: float = 0.6, ewma_thresh: float = 0.5) -> float:
    """
    Hybrid returns 1.0 if either the max prob >= max_thresh or ewma >= ewma_thresh; else returns combined score.
    This is a conservative aggregator to preserve short strong signals while avoiding over-triggering.
    """
    if not probs:
        return 0.0
    m = agg_max(probs)
    e = agg_ewma(probs, alpha=alpha)
    if m >= max_thresh or e >= ewma_thresh:
        return max(m, e)
    # otherwise return mean as a middle-ground score
    return agg_mean(probs)
