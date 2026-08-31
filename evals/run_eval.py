import json
import requests
import sys

API_URL = "http://localhost:8001/triage"

with open("evals/cases.json") as f:
    cases = json.load(f)

passed = 0
failed = []

for i, case in enumerate(cases):
    response = requests.post(API_URL, json={"text": case["input"]})
    result = response.json()
    # print(f"DEBUG Case {i+1}: status={response.status_code}, result={result}")  # add karo
    got = result.get("category")
    expected = case["expected_category"]

    if got == expected:
        passed += 1
        print(f"✅ Case {i+1}: '{case['input'][:40]}...' → {got}")
    else:
        failed.append({"case": i+1, "input": case["input"], "expected": expected, "got": got})
        print(f"❌ Case {i+1}: '{case['input'][:40]}...' → got={got}, expected={expected}")

print(f"\nScore: {passed}/{len(cases)}")

if failed:
    print("\nFailed cases:")
    for f in failed:
        print(f"  Case {f['case']}: expected={f['expected']}, got={f['got']}")