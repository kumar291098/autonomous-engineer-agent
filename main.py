import argparse
import sys
import os
from pathlib import Path

# Ensure src module is in Python path
sys.path.insert(0, str(Path(__file__).parent.resolve()))

from src.schemas.models import IssueTicket
from src.agent.llm_client import LLMClient
from src.agent.orchestrator import OrchestratorEngine
from src.agent.fullstack_orchestrator import FullStackOrchestrator


def parse_args():
    parser = argparse.ArgumentParser(description="Autonomous Senior Software Engineer Agent Pipeline")
    parser.add_argument("--mode", type=str, default="bugfix", choices=["bugfix", "fullstack"], help="Agent mode: bugfix or fullstack")
    parser.add_argument("--feature", type=str, default="Order Management Service with React UI Dashboard and Java Spring Boot REST API", help="Feature requirement for fullstack mode")
    parser.add_argument("--repo", type=str, default="./demo_repo", help="Path to target repository")
    parser.add_argument("--issue-title", type=str, default="Calculation Return Value Bug", help="Title of bug ticket")
    parser.add_argument("--issue-desc", type=str, default="The calculate function returns x - 1 instead of x + 1", help="Bug description")
    parser.add_argument("--stack-trace", type=str, default="", help="Optional stack trace")
    parser.add_argument("--provider", type=str, default="mock", choices=["gemini", "openai", "mock"], help="LLM Provider")
    parser.add_argument("--max-retries", type=int, default=3, help="Max validation retries")
    return parser.parse_args()


def main():
    args = parse_args()

    repo_path = Path(args.repo).resolve()
    if not repo_path.exists():
        repo_path.mkdir(parents=True, exist_ok=True)

    llm_client = LLMClient(provider=args.provider)

    if args.mode == "fullstack":
        fullstack_orchestrator = FullStackOrchestrator(
            feature_requirement=args.feature,
            target_dir=str(repo_path),
            llm_client=llm_client,
        )
        result = fullstack_orchestrator.generate_fullstack_app()
        print("\n=======================================================")
        print(f"[RESULT] Full-Stack Generation Result: {result.get('status')}")
        print("=======================================================")
        print(f"Backend Target: {result['backend_path']} ({result['backend_files_count']} files)")
        print(f"Frontend Target: {result['frontend_path']} ({result['frontend_files_count']} files)")

    else:
        issue = IssueTicket(
            title=args.issue_title,
            description=args.issue_desc,
            stack_trace=args.stack_trace,
            target_repo_path=str(repo_path),
        )

        orchestrator = OrchestratorEngine(issue=issue, llm_client=llm_client, max_retries=args.max_retries)
        result = orchestrator.run_pipeline()

        print("\n=======================================================")
        print(f"[RESULT] Pipeline Execution Result: {result.get('status')}")
        print("=======================================================")
        if result.get("status") == "SUCCESS":
            print(f"Diagnosis Root Cause: {result['diagnosis']['root_cause']}")
            print(f"Patch Diff:\n{result['patch_diff']}")
        else:
            print(f"Failure Reason: {result.get('reason')}")


if __name__ == "__main__":
    main()
