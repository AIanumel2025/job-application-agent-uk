"""Build a consolidated career-matching profile from validated career data."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from src.matching_models import CareerEvidence, CareerMatchingProfile, EvidenceType


TOOL_SKILL_CATEGORIES = {
    "analytics_and_visualisation",
    "cloud",
    "databases_and_vector_stores",
    "developer_tools",
    "frameworks_and_libraries",
}


def _as_mapping(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="python")
    if isinstance(value, dict):
        return value
    return {}


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    return [value]


def _clean_text(value: Any) -> str:
    if value is None:
        return ""
    if hasattr(value, "value"):
        value = value.value
    return " ".join(str(value).split()).strip()


def _unique(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []
    for value in values:
        cleaned = _clean_text(value)
        if not cleaned:
            continue
        key = cleaned.casefold()
        if key not in seen:
            output.append(cleaned)
            seen.add(key)
    return output


def _find_section(bundle: Any, *names: str) -> Any:
    for name in names:
        if hasattr(bundle, name):
            return getattr(bundle, name)
    data = _as_mapping(bundle)
    for name in names:
        if name in data:
            return data[name]
    return None


def _iter_records(section: Any) -> list[dict[str, Any]]:
    data = _as_mapping(section)

    if isinstance(section, list):
        return [_as_mapping(item) for item in section]

    if not data:
        return []

    likely_keys = (
        "items",
        "records",
        "entries",
        "experience",
        "experiences",
        "projects",
        "certifications",
        "education",
        "achievements",
        "answers",
        "target_roles",
        "roles",
    )

    for key in likely_keys:
        if key in data and isinstance(data[key], list):
            return [_as_mapping(item) for item in data[key]]

    list_values = [value for value in data.values() if isinstance(value, list)]
    if len(list_values) == 1 and all(
        isinstance(item, dict) or hasattr(item, "model_dump")
        for item in list_values[0]
    ):
        return [_as_mapping(item) for item in list_values[0]]

    return []


def _iter_skill_records(section: Any) -> list[tuple[str, dict[str, Any]]]:
    data = _as_mapping(section)
    nested = data.get("skills")
    output: list[tuple[str, dict[str, Any]]] = []

    if isinstance(nested, dict):
        for category, records in nested.items():
            if not isinstance(records, list):
                continue
            for item in records:
                record = _as_mapping(item)
                if record:
                    output.append((str(category), record))
        return output

    return [("uncategorised", record) for record in _iter_records(section)]


def _extract_strings(record: dict[str, Any], keys: tuple[str, ...]) -> list[str]:
    output: list[str] = []
    for key in keys:
        value = record.get(key)
        if isinstance(value, str):
            output.append(value)
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, str):
                    output.append(item)
                elif isinstance(item, dict):
                    for nested_key in ("name", "title", "skill", "value"):
                        nested = item.get(nested_key)
                        if nested:
                            output.append(str(nested))
                            break
    return output


def _extract_bool(section: Any, keys: tuple[str, ...]) -> bool | None:
    data = _as_mapping(section)
    for key in keys:
        value = data.get(key)
        if isinstance(value, bool):
            return value
    return None


def _extract_scalar(section: Any, keys: tuple[str, ...]) -> Any:
    data = _as_mapping(section)
    for key in keys:
        value = data.get(key)
        if value not in (None, ""):
            return value
    return None


def _make_evidence(
    *,
    evidence_id: str,
    evidence_type: EvidenceType,
    source_record_id: str | None,
    title: str,
    description: str,
    verified: bool = False,
    approved_for_application: bool = True,
) -> CareerEvidence:
    return CareerEvidence(
        evidence_id=evidence_id,
        evidence_type=evidence_type,
        source_record_id=source_record_id,
        title=title,
        description=description,
        verified=verified,
        approved_for_application=approved_for_application,
        relevance_score=0.0,
    )


def _nested_profile_values(profile_section: Any) -> dict[str, Any]:
    profile = _as_mapping(profile_section)
    person = _as_mapping(profile.get("person"))
    career_preferences = _as_mapping(profile.get("career_preferences"))
    availability = _as_mapping(career_preferences.get("availability"))
    right_to_work = _as_mapping(career_preferences.get("right_to_work"))
    professional_identity = _as_mapping(profile.get("professional_identity"))

    return {
        "name": (
            person.get("full_name")
            or profile.get("full_name")
            or profile.get("name")
            or profile.get("candidate_name")
        ),
        "primary_role": (
            career_preferences.get("primary_role")
            or professional_identity.get("primary_title")
        ),
        "minimum_salary": (
            career_preferences.get("minimum_salary_gbp")
            or career_preferences.get("minimum_salary")
        ),
        "preferred_locations": career_preferences.get("preferred_locations"),
        "preferred_work_models": career_preferences.get("work_model"),
        "preferred_employment_types": career_preferences.get("employment_types"),
        "right_to_work_uk": right_to_work.get("authorised_to_work_in_uk"),
        "future_sponsorship_required": right_to_work.get(
            "future_sponsorship_required"
        ),
        "earliest_start_date": availability.get("earliest_start_date"),
        "driving_licence": career_preferences.get("driving_licence"),
        "willing_to_relocate": career_preferences.get("relocation"),
    }


def _nested_target_values(targets_section: Any) -> dict[str, Any]:
    targets = _as_mapping(targets_section)
    role_strategy = _as_mapping(targets.get("role_strategy"))
    location_preferences = _as_mapping(targets.get("location_preferences"))
    employment_preferences = _as_mapping(targets.get("employment_preferences"))
    sponsorship_filter = _as_mapping(targets.get("sponsorship_filter"))

    roles: list[str] = []
    primary_roles = role_strategy.get("primary_roles")
    if isinstance(primary_roles, list):
        for item in primary_roles:
            if isinstance(item, str):
                roles.append(item)
            else:
                record = _as_mapping(item)
                title = record.get("title") or record.get("name")
                if title:
                    roles.append(str(title))

    secondary_roles = role_strategy.get("secondary_roles")
    if isinstance(secondary_roles, list):
        roles.extend(str(item) for item in secondary_roles if item not in (None, ""))

    employment_types: list[str] = []
    labels = {
        "permanent": "Permanent",
        "contract": "Contract",
        "fixed_term": "Fixed-term",
        "graduate_scheme": "Graduate scheme",
        "internship": "Internship",
        "placement": "Placement",
    }
    for key, label in labels.items():
        if employment_preferences.get(key) is True:
            employment_types.append(label)

    return {
        "roles": roles,
        "minimum_salary": targets.get("minimum_salary_gbp"),
        "preferred_locations": location_preferences.get("confirmed"),
        "preferred_work_models": location_preferences.get("work_models"),
        "preferred_employment_types": employment_types,
        "willing_to_relocate": location_preferences.get("willing_to_relocate"),
        "right_to_work_uk": sponsorship_filter.get(
            "currently_authorised_to_work_in_uk"
        ),
        "future_sponsorship_required": sponsorship_filter.get(
            "future_sponsorship_required"
        ),
    }


def build_career_matching_profile(bundle: Any) -> CareerMatchingProfile:
    """Create one matching profile from validated career data."""

    profile_section = _find_section(bundle, "profile")
    skills_section = _find_section(bundle, "skills")
    experience_section = _find_section(bundle, "experience")
    projects_section = _find_section(bundle, "projects")
    certifications_section = _find_section(bundle, "certifications")
    education_section = _find_section(bundle, "education")
    achievements_section = _find_section(bundle, "achievements")
    answers_section = _find_section(bundle, "application_answers")
    targets_section = _find_section(bundle, "target_roles")

    profile_data = _as_mapping(profile_section)
    profile_nested = _nested_profile_values(profile_section)
    target_nested = _nested_target_values(targets_section)

    name = (
        profile_nested.get("name")
        or profile_data.get("full_name")
        or profile_data.get("name")
        or profile_data.get("candidate_name")
        or "Unknown candidate"
    )

    skill_records = _iter_skill_records(skills_section)
    experience_records = _iter_records(experience_section)
    project_records = _iter_records(projects_section)
    certification_records = _iter_records(certifications_section)
    education_records = _iter_records(education_section)
    achievement_records = _iter_records(achievements_section)
    answer_records = _iter_records(answers_section)
    target_records = _iter_records(targets_section)

    skills: list[str] = []
    tools: list[str] = []
    industries: list[str] = []
    certifications: list[str] = []
    education_levels: list[str] = []
    target_roles: list[str] = []
    evidence: list[CareerEvidence] = []

    for index, (category, record) in enumerate(skill_records, start=1):
        skill_values = _extract_strings(
            record, ("name", "skill", "skills", "technical_skills", "value")
        )
        explicit_tool_values = _extract_strings(
            record, ("tools", "technologies", "platforms", "libraries")
        )

        skills.extend(skill_values)
        skills.extend(explicit_tool_values)

        if category in TOOL_SKILL_CATEGORIES:
            tools.extend(skill_values)
        tools.extend(explicit_tool_values)

        title = next(iter(skill_values or explicit_tool_values), f"Skill record {index}")
        description_parts = _unique([*skill_values, *explicit_tool_values])

        evidence_level = _clean_text(record.get("evidence_level"))
        if evidence_level:
            description_parts.append(f"Evidence level: {evidence_level}")

        evidence.append(
            _make_evidence(
                evidence_id=f"skill_{index}",
                evidence_type=EvidenceType.SKILL,
                source_record_id=_clean_text(
                    record.get("skill_id") or record.get("id")
                ) or None,
                title=title,
                description="; ".join(_unique(description_parts)) or title,
                verified=bool(record.get("verified", False)),
                approved_for_application=bool(
                    record.get("approved_for_application", True)
                ),
            )
        )

    for index, record in enumerate(experience_records, start=1):
        title = _clean_text(
            record.get("job_title")
            or record.get("role")
            or record.get("title")
            or f"Experience {index}"
        )
        organisation = _clean_text(
            record.get("company")
            or record.get("organisation")
            or record.get("employer")
        )
        responsibilities = _extract_strings(
            record,
            ("responsibilities", "achievements", "highlights", "description"),
        )
        industry_values = _extract_strings(
            record, ("industry", "industries", "sector", "domain")
        )
        industries.extend(industry_values)

        description_parts = [part for part in (organisation, *responsibilities) if part]
        description = "; ".join(description_parts) or title

        evidence.append(
            _make_evidence(
                evidence_id=f"experience_{index}",
                evidence_type=EvidenceType.EXPERIENCE,
                source_record_id=_clean_text(
                    record.get("experience_id") or record.get("id")
                ) or None,
                title=title,
                description=description,
                verified=True,
            )
        )

    for index, record in enumerate(project_records, start=1):
        title = _clean_text(
            record.get("project_name")
            or record.get("name")
            or record.get("title")
            or f"Project {index}"
        )
        description = _clean_text(
            record.get("description")
            or record.get("summary")
            or record.get("overview")
            or title
        )
        project_skills = _extract_strings(
            record, ("skills", "technologies", "tools", "tech_stack")
        )
        skills.extend(project_skills)

        evidence.append(
            _make_evidence(
                evidence_id=f"project_{index}",
                evidence_type=EvidenceType.PROJECT,
                source_record_id=_clean_text(
                    record.get("project_id") or record.get("id")
                ) or None,
                title=title,
                description=description,
                verified=bool(record.get("verified", True)),
                approved_for_application=not bool(record.get("confidential", False)),
            )
        )

    for index, record in enumerate(certification_records, start=1):
        title = _clean_text(
            record.get("certification_name")
            or record.get("name")
            or record.get("title")
            or f"Certification {index}"
        )
        issuer = _clean_text(record.get("issuer") or record.get("provider"))
        certifications.append(title)

        evidence.append(
            _make_evidence(
                evidence_id=f"certification_{index}",
                evidence_type=EvidenceType.CERTIFICATION,
                source_record_id=_clean_text(
                    record.get("certification_id") or record.get("id")
                ) or None,
                title=title,
                description=" — ".join(part for part in (title, issuer) if part),
                verified=True,
            )
        )

    for index, record in enumerate(education_records, start=1):
        title = _clean_text(
            record.get("degree")
            or record.get("qualification")
            or record.get("programme")
            or record.get("title")
            or f"Education {index}"
        )
        institution = _clean_text(
            record.get("institution")
            or record.get("university")
            or record.get("school")
        )
        level = _clean_text(
            record.get("level")
            or record.get("degree_level")
            or record.get("qualification_level")
            or title
        )
        education_levels.append(level)

        evidence.append(
            _make_evidence(
                evidence_id=f"education_{index}",
                evidence_type=EvidenceType.EDUCATION,
                source_record_id=_clean_text(
                    record.get("education_id") or record.get("id")
                ) or None,
                title=title,
                description=" — ".join(part for part in (title, institution) if part),
                verified=True,
            )
        )

    for index, record in enumerate(achievement_records, start=1):
        title = _clean_text(
            record.get("statement")
            or record.get("title")
            or record.get("achievement")
            or f"Achievement {index}"
        )
        approved = bool(record.get("approved_for_application", False))
        verification_status = _clean_text(record.get("verification_status"))
        verified = verification_status in {
            "verified",
            "source_supported",
            "approved",
        }

        evidence.append(
            _make_evidence(
                evidence_id=_clean_text(
                    record.get("claim_id") or record.get("id")
                ) or f"achievement_{index}",
                evidence_type=EvidenceType.ACHIEVEMENT,
                source_record_id=_clean_text(
                    record.get("claim_id") or record.get("id")
                ) or None,
                title=title,
                description=_clean_text(record.get("recommended_wording") or title),
                verified=verified,
                approved_for_application=approved,
            )
        )

    target_roles.extend(target_nested.get("roles", []))
    if profile_nested.get("primary_role"):
        target_roles.insert(0, str(profile_nested["primary_role"]))

    for record in target_records:
        target_roles.extend(
            _extract_strings(
                record,
                ("role", "title", "name", "target_roles", "preferred_roles"),
            )
        )

    target_data = _as_mapping(targets_section)
    target_roles.extend(
        _as_list(
            target_data.get("preferred_roles")
            or target_data.get("target_roles")
            or target_data.get("roles")
        )
    )

    answer_data = _as_mapping(answers_section)
    for record in answer_records:
        key = _clean_text(
            record.get("key")
            or record.get("answer_id")
            or record.get("question_id")
        ).lower()
        value = record.get("value", record.get("answer"))
        if key:
            answer_data.setdefault(key, value)

    minimum_salary = (
        target_nested.get("minimum_salary")
        or profile_nested.get("minimum_salary")
        or _extract_scalar(
            targets_section,
            ("minimum_salary", "salary_minimum", "minimum_salary_gbp"),
        )
        or answer_data.get("minimum_salary")
        or answer_data.get("salary_expectation")
    )
    try:
        minimum_salary = int(minimum_salary) if minimum_salary is not None else None
    except (TypeError, ValueError):
        minimum_salary = None

    preferred_locations = (
        target_nested.get("preferred_locations")
        or profile_nested.get("preferred_locations")
        or target_data.get("preferred_locations")
        or answer_data.get("preferred_locations")
        or []
    )
    preferred_work_models = (
        target_nested.get("preferred_work_models")
        or profile_nested.get("preferred_work_models")
        or target_data.get("preferred_work_models")
        or target_data.get("work_models")
        or answer_data.get("preferred_work_models")
        or []
    )
    preferred_employment_types = (
        target_nested.get("preferred_employment_types")
        or profile_nested.get("preferred_employment_types")
        or target_data.get("employment_types")
        or target_data.get("preferred_employment_types")
        or answer_data.get("employment_types")
        or []
    )

    right_to_work_uk = profile_nested.get("right_to_work_uk")
    if not isinstance(right_to_work_uk, bool):
        right_to_work_uk = target_nested.get("right_to_work_uk")
    if not isinstance(right_to_work_uk, bool):
        right_to_work_uk = (
            answer_data.get("right_to_work_uk")
            if isinstance(answer_data.get("right_to_work_uk"), bool)
            else _extract_bool(
                answers_section,
                ("right_to_work_uk", "right_to_work", "uk_work_authorisation"),
            )
        )

    future_sponsorship_required = profile_nested.get(
        "future_sponsorship_required"
    )
    if not isinstance(future_sponsorship_required, bool):
        future_sponsorship_required = target_nested.get(
            "future_sponsorship_required"
        )
    if not isinstance(future_sponsorship_required, bool):
        future_sponsorship_required = (
            answer_data.get("future_sponsorship_required")
            if isinstance(answer_data.get("future_sponsorship_required"), bool)
            else _extract_bool(
                answers_section,
                ("future_sponsorship_required", "sponsorship_required"),
            )
        )

    earliest_start_date = _clean_text(
        profile_nested.get("earliest_start_date")
        or answer_data.get("earliest_start_date")
        or _extract_scalar(
            answers_section,
            ("earliest_start_date", "available_from"),
        )
    ) or None

    driving_licence_status = _clean_text(
        profile_nested.get("driving_licence")
        or answer_data.get("driving_licence")
        or answer_data.get("driving_licence_status")
        or _extract_scalar(
            answers_section,
            ("driving_licence", "driving_licence_status"),
        )
    ) or None

    willing_to_relocate = profile_nested.get("willing_to_relocate")
    if not isinstance(willing_to_relocate, bool):
        willing_to_relocate = target_nested.get("willing_to_relocate")
    if not isinstance(willing_to_relocate, bool):
        willing_to_relocate = (
            answer_data.get("willing_to_relocate")
            if isinstance(answer_data.get("willing_to_relocate"), bool)
            else _extract_bool(
                answers_section,
                ("willing_to_relocate", "relocation"),
            )
        )

    return CareerMatchingProfile(
        name=_clean_text(name),
        target_roles=_unique(str(item) for item in target_roles),
        skills=_unique(skills),
        tools=_unique(tools),
        industries=_unique(industries),
        certifications=_unique(certifications),
        education_levels=_unique(education_levels),
        years_of_experience=None,
        preferred_locations=_unique(
            _clean_text(item) for item in _as_list(preferred_locations)
        ),
        preferred_work_models=_unique(
            _clean_text(item) for item in _as_list(preferred_work_models)
        ),
        preferred_employment_types=_unique(
            _clean_text(item) for item in _as_list(preferred_employment_types)
        ),
        minimum_salary=minimum_salary,
        right_to_work_uk=right_to_work_uk,
        future_sponsorship_required=future_sponsorship_required,
        earliest_start_date=earliest_start_date,
        driving_licence_status=driving_licence_status,
        willing_to_relocate=willing_to_relocate,
        evidence=[
            item
            for item in evidence
            if item.approved_for_application
            or item.evidence_type != EvidenceType.ACHIEVEMENT
        ],
    )
