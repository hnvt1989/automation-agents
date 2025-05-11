# -----------------------------------------------------------------------------
#  Template for final test file
# -----------------------------------------------------------------------------
TEST_TEMPLATE = """
import os
import requests
import pytest

BASE_URL = os.getenv('TEST_API_URL', 'http://localhost:8000')

{test_functions}
"""

# -----------------------------------------------------------------------------
#  PROMPTS
# -----------------------------------------------------------------------------
PLAN_PROMPT = (
    "Generate a test plan for a fictional REST API with categories like "
    "authorization, boundary, and error handling. Include a few scenarios each."
)

# NOTE: Double braces around {{test_functions}} to avoid f-string substitution
GENERATION_PROMPT = f"""
Below is a skeleton of our test file using pytest. Fill in the 'test_functions'
placeholder with tests for the following real API behavior from main.py:

1) GET /api/endpoint?param=max => 200, JSON {{ "result": "success" }}
2) GET /api/endpoint?param=min => 200, JSON {{ "result": "success" }}
3) If param != 'max'/'min':
   - no Authorization header => 401
   - 'Bearer invalid-api-key' => 403
   - otherwise => 404
4) GET /api/nonexistent => 404
5) GET /api/error => 500

We want these exact tests:
- test_endpoint_with_max
- test_endpoint_with_min
- test_endpoint_no_auth
- test_endpoint_invalid_api_key
- test_endpoint_random_auth_key
- test_nonexistent_endpoint
- test_error_endpoint

Skeleton:
```python
{TEST_TEMPLATE}
```

Requirements:
1. Use '/api/' prefix for all routes.
2. Only return valid Python code, wrapped in triple backticks (no extra commentary).
3. Keep 'BASE_URL' from env or default http://localhost:8000.
4. Provide all tests in place of {{test_functions}}.
5. Each test asserts the correct status code (and JSON if needed).
6. The final output should be a complete Python file that can run under pytest.
"""
