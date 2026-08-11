import subprocess
import re
from pathlib import Path
from typing import Tuple


class PatchApplier:
    """Applies unified git diff patches onto the target repository."""

    def __init__(self, target_repo_path: str):
        self.target_repo_path = Path(target_repo_path).resolve()

    def apply_patch(self, patch_diff: str) -> Tuple[bool, str]:
        """
        Applies a unified diff patch to the repository.
        Returns (success: bool, log_message: str).
        """
        if not patch_diff or not patch_diff.strip():
            return False, "Patch diff is empty."

        patch_file = self.target_repo_path / "patch.diff"
        patch_file.write_text(patch_diff, encoding="utf-8")

        # Attempt 1: git apply --whitespace=fix patch.diff
        try:
            res = subprocess.run(
                ["git", "apply", "--whitespace=fix", "patch.diff"],
                cwd=str(self.target_repo_path),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                timeout=30,
            )
            if res.returncode == 0:
                return True, "Patch applied successfully via git apply."
            
            # Attempt 2: git apply --ignore-space-change --ignore-whitespace patch.diff
            res2 = subprocess.run(
                ["git", "apply", "--ignore-space-change", "--ignore-whitespace", "patch.diff"],
                cwd=str(self.target_repo_path),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                timeout=30,
            )
            if res2.returncode == 0:
                return True, "Patch applied successfully with relaxed whitespace."
            
            # Fallback: Parse diff chunks and modify target files directly
            fallback_success, fallback_log = self._fallback_patch_apply(patch_diff)
            if fallback_success:
                return True, fallback_log

            return False, f"git apply failed:\n{res.stdout}\n{res2.stdout}\nFallback error: {fallback_log}"

        except Exception as ex:
            return False, f"Patch application failed with exception: {str(ex)}"

    def revert_patch(self) -> Tuple[bool, str]:
        """Reverts all unstaged/staged git changes in target repo."""
        try:
            res = subprocess.run(
                ["git", "checkout", "."],
                cwd=str(self.target_repo_path),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )
            res2 = subprocess.run(
                ["git", "clean", "-fd"],
                cwd=str(self.target_repo_path),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )
            return res.returncode == 0, f"{res.stdout}\n{res2.stdout}"
        except Exception as ex:
            return False, str(ex)

    def _fallback_patch_apply(self, patch_diff: str) -> Tuple[bool, str]:
        """Simple line-matching fallback applier for basic diffs."""
        try:
            file_diffs = patch_diff.split("diff --git ")
            applied_files = 0

            for block in file_diffs:
                if not block.strip():
                    continue

                lines = block.splitlines()
                target_file_rel = None

                for line in lines:
                    if line.startswith("+++ b/"):
                        target_file_rel = line[6:].strip()
                        break

                if not target_file_rel:
                    continue

                target_file = self.target_repo_path / target_file_rel
                if not target_file.exists():
                    continue

                content = target_file.read_text(encoding="utf-8")
                content_lf = content.replace("\r\n", "\n")
                
                # Extract simple replacements
                removals = [l[1:] for l in lines if l.startswith("-") and not l.startswith("---")]
                additions = [l[1:] for l in lines if l.startswith("+") and not l.startswith("+++")]

                if removals:
                    target_chunk = "\n".join(removals)
                    replacement_chunk = "\n".join(additions)
                    if target_chunk in content_lf:
                        new_content = content_lf.replace(target_chunk, replacement_chunk, 1)
                        target_file.write_text(new_content, encoding="utf-8", newline="\n")
                        applied_files += 1

            if applied_files > 0:
                return True, f"Fallback patch applied {applied_files} files."
            return False, "Fallback matching found no exact chunk matches."

        except Exception as ex:
            return False, f"Fallback applier exception: {str(ex)}"
