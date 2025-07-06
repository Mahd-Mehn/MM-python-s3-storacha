# ---------- Variables ----------
PYTHON   ?= python
PIP      ?= $(PYTHON) -m pip
PYRIGHT  ?= pyright
RUFF     ?= ruff
PYTEST   ?= pytest -q --color=yes

# ---------- Targets ----------
install:
	$(PIP) install --upgrade pip
	$(PIP) install -e .[dev]

format:
	$(RUFF) format .

lint:
	$(RUFF) check .

typecheck:
	$(PYRIGHT)

test:
	$(PYTEST)

# Run everything locally (mirrors CI)
ci: format lint typecheck test

clean:
	find . -type f -name '*.py[co]' -delete
	find . -type d -name '__pycache__' -exec rm -rf {} +
	rm -rf build dist *.egg-info .pytest_cache .ruff_cache .pyright

.PHONY: install format lint typecheck test ci clean
