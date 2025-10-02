Model output end-to-end tests
===========================

These tests exercise the model output and are intended to be run separately
from the localhost e2e tests.

Setup
-----

- Set the PRODUCTION_API_BASE environment variable to the full base URL of the
  production API, for example.

```bash
export PRODUCTION_API_BASE=https://api.example.com
```

Run
---

From the repository root run:

```bash
pytest e2e/model_output_testing -q
```

Notes
-----

- Tests are skipped automatically if PRODUCTION_API_BASE is not set.
- Keep tests minimal and non-destructive.
