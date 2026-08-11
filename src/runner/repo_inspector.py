import os
import glob
from pathlib import Path
from typing import List, Dict, Tuple, Optional

from src.schemas.models import RepoContext


class RepoInspector:
    """Inspects target workspace to extract directory structures, build configs, and source files."""

    MAX_FILE_SIZE_BYTES = 50000  # 50KB limit per file context injection

    def __init__(self, target_repo_path: str):
        self.target_repo_path = Path(target_repo_path).resolve()

    def inspect(self) -> RepoContext:
        """Inspects the repository and returns a populated RepoContext."""
        if not self.target_repo_path.exists():
            raise FileNotFoundError(f"Repository directory does not exist: {self.target_repo_path}")

        file_tree = self._build_file_tree()
        build_system, test_framework, test_cmd, lint_cmd = self._detect_environment()
        key_files_content = self._read_key_source_files(file_tree)

        return RepoContext(
            repo_name=self.target_repo_path.name,
            file_tree=file_tree,
            build_system=build_system,
            test_framework=test_framework,
            test_command=test_cmd,
            linter_command=lint_cmd,
            key_files_content=key_files_content,
        )

    def _build_file_tree(self) -> List[str]:
        """Generates relative file tree ignoring hidden/git/venv directories."""
        ignored_dirs = {".git", ".venv", "venv", "__pycache__", "node_modules", "target", "build", ".idea"}
        relative_paths = []

        for root, dirs, files in os.walk(self.target_repo_path):
            dirs[:] = [d for d in dirs if d not in ignored_dirs and not d.startswith(".")]
            for file in files:
                if file.startswith("."):
                    continue
                full_path = Path(root) / file
                rel_path = str(full_path.relative_to(self.target_repo_path)).replace("\\", "/")
                relative_paths.append(rel_path)

        return sorted(relative_paths)

    def _detect_environment(self) -> Tuple[str, str, str, Optional[str]]:
        """Detects build tool, test runner, test command, and linter command."""
        repo_files = {Path(p).name for p in self._build_file_tree()}

        if "pytest.ini" in repo_files or "conftest.py" in repo_files or any(f.endswith(".py") for f in repo_files):
            return "python", "pytest", "python -m pytest", None
        elif "pom.xml" in repo_files:
            return "maven", "junit", "mvn test", "mvn checkstyle:check"
        elif "package.json" in repo_files:
            return "npm", "jest", "npm test", "npm run lint"
        
        return "unknown", "pytest", "pytest", None

    def _read_key_source_files(self, file_tree: List[str]) -> Dict[str, str]:
        """Reads content of non-binary source files up to size limits."""
        key_extensions = {".py", ".java", ".js", ".ts", ".json", ".xml", ".yaml", ".yml", ".md"}
        contents = {}

        for rel_path in file_tree:
            ext = os.path.splitext(rel_path)[1].lower()
            if ext in key_extensions:
                full_path = self.target_repo_path / rel_path
                try:
                    if full_path.stat().st_size <= self.MAX_FILE_SIZE_BYTES:
                        contents[rel_path] = full_path.read_text(encoding="utf-8", errors="replace")
                except Exception:
                    pass

        return contents

    def format_repo_context_string(self, repo_context: RepoContext) -> str:
        """Formats RepoContext into a structured text string for prompt injection."""
        lines = []
        lines.append(f"Repository Name: {repo_context.repo_name}")
        lines.append(f"Build System: {repo_context.build_system}")
        lines.append(f"Test Framework: {repo_context.test_framework}")
        lines.append(f"Test Command: {repo_context.test_command}")
        lines.append(f"Linter Command: {repo_context.linter_command or 'None'}")
        lines.append("\n--- Directory File Tree ---")
        lines.extend(repo_context.file_tree[:100])  # limit top 100 files

        lines.append("\n--- Source Files Content ---")
        for file_path, content in repo_context.key_files_content.items():
            lines.append(f"\n[FILE: {file_path}]")
            lines.append("```")
            lines.append(content)
            lines.append("```")

        return "\n".join(lines)
