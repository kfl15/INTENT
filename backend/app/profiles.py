"""Business profiles define which intents are trusted for a domain."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BusinessTypeProfile:
    business_type: str
    allowed_intents: frozenset[str]
    platform_intents: frozenset[str]

    @property
    def all_intents(self) -> frozenset[str]:
        return self.allowed_intents | self.platform_intents


EDTECH_PROFILE = BusinessTypeProfile(
    business_type="edtech",
    allowed_intents=frozenset(
        {
            "course_list",
            "course_details",
            "course_pricing_payment",
            "course_projects",
            "course_schedule_duration",
            "career_certificate_outcomes",
            "prerequisite_fit",
            "beginner_friendliness",
            "background_fit",
            "career_guidance",
            "demo_trial_counseling",
            "enrollment_admission",
            "student_support_redirect",
            "instructor_info",
            "recording_access",
            "missed_class_recovery",
        }
    ),
    platform_intents=frozenset({"neutral", "irrelevant", "unknown"}),
)

PROFILES: dict[str, BusinessTypeProfile] = {
    EDTECH_PROFILE.business_type: EDTECH_PROFILE,
}


def resolve_profile(business_type: str = "edtech") -> BusinessTypeProfile:
    """Resolve the active profile. Unknown domains fall back to EdTech for v1."""

    return PROFILES.get(business_type, EDTECH_PROFILE)
