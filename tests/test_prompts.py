from src.prompts.templates import (
    render_master_prompt,
    render_phase_3_injection,
    render_phase_4_injection,
    render_phase_5_retry_injection,
)


def test_render_master_prompt():
    prompt = render_master_prompt(
        issue_title="Bug Title",
        issue_description="Bug Desc",
        stack_trace="Traceback...",
        repo_context="Repo files info",
        phase_injection="PHASE 3 TEST INJECTION",
    )
    assert "Bug Title" in prompt
    assert "Bug Desc" in prompt
    assert "PHASE 3 TEST INJECTION" in prompt
    assert "# SYSTEM IDENTITY" in prompt


def test_phase_injections():
    p3 = render_phase_3_injection("pytest")
    assert "Reproduction (The Safety Gate)" in p3
    assert "pytest" in p3

    p4 = render_phase_4_injection("FAILED with 1 error")
    assert "FAILED with 1 error" in p4

    p5 = render_phase_5_retry_injection(2, "Assertion error log")
    assert "Retry Attempt 2" in p5
    assert "Assertion error log" in p5
