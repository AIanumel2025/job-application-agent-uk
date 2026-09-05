"""Load profile-driven job search preferences."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass(slots=True)
class JobSearchPreferences:
    role_terms: list[str]
    location_terms: list[str]
    preferred_seniority: list[str]
    avoided_seniority: list[str]
    employment_types: list[str]
    minimum_salary_gbp: int | None
    future_sponsorship_required: bool
    exclude_no_sponsorship_roles: bool


def _deduplicate(values: list[str]) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []

    for value in values:
        cleaned = str(value).strip()

        if not cleaned:
            continue

        key = cleaned.lower()

        if key in seen:
            continue

        seen.add(key)
        output.append(cleaned)

    return output


def load_job_search_preferences(
    repository_root: Path | None = None,
) -> JobSearchPreferences:
    """Load search preferences from career_data/target_roles.yaml."""

    root = (
        repository_root
        or Path(__file__).resolve().parents[1]
    )

    path = (
        root
        / "career_data"
        / "target_roles.yaml"
    )

    if not path.exists():
        raise FileNotFoundError(
            f"Target role configuration not found: {path}"
        )

    with path.open(
        "r",
        encoding="utf-8",
    ) as handle:
        data = yaml.safe_load(handle) or {}

    role_strategy = data.get(
        "role_strategy"
    ) or {}

    role_terms: list[str] = []

    for item in role_strategy.get(
        "primary_roles"
    ) or []:
        if isinstance(item, dict):
            title = item.get("title")

            if title:
                role_terms.append(
                    str(title)
                )

        elif isinstance(item, str):
            role_terms.append(item)

    for item in role_strategy.get(
        "secondary_roles"
    ) or []:
        if isinstance(item, dict):
            title = item.get("title")

            if title:
                role_terms.append(
                    str(title)
                )

        elif isinstance(item, str):
            role_terms.append(item)

    # Existing search_keywords are also useful discovery terms.
    for item in data.get(
        "search_keywords"
    ) or []:
        if item:
            role_terms.append(
                str(item)
            )

    location_preferences = data.get(
        "location_preferences"
    ) or {}

    location_terms = [
        str(item)
        for item in (
            location_preferences.get(
                "confirmed"
            )
            or []
        )
        if item
    ]

    seniority = data.get(
        "seniority"
    ) or {}

    preferred_seniority = [
        str(item)
        for item in (
            seniority.get(
                "preferred"
            )
            or []
        )
        if item
    ]

    avoided_seniority = [
        str(item)
        for item in (
            seniority.get(
                "avoid"
            )
            or []
        )
        if item
    ]

    employment_preferences = data.get(
        "employment_preferences"
    ) or {}

    employment_types: list[str] = []

    employment_mapping = {
        "permanent": "Permanent",
        "full_time": "Full-time",
        "internship": "Internship",
        "graduate_scheme": "Graduate",
        "contract": "Contract",
        "fixed_term": "Fixed-term",
        "placement": "Placement",
    }

    for key, label in employment_mapping.items():
        if employment_preferences.get(key) is True:
            employment_types.append(label)

    sponsorship = data.get(
        "sponsorship_filter"
    ) or {}

    return JobSearchPreferences(
        role_terms=_deduplicate(
            role_terms
        ),
        location_terms=_deduplicate(
            location_terms
        ),
        preferred_seniority=_deduplicate(
            preferred_seniority
        ),
        avoided_seniority=_deduplicate(
            avoided_seniority
        ),
        employment_types=_deduplicate(
            employment_types
        ),
        minimum_salary_gbp=data.get(
            "minimum_salary_gbp"
        ),
        future_sponsorship_required=bool(
            sponsorship.get(
                "future_sponsorship_required",
                False,
            )
        ),
        exclude_no_sponsorship_roles=bool(
            sponsorship.get(
                "exclude_roles_explicitly_stating_no_future_sponsorship",
                False,
            )
        ),
    )
