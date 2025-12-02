from __future__ import annotations

from typing import Callable, List, Optional, Tuple

from app.models.applications import Application, DecisionOutcome


MIN_SUPPORT = 2
MIN_CONFIDENCE = 0.8


def compute_rule_stats(
    applications: List[Application],
    condition_fn: Callable[[Application], bool],
    target_decision: DecisionOutcome,
) -> tuple[int, float, List[str]]:
    """
    Compute:
      - support_count: how many loans match the condition
      - confidence: among those, fraction with the target_decision
      - aligned_decline_reason_codes: decline reason codes if target_decision == "decline"
    """
    matching_apps: List[Application] = [a for a in applications if condition_fn(a)]
    support_count = len(matching_apps)

    if support_count == 0:
        return 0, 0.0, []

    outcome_matches = [a for a in matching_apps if a.final_decision == target_decision]
    confidence = len(outcome_matches) / support_count

    aligned_codes: set[str] = set()
    if target_decision == "decline":
        for a in outcome_matches:
            for reason in a.manual_decline_reasons:
                aligned_codes.add(reason.code)

    return support_count, confidence, sorted(aligned_codes)


def score_from_confidence(confidence: float, target_decision: DecisionOutcome) -> float:
    """
    Simple mapping from confidence to base_score.
    Negative for declines, positive for approvals.
    """
    magnitude = round(confidence * 100)  # 0–100
    return -float(magnitude) if target_decision == "decline" else float(magnitude)


def find_best_univariate_threshold(
    applications: List[Application],
    feature_getter: Callable[[Application], float | int],
    candidate_thresholds: List[float | int],
    target_decision: DecisionOutcome,
    direction: str = "ge",  # "ge" (>=) or "le" (<=)
) -> Optional[tuple[float | int, int, float, List[str]]]:
    """
    Explore a set of candidate thresholds for a single feature and pick the one
    that best predicts the target decision.

    Returns (best_threshold, support, confidence, aligned_decline_codes) or None.
    """
    best: Optional[tuple[float | int, int, float, List[str]]] = None

    for thr in candidate_thresholds:
        if direction == "ge":
            cond = lambda a, thr=thr: feature_getter(a) >= thr
        elif direction == "le":
            cond = lambda a, thr=thr: feature_getter(a) <= thr
        else:
            raise ValueError(f"Unsupported direction: {direction}")

        support, conf, aligned_codes = compute_rule_stats(
            applications, cond, target_decision
        )

        if support < MIN_SUPPORT or conf < MIN_CONFIDENCE:
            continue

        if best is None:
            best = (thr, support, conf, aligned_codes)
        else:
            _, best_support, best_conf, _ = best
            if conf > best_conf or (conf == best_conf and support > best_support):
                best = (thr, support, conf, aligned_codes)

    return best


def find_best_score_dti_combo(
    applications: List[Application],
    score_thresholds: List[int],
    dti_thresholds: List[float],
    target_decision: DecisionOutcome,
) -> Optional[tuple[int, float, int, float]]:
    """
    Explore a grid of (score >= S) AND (dti_ratio <= D) conditions and pick
    (S, D) with best confidence & support.

    Returns (best_score_thr, best_dti_thr, support, confidence) or None.
    """
    best: Optional[tuple[int, float, int, float]] = None

    from app.models.applications import Application as AppType  # for type hint clarity

    for s_thr in score_thresholds:
        for d_thr in dti_thresholds:
            def cond(a: AppType, s=s_thr, d=d_thr) -> bool:
                return (a.credit_score >= s) and (a.dti_ratio <= d)

            support, conf, _ = compute_rule_stats(
                applications,
                cond,
                target_decision,
            )

            if support < MIN_SUPPORT or conf < MIN_CONFIDENCE:
                continue

            if best is None:
                best = (s_thr, d_thr, support, conf)
            else:
                _, _, best_support, best_conf = best
                if conf > best_conf or (conf == best_conf and support > best_support):
                    best = (s_thr, d_thr, support, conf)

    return best
