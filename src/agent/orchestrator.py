import time
from typing import Dict, Any

from src.schemas.models import (
    IssueTicket,
    RepoContext,
    ReproductionTest,
    PatchSubmission,
    ValidationResult,
)
from src.prompts.templates import (
    render_master_prompt,
    render_phase_3_injection,
    render_phase_4_injection,
    render_phase_5_retry_injection,
)
from src.runner.repo_inspector import RepoInspector
from src.runner.test_runner import TestRunner
from src.runner.patch_applier import PatchApplier
from src.agent.llm_client import LLMClient


class OrchestratorEngine:
    """
    Core Orchestrator driving the Senior Software Engineer Agent through the 5-phase execution loop.
    """

    def __init__(
        self,
        issue: IssueTicket,
        llm_client: LLMClient,
        max_retries: int = 3,
    ):
        self.issue = issue
        self.llm_client = llm_client
        self.max_retries = max_retries
        self.target_repo_path = issue.target_repo_path

        self.inspector = RepoInspector(self.target_repo_path)
        self.test_runner = TestRunner(self.target_repo_path)
        self.patch_applier = PatchApplier(self.target_repo_path)

        self.repo_context: RepoContext = None
        self.formatted_context_str: str = ""

    def run_pipeline(self) -> Dict[str, Any]:
        """Executes the full automated bug resolution pipeline."""
        print(f"\n=======================================================")
        print(f"[START] Starting Autonomous Agent Pipeline for Issue: {self.issue.title}")
        print(f"=======================================================\n")

        # PHASE 1 & 2: Context Gathering & Environment Initialization
        print("[PHASE 1 & 2] Gathering Repo Context & Checking Environment...")
        self.repo_context = self.inspector.inspect()
        self.formatted_context_str = self.inspector.format_repo_context_string(self.repo_context)
        print(f"   [OK] Discovered {len(self.repo_context.file_tree)} files.")
        print(f"   [OK] Build System: {self.repo_context.build_system} | Test Framework: {self.repo_context.test_framework}")

        # PHASE 3: Reproduction Safety Gate
        print("\n[PHASE 3] Reproduction (The Safety Gate)...")
        repro_prompt = render_master_prompt(
            issue_title=self.issue.title,
            issue_description=self.issue.description,
            stack_trace=self.issue.stack_trace,
            repo_context=self.formatted_context_str,
            phase_injection=render_phase_3_injection(self.repo_context.test_framework),
        )

        repro_test: ReproductionTest = self.llm_client.generate_structured_output(
            repro_prompt, ReproductionTest
        )
        print(f"   [OK] Generated Reproduction Test: {repro_test.test_file_path}")

        print("   Running reproduction test against buggy codebase...")
        exit_code, test_out = self.test_runner.run_reproduction_test(repro_test)

        if exit_code == 0:
            print("   [FAIL] Safety Gate FAILED: Reproduction test PASSED on buggy codebase! (Must fail to prove bug).")
            return {
                "status": "FAILED_SAFETY_GATE",
                "reason": "Reproduction test passed on buggy codebase.",
                "test_output": test_out,
            }

        print(f"   [OK] Safety Gate PASSED: Test FAILED as expected (exit_code={exit_code}). Bug reproduced!")

        # PHASE 4: Diagnose and Patch (Attempt 1)
        print("\n[PHASE 4] Diagnose and Patch (Attempt 1)...")
        phase_4_prompt = render_master_prompt(
            issue_title=self.issue.title,
            issue_description=self.issue.description,
            stack_trace=self.issue.stack_trace,
            repo_context=self.formatted_context_str,
            phase_injection=render_phase_4_injection(test_failed_output=test_out),
        )

        patch_submission: PatchSubmission = self.llm_client.generate_structured_output(
            phase_4_prompt, PatchSubmission
        )
        print(f"   [OK] Root Cause Diagnosis: {patch_submission.diagnosis.root_cause}")
        print(f"   [OK] Suspected Files: {patch_submission.diagnosis.suspected_files}")

        # PHASE 5: Validation Loop
        print("\n[PHASE 5] Applying Patch & Running Validation Loop...")
        for attempt in range(1, self.max_retries + 1):
            print(f"\n--- Validation Attempt {attempt}/{self.max_retries} ---")
            
            applied, apply_log = self.patch_applier.apply_patch(patch_submission.patch_diff)
            if not applied:
                print(f"   [FAIL] Patch application failed: {apply_log}")
                failure_log = f"Git apply failed: {apply_log}"
            else:
                print(f"   [OK] Patch applied cleanly to workspace.")
                validation_res: ValidationResult = self.test_runner.run_suite_and_linter(
                    test_cmd=self.repo_context.test_command,
                    linter_cmd=self.repo_context.linter_command,
                    attempt_number=attempt,
                )

                if validation_res.success:
                    print("   [SUCCESS] Patch passed all tests and linters!")
                    return {
                        "status": "SUCCESS",
                        "diagnosis": patch_submission.diagnosis.model_dump(),
                        "patch_diff": patch_submission.patch_diff,
                        "attempts_used": attempt,
                        "console_output": validation_res.console_output,
                    }

                print(f"   [FAIL] Validation failed on attempt {attempt}.")
                failure_log = validation_res.error_log or validation_res.console_output

            # If failed, revert patch before next attempt
            self.patch_applier.revert_patch()

            if attempt < self.max_retries:
                print("   [RETRY] Triggering Validation Retry Loop with failure logs...")
                retry_prompt = render_master_prompt(
                    issue_title=self.issue.title,
                    issue_description=self.issue.description,
                    stack_trace=self.issue.stack_trace,
                    repo_context=self.formatted_context_str,
                    phase_injection=render_phase_5_retry_injection(
                        attempt_number=attempt + 1,
                        previous_failure_log=failure_log,
                    ),
                )
                patch_submission = self.llm_client.generate_structured_output(
                    retry_prompt, PatchSubmission
                )

        print("\n[FAIL] PIPELINE FAILED: Reached max retry attempts without resolving issue.")
        return {
            "status": "FAILED_VALIDATION",
            "reason": f"Exceeded max retries ({self.max_retries}).",
            "last_error_log": failure_log,
        }
