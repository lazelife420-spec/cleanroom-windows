# Contributing

Please verify the current repo health checks before opening a pull request:

```powershell
python -m pytest -p no:xonsh tests/
python -m ruff check .
```

CI runs the same checks on pull requests. The active supported product path is
the Cleanroom desktop GUI + CLI/headless flow; legacy smart-clean modules remain
in the repo for reference, but they are not the primary supported surface.
