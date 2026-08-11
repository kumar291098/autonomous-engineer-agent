import pytest
from pathlib import Path
from src.schemas.models import (
    FeatureSpecification,
    SpringBootArtifacts,
    ReactArtifacts,
    CodeFile,
)
from src.prompts.templates import (
    render_fullstack_prompt,
    render_spring_boot_prompt,
    render_react_prompt,
)
from src.runner.spring_boot_scaffolder import SpringBootScaffolder
from src.runner.react_scaffolder import ReactScaffolder


def test_fullstack_prompts():
    feature = "Create User Auth Service with React Login UI and Spring Boot REST API"
    fs_prompt = render_fullstack_prompt(feature)
    sb_prompt = render_spring_boot_prompt(feature)
    react_prompt = render_react_prompt(feature)

    assert "User Auth Service" in fs_prompt
    assert "Spring Boot 3" in fs_prompt
    assert "JUnit 5" in sb_prompt
    assert "React UI components" in react_prompt


def test_spring_boot_scaffolder(tmp_path):
    scaffolder = SpringBootScaffolder(str(tmp_path))
    artifacts = SpringBootArtifacts(
        pom_xml=CodeFile(file_path="pom.xml", content="<project></project>"),
        java_files=[
            CodeFile(
                file_path="src/main/java/com/example/App.java",
                content="package com.example; public class App {}",
            )
        ],
        test_files=[
            CodeFile(
                file_path="src/test/java/com/example/AppTest.java",
                content="package com.example; public class AppTest {}",
            )
        ],
    )

    created_paths = scaffolder.scaffold(artifacts)
    assert len(created_paths) == 3
    assert (tmp_path / "backend" / "pom.xml").exists()
    assert (tmp_path / "backend" / "src" / "main" / "java" / "com" / "example" / "App.java").exists()


def test_react_scaffolder(tmp_path):
    scaffolder = ReactScaffolder(str(tmp_path))
    artifacts = ReactArtifacts(
        package_json=CodeFile(file_path="package.json", content="{}"),
        component_files=[
            CodeFile(file_path="src/App.jsx", content="export default function App() {}")
        ],
        test_files=[
            CodeFile(file_path="src/App.test.jsx", content="test('dummy', () => {})")
        ],
    )

    created_paths = scaffolder.scaffold(artifacts)
    assert len(created_paths) == 3
    assert (tmp_path / "frontend" / "package.json").exists()
    assert (tmp_path / "frontend" / "src" / "App.jsx").exists()
