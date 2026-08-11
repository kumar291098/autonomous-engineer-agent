import os
from pathlib import Path
from typing import Dict, Any

from src.schemas.models import (
    FeatureSpecification,
    SpringBootArtifacts,
    ReactArtifacts,
    FullStackBundle,
)
from src.prompts.templates import (
    render_fullstack_prompt,
    render_spring_boot_prompt,
    render_react_prompt,
)
from src.runner.spring_boot_scaffolder import SpringBootScaffolder
from src.runner.react_scaffolder import ReactScaffolder
from src.agent.llm_client import LLMClient


class FullStackOrchestrator:
    """Orchestrates natural language feature requirements into Java Spring Boot + React + Test suites."""

    def __init__(
        self,
        feature_requirement: str,
        target_dir: str,
        llm_client: LLMClient,
    ):
        self.feature_requirement = feature_requirement
        self.target_dir = Path(target_dir).resolve()
        self.llm_client = llm_client

        self.backend_scaffolder = SpringBootScaffolder(str(self.target_dir))
        self.frontend_scaffolder = ReactScaffolder(str(self.target_dir))

    def generate_fullstack_app(self) -> Dict[str, Any]:
        """Executes full-stack generation lifecycle."""
        print(f"\n=======================================================")
        print(f"[START] Full-Stack Java Spring Boot & React Generation")
        print(f"=======================================================\n")
        print(f"Feature Requirement: {self.feature_requirement}")

        # STEP 1: Parse Architecture Specification
        print("\n[STEP 1] Generating Architectural Specification...")
        spec_prompt = render_fullstack_prompt(self.feature_requirement)
        spec: FeatureSpecification = self.llm_client.generate_structured_output(
            spec_prompt, FeatureSpecification
        )
        print(f"   [OK] Feature Title: {spec.feature_title}")
        print(f"   [OK] Entities: {spec.entities}")
        print(f"   [OK] REST Endpoints: {spec.api_endpoints}")
        print(f"   [OK] UI Views: {spec.ui_views}")

        # STEP 2: Generate Java Spring Boot Backend & JUnit 5 Tests
        print("\n[STEP 2] Generating Java Spring Boot Backend & JUnit 5 Test Suite...")
        sb_prompt = render_spring_boot_prompt(self.feature_requirement)
        backend: SpringBootArtifacts = self.llm_client.generate_structured_output(
            sb_prompt, SpringBootArtifacts
        )
        sb_paths = self.backend_scaffolder.scaffold(backend)
        print(f"   [OK] Generated {len(sb_paths)} backend files (pom.xml, Java sources, JUnit tests).")

        # STEP 3: Generate React UI Frontend & Component Tests
        print("\n[STEP 3] Generating React UI Frontend & Test Suite...")
        react_prompt = render_react_prompt(self.feature_requirement)
        frontend: ReactArtifacts = self.llm_client.generate_structured_output(
            react_prompt, ReactArtifacts
        )
        react_paths = self.frontend_scaffolder.scaffold(frontend)
        print(f"   [OK] Generated {len(react_paths)} frontend files (package.json, JSX components, CSS, React tests).")

        # STEP 4: Test Suite Validation
        print("\n[STEP 4] Running Test Suite Validation Gate...")
        sb_code, sb_log = self.backend_scaffolder.run_tests()
        react_code, react_log = self.frontend_scaffolder.run_tests()

        bundle = FullStackBundle(
            spec=spec,
            backend=backend,
            frontend=frontend,
        )

        print("\n[SUCCESS] Full-Stack Application Generated Successfully!")
        print(f"   Backend Target: {self.backend_scaffolder.target_dir}")
        print(f"   Frontend Target: {self.frontend_scaffolder.target_dir}")

        return {
            "status": "SUCCESS",
            "feature_title": spec.feature_title,
            "backend_path": str(self.backend_scaffolder.target_dir),
            "frontend_path": str(self.frontend_scaffolder.target_dir),
            "backend_files_count": len(sb_paths),
            "frontend_files_count": len(react_paths),
            "backend_test_log": sb_log,
            "frontend_test_log": react_log,
            "bundle": bundle,
        }
