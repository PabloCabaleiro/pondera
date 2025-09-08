"""Tests for pondera.runner.custom_runner_template module."""

import pytest
from unittest.mock import AsyncMock
from typing import Any

from pondera.runner.custom_runner_template import my_runner
from pondera.models.run import RunResult


class TestMyRunner:
    """Test the my_runner example implementation."""

    @pytest.mark.asyncio
    async def test_my_runner_minimal(self) -> None:
        """Test my_runner with minimal parameters."""
        question = "What is the meaning of life?"

        result = await my_runner(question=question)

        assert isinstance(result, RunResult)
        assert result.question == question
        assert "# Answer" in result.answer_markdown
        assert f"Question: **{question}**" in result.answer_markdown
        assert result.artifacts == []
        assert result.metadata == {"steps": 1}

    @pytest.mark.asyncio
    async def test_my_runner_with_attachments(self) -> None:
        """Test my_runner with attachments."""
        question = "Analyze these files"
        attachments = ["file1.txt", "file2.pdf"]

        result = await my_runner(question=question, attachments=attachments)

        assert isinstance(result, RunResult)
        assert result.question == question
        assert "# Answer" in result.answer_markdown

    @pytest.mark.asyncio
    async def test_my_runner_with_params(self) -> None:
        """Test my_runner with parameters."""
        question = "Generate code"
        params = {"language": "python", "style": "functional"}

        result = await my_runner(question=question, params=params)

        assert isinstance(result, RunResult)
        assert result.question == question
        assert "language" in result.answer_markdown
        assert "functional" in result.answer_markdown
        assert result.metadata == {"steps": 1}

    @pytest.mark.asyncio
    async def test_my_runner_with_progress_callback(self) -> None:
        """Test my_runner with progress callback."""
        question = "Process with progress"
        progress_callback = AsyncMock()

        result = await my_runner(question=question, progress=progress_callback)

        assert isinstance(result, RunResult)
        assert result.question == question

        # Should have called progress twice
        assert progress_callback.call_count == 2
        progress_callback.assert_any_call("runner: starting…")
        progress_callback.assert_any_call("runner: preparing result…")

    @pytest.mark.asyncio
    async def test_my_runner_with_all_parameters(self) -> None:
        """Test my_runner with all parameters provided."""
        question = "Complete test"
        attachments = ["doc1.txt", "doc2.pdf", "image.png"]
        params = {"temperature": 0.7, "max_tokens": 1000}
        progress_callback = AsyncMock()

        result = await my_runner(
            question=question, attachments=attachments, params=params, progress=progress_callback
        )

        assert isinstance(result, RunResult)
        assert result.question == question
        assert "# Answer" in result.answer_markdown
        assert "temperature" in result.answer_markdown
        assert "max_tokens" in result.answer_markdown
        assert result.artifacts == []
        assert result.metadata == {"steps": 1}

        # Check progress calls
        assert progress_callback.call_count == 2

    @pytest.mark.asyncio
    async def test_my_runner_none_attachments_handled(self) -> None:
        """Test that None attachments are handled correctly."""
        question = "Test question"

        result = await my_runner(question=question, attachments=None)

        assert isinstance(result, RunResult)
        assert result.question == question

    @pytest.mark.asyncio
    async def test_my_runner_none_params_handled(self) -> None:
        """Test that None params are handled correctly."""
        question = "Test question"

        result = await my_runner(question=question, params=None)

        assert isinstance(result, RunResult)
        assert result.question == question
        assert "Params: `{}`" in result.answer_markdown

    @pytest.mark.asyncio
    async def test_my_runner_empty_lists_and_dicts(self) -> None:
        """Test my_runner with empty lists and dicts."""
        question = "Empty test"
        attachments: list[str] = []
        params: dict[str, Any] = {}

        result = await my_runner(question=question, attachments=attachments, params=params)

        assert isinstance(result, RunResult)
        assert result.question == question
        assert "Params: `{}`" in result.answer_markdown

    @pytest.mark.asyncio
    async def test_my_runner_progress_none_handled(self) -> None:
        """Test that None progress callback is handled."""
        question = "Test without progress"

        # Should not raise any exception
        result = await my_runner(question=question, progress=None)

        assert isinstance(result, RunResult)
        assert result.question == question

    @pytest.mark.asyncio
    async def test_my_runner_answer_markdown_format(self) -> None:
        """Test the format of the generated answer markdown."""
        question = "Format test"
        params = {"key1": "value1", "key2": 42}

        result = await my_runner(question=question, params=params)

        # Check markdown structure
        lines = result.answer_markdown.split("\n")
        assert lines[0] == "# Answer"
        assert lines[1] == ""  # Empty line after header
        assert f"Question: **{question}**" in result.answer_markdown
        assert "key1" in result.answer_markdown
        assert "value1" in result.answer_markdown
        assert "42" in result.answer_markdown

    @pytest.mark.asyncio
    async def test_my_runner_complex_params(self) -> None:
        """Test my_runner with complex parameter types."""
        question = "Complex params test"
        params = {
            "nested": {"inner": "value"},
            "list": [1, 2, 3],
            "bool": True,
            "float": 3.14,
            "none": None,
        }

        result = await my_runner(question=question, params=params)

        assert isinstance(result, RunResult)
        assert result.question == question
        # Should contain string representation of complex params
        assert "nested" in result.answer_markdown
        assert "inner" in result.answer_markdown
