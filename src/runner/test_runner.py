import subprocess
import sys
from pathlib import Path
from typing import Tuple

from src.schemas.models import ReproductionTest, ValidationResult


class TestRunner:
    """Handles execution of tests and lint commands inside the target workspace."""

    def __init__(self, target_repo_path: str):
        self.target_repo_path = Path(target_repo_path).resolve()

    def write_reproduction_test(self, repro_test: ReproductionTest) -> Path:
        """Saves reproduction test code to target repo file path."""
        test_path = self.target_repo_path / repro_test.test_file_path
        test_path.parent.mkdir(parents=True, exist_ok=True)
        test_path.write_text(repro_test.test_code, encoding="utf-8")
        return test_path

    def run_reproduction_test(self, repro_test: ReproductionTest) -> Tuple[int, str]:
        """
        Executes reproduction test.
        Returns exit_code and stdout/stderr output.
        Safety Gate Expectation: Must return exit_code != 0 on buggy code to prove bug existence.
        """
        self.write_reproduction_test(repro_test)
        cmd = repro_test.runner_command or f"pytest {repro_test.test_file_path}"
        
        return self._run_command_in_repo(cmd)

    def run_suite_and_linter(
        self, test_cmd: str, linter_cmd: str = None, attempt_number: int = 1
    ) -> ValidationResult:
        """Runs test suite and optional linter command to validate fix."""
        repro_code, repro_out = self._run_command_in_repo(test_cmd)
        
        linter_out = ""
        linter_code = 0
        if linter_cmd:
            linter_code, linter_out = self._run_command_in_repo(linter_cmd)

        suite_passed = (repro_code == 0)
        linter_passed = (linter_code == 0)
        success = suite_passed and linter_passed

        combined_logs = f"=== Test Suite Output (exit_code={repro_code}) ===\n{repro_out}\n"
        if linter_cmd:
            combined_logs += f"\n=== Linter Output (exit_code={linter_code}) ===\n{linter_out}\n"

        return ValidationResult(
            success=success,
            attempt_number=attempt_number,
            reproduction_test_passed=suite_passed,
            suite_passed=suite_passed,
            console_output=combined_logs,
            error_log=combined_logs if not success else None,
        )

    def _run_command_in_repo(self, command: str) -> Tuple[int, str]:
        """Executes a command inside the target repo folder."""
        try:
            if command.startswith("python "):
                command = f'"{sys.executable}" ' + command[7:]
            elif command.startswith("pytest"):
                command = f'"{sys.executable}" -m pytest' + command[6:]

            res = subprocess.run(
                command,
                shell=True,
                cwd=str(self.target_repo_path),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                timeout=60,
            )
            return res.returncode, res.stdout
        except subprocess.TimeoutExpired as err:
            return -1, f"Command timed out after 60 seconds: {err}"
        except Exception as ex:
            return -1, f"Execution failed: {str(ex)}"
