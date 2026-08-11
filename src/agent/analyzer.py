"""
Requirement Analyzer Agent for Full-Stack Java & React Application Specifications.
Analyzes user inputs, detects ambiguities, and structures dynamic feature specs.
"""
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from src.agent.llm_client import LLMClient


class RequirementAnalysisResult(BaseModel):
    is_clear: bool = Field(description="True if requirement is sufficiently clear for code generation")
    summary: str = Field(description="High-level architectural summary of requested application")
    suggested_entities: List[str] = Field(description="Dynamically identified domain model entities")
    suggested_endpoints: List[str] = Field(description="Dynamically identified REST API endpoints")
    clarifying_questions: Optional[List[str]] = Field(default=[], description="Questions for developer if prompt is ambiguous")


class RequirementAnalyzer:
    """Agent that dynamically analyzes developer input prompts without any hardcoded templates."""

    def __init__(self, llm_client: LLMClient):
        self.llm_client = llm_client

    def analyze_requirement(self, feature_prompt: str) -> RequirementAnalysisResult:
        """Analyzes natural language prompt dynamically via LLM."""
        prompt = (
            "You are a Senior Software Architect Agent.\n"
            "Analyze the following software requirement from a developer:\n\n"
            f"REQUIREMENT: \"{feature_prompt}\"\n\n"
            "Determine if the requirement is clear. Extract key domain entities and REST API endpoints.\n"
            "If the requirement is ambiguous or missing key details, list clarifying questions."
        )
        return self.llm_client.generate_structured_output(prompt, RequirementAnalysisResult)
