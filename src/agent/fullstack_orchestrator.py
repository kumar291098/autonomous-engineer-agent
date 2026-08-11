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


from src.runner.app_launcher import AppLauncher


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

    def generate_fullstack_app(self, run_app: bool = False, stream_callback=None) -> Dict[str, Any]:
        """Executes full-stack generation lifecycle with real-time code streaming."""
        def emit(event_type: str, message: str, file_path: str = None, code_chunk: str = None):
            print(message)
            if stream_callback:
                stream_callback({
                    "type": event_type,
                    "message": message,
                    "file_path": file_path,
                    "code_chunk": code_chunk,
                })

        emit("log", f"\n=======================================================")
        emit("log", f"[START] Full-Stack Java Spring Boot & React Generation")
        emit("log", f"=======================================================\n")
        emit("log", f"Feature Requirement: {self.feature_requirement}")

        # STEP 0: Requirement Analyzer Agent
        emit("step", "\n[STEP 0] Running Architect Requirement Analyzer Agent...")
        from src.agent.analyzer import RequirementAnalyzer
        analyzer = RequirementAnalyzer(self.llm_client)
        analysis = analyzer.analyze_requirement(self.feature_requirement)
        emit("log", f"   [ANALYSIS SUMMARY]: {analysis.summary}")
        emit("log", f"   [DYNAMIC ENTITIES]: {analysis.suggested_entities}")
        emit("log", f"   [DYNAMIC ENDPOINTS]: {analysis.suggested_endpoints}")
        if analysis.clarifying_questions:
            emit("log", f"   [CLARIFYING QUESTIONS FOR DEVELOPER]: {analysis.clarifying_questions}")

        # STEP 1: Parse Architecture Specification
        emit("step", "\n[STEP 1] Generating Architectural Specification...")
        spec_prompt = render_fullstack_prompt(self.feature_requirement)
        spec: FeatureSpecification = self.llm_client.generate_structured_output(
            spec_prompt, FeatureSpecification
        )
        emit("log", f"   [OK] Feature Title: {spec.feature_title}")
        emit("log", f"   [OK] Entities: {spec.entities}")
        emit("log", f"   [OK] REST Endpoints: {spec.api_endpoints}")
        emit("log", f"   [OK] UI Views: {spec.ui_views}")

        # STEP 2: Generate Java Spring Boot Backend & JUnit 5 Tests
        emit("step", "\n[STEP 2] Generating Java Spring Boot Backend & JUnit 5 Test Suite...")
        sb_prompt = render_spring_boot_prompt(self.feature_requirement)
        backend: SpringBootArtifacts = self.llm_client.generate_structured_output(
            sb_prompt, SpringBootArtifacts
        )
        sb_paths = self.backend_scaffolder.scaffold(backend)
        emit("log", f"   [OK] Generated {len(sb_paths)} backend files (pom.xml, Java sources, JUnit tests).")

        # Stream Java source code live
        for java_file in backend.java_files:
            emit("stream_code", f"\n▶️ [STREAMING JAVA SOURCE]: {java_file.file_path}", java_file.file_path, java_file.content)
            self._stream_code_to_console(java_file.file_path, java_file.content)

        # STEP 3: Generate React UI Frontend & Component Tests
        emit("step", "\n[STEP 3] Generating React UI Frontend & Test Suite...")
        react_prompt = render_react_prompt(self.feature_requirement)
        frontend: ReactArtifacts = self.llm_client.generate_structured_output(
            react_prompt, ReactArtifacts
        )
        react_paths = self.frontend_scaffolder.scaffold(frontend)
        emit("log", f"   [OK] Generated {len(react_paths)} frontend files (package.json, JSX components, CSS, React tests).")

        # Stream React JSX code live
        for react_file in frontend.component_files:
            emit("stream_code", f"\n▶️ [STREAMING REACT JSX]: {react_file.file_path}", react_file.file_path, react_file.content)
            self._stream_code_to_console(react_file.file_path, react_file.content)

        # STEP 4: Generate Standalone Application Metadata
        emit("step", "\n[STEP 4] Generating Standalone Application Metadata...")
        self._generate_standalone_metadata(spec)

        # STEP 5: Test Suite Validation
        emit("step", "\n[STEP 5] Running Test Suite Validation Gate...")
        sb_code, sb_log = self.backend_scaffolder.run_tests()
        react_code, react_log = self.frontend_scaffolder.run_tests()

        bundle = FullStackBundle(
            spec=spec,
            backend=backend,
            frontend=frontend,
        )

        print("\n[SUCCESS] Full-Stack Application Generated Successfully!")
        print(f"   Standalone Root Directory: {self.target_dir}")
        print(f"   Backend Path: {self.backend_scaffolder.target_dir}")
        print(f"   Frontend Path: {self.frontend_scaffolder.target_dir}")

        self._print_generated_files_tree(sb_paths + react_paths)

        if run_app:
            launcher = AppLauncher(str(self.target_dir))
            launcher.launch_local_servers()

        return {
            "status": "SUCCESS",
            "feature_title": spec.feature_title,
            "target_dir": str(self.target_dir),
            "backend_path": str(self.backend_scaffolder.target_dir),
            "frontend_path": str(self.frontend_scaffolder.target_dir),
            "backend_files_count": len(sb_paths),
            "frontend_files_count": len(react_paths),
            "backend_test_log": sb_log,
            "frontend_test_log": react_log,
            "bundle": bundle,
        }

    def _stream_code_to_console(self, filepath: str, content: str):
        """Streams generated code to console with live line-by-line typing effect."""
        import sys, time
        print("-------------------------------------------------------")
        lines = content.splitlines()
        preview = lines[:20]
        for line in preview:
            sys.stdout.write(f"   {line}\n")
            sys.stdout.flush()
            time.sleep(0.01)
        if len(lines) > 20:
            print(f"   ... ({len(lines) - 20} more lines generated)")
        print("-------------------------------------------------------")

    def _print_generated_files_tree(self, all_paths: list):
        """Prints formatted list of all generated files."""
        print("\n[FILES] GENERATED FILE TREE & ARTIFACTS:")
        print("-------------------------------------------------------")
        for p in all_paths:
            try:
                rel = p.relative_to(self.target_dir)
                size_kb = round(p.stat().st_size / 1024, 2)
                print(f"   [FILE] {rel} ({size_kb} KB)")
            except Exception:
                print(f"   [FILE] {p.name}")
        print("-------------------------------------------------------")

    def _generate_standalone_metadata(self, spec: FeatureSpecification):
        """Generates standalone README.md and docker-compose.yml for the generated application."""
        # 1. Standalone README.md
        readme_path = self.target_dir / "README.md"
        readme_content = f"""# 🚀 {spec.feature_title}

{spec.summary}

This is a **standalone, fully decoupled Full-Stack Application** generated independently of the AI Agent.

---

## 🏗️ Project Architecture

* **Backend (`/backend`)**: Java Spring Boot 3 REST API (Maven, JPA, H2/PostgreSQL)
* **Frontend (`/frontend`)**: Modern React UI (NPM, JSX/TSX, CSS, API Client)

---

## ⚡ Quick Start & How to Run

### 1. Run Java Spring Boot Backend
```bash
cd backend
mvn spring-boot:run
```
Backend runs at `http://localhost:8080` (H2 Console: `http://localhost:8080/h2-console`)

### 2. Run React UI Frontend
```bash
cd frontend
npm install
npm start
```
Frontend runs at `http://localhost:3000`

### 3. Run Backend & Frontend Tests
```bash
# Backend JUnit 5 tests
cd backend && mvn test

# Frontend React tests
cd frontend && npm test
```

---

## 🐳 Docker Deployment
Run backend and frontend containers together:
```bash
docker-compose up --build
```
"""
        readme_path.write_text(readme_content, encoding="utf-8")

        # 2. Standalone docker-compose.yml
        compose_path = self.target_dir / "docker-compose.yml"
        compose_content = f"""version: '3.8'

services:
  backend:
    build: ./backend
    ports:
      - "8080:8080"
    environment:
      - SPRING_PROFILES_ACTIVE=prod

  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    depends_on:
      - backend
"""
        compose_path.write_text(compose_content, encoding="utf-8")

    def export_as_zip(self, zip_destination: str) -> str:
        """Packages the standalone application directory into a clean .zip archive."""
        import shutil
        zip_path = Path(zip_destination).resolve()
        archive_base = zip_path.with_suffix("")
        output_filename = shutil.make_archive(
            base_name=str(archive_base),
            format="zip",
            root_dir=str(self.target_dir),
        )
        return output_filename

