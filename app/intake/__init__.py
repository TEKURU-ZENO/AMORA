"""AMORA Intake Module: Zero-Scraping Onboarding.

Provides:
1. Psychological & Behavioral Archetype Profiling Engine (Life, Work, Future, & Attachment)
2. AI Intake Interview ('3-Minute Coffee with Your Agent')
3. LinkedIn PDF & Resume Ingestion Parser
"""
from .interview import INTAKE_QUESTIONS, synthesize_interview_persona
from .pdf_parser import parse_linkedin_pdf, parse_linkedin_pdf_text
from .psychology import (
    ARCHETYPES,
    ATTACHMENT_STYLES,
    CONFLICT_STYLES,
    PSYCHOLOGICAL_ASSESSMENT_SECTIONS,
    classify_archetype,
    infer_attachment_style,
    infer_conflict_style,
    synthesize_psychological_persona,
)

__all__ = [
    "ARCHETYPES",
    "ATTACHMENT_STYLES",
    "CONFLICT_STYLES",
    "PSYCHOLOGICAL_ASSESSMENT_SECTIONS",
    "INTAKE_QUESTIONS",
    "classify_archetype",
    "infer_attachment_style",
    "infer_conflict_style",
    "synthesize_psychological_persona",
    "synthesize_interview_persona",
    "parse_linkedin_pdf",
    "parse_linkedin_pdf_text",
]
