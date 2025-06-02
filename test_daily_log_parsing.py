#!/usr/bin/env python3
"""Test daily log parsing."""

import re

# Test the regex pattern
test_cases = [
    "add a daily log 'research automated test analysis' took 2 hours",
    "add daily log 'fix bug in parser' spent 3.5 hours",
    "add a daily log \"meeting notes\" for 1 hour",
    "add daily log testing work took 2 hours"
]

pattern = r"add\s+(?:a\s+)?daily\s+log\s+['\"]?(.+?)['\"]?\s+(?:took|spent|for)\s+(\d+(?:\.\d+)?)\s*hours?"

for test in test_cases:
    print(f"\nTest: {test}")
    match = re.search(pattern, test.lower())
    if match:
        print(f"  Description: '{match.group(1)}'")
        print(f"  Hours: {match.group(2)}")
    else:
        print("  No match!")

# Let's try a better pattern
print("\n" + "="*50 + "\nTrying improved pattern:\n")

# Better pattern that handles quotes properly
pattern2 = r"add\s+(?:a\s+)?daily\s+log\s+(?:['\"]([^'\"]+)['\"]|(.+?))\s+(?:took|spent|for)\s+(\d+(?:\.\d+)?)\s*hours?"

for test in test_cases:
    print(f"\nTest: {test}")
    match = re.search(pattern2, test.lower())
    if match:
        # Group 1 is for quoted, group 2 is for unquoted
        description = match.group(1) if match.group(1) else match.group(2)
        hours = match.group(3)
        print(f"  Description: '{description}'")
        print(f"  Hours: {hours}")
    else:
        print("  No match!")