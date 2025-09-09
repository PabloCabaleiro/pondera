# Testing Guide

## Test Organization

This project uses pytest markers to organize tests into different categories:

- `unit`: Fast unit tests that don't require external dependencies
- `integration`: Integration tests that may require external services, API keys, or longer execution times

## Running Tests

### Regular Development (Unit Tests Only)
```bash
# Run all unit tests (default, excludes integration tests)
uv run pytest

# Explicitly run only unit tests
uv run pytest -m "not integration"
```

### Integration Tests
```bash
# Run all integration tests
uv run pytest -m integration

# Run specific integration test file
uv run pytest tests/integration/test_api_integration.py

# Run all tests (unit + integration)
uv run pytest -m ""
```

## Pre-commit Hooks

The pre-commit configuration automatically runs only unit tests to ensure fast feedback:

```yaml
- id: pytest
  name: pytest
  entry: uv run pytest -m "not integration"
```

## Adding New Tests

### Unit Tests
Place unit tests in the appropriate module directories (e.g., `tests/models/`, `tests/judge/`) without any special markers.

### Integration Tests
1. Place integration tests in `tests/integration/`
2. Add the `@pytest.mark.integration` decorator to test classes:

```python
import pytest

@pytest.mark.integration
class TestMyIntegration:
    def test_something(self):
        # Integration test code here
        pass
```

## Test Markers Configuration

The pytest markers are defined in `pytest.ini`:

```ini
markers =
    unit: Unit tests
    integration: Integration tests
    asyncio: Async tests
```
