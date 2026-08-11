import os
import json
import re
from typing import Type, TypeVar, Optional
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class LLMClient:
    """
    LLM Client that queries LLM APIs (Gemini/OpenAI) or parses JSON responses into target Pydantic schemas.
    Includes robust JSON extraction and cleaning for multi-line code/diff strings.
    """

    def __init__(self, api_key: Optional[str] = None, provider: str = "gemini", model_name: str = "gemini-2.5-flash"):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY") or os.getenv("OPENAI_API_KEY")
        self.provider = provider.lower()
        self.model_name = model_name

    def generate_structured_output(self, prompt: str, schema_cls: Type[T]) -> T:
        """Sends prompt to LLM and forces response into requested Pydantic schema class."""
        if self.provider == "mock" or not self.api_key:
            # Fallback for testing without active API key or mock provider
            return self._generate_mock_output(prompt, schema_cls)

        try:
            if self.provider == "gemini":
                return self._call_gemini(prompt, schema_cls)
            elif self.provider == "openai":
                return self._call_openai(prompt, schema_cls)
            else:
                return self._call_gemini(prompt, schema_cls)
        except Exception as ex:
            print(f"[LLMClient Warning] LLM API call failed: {ex}. Falling back to clean JSON extraction.")
            raw_text = self._call_generic_completion(prompt)
            return self.extract_json_schema(raw_text, schema_cls)

    def _call_gemini(self, prompt: str, schema_cls: Type[T]) -> T:
        """Uses google-genai library if installed."""
        try:
            from google import genai
            from google.genai import types

            client = genai.Client(api_key=self.api_key)
            response = client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=schema_cls,
                ),
            )
            return schema_cls.model_validate_json(response.text)
        except ImportError:
            # Fallback if library not available
            raw_text = self._call_generic_completion(prompt)
            return self.extract_json_schema(raw_text, schema_cls)

    def _call_openai(self, prompt: str, schema_cls: Type[T]) -> T:
        """Uses OpenAI structured outputs parser."""
        try:
            import openai
            client = openai.OpenAI(api_key=self.api_key)
            completion = client.beta.chat.completions.parse(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                response_format=schema_cls,
            )
            return completion.choices[0].message.parsed
        except Exception:
            raw_text = self._call_generic_completion(prompt)
            return self.extract_json_schema(raw_text, schema_cls)

    def _call_generic_completion(self, prompt: str) -> str:
        """Generic text completion fallback."""
        return "{}"

    def extract_json_schema(self, raw_text: str, schema_cls: Type[T]) -> T:
        """Extracts JSON block from raw text and parses it with Pydantic schema."""
        cleaned = raw_text.strip()

        # Remove markdown fences if present
        json_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", cleaned, re.IGNORECASE)
        if json_match:
            cleaned = json_match.group(1).strip()

        # Parse JSON
        data = json.loads(cleaned)
        return schema_cls.model_validate(data)

    def _generate_mock_output(self, prompt: str, schema_cls: Type[T]) -> T:
        """Mock fallback for offline validation and demo testing."""
        from src.schemas.models import ReproductionTest, PatchSubmission, Diagnosis

        if schema_cls == ReproductionTest:
            return ReproductionTest(
                test_file_path="tests/test_reproduction.py",
                test_code="from sample_app import calculate\n\ndef test_calculate_bug():\n    # Expect calculate(5) to return 6 (5 + 1), currently returns 4 (5 - 1)\n    assert calculate(5) == 6\n",
                runner_command="python -m pytest tests/test_reproduction.py",
            )
        elif schema_cls == PatchSubmission:
            return PatchSubmission(
                diagnosis=Diagnosis(
                    root_cause="Fix calculation function in sample_app.py to add 1 instead of subtracting 1.",
                    suspected_files=["sample_app.py"],
                ),
                patch_diff=(
                    "diff --git a/sample_app.py b/sample_app.py\n"
                    "--- a/sample_app.py\n"
                    "+++ b/sample_app.py\n"
                    "@@ -1,4 +1,4 @@\n"
                    " def calculate(x: int) -> int:\n"
                    '     """Calculates incremented value."""\n'
                    "-    # BUG: Subtracts 1 instead of adding 1\n"
                    "-    return x - 1\n"
                    "+    # FIXED: Adds 1\n"
                    "+    return x + 1\n"
                ),
            )
        else:
            return schema_cls()
