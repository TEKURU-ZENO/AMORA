"""Core data models. Everything an agent knows about a person flows through these."""
from __future__ import annotations

from typing import Literal, Optional
from pydantic import BaseModel, Field


# ---------- Raw sources (the ONLY two inputs) ----------

class LinkedInExperience(BaseModel):
    title: str = ""
    company: str = ""
    duration: str = ""
    description: str = ""


class LinkedInData(BaseModel):
    url: str
    full_name: str = ""
    headline: str = ""
    about: str = ""
    location: str = ""
    experience: list[LinkedInExperience] = []
    education: list[str] = []
    skills: list[str] = []
    volunteering: list[str] = []
    languages: list[str] = []


class InstagramPost(BaseModel):
    caption: str = ""
    hashtags: list[str] = []
    location: str = ""
    kind: str = "image"  # image | video | carousel


class InstagramData(BaseModel):
    url: str
    username: str = ""
    full_name: str = ""
    bio: str = ""
    is_private: bool = False
    external_url: str = ""  # the link in their bio, used to verify a LinkedIn cross-link
    followers: int = 0
    following: int = 0
    posts: list[InstagramPost] = []


class SourceBundle(BaseModel):
    linkedin: LinkedInData
    instagram: InstagramData


# ---------- Agent analysis (what the profile page shows) ----------

class Evidence(BaseModel):
    claim: str
    source: Literal["linkedin", "instagram"]
    snippet: str


class Analysis(BaseModel):
    display_name: str
    one_liner: str
    summary: str
    needs: list[str] = Field(description="What this person needs from a partner / relationship")
    hobbies: list[str]
    interests: list[str]
    values: list[str]
    personality: list[str]
    lifestyle: dict[str, str] = Field(default_factory=dict, description="pace, social energy, schedule, travel ...")
    communication_style: str
    green_flags: list[str]
    dealbreakers: list[str]
    ideal_date: str
    conversation_starters: list[str]
    evidence: list[Evidence]
    confidence: float = Field(ge=0, le=1)
    engine_used: str = "offline"
    fallback_occurred: bool = False
    fallback_reason: Optional[str] = None
    validation_warnings: list[str] = []



# ---------- Dating ----------

class Turn(BaseModel):
    speaker: str  # person id
    text: str
    thought: str = ""  # private inner monologue of the agent (shown in replay)
    observation: str = ""  # running read / deduction about the other person this turn


class Verdict(BaseModel):
    agent_for: str
    score: float = Field(ge=0, le=10)
    chemistry: float = Field(ge=0, le=10)
    needs_met: float = Field(ge=0, le=10)
    values_alignment: float = Field(ge=0, le=10)
    dealbreaker_hit: bool = False
    second_date: bool
    reasons: list[str]
    report_to_human: str
    learned_about_other: list[str] = Field(default_factory=list, description="Key insights discovered about the date during conversation")


class StressTurn(BaseModel):
    speaker: str  # person id
    text: str
    thought: str = ""
    emotional_tone: str = "open"  # empathetic, defensive, conciliatory, firm, collaborative, curious, guarded


class StressVerdict(BaseModel):
    agent_for: str
    resilience_score: float = Field(ge=0, le=10)
    resolution_style: str
    stress_verdict: Literal["passed", "conditional", "failed"]
    key_takeaway: str
    growth_potential: str


class FirstFightRecord(BaseModel):
    id: str
    date_id: str
    a: str
    b: str
    scenario_title: str
    scenario_prompt: str
    turns: list[StressTurn] = []
    verdict_a: StressVerdict
    verdict_b: StressVerdict
    mutual_resilience: float
    outcome: Literal["stronger_together", "navigable_compromise", "irreconcilable_friction"]
    engine: str = "offline"


class SecondDatePlan(BaseModel):
    id: str
    date_id: str
    activity: str
    venue_name: str
    location_idea: str
    day_and_time: str
    budget_tier: str  # $, $$, $$$
    vibe: str
    plan_notes: str
    drafted_intro_for_a: str  # Personalized first DM for Human A to send
    drafted_intro_for_b: str  # Personalized first DM for Human B to send
    agreed: bool = True


class HonestyAuditItem(BaseModel):
    speaker: str
    claim_made: str
    status: Literal["grounded", "embellished", "ungrounded"]
    source_evidence: str
    explanation: str


class HonestyAudit(BaseModel):
    id: str
    date_id: str
    grounding_score_a: float  # 0 to 100
    grounding_score_b: float  # 0 to 100
    overall_grounding: float  # 0 to 100
    flags_a: list[str] = Field(default_factory=list)
    flags_b: list[str] = Field(default_factory=list)
    verified_claims: list[str] = Field(default_factory=list)
    audit_summary: str = ""
    items: list[HonestyAuditItem] = Field(default_factory=list)


class GroupTurn(BaseModel):
    speaker: str
    text: str
    thought: str = ""
    target: Optional[str] = None  # who the remark is addressed to or None for group


class GroupDateRecord(BaseModel):
    id: str
    participants: list[str]  # 3-4 participant IDs
    activity: str
    venue: str
    turns: list[GroupTurn] = Field(default_factory=list)
    group_chemistry: float = 0.0  # 0 to 10
    social_observations: dict[str, list[str]] = Field(default_factory=dict)
    takeaways: list[str] = Field(default_factory=list)
    engine: str = "offline"


class DateRecord(BaseModel):
    id: str
    a: str
    b: str
    venue: str
    venue_reason: str
    turns: list[Turn]
    verdict_a: Verdict
    verdict_b: Verdict
    mutual: float
    engine: str
    stage: Literal["speed", "dinner", "standard"] = "standard"
    observations_a: list[str] = Field(default_factory=list, description="What agent A deduced about B")
    observations_b: list[str] = Field(default_factory=list, description="What agent B deduced about A")
    first_fight: Optional[FirstFightRecord] = None
    second_date_plan: Optional[SecondDatePlan] = None
    honesty_audit: Optional[HonestyAudit] = None


class Person(BaseModel):
    id: str
    linkedin_url: str
    instagram_url: str
    consent: bool
    status: Literal["pending", "scraped", "analyzed", "error"] = "pending"
    error: Optional[str] = None
    sources: Optional[SourceBundle] = None
    analysis: Optional[Analysis] = None
    reading_log: list[str] = []  # the agent's step-by-step reading trace
    warnings: list[str] = []  # partial failures, e.g. one source could not be read
    synthetic: bool = False  # a fictional demo persona (demo mode only); never a scraped person
    coaching_notes: list[str] = Field(default_factory=list, description="Pre-date instructions from human to agent")
    dating_learnings: list[str] = Field(default_factory=list, description="Cross-date insights learned by agent across rounds")
    feedback_history: list[dict] = Field(default_factory=list, description="History of post-date user corrections and brief updates")
