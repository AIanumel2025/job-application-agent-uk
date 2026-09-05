"""Load configured public job-discovery sources."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

@dataclass(slots=True)
class SmartRecruitersCompany:
    """One configured SmartRecruiters employer."""

    identifier: str
    company: str | None = None
    enabled: bool = True

@dataclass(slots=True)
class WorkableSite:
    """One configured public Workable careers site."""

    url: str
    company: str | None = None
    enabled: bool = True

@dataclass(slots=True)
class LeverSite:
    """One configured Lever employer site."""

    token: str
    company: str | None = None
    enabled: bool = True
    
@dataclass(slots=True)
class GreenhouseBoard:
    """One configured Greenhouse employer board."""

    token: str
    company: str | None = None
    enabled: bool = True

@dataclass(slots=True)
class AshbyBoard:
    """One configured Ashby employer board."""

    token: str
    company: str | None = None
    enabled: bool = True

def load_greenhouse_boards(
    repository_root: Path | None = None,
) -> list[GreenhouseBoard]:
    """Load enabled Greenhouse boards from config/job_sources.yaml."""

    root = (
        repository_root
        or Path(__file__).resolve().parents[1]
    )

    config_path = (
        root
        / "config"
        / "job_sources.yaml"
    )

    if not config_path.exists():
        return []

    with config_path.open(
        "r",
        encoding="utf-8",
    ) as handle:
        data = yaml.safe_load(handle) or {}

    discovery = data.get(
    "discovery",
    {},
    )
    
    greenhouse = discovery.get(
    "greenhouse",
    {},
    )

    if not greenhouse.get(
        "enabled",
        True,
    ):
        return []

    boards_data = greenhouse.get(
        "boards",
        [],
    )

    boards: list[GreenhouseBoard] = []

    for item in boards_data:
        if not isinstance(item, dict):
            continue

        token = str(
            item.get("token") or ""
        ).strip()

        if not token:
            continue

        enabled = bool(
            item.get(
                "enabled",
                True,
            )
        )

        if not enabled:
            continue

        company = str(
            item.get("company") or ""
        ).strip() or None

        boards.append(
            GreenhouseBoard(
                token=token,
                company=company,
                enabled=True,
            )
        )

    return boards


def load_greenhouse_board_tokens(
    repository_root: Path | None = None,
) -> list[str]:
    """Return enabled Greenhouse board tokens."""

    return [
        board.token
        for board in load_greenhouse_boards(
            repository_root
        )
    ]

def load_lever_sites(
    repository_root: Path | None = None,
) -> list[LeverSite]:
    """Load enabled Lever sites from config/job_sources.yaml."""

    root = (
        repository_root
        or Path(__file__).resolve().parents[1]
    )

    config_path = (
        root
        / "config"
        / "job_sources.yaml"
    )

    if not config_path.exists():
        return []

    with config_path.open(
        "r",
        encoding="utf-8",
    ) as handle:
        data = yaml.safe_load(handle) or {}

    discovery = data.get(
    "discovery"
    ) or {}

    lever = discovery.get(
    "lever"
    ) or {}

    if not lever.get(
        "enabled",
        True,
    ):
        return []

    sites_data = lever.get(
        "sites",
        [],
    )

    sites: list[LeverSite] = []

    for item in sites_data:
        if isinstance(item, str):
            token = item.strip()

            if token:
                sites.append(
                    LeverSite(
                        token=token,
                    )
                )

            continue

        if not isinstance(item, dict):
            continue

        token = str(
            item.get("token")
            or item.get("site")
            or ""
        ).strip()

        if not token:
            continue

        if not bool(
            item.get(
                "enabled",
                True,
            )
        ):
            continue

        company = (
            str(
                item.get("company")
                or ""
            ).strip()
            or None
        )

        sites.append(
            LeverSite(
                token=token,
                company=company,
                enabled=True,
            )
        )

    return sites
def load_lever_site_tokens(
    repository_root: Path | None = None,
) -> list[str]:
    """Return enabled Lever site tokens."""

    return [
        site.token
        for site in load_lever_sites(
            repository_root
        )
    ]

def load_ashby_boards(
    repository_root: Path | None = None,
) -> list[AshbyBoard]:
    """Load enabled Ashby boards from config/job_sources.yaml."""

    root = (
        repository_root
        or Path(__file__).resolve().parents[1]
    )

    config_path = (
        root
        / "config"
        / "job_sources.yaml"
    )

    if not config_path.exists():
        return []

    with config_path.open(
        "r",
        encoding="utf-8",
    ) as handle:
        data = yaml.safe_load(handle) or {}

    discovery = data.get("discovery") or {}
    ashby = discovery.get("ashby") or {}

    if not ashby.get("enabled", True):
        return []

    boards_data = ashby.get("boards") or []

    boards: list[AshbyBoard] = []

    for item in boards_data:
        if isinstance(item, str):
            token = item.strip()

            if token:
                boards.append(
                    AshbyBoard(
                        token=token,
                    )
                )

            continue

        if not isinstance(item, dict):
            continue

        token = str(
            item.get("token")
            or item.get("board")
            or ""
        ).strip()

        if not token:
            continue

        if not bool(
            item.get("enabled", True)
        ):
            continue

        company = (
            str(
                item.get("company")
                or ""
            ).strip()
            or None
        )

        boards.append(
            AshbyBoard(
                token=token,
                company=company,
                enabled=True,
            )
        )

    return boards


def load_ashby_board_tokens(
    repository_root: Path | None = None,
) -> list[str]:
    """Return enabled Ashby board tokens."""

    return [
        board.token
        for board in load_ashby_boards(
            repository_root
        )
    ]

def load_workable_sites(
    repository_root: Path | None = None,
) -> list[WorkableSite]:
    """Load enabled Workable sites from config/job_sources.yaml."""

    root = (
        repository_root
        or Path(__file__).resolve().parents[1]
    )

    config_path = (
        root
        / "config"
        / "job_sources.yaml"
    )

    if not config_path.exists():
        return []

    with config_path.open(
        "r",
        encoding="utf-8",
    ) as handle:
        data = yaml.safe_load(handle) or {}

    discovery = data.get("discovery") or {}
    workable = discovery.get("workable") or {}

    if not workable.get("enabled", True):
        return []

    sites_data = workable.get("sites") or []

    sites: list[WorkableSite] = []

    for item in sites_data:
        if isinstance(item, str):
            url = item.strip()

            if url:
                sites.append(
                    WorkableSite(
                        url=url,
                    )
                )

            continue

        if not isinstance(item, dict):
            continue

        url = str(
            item.get("url")
            or item.get("site")
            or ""
        ).strip()

        if not url:
            continue

        if not bool(
            item.get("enabled", True)
        ):
            continue

        company = (
            str(
                item.get("company")
                or ""
            ).strip()
            or None
        )

        sites.append(
            WorkableSite(
                url=url,
                company=company,
                enabled=True,
            )
        )

    return sites


def load_workable_site_urls(
    repository_root: Path | None = None,
) -> list[str]:
    """Return enabled Workable careers-page URLs."""

    return [
        site.url
        for site in load_workable_sites(
            repository_root
        )
    ]

def load_smartrecruiters_companies(
    repository_root: Path | None = None,
) -> list[SmartRecruitersCompany]:
    """Load enabled SmartRecruiters companies from config/job_sources.yaml."""

    root = (
        repository_root
        or Path(__file__).resolve().parents[1]
    )

    config_path = (
        root
        / "config"
        / "job_sources.yaml"
    )

    if not config_path.exists():
        return []

    with config_path.open(
        "r",
        encoding="utf-8",
    ) as handle:
        data = yaml.safe_load(handle) or {}

    discovery = data.get("discovery") or {}
    smartrecruiters = discovery.get("smartrecruiters") or {}

    if not smartrecruiters.get("enabled", True):
        return []

    companies_data = smartrecruiters.get("companies") or []

    companies: list[SmartRecruitersCompany] = []

    for item in companies_data:
        if isinstance(item, str):
            identifier = item.strip()

            if identifier:
                companies.append(
                    SmartRecruitersCompany(
                        identifier=identifier,
                    )
                )

            continue

        if not isinstance(item, dict):
            continue

        identifier = str(
            item.get("identifier")
            or item.get("company_identifier")
            or item.get("token")
            or ""
        ).strip()

        if not identifier:
            continue

        if not bool(
            item.get("enabled", True)
        ):
            continue

        company = (
            str(
                item.get("company")
                or ""
            ).strip()
            or None
        )

        companies.append(
            SmartRecruitersCompany(
                identifier=identifier,
                company=company,
                enabled=True,
            )
        )

    return companies


def load_smartrecruiters_company_identifiers(
    repository_root: Path | None = None,
) -> list[str]:
    """Return enabled SmartRecruiters company identifiers."""

    return [
        company.identifier
        for company in load_smartrecruiters_companies(
            repository_root
        )
    ]
