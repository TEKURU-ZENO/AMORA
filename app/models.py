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


# ---------- Dating ----------

class Turn(BaseModel):
    speaker: str  # person id
    text: str
    thought: str = ""  # private inner monologue of the agent (shown in replay)


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


class Person(BaseModel):
    id: str
    linkedin_url: str
    instagram_url: str
    consent: bool
    synthetic: bool = False
    status: Literal["pending", "scraped", "analyzed", "error"] = "pending"
    error: Optional[str] = None
    sources: Optional[SourceBundle] = None
    analysis: Optional[Analysis] = None
    reading_log: list[str] = []  # the agent's step-by-step reading trace
    warnings: list[str] = []  # partial failures, e.g. one source could not be read
