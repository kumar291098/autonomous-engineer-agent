import pytest
from src.schemas.models import IssueTicket, Diagnosis, PatchSubmission, ReproductionTest


def test_issue_ticket_model():
    issue = IssueTicket(
        title="Fix NPE",
        description="Null pointer exception when user is null",
        target_repo_path="/tmp/repo",
    )
    assert issue.title == "Fix NPE"
    assert issue.stack_trace == ""


def test_patch_submission_model():
    diag = Diagnosis(root_cause="Missing null check", suspected_files=["user_service.py"])
    patch = PatchSubmission(
        diagnosis=diag,
        patch_diff="diff --git a/user_service.py b/user_service.py",
    )
    assert patch.diagnosis.root_cause == "Missing null check"
    assert "user_service.py" in patch.diagnosis.suspected_files
