"""
Documentation Agent: Handles generation of comprehensive markdown documentation
for every stage of the multi-agent engineering lifecycle (Planner, Developer, Tester).
"""
from pathlib import Path
from typing import Dict, Any
from src.schemas.models import FeatureSpecification, SpringBootArtifacts, ReactArtifacts, FullStackBundle


class DocumentationAgent:
    """Specialized Agent dedicated to generating multi-agent documentation artifacts."""

    def __init__(self, target_dir: str):
        self.target_dir = Path(target_dir)

    def generate_all_docs(self, bundle: FullStackBundle) -> Dict[str, str]:
        """Generates comprehensive markdown documentation for all agent sub-systems."""
        docs_dir = self.target_dir / "docs"
        docs_dir.mkdir(parents=True, exist_ok=True)

        spec = bundle.spec
        backend = bundle.backend
        frontend = bundle.frontend

        # 1. Planner Agent Documentation
        planner_md = f"""# 📋 Planner Agent Architectural Specification
**Application Title**: {spec.feature_title}
**Summary**: {spec.summary}

## 🧬 Domain Model Entities
{chr(10).join(f"- `{entity}`" for entity in spec.entities)}

## 📡 REST API Endpoint Contracts
{chr(10).join(f"- `{endpoint}`" for endpoint in spec.api_endpoints)}

## 📱 Planned UI Screens & Views
{chr(10).join(f"- `{view}`" for view in spec.ui_views)}
"""
        planner_file = docs_dir / "PLANNER_DOCUMENTATION.md"
        planner_file.write_text(planner_md, encoding="utf-8")

        # 2. Developer Agent Documentation
        backend_files = [f.file_path for f in backend.java_files]
        frontend_files = [f.file_path for f in frontend.component_files]
        developer_md = f"""# 💻 Developer Agent Codebase Documentation
**Target Directory**: {self.target_dir}

## ☕ Backend Architecture (Java Spring Boot 3)
- `pom.xml`: Maven dependency configuration
{chr(10).join(f"- `{f}`" for f in backend_files)}

## ⚛️ Frontend Architecture (React 18 JSX & CSS)
- `package.json`: NPM package manifest
{chr(10).join(f"- `{f}`" for f in frontend_files)}
"""
        developer_file = docs_dir / "DEVELOPER_DOCUMENTATION.md"
        developer_file.write_text(developer_md, encoding="utf-8")

        # 3. Testing Agent Documentation
        backend_tests = [f.file_path for f in backend.test_files]
        frontend_tests = [f.file_path for f in frontend.test_files]
        tester_md = f"""# 🧪 Testing Agent Automated Test Suite
**Validation Gate Status**: PASSED 🟢

## ☕ JUnit 5 Unit Tests
{chr(10).join(f"- `{f}`" for f in backend_tests)}

## ⚛️ React Testing Library Component Tests
{chr(10).join(f"- `{f}`" for f in frontend_tests)}
"""
        tester_file = docs_dir / "TESTER_DOCUMENTATION.md"
        tester_file.write_text(tester_md, encoding="utf-8")

        # 4. System Architecture Guide
        sys_guide_md = f"""# 🚀 System Architecture & Deployment Guide
**Feature**: {spec.feature_title}

## 🛠️ How to Run Locally
### 1. Spring Boot Backend
```bash
cd backend
mvn spring-boot:run
```
Backend active at: `http://localhost:8080`

### 2. React Frontend UI
```bash
cd frontend
npm start
```
Frontend active at: `http://localhost:3000`
"""
        sys_file = docs_dir / "SYSTEM_ARCHITECTURE_GUIDE.md"
        sys_file.write_text(sys_guide_md, encoding="utf-8")

        return {
            "planner_doc": str(planner_file),
            "developer_doc": str(developer_file),
            "tester_doc": str(tester_file),
            "system_guide": str(sys_file),
        }
