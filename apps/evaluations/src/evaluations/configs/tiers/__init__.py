"""Evaluation tier configurations."""

from evaluations.configs.base import TierConfig, TierName
from evaluations.configs.tiers.full import full_tier
from evaluations.configs.tiers.smoke import smoke_tier
from evaluations.configs.tiers.standard import standard_tier

ALL_TIERS: dict[TierName, TierConfig] = {
    TierName.SMOKE: smoke_tier,
    TierName.STANDARD: standard_tier,
    TierName.FULL: full_tier,
}


def get_tier(name: TierName) -> TierConfig:
    """Get a tier configuration by name."""
    return ALL_TIERS[name]


def list_tiers() -> list[TierConfig]:
    """List all tier configurations."""
    return list(ALL_TIERS.values())


__all__ = [  # noqa: RUF022
    "smoke_tier",
    "standard_tier",
    "full_tier",
    "ALL_TIERS",
    "get_tier",
    "list_tiers",
]
