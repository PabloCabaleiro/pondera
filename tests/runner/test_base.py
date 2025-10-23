"""Tests for pondera.runner.base module."""

import pytest
from unittest.mock import AsyncMock
from typing import Any

from pondera.runner.base import (
    Runner,
    RunnerError,
    ProgressCallback,
    emit_progress,
    normalize_run_result,
)
from pondera.models.run import RunResult


class TestEmitProgress:
    """Test the emit_progress utility function."""

    @pytest.mark.asyncio
    async def test_emit_progress_with_callback(self) -> None:
        """Test that progress is emitted when callback is provided."""
        callback = AsyncMock()
        message = "Processing step 1"

        await emit_progress(callback, message)

        callback.assert_called_once_with(message)

    @pytest.mark.asyncio
    async def test_emit_progress_with_none_callback(self) -> None:
        """Test that no error occurs when callback is None."""
        # Should not raise any exception
        await emit_progress(None, "test message")

    @pytest.mark.asyncio
    async def test_emit_progress_swallows_callback_exceptions(self) -> None:
        """Test that callback exceptions are swallowed."""
        callback = AsyncMock(side_effect=Exception("Callback failed"))

        # Should not raise despite callback failure
        await emit_progress(callback, "test message")

        callback.assert_called_once_with("test message")

    @pytest.mark.asyncio
    async def test_emit_progress_swallows_runtime_error(self) -> None:
        """Test that runtime errors in callback are swallowed."""
        callback = AsyncMock(side_effect=RuntimeError("Network timeout"))

        await emit_progress(callback, "network operation")

        callback.assert_called_once_with("network operation")

    @pytest.mark.asyncio
    async def test_emit_progress_with_empty_message(self) -> None:
        """Test emit_progress with empty message."""
        callback = AsyncMock()

        await emit_progress(callback, "")

        callback.assert_called_once_with("")


class TestNormalizeRunResult:
    """Test the normalize_run_result function."""

    def test_normalize_run_result_already_run_result(self) -> None:
        """Test that RunResult objects are returned as-is."""
        original = RunResult(question="Test question", answer="Test answer")

        result = normalize_run_result(original, question="Different question")

        assert result is original
        assert result.question == "Test question"  # Original preserved

    def test_normalize_run_result_from_dict_minimal(self) -> None:
        """Test normalization from minimal dict."""
        result_dict = {"answer": "Test answer"}
        question = "What is the answer?"

        result = normalize_run_result(result_dict, question=question)

        assert isinstance(result, RunResult)
        assert result.question == question
        assert result.answer == "Test answer"
        assert result.artifacts == []
        assert result.metadata == {}

    def test_normalize_run_result_from_dict_complete(self) -> None:
        """Test normalization from complete dict."""
        result_dict = {
            "answer": "Complete answer",
            "artifacts": ["file1.txt", "file2.pdf"],
            "metadata": {"steps": 5, "duration": 1.23},
        }
        question = "Complete question?"

        result = normalize_run_result(result_dict, question=question)

        assert isinstance(result, RunResult)
        assert result.question == question
        assert result.answer == "Complete answer"
        assert result.artifacts == ["file1.txt", "file2.pdf"]
        assert result.metadata == {"steps": 5, "duration": 1.23}

    def test_normalize_run_result_dict_overrides_question(self) -> None:
        """Test that question in dict overrides parameter."""
        result_dict = {"question": "Dict question", "answer": "Test answer"}

        result = normalize_run_result(result_dict, question="Param question")

        # Dict value should take precedence due to **result spread
        assert result.question == "Dict question"

    def test_normalize_run_result_invalid_type(self) -> None:
        """Test error handling for unsupported types."""
        invalid_result = "string result"

        with pytest.raises(RunnerError) as exc_info:
            normalize_run_result(invalid_result, question="Test question")

        error_msg = str(exc_info.value)
        assert "Unsupported runner return type" in error_msg
        assert "Return a RunResult or a dict" in error_msg

    def test_normalize_run_result_none_type(self) -> None:
        """Test error handling for None result."""
        with pytest.raises(RunnerError) as exc_info:
            normalize_run_result(None, question="Test question")

        assert "Unsupported runner return type" in str(exc_info.value)

    def test_normalize_run_result_list_type(self) -> None:
        """Test error handling for list result."""
        with pytest.raises(RunnerError) as exc_info:
            normalize_run_result(["answer"], question="Test question")

        assert "Unsupported runner return type" in str(exc_info.value)


class TestRunnerError:
    """Test the RunnerError exception."""

    def test_runner_error_inheritance(self) -> None:
        """Test that RunnerError inherits from RuntimeError."""
        error = RunnerError("Test error")
        assert isinstance(error, RuntimeError)

    def test_runner_error_message(self) -> None:
        """Test RunnerError message handling."""
        message = "Custom error message"
        error = RunnerError(message)
        assert str(error) == message

    def test_runner_error_with_cause(self) -> None:
        """Test RunnerError with exception chaining."""
        original_error = ValueError("Original error")

        try:
            raise RunnerError("Wrapped error") from original_error
        except RunnerError as e:
            assert str(e) == "Wrapped error"
            assert e.__cause__ is original_error


class TestRunnerProtocol:
    """Test the Runner protocol interface."""

    def test_runner_protocol_exists(self) -> None:
        """Test that Runner protocol exists and can be imported."""
        # This test verifies the protocol exists and can be imported
        assert Runner is not None

    @pytest.mark.asyncio
    async def test_mock_runner_implementation(self) -> None:
        """Test a mock implementation of the Runner protocol."""

        class MockRunner:
            async def run(
                self,
                *,
                question: str,
                attachments: list[str] | None = None,
                params: dict[str, Any] | None = None,
                progress: ProgressCallback | None = None,
            ) -> RunResult:
                return RunResult(question=question, answer=f"Mock answer for: {question}")

        runner = MockRunner()
        result = await runner.run(question="Test question")

        assert isinstance(result, RunResult)
        assert result.question == "Test question"
        assert "Mock answer for: Test question" in result.answer

    @pytest.mark.asyncio
    async def test_runner_with_all_parameters(self) -> None:
        """Test runner implementation using all parameters."""

        class FullRunner:
            async def run(
                self,
                *,
                question: str,
                attachments: list[str] | None = None,
                params: dict[str, Any] | None = None,
                progress: ProgressCallback | None = None,
            ) -> RunResult:
                if progress:
                    await progress("Starting processing")

                attachment_info = f"Attachments: {len(attachments or [])}"
                param_info = f"Params: {params or {}}"

                return RunResult(
                    question=question,
                    answer=f"Answer\n{attachment_info}\n{param_info}",
                    metadata={"processed": True},
                )

        runner = FullRunner()
        progress_callback = AsyncMock()

        result = await runner.run(
            question="Full test",
            attachments=["file1.txt", "file2.txt"],
            params={"temperature": 0.7},
            progress=progress_callback,
        )

        assert result.question == "Full test"
        assert "Attachments: 2" in result.answer
        assert "temperature" in result.answer
        assert result.metadata["processed"] is True
        progress_callback.assert_called_once_with("Starting processing")


class TestProgressCallback:
    """Test the ProgressCallback type alias."""

    def test_progress_callback_type_signature(self) -> None:
        """Test that ProgressCallback is properly defined."""
        # ProgressCallback should be a callable type
        assert ProgressCallback is not None

        # Test that it can be used for type annotations
        def accepts_callback(callback: ProgressCallback | None) -> None:
            pass

        # Should not raise type errors
        accepts_callback(None)

    @pytest.mark.asyncio
    async def test_progress_callback_implementation(self) -> None:
        """Test a concrete implementation of ProgressCallback."""
        messages = []

        async def progress_impl(message: str) -> None:
            messages.append(message)

        # Should match ProgressCallback signature
        callback: ProgressCallback = progress_impl

        await callback("Test message")
        assert messages == ["Test message"]
