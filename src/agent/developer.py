"""
Developer Agent: Writes Java Spring Boot 3 backend code and React 18 frontend components.
"""
from src.agent.llm_client import LLMClient
from src.schemas.models import FeatureSpecification, SpringBootArtifacts, ReactArtifacts
from src.prompts.templates import render_spring_boot_prompt, render_react_prompt


class DeveloperAgent:
    """Specialized Developer Agent for Backend & Frontend Code Construction."""

    def __init__(self, llm_client: LLMClient):
        self.llm_client = llm_client

    def build_backend(self, spec: FeatureSpecification) -> SpringBootArtifacts:
        """Constructs Spring Boot backend Java sources and POM configuration."""
        prompt = render_spring_boot_prompt(f"{spec.feature_title}: {spec.summary}")
        return self.llm_client.generate_structured_output(prompt, SpringBootArtifacts)

    def build_frontend(self, spec: FeatureSpecification) -> ReactArtifacts:
        """Constructs React 18 frontend JSX components and CSS stylesheets."""
        prompt = render_react_prompt(f"{spec.feature_title}: {spec.summary}")
        return self.llm_client.generate_structured_output(prompt, ReactArtifacts)
