this is the good orchestration sample that we need to use /Users/hnguyen/Desktop/projects/ottomator-agents/pydantic-ai-langfuse/pydantic_ai_langfuse_agent.py

#json report
source .venv/bin/activate && python -m pytest src/tests/test_jsonplaceholder_api.py --json-report --json-report-file=test-results/report.json -v

#pretty printing
source .venv/bin/activate && python -m pytest src/tests/test_jsonplaceholder_api.py --json-report --json-report-file=test-results/summary.json --json-report-summary --json-report-indent=4 -v


example prompt: read the test results in directory ./reports and analyze the content, extract the test name, details, status PASS of FAIL, then notify the slack channel all-acme-automation with these details

read this:
https://github.com/furudo-erika/ai-testing-agent/blob/main/api_tester.py

this might be better:
https://github.com/qodo-ai/qodo-cover
https://www.qodo.ai/