"""Select the most appropriate CV references for a target vacancy.

The master template remains the structural base.
Reference CVs may contribute wording only and never override career_data facts.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from src.cv_template_loader import (
    CVRegistry,
    CVRegistryEntry,
    LoadedCVDocument,
    load_cv_document,
    load_default_master_template,
)


class CVTemplateSelectorError(RuntimeError):
    """Raised when a valid CV selection cannot be made."""


@dataclass(slots=True)
class CVSelection:
    """Resolved CV material for one application."""

    target_role_family: str
    master_template: LoadedCVDocument
    reference_cvs: list[LoadedCVDocument]
    matched_reference_keys: list[str]
    fallback_used: bool
    reasons: list[str]


ROLE_FAMILY_ALIASES: dict[str, set[str]] = {
    "ai_engineering": {
        "ai engineer",
        "artificial intelligence engineer",
        "applied ai engineer",
        "generative ai engineer",
    },
    "machine_learning_engineering": {
        "machine learning engineer",
        "ml engineer",
        "ml ops engineer",
        "mlops engineer",
    },
    "applied_ai": {
        "applied ai",
        "ai developer",
        "ai specialist",
    },
    "nlp_engineering": {
        "nlp engineer",
        "natural language processing engineer",
        "llm engineer",
    },
    "computer_vision": {
        "computer vision engineer",
        "vision engineer",
    },
    "mlops": {
        "mlops",
        "mlops engineer",
        "machine learning operations",
    },
    "data_engineering": {
        "data engineer",
        "data engineering",
        "etl engineer",
        "analytics platform engineer",
    },
    "analytics_engineering": {
        "analytics engineer",
        "analytics engineering",
    },
    "data_analytics": {
        "data analyst",
        "data analytics",
        "analytics analyst",
    },
    "data_quality": {
        "data quality analyst",
        "data quality engineer",
        "data quality",
    },
    "business_intelligence": {
        "business intelligence",
        "bi analyst",
        "power bi analyst",
    },
    "data_governance": {
        "data governance",
        "data governance analyst",
    },
    "data_science": {
        "data scientist",
        "data science",
    },
    "teaching": {
        "teacher",
        "teaching",
        "educator",
    },
    "education": {
        "education",
        "education specialist",
    },
    "tutoring": {
        "tutor",
        "tutoring",
    },
    "learning_support": {
        "learning support",
        "teaching assistant",
        "learning mentor",
    },
    "education_technology": {
        "edtech",
        "education technology",
        "learning technology",
    },
}


def _normalise(value: str) -> str:
    return " ".join(
        value.casefold()
        .replace("-", " ")
        .replace("_", " ")
        .replace("/", " ")
        .split()
    )


def infer_role_family(job_title: str) -> str:
    """Infer the best supported role family from a job title."""

    title = _normalise(job_title)

    exact_candidates: list[tuple[int, str]] = []
    partial_candidates: list[tuple[int, str]] = []

    for family, aliases in ROLE_FAMILY_ALIASES.items():
        family_text = _normalise(family)

        candidates = {
            family_text,
            *{_normalise(alias) for alias in aliases},
        }

        for candidate in candidates:
            if title == candidate:
                exact_candidates.append((len(candidate), family))
            elif candidate in title or title in candidate:
                partial_candidates.append((len(candidate), family))

    if exact_candidates:
        exact_candidates.sort(reverse=True)
        return exact_candidates[0][1]

    if partial_candidates:
        partial_candidates.sort(reverse=True)
        return partial_candidates[0][1]

    # Conservative fallback for broad but common titles.
    if "data" in title and "engineer" in title:
        return "data_engineering"

    if "machine learning" in title or title.startswith("ml "):
        return "machine_learning_engineering"

    if "ai" in title or "artificial intelligence" in title:
        return "ai_engineering"

    if "data" in title and "analyst" in title:
        return "data_analytics"

    if "teacher" in title or "tutor" in title:
        return "teaching"

    return "unknown"


def _role_match_score(
    entry: CVRegistryEntry,
    target_role_family: str,
) -> int:
    target = _normalise(target_role_family)

    score = 0
    for family in entry.role_families:
        family_n = _normalise(family)

        if family_n == target:
            score = max(score, 100)
        elif family_n in target or target in family_n:
            score = max(score, 70)

    return score


def _priority_score(entry: CVRegistryEntry) -> int:
    if entry.priority is None:
        return 0

    # Lower numeric priority means stronger preference.
    return max(0, 20 - entry.priority)


def _eligible_reference_entries(
    registry: CVRegistry,
) -> list[CVRegistryEntry]:
    return [
        entry
        for entry in registry.reference_cvs
        if entry.status.casefold() == "active"
        and entry.wording_source
        and not entry.factual_authority
    ]


def select_reference_entries(
    registry: CVRegistry,
    target_role_family: str,
    *,
    maximum_references: int | None = None,
) -> list[CVRegistryEntry]:
    """Return the best matching registered reference CV entries."""

    maximum = (
        maximum_references
        if maximum_references is not None
        else int(
            registry.selection_rules.get(
                "maximum_reference_cvs_per_application",
                2,
            )
        )
    )

    if maximum < 0:
        raise CVTemplateSelectorError(
            "maximum_references cannot be negative."
        )

    candidates: list[tuple[int, str, CVRegistryEntry]] = []

    for entry in _eligible_reference_entries(registry):
        role_score = _role_match_score(entry, target_role_family)

        if role_score <= 0:
            continue

        total_score = role_score + _priority_score(entry)
        candidates.append(
            (
                total_score,
                entry.key,
                entry,
            )
        )

    candidates.sort(
        key=lambda item: (
            item[0],
            item[1],
        ),
        reverse=True,
    )

    return [
        item[2]
        for item in candidates[:maximum]
    ]


def select_cv_material(
    registry: CVRegistry,
    *,
    job_title: str | None = None,
    target_role_family: str | None = None,
    maximum_references: int | None = None,
) -> CVSelection:
    """Select the structural master and best wording references.

    Either job_title or target_role_family must be provided.
    """

    if not target_role_family and not job_title:
        raise CVTemplateSelectorError(
            "Provide either job_title or target_role_family."
        )

    resolved_family = (
        _normalise(target_role_family)
        if target_role_family
        else infer_role_family(job_title or "")
    )

    master = load_default_master_template(registry)

    reference_entries = select_reference_entries(
        registry,
        resolved_family,
        maximum_references=maximum_references,
    )

    fallback_used = not reference_entries
    reasons: list[str] = []

    if fallback_used:
        reasons.append(
            "No active wording-reference CV matched the target role family. "
            "Use the master template with verified career_data only."
        )
    else:
        reasons.append(
            "Selected reference CVs matched the target role family and are "
            "approved as wording sources only."
        )

    references = [
        load_cv_document(registry, entry.key)
        for entry in reference_entries
    ]

    return CVSelection(
        target_role_family=resolved_family,
        master_template=master,
        reference_cvs=references,
        matched_reference_keys=[
            entry.key for entry in reference_entries
        ],
        fallback_used=fallback_used,
        reasons=reasons,
    )


def explain_selection(selection: CVSelection) -> str:
    """Return a compact human-readable summary of one CV selection."""

    references = (
        ", ".join(cv.path.name for cv in selection.reference_cvs)
        if selection.reference_cvs
        else "none"
    )

    lines = [
        f"Role family: {selection.target_role_family}",
        f"Master: {selection.master_template.path.name}",
        f"References: {references}",
        f"Fallback used: {selection.fallback_used}",
    ]

    if selection.reasons:
        lines.append("Reason: " + " ".join(selection.reasons))

    return "\n".join(lines)


def select_for_multiple_role_families(
    registry: CVRegistry,
    role_families: Iterable[str],
) -> dict[str, CVSelection]:
    """Convenience helper for inspecting several role families at once."""

    return {
        role_family: select_cv_material(
            registry,
            target_role_family=role_family,
        )
        for role_family in role_families
    }
