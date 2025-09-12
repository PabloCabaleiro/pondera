import pytest
from pydantic import ValidationError

from pondera.models.run import RunResult


class TestRunResult:
    """Tests for RunResult model."""

    def test_minimal_run_result(self) -> None:
        result = RunResult(question="What is 2+2?")
        assert result.question == "What is 2+2?"
        assert result.answer == ""
        assert result.artifacts == []
        assert result.files == []
        assert result.metadata == {}

    def test_full_run_result(self) -> None:
        result = RunResult(
            question="Analyze the data",
            answer="# Analysis Results\n\nThe data shows...",
            artifacts=["chart.png", "report.pdf"],
            files=["chart.png"],
            metadata={
                "execution_time": 5.2,
                "model_used": "gpt-4",
                "tokens_used": 150,
                "cost": 0.003,
            },
        )
        assert result.question == "Analyze the data"
        assert result.answer == "# Analysis Results\n\nThe data shows..."
        assert result.artifacts == ["chart.png", "report.pdf"]
        assert result.files == ["chart.png"]
        assert result.metadata["execution_time"] == 5.2
        assert result.metadata["model_used"] == "gpt-4"
        assert result.metadata["tokens_used"] == 150
        assert result.metadata["cost"] == 0.003

    def test_complex_metadata(self) -> None:
        result = RunResult(
            question="Complex task",
            metadata={
                "steps": ["step1", "step2", "step3"],
                "tool_usage": {"calculator": 3, "web_search": 1, "code_runner": 2},
                "nested": {"level1": {"level2": ["a", "b", "c"]}},
                "timestamp": "2024-01-01T12:00:00Z",
                "success": True,
            },
        )
        assert result.metadata["steps"] == ["step1", "step2", "step3"]
        assert result.metadata["tool_usage"]["calculator"] == 3
        assert result.metadata["nested"]["level1"]["level2"] == ["a", "b", "c"]
        assert result.metadata["timestamp"] == "2024-01-01T12:00:00Z"
        assert result.metadata["success"] is True

    def test_missing_question_fails(self) -> None:
        with pytest.raises(ValidationError) as exc_info:
            RunResult()  # missing required question
        assert "Field required" in str(exc_info.value)

    def test_empty_question_allowed(self) -> None:
        result = RunResult(question="")
        assert result.question == ""

    def test_artifacts_with_paths(self) -> None:
        result = RunResult(
            question="Generate files",
            artifacts=[
                "/absolute/path/file.txt",
                "relative/path/file.csv",
                "./current/dir/file.json",
                "../parent/dir/file.xml",
            ],
            files=["/absolute/path/file.txt"],
        )
        assert len(result.artifacts) == 4
        assert "/absolute/path/file.txt" in result.artifacts
        assert result.files == ["/absolute/path/file.txt"]
        assert "relative/path/file.csv" in result.artifacts
        assert "./current/dir/file.json" in result.artifacts
        assert "../parent/dir/file.xml" in result.artifacts

    def test_markdown_formatting(self) -> None:
        markdown_content = """# Title

## Subtitle

- Bullet point 1
- Bullet point 2

```python
print("Hello, World!")
```

**Bold text** and *italic text*.

[Link](https://example.com)

| Column 1 | Column 2 |
|----------|----------|
| Value 1  | Value 2  |
"""
        result = RunResult(question="Format this nicely", answer=markdown_content)
        assert result.answer == markdown_content
        assert "# Title" in result.answer
        assert "```python" in result.answer
        assert "**Bold text**" in result.answer

    def test_extra_fields_forbidden(self) -> None:
        with pytest.raises(ValidationError) as exc_info:
            RunResult(
                question="test",
                extra_field="not allowed",  # extra field should trigger validation error
            )
        assert "Extra inputs are not permitted" in str(exc_info.value)
