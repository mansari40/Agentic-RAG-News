export PYTHONPATH=.

install:
	uv pip install -e ".[dev]"

check:
	python -m pre_commit run -a
	ruff check .
	ruff format .
	mypy src
	pytest

test:
	pytest
