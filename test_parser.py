#!/usr/bin/env python3
"""
test_parser.py — Unit tests for build.py parser
Run: python test_parser.py
"""
import sys
import json
import os
sys.path.insert(0, os.path.dirname(__file__))

from build import parse_markdown, validate, get_domain, _parse_block, EXPECTED_TOTAL, EXPECTED_COUNTS

PASS = "\033[92mPASS\033[0m"
FAIL = "\033[91mFAIL\033[0m"

results = []

def test(name, fn):
    try:
        fn()
        print(f"  [{PASS}] {name}")
        results.append(True)
    except AssertionError as e:
        print(f"  [{FAIL}] {name}: {e}")
        results.append(False)
    except Exception as e:
        print(f"  [{FAIL}] {name}: EXCEPTION — {e}")
        results.append(False)


# ─── Unit tests for get_domain ───────────────────────────────────────────────

print("\n=== Domain assignment ===")

def t_domain_q1():
    assert get_domain("Q1") == "D1"

def t_domain_q325():
    assert get_domain("Q325") == "D1"

def t_domain_q326():
    assert get_domain("Q326") == "D2"

def t_domain_q515():
    assert get_domain("Q515") == "D2"

def t_domain_q516():
    assert get_domain("Q516") == "D3"

def t_domain_q715():
    assert get_domain("Q715") == "D3"

def t_domain_q716():
    assert get_domain("Q716") == "D4"

def t_domain_q915():
    assert get_domain("Q915") == "D4"

def t_domain_q916():
    assert get_domain("Q916") == "D5"

def t_domain_q1145():
    assert get_domain("Q1145") == "D5"

def t_domain_sq():
    assert get_domain("SQ1") == "SQ"
    assert get_domain("SQ12") == "SQ"

test("Q1 → D1", t_domain_q1)
test("Q325 → D1 (boundary)", t_domain_q325)
test("Q326 → D2 (boundary)", t_domain_q326)
test("Q515 → D2 (boundary)", t_domain_q515)
test("Q516 → D3 (boundary)", t_domain_q516)
test("Q715 → D3 (boundary)", t_domain_q715)
test("Q716 → D4 (boundary)", t_domain_q716)
test("Q915 → D4 (boundary)", t_domain_q915)
test("Q916 → D5 (boundary)", t_domain_q916)
test("Q1145 → D5 (boundary)", t_domain_q1145)
test("SQ → SQ domain", t_domain_sq)


# ─── Unit tests for _parse_block ─────────────────────────────────────────────

print("\n=== Block parser ===")

WELL_FORMED_BLOCK = """
A) Add a prerequisite check
B) Enhance the system prompt
C) Add few-shot examples
D) Implement a classifier

**Correct Answer: A**
When a specific tool sequence is required, programmatic enforcement provides guarantees.

---
"""

def t_well_formed():
    q = _parse_block("Q1", "You are building an agent. What is wrong?", WELL_FORMED_BLOCK)
    assert q['id'] == "Q1"
    assert q['domain'] == "D1"
    assert q['answer'] == "A"
    assert q['choices']['A'] == "Add a prerequisite check"
    assert q['choices']['B'] == "Enhance the system prompt"
    assert q['choices']['C'] == "Add few-shot examples"
    assert q['choices']['D'] == "Implement a classifier"
    assert "programmatic enforcement" in q['explanation']
    assert q['question'] == "You are building an agent. What is wrong?"

def t_sq_domain():
    q = _parse_block("SQ5", "Which approach should you take?", WELL_FORMED_BLOCK)
    assert q['domain'] == "SQ"

def t_answer_b():
    block = WELL_FORMED_BLOCK.replace("**Correct Answer: A**", "**Correct Answer: B**")
    q = _parse_block("Q500", "Which is best?", block)
    assert q['answer'] == "B"

def t_answer_d():
    block = WELL_FORMED_BLOCK.replace("**Correct Answer: A**", "**Correct Answer: D**")
    q = _parse_block("Q700", "Which is best?", block)
    assert q['answer'] == "D"

MULTILINE_QUESTION_BLOCK = """
A) Option alpha
B) Option beta
C) Option gamma
D) Option delta

**Correct Answer: C**
This tests multi-line question text handling.

---
"""

def t_multiline_question():
    # First line from header, second line in block
    q = _parse_block("Q42", "Your agent runs in production.", MULTILINE_QUESTION_BLOCK)
    assert "Your agent runs in production." in q['question']
    assert q['answer'] == "C"

MULTILINE_EXPLANATION_BLOCK = """
A) Option one is correct
B) Option two is wrong
C) Option three is also wrong
D) Option four is definitely wrong

**Correct Answer: A**
First sentence of explanation. This is a long explanation that spans
multiple lines and contains important detail about the correct approach.
The explanation continues here with additional context.

---
"""

def t_multiline_explanation():
    q = _parse_block("Q100", "What is best?", MULTILINE_EXPLANATION_BLOCK)
    assert "First sentence of explanation" in q['explanation']
    assert "additional context" in q['explanation']

def t_backtick_in_text():
    block = """
A) Call `get_customer` first
B) Call `lookup_order` with `order_id`
C) Use `tool_choice: "auto"`
D) Set `stop_reason` to end_turn

**Correct Answer: B**
The `lookup_order` tool requires a valid `order_id`.

---
"""
    q = _parse_block("Q200", "How should you call `lookup_order`?", block)
    assert "`lookup_order`" in q['choices']['B']
    assert "`lookup_order`" in q['explanation']

def t_missing_choice_raises():
    block = """
A) Only option A
B) Only option B

**Correct Answer: A**
Some explanation.

---
"""
    raised = False
    try:
        _parse_block("Q999", "Bad question", block)
    except Exception:
        raised = True
    assert raised, "Should raise on missing choices"

def t_missing_answer_raises():
    block = """
A) Option A
B) Option B
C) Option C
D) Option D

Some explanation without an answer line.

---
"""
    raised = False
    try:
        _parse_block("Q999", "Bad question", block)
    except Exception:
        raised = True
    assert raised, "Should raise on missing answer"

test("Well-formed block parses correctly", t_well_formed)
test("SQ question gets SQ domain", t_sq_domain)
test("Answer B parses correctly", t_answer_b)
test("Answer D parses correctly", t_answer_d)
test("Multi-line question text", t_multiline_question)
test("Multi-line explanation", t_multiline_explanation)
test("Backticks in text preserved", t_backtick_in_text)
test("Missing choices raises error", t_missing_choice_raises)
test("Missing answer raises error", t_missing_answer_raises)


# ─── Integration test against real file ─────────────────────────────────────

print("\n=== Integration: full file parse ===")

# Look for source file: first in same dir as test script, then one level up
_script_dir = os.path.dirname(os.path.abspath(__file__))
_same_dir   = os.path.join(_script_dir, 'Claude_Architect_Exam_FINAL.md')
_parent_dir = os.path.join(_script_dir, '..', 'Claude_Architect_Exam_FINAL.md')
SOURCE_FILE = _same_dir if os.path.exists(_same_dir) else os.path.abspath(_parent_dir)

questions = None
errors = None

def t_file_exists():
    assert os.path.exists(SOURCE_FILE), f"Source file not found: {SOURCE_FILE}"

def t_parse_no_crash():
    global questions, errors
    with open(SOURCE_FILE, 'r', encoding='utf-8') as f:
        text = f.read()
    questions, errors = parse_markdown(text)
    assert questions is not None

def t_total_count():
    assert len(questions) == EXPECTED_TOTAL, f"Expected {EXPECTED_TOTAL}, got {len(questions)}"

def t_zero_parse_errors():
    assert len(errors) == 0, f"{len(errors)} parse errors: {errors[:5]}"

def t_domain_counts():
    from collections import Counter
    counts = Counter(q['domain'] for q in questions)
    for code, expected in EXPECTED_COUNTS.items():
        actual = counts.get(code, 0)
        assert actual == expected, f"{code}: expected {expected}, got {actual}"

def t_no_duplicate_ids():
    ids = [q['id'] for q in questions]
    from collections import Counter
    dupes = [k for k, v in Counter(ids).items() if v > 1]
    assert len(dupes) == 0, f"Duplicate IDs: {dupes}"

def t_all_have_four_choices():
    bad = [q['id'] for q in questions if set(q['choices'].keys()) != {'A','B','C','D'}]
    assert len(bad) == 0, f"Missing choices in: {bad[:5]}"

def t_all_valid_answers():
    bad = [q['id'] for q in questions if q['answer'] not in ('A','B','C','D')]
    assert len(bad) == 0, f"Invalid answers in: {bad[:5]}"

def t_all_have_explanation():
    bad = [q['id'] for q in questions if not q['explanation'].strip()]
    assert len(bad) == 0, f"Empty explanations in: {bad[:5]}"

def t_all_have_question_text():
    bad = [q['id'] for q in questions if not q['question'].strip()]
    assert len(bad) == 0, f"Empty question text in: {bad[:5]}"

def t_answer_distribution():
    from collections import Counter
    dist = Counter(q['answer'] for q in questions)
    total = len(questions)
    for letter in 'ABCD':
        pct = dist[letter] / total * 100
        assert 15 <= pct <= 35, f"Answer {letter} at {pct:.1f}% — outside 15-35% range"

def t_json_serializable():
    # All questions must serialize to valid JSON (no bad chars)
    json_str = json.dumps(questions, ensure_ascii=False)
    parsed = json.loads(json_str)
    assert len(parsed) == len(questions)

def t_spot_check_q1():
    q = next(q for q in questions if q['id'] == 'Q1')
    assert q['domain'] == 'D1'
    assert q['answer'] == 'A'
    assert 'conversation history' in q['explanation'].lower() or 'tool results' in q['explanation'].lower()

def t_spot_check_sq1():
    q = next(q for q in questions if q['id'] == 'SQ1')
    assert q['domain'] == 'SQ'
    assert q['answer'] == 'A'

def t_spot_check_q1145():
    q = next(q for q in questions if q['id'] == 'Q1145')
    assert q['domain'] == 'D5'
    assert q['answer'] == 'C'

test("Source file exists", t_file_exists)
test("File parses without crash", t_parse_no_crash)
test(f"Total count == {EXPECTED_TOTAL}", t_total_count)
test("Zero parse errors", t_zero_parse_errors)
test("Per-domain counts correct", t_domain_counts)
test("No duplicate IDs", t_no_duplicate_ids)
test("All questions have 4 choices", t_all_have_four_choices)
test("All answers are A/B/C/D", t_all_valid_answers)
test("All questions have explanation", t_all_have_explanation)
test("All questions have question text", t_all_have_question_text)
test("Answer distribution 15-35% each", t_answer_distribution)
test("All questions JSON-serializable", t_json_serializable)
test("Spot-check Q1 (D1, answer A)", t_spot_check_q1)
test("Spot-check SQ1 (SQ domain, answer A)", t_spot_check_sq1)
test("Spot-check Q1145 (D5, answer C)", t_spot_check_q1145)


# ─── Summary ─────────────────────────────────────────────────────────────────

print("\n" + "=" * 60)
passed = sum(results)
total = len(results)
print(f"Results: {passed}/{total} passed")
if passed == total:
    print("ALL TESTS PASSED ✓")
else:
    print(f"FAILURES: {total - passed}")
print("=" * 60)

sys.exit(0 if passed == total else 1)
