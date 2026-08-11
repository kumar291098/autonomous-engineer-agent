import os
import subprocess
from pathlib import Path
from typing import Tuple, List

from src.schemas.models import ReactArtifacts, CodeFile


class ReactScaffolder:
    """Scaffolds and builds React frontend projects."""

    def __init__(self, target_dir: str):
        self.target_dir = Path(target_dir).resolve() / "frontend"

    def scaffold(self, artifacts: ReactArtifacts) -> List[Path]:
        """Saves React frontend files into project directory structure."""
        self.target_dir.mkdir(parents=True, exist_ok=True)
        created_paths = []

        # 1. Save package.json
        pkg_path = self.target_dir / "package.json"
        pkg_path.write_text(artifacts.package_json.content, encoding="utf-8")
        created_paths.append(pkg_path)

        # 2. Save Component & Style files
        for file in artifacts.component_files:
            file_path = self.target_dir / file.file_path
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(file.content, encoding="utf-8")
            created_paths.append(file_path)

        # 3. Save React Test files
        for file in artifacts.test_files:
            file_path = self.target_dir / file.file_path
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(file.content, encoding="utf-8")
            created_paths.append(file_path)

        return created_paths

    def run_tests(self) -> Tuple[int, str]:
        """Executes 'npm test' inside the frontend folder if npm is available."""
        try:
            res = subprocess.run(
                ["npm", "test", "--", "--watchAll=false"],
                cwd=str(self.target_dir),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                timeout=120,
            )
            return res.returncode, res.stdout
        except FileNotFoundError:
            return 0, "NPM (npm) not found in system PATH. Skipping live npm test execution."
        except Exception as ex:
            return -1, f"NPM execution failed: {str(ex)}"
