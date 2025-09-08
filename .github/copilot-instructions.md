### Architecture

- You MUST NOT over-engineer
- Always prefer simplicity and direct approaches, instead of unnecessary abstractions.

### Communication

- NEVER write useless summaries of what you did. Just say "I'm done" or "Finished"

### Documentation

- There SHOULD be an `README.md` with the typical sections.
- There SHOULD be an `SUMMARY.md` which briefly describes the project's goals and structure (high level details). This file SHOULD be updated whenever you add significant new features.
- The files `PROMPT_*.md` has the prompts for LLMs. You MUST NOT read or edit this file
- Design documents MUST saved as markdown in `docs/design`
- Documentation SHOULD be simple and to the point. Do not write unnecessary explanations or diagrams.
- When describing, avoid bullet points
- Use diagrams only when necessary to clarify. Do not draw mermaid diagrams if you have two classes.
- Do not write a "File Structure" section

### Python code style

- Type hints:
  - you MUST use type hints in functions and methods signatures
  - you MUST use new way of defining types (Python 3.9+); e.g. " `dict`, `list`, `| None`, `any`, instead of the old `from typing import Dict, Optional, Any`
- Docstrings: SHOULD be short but informative. Multi-line comments just saying the same as the signature are not useful.
- Files operations MUST use pathlib's `Path`, NEVER use `str`
- Classes for data: You SHOULD use Pydantic classes or dataclasses instead of `dict` structures, or "record classes" (a class that only have fields and no functionality).
- Enums: Do not hard-code string values, use `Enum` objects, e.g. `MyEnum(str, Enum)` for better serialization
- Code line length: The lines SHOULD be coded for modern monitors (not 80 character terminals from 1960). Don't spread one statement to multiple lines unless really necessary for clarity.
- Code lint:
  - The effective line length for lis infinite
  - You SHOULD remove unused imports
  - Functions and methods SHOULD be sorted alphabetically (except underscores)
- Code files:
  - SHOULD not exceed 500 lines. Refactor code if it's too long.
  - Write classes (and enums) into their own files whenever possible.
- DRY: Do not repeat yourself
- Consider `match / case` instead of multiple `elif` statements
- `config.py`: Config variables
  - You SHOULD store configuration variables and defaults in a file called `config.py`.
  - Also read the variables from `.env`.
  - Simple values should be just be set (not configured).
  - You SHOULD NOT create functions in `config.py`
- `__str__()`: Classes SHOULD be "printable" so they are easier to understand when developing and debugging
- `__init__.py`: Don't write unnecessary comments, versions, etc. in `__init__` files. If an empty one can do the trick, that's fine.
- Pydantic: use proper Pydantic v2 syntax.

### Python packages

- Use `uv` instead of `pip`
- Use `ruff` instead of `black`

### Python testing rules

- You SHOULD use `pytest`
- You SHOULD Put all test files in a `tests` directory
- Any data necessary for testing MUST be in `tests/data`

- For "simple examples" you MAY use Jupyter notebooks.
- NEVER create python scripts to test, use proper test cases if needed

### Bash

- You MUST start shell script with these two lines:
```
#!/bin/bash -eu
set -o pipfail
```
