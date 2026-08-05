"""Load and validate Phase 1 YAML career data.

The loader performs four jobs:

1. Locate the repository root.
2. Confirm every required YAML file exists.
3. Parse YAML safely.
4. Validate each parsed document with the Pydantic models in ``src.models``.

Cross-file business rules, privacy checks, and reporting are handled by later
Phase 2 modules.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, TypeVar

import yaml
from pydantic import BaseModel, ValidationError

from src.models import (
    AchievementsFile,
    ApplicationAnswersFile,
    ArticleLinksFile,
    CareerDataBundle,
    CertificationIndexFile,
    CertificationsFile,
    EducationFile,
    ExperienceFile,
    ProfileFile,
    ProfileLinksFile,
    ProjectLinksFile,
    ProjectsFile,
    SkillsFile,
    TargetRolesFile,
)


ModelT = TypeVar("ModelT", bound=BaseModel)


class CareerDataLoadError(RuntimeError):
    """Raised when career data cannot be located, parsed, or validated."""


@dataclass(frozen=True)
class FileDefinition:
    """Maps a logical career-data name to its file path and model."""

    relative_path: Path
    model: type[BaseModel]


REQUIRED_FILES: dict[str, FileDefinition] = {
    "profile": FileDefinition(
        Path("career_data/profile.yaml"),
        ProfileFile,
    ),
    "experience": FileDefinition(
        Path("career_data/experience.yaml"),
        ExperienceFile,
    ),
    "projects": FileDefinition(
        Path("career_data/projects.yaml"),
        ProjectsFile,
    ),
    "education": FileDefinition(
        Path("career_data/education.yaml"),
        EducationFile,
    ),
    "certifications": FileDefinition(
        Path("career_data/certifications.yaml"),
        CertificationsFile,
    ),
    "skills": FileDefinition(
        Path("career_data/skills.yaml"),
        SkillsFile,
    ),
    "achievements": FileDefinition(
        Path("career_data/achievements.yaml"),
        AchievementsFile,
    ),
    "application_answers": FileDefinition(
        Path("career_data/application_answers.yaml"),
        ApplicationAnswersFile,
    ),
    "target_roles": FileDefinition(
        Path("career_data/target_roles.yaml"),
        TargetRolesFile,
    ),
    "profile_links": FileDefinition(
        Path("source_documents/profile_links.yaml"),
        ProfileLinksFile,
    ),
    "project_links": FileDefinition(
        Path("source_documents/project_links.yaml"),
        ProjectLinksFile,
    ),
    "article_links": FileDefinition(
        Path("source_documents/article_links.yaml"),
        ArticleLinksFile,
    ),
    "certification_index": FileDefinition(
        Path("source_documents/certification_index.yaml"),
        CertificationIndexFile,
    ),
}


def find_repository_root(start: Path | None = None) -> Path:
    """Find the repository root by searching upward from ``start``.

    A valid project root must contain both ``career_data`` and
    ``source_documents`` directories.

    Parameters
    ----------
    start:
        Starting file or directory. Defaults to the current working directory.

    Returns
    -------
    pathlib.Path
        Absolute path to the repository root.

    Raises
    ------
    CareerDataLoadError
        If no valid root can be found.
    """

    candidate = (start or Path.cwd()).expanduser().resolve()

    if candidate.is_file():
        candidate = candidate.parent

    locations = [candidate, *candidate.parents]

    for location in locations:
        if (
            (location / "career_data").is_dir()
            and (location / "source_documents").is_dir()
        ):
            return location

    raise CareerDataLoadError(
        "Could not locate the repository root. Expected to find both "
        "'career_data/' and 'source_documents/' in the current directory "
        "or one of its parent directories."
    )


def check_required_files(repository_root: Path) -> dict[str, Path]:
    """Return resolved required paths or raise one grouped missing-file error."""

    resolved_paths = {
        name: repository_root / definition.relative_path
        for name, definition in REQUIRED_FILES.items()
    }

    missing = [
        path.relative_to(repository_root)
        for path in resolved_paths.values()
        if not path.is_file()
    ]

    if missing:
        formatted = "\n".join(f"  - {path}" for path in missing)
        raise CareerDataLoadError(
            "Required career-data files are missing:\n"
            f"{formatted}\n"
            "Restore or create these files before running the loader."
        )

    return resolved_paths


def read_yaml_file(path: Path) -> dict[str, Any]:
    """Read one YAML document and return its top-level mapping."""

    try:
        raw_text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise CareerDataLoadError(
            f"Could not read YAML file '{path}': {exc}"
        ) from exc

    try:
        parsed = yaml.safe_load(raw_text)
    except yaml.YAMLError as exc:
        location = ""

        problem_mark = getattr(exc, "problem_mark", None)
        if problem_mark is not None:
            location = (
                f" at line {problem_mark.line + 1}, "
                f"column {problem_mark.column + 1}"
            )

        problem = getattr(exc, "problem", None)
        detail = f": {problem}" if problem else ""

        raise CareerDataLoadError(
            f"Malformed YAML in '{path}'{location}{detail}"
        ) from exc

    if parsed is None:
        raise CareerDataLoadError(f"YAML file '{path}' is empty.")

    if not isinstance(parsed, dict):
        raise CareerDataLoadError(
            f"YAML file '{path}' must contain a top-level mapping, "
            f"not {type(parsed).__name__}."
        )

    return parsed


def validate_document(
    path: Path,
    raw_data: dict[str, Any],
    model: type[ModelT],
) -> ModelT:
    """Validate one parsed YAML document against a Pydantic model."""

    try:
        return model.model_validate(raw_data)
    except ValidationError as exc:
        formatted_errors: list[str] = []

        for error in exc.errors():
            field_path = ".".join(str(part) for part in error["loc"])
            message = error["msg"]
            formatted_errors.append(
                f"  - {field_path or '<document>'}: {message}"
            )

        details = "\n".join(formatted_errors)

        raise CareerDataLoadError(
            f"Validation failed for '{path}':\n{details}"
        ) from exc


def load_document(
    repository_root: Path,
    definition: FileDefinition,
) -> BaseModel:
    """Read and validate one required YAML document."""

    path = repository_root / definition.relative_path
    raw_data = read_yaml_file(path)

    return validate_document(
        path=path,
        raw_data=raw_data,
        model=definition.model,
    )


def load_career_data(
    repository_root: Path | str | None = None,
) -> CareerDataBundle:
    """Load all required Phase 1 YAML files.

    Parameters
    ----------
    repository_root:
        Optional explicit repository root. If omitted, the loader searches
        upward from the current working directory.

    Returns
    -------
    CareerDataBundle
        A single validated object containing all 13 YAML documents.

    Raises
    ------
    CareerDataLoadError
        If the project root cannot be found, a file is missing, YAML is
        malformed, or Pydantic validation fails.
    """

    if repository_root is None:
        root = find_repository_root()
    else:
        root = Path(repository_root).expanduser().resolve()

        if not root.is_dir():
            raise CareerDataLoadError(
                f"Repository root does not exist or is not a directory: {root}"
            )

        if not (root / "career_data").is_dir():
            raise CareerDataLoadError(
                f"Missing required directory: {root / 'career_data'}"
            )

        if not (root / "source_documents").is_dir():
            raise CareerDataLoadError(
                f"Missing required directory: {root / 'source_documents'}"
            )

    check_required_files(root)

    loaded = {
        name: load_document(root, definition)
        for name, definition in REQUIRED_FILES.items()
    }

    return CareerDataBundle.model_validate(loaded)


def get_loaded_file_summary(bundle: CareerDataBundle) -> dict[str, int]:
    """Return basic record counts for logging and later reports."""

    return {
        "yaml_files": len(REQUIRED_FILES),
        "experience_records": len(bundle.experience.experience),
        "projects": len(bundle.projects.projects),
        "education_records": len(bundle.education.education),
        "certifications": len(bundle.certifications.certifications),
        "achievement_claims": len(bundle.achievements.claims),
        "articles": len(bundle.article_links.articles),
        "project_links": len(bundle.project_links.projects),
    }
