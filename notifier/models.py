"""Normalized job posting shared by every source adapter."""

from dataclasses import dataclass, field


@dataclass
class Job:
    source: str  # e.g. "greenhouse/stripe" — must not contain ":"
    native_id: str  # the source's own ID for this posting
    company: str
    title: str
    url: str
    locations: list[str] = field(default_factory=list)
    posted_at: str | None = None  # ISO date/datetime when the source provides one

    @property
    def uid(self) -> str:
        """Globally unique ID; safe across sources because source has no ':'."""
        return f"{self.source}:{self.native_id}"
