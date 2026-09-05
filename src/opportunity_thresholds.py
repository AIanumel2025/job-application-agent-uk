"""Thresholds for classifying job opportunities."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class OpportunityThresholds:
    high_quality_ats: float = 85.0
    high_quality_interview_fit: float = 85.0
    high_quality_must_have: float = 80.0
    required_claim_integrity: float = 100.0

    best_ats: float = 92.0
    best_interview_fit: float = 90.0
    best_must_have: float = 90.0


DEFAULT_THRESHOLDS = OpportunityThresholds()
