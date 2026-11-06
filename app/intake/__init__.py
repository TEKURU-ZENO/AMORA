"""AMORA Intake Module: Zero-Scraping Onboarding.

Provides:
1. AI Intake Interview ('3-Minute Coffee with Your Agent')
2. LinkedIn PDF & Resume Ingestion Parser
"""
from .interview import INTAKE_QUESTIONS, synthesize_interview_persona
from .pdf_parser import parse_linkedin_pdf, parse_linkedin_pdf_text

__all__ = [
    "INTAKE_QUESTIONS",
    "synthesize_interview_persona",
    "parse_linkedin_pdf",
    "parse_linkedin_pdf_text",
]
