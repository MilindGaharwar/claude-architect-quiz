#!/usr/bin/env python3
"""
build.py — Claude Architect Quiz App builder
Parses Claude_Architect_Exam_FINAL.md → validates → injects into HTML template
Usage:
  python build.py --input <md> --template <html> --output <html>
  python build.py --validate-only --input <md>
  python build.py --parse-only --input <md>   # writes questions.json for inspection
"""

import re
import json
import sys
import os
import argparse
from pathlib import Path

# Domain assignment by question ID range
DOMAIN_RANGES = [
    ("D1", 1, 325,  "Agentic Architecture & Orchestration",   0.27),
    ("D2", 326, 515, "Tool Design & MCP Integration",          0.18),
    ("D3", 516, 715, "Claude Code Configuration & Workflows",  0.20),
    ("D4", 716, 915, "Prompt Engineering & Structured Output", 0.20),
    ("D5", 916, 1145,"Context Management & Reliability",       0.15),
]

EXPECTED_COUNTS = {
    "D1": 325, "D2": 190, "D3": 200, "D4": 200, "D5": 230, "SQ": 12
}

EXPECTED_TOTAL = 1157


def get_domain(qid: str) -> str:
    """Return domain code for a question ID string like 'Q42' or 'SQ3'."""
    if qid.startswith("SQ"):
        return "SQ"
    num = int(qid[1:])
    for code, lo, hi, _, _ in DOMAIN_RANGES:
        if lo <= num <= hi:
            return code
    raise ValueError(f"Question ID {qid} not in any domain range")


def get_domain_info(domain_code: str):
    """Return (name, weight) for a domain code."""
    for code, _, _, name, weight in DOMAIN_RANGES:
        if code == domain_code:
            return name, weight
    # SQ questions distributed across all domains for weighting purposes
    return "Official Sample Questions", 0.0


def parse_markdown(text: str) -> list:
    """
    Parse all questions from the markdown text.
    Returns a list of question dicts:
      {id, domain, domain_name, question, choices: {A,B,C,D}, answer, explanation}
    """
    questions = []
    errors = []

    # Split into blocks by question header: **Q123.** or **SQ12.**
    # We split on the header pattern and process each chunk
    pattern = re.compile(
        r'^\*\*((?:SQ|Q)\d+)\.\*\*\s*(.+?)$',
        re.MULTILINE
    )

    # Find all question header positions
    headers = list(pattern.finditer(text))

    if not headers:
        raise ValueError("No questions found in file — check format")

    for i, match in enumerate(headers):
        qid = match.group(1)
        # The block runs from the end of this header line to the start of the next header
        block_start = match.end()
        block_end = headers[i + 1].start() if i + 1 < len(headers) else len(text)
        block = text[block_start:block_end]

        # First line of question text may start on the same line as the header (already captured)
        # or continue after the header. The header regex captures first line in group(2).
        first_line = match.group(2).strip()

        try:
            q = _parse_block(qid, first_line, block)
            questions.append(q)
        except Exception as e:
            errors.append(f"{qid}: {e}")

    if errors:
        print(f"\n[PARSER ERRORS] {len(errors)} questions failed to parse:")
        for err in errors:
            print(f"  {err}")

    return questions, errors


def _parse_block(qid: str, first_line: str, block: str) -> dict:
    """Parse a single question block into a structured dict."""
    lines = block.split('\n')

    # Collect question text lines (before choices start)
    question_lines = [first_line] if first_line else []
    choice_lines = {}
    answer = None
    explanation_lines = []

    state = "question"  # states: question, choices, answer, explanation

    for raw_line in lines:
        line = raw_line.rstrip()

        # Choice line: starts with A) B) C) D)
        choice_match = re.match(r'^([ABCD])\)\s*(.+)$', line)
        if choice_match:
            state = "choices"
            choice_lines[choice_match.group(1)] = choice_match.group(2).strip()
            continue

        # Answer line: **Correct Answer: X**
        answer_match = re.match(r'^\*\*Correct Answer:\s*([ABCD])\*\*', line)
        if answer_match:
            state = "answer"
            answer = answer_match.group(1)
            continue

        # Separator lines
        if re.match(r'^-{3,}$', line.strip()):
            if state == "explanation":
                break  # end of this block
            continue

        # Section headers (domain headers, scenario headers) — skip
        if re.match(r'^#{1,6}\s', line) or re.match(r'^\*\*(Domain|Scenario).*\*\*', line):
            continue

        # Accumulate based on state
        if state == "question":
            stripped = line.strip()
            if stripped:
                question_lines.append(stripped)
        elif state == "choices":
            # Multi-line choice continuation (indented or blank lines between choices are ignored)
            pass
        elif state == "answer":
            # After the answer line, everything is explanation until next separator
            stripped = line.strip()
            if stripped:
                state = "explanation"
                explanation_lines.append(stripped)
        elif state == "explanation":
            stripped = line.strip()
            if stripped:
                explanation_lines.append(stripped)

    # Build question text
    question_text = ' '.join(q.strip() for q in question_lines if q.strip())

    # Validate completeness
    if not question_text:
        raise ValueError("Empty question text")
    for letter in ['A', 'B', 'C', 'D']:
        if letter not in choice_lines or not choice_lines[letter].strip():
            raise ValueError(f"Missing or empty choice {letter}")
    if answer not in ('A', 'B', 'C', 'D'):
        raise ValueError(f"Invalid or missing answer: {answer!r}")
    if not explanation_lines:
        raise ValueError("Missing explanation")

    domain = get_domain(qid)
    domain_name, _ = get_domain_info(domain)

    return {
        "id": qid,
        "domain": domain,
        "domain_name": domain_name,
        "question": question_text,
        "choices": {
            "A": choice_lines['A'],
            "B": choice_lines['B'],
            "C": choice_lines['C'],
            "D": choice_lines['D'],
        },
        "answer": answer,
        "explanation": ' '.join(explanation_lines),
    }


def validate(questions: list, errors: list) -> bool:
    """Validate parsed questions against expected counts. Print report. Return True if valid."""
    print("\n" + "=" * 60)
    print("VALIDATION REPORT")
    print("=" * 60)

    all_passed = True

    # Count by domain
    domain_counts = {}
    for q in questions:
        d = q['domain']
        domain_counts[d] = domain_counts.get(d, 0) + 1

    # Check total
    total = len(questions)
    total_ok = total == EXPECTED_TOTAL
    status = "PASS" if total_ok else "FAIL"
    print(f"\n[{status}] Total questions: {total} (expected {EXPECTED_TOTAL})")
    if not total_ok:
        all_passed = False

    # Check per-domain
    print("\nPer-domain counts:")
    for code, expected in EXPECTED_COUNTS.items():
        actual = domain_counts.get(code, 0)
        ok = actual == expected
        status = "PASS" if ok else "FAIL"
        print(f"  [{status}] {code}: {actual} (expected {expected})")
        if not ok:
            all_passed = False

    # Check no duplicate IDs
    ids = [q['id'] for q in questions]
    dupes = [qid for qid in ids if ids.count(qid) > 1]
    dupes = list(set(dupes))
    dupe_ok = len(dupes) == 0
    status = "PASS" if dupe_ok else "FAIL"
    print(f"\n[{status}] Duplicate IDs: {len(dupes)}", end="")
    if dupes:
        print(f" — {dupes[:10]}")
        all_passed = False
    else:
        print()

    # Check parse errors
    err_ok = len(errors) == 0
    status = "PASS" if err_ok else "FAIL"
    print(f"[{status}] Parse errors: {len(errors)}")

    # Check answer distribution
    dist = {l: sum(1 for q in questions if q['answer'] == l) for l in 'ABCD'}
    total_q = len(questions)
    print(f"\nAnswer distribution: A={dist['A']} B={dist['B']} C={dist['C']} D={dist['D']}")
    for letter, count in dist.items():
        pct = count / total_q * 100 if total_q else 0
        if not (15 <= pct <= 35):
            print(f"  WARNING: {letter} at {pct:.1f}% (expected ~25%)")

    print("\n" + "=" * 60)
    if all_passed and err_ok:
        print("VALIDATION PASSED ✓")
    else:
        print("VALIDATION FAILED ✗")
    print("=" * 60 + "\n")

    return all_passed and err_ok


def inject_into_template(questions: list, template_path: str, output_path: str, minify: bool = True):
    """Read template HTML, replace placeholder with JSON data, write output."""
    with open(template_path, 'r', encoding='utf-8') as f:
        template = f.read()

    PLACEHOLDER = '/*QUESTIONS_DATA_PLACEHOLDER*/'
    if PLACEHOLDER not in template:
        raise ValueError(f"Placeholder '{PLACEHOLDER}' not found in template")

    if minify:
        json_str = json.dumps(questions, ensure_ascii=False, separators=(',', ':'))
    else:
        json_str = json.dumps(questions, ensure_ascii=False, indent=2)

    data_block = f"const QUESTIONS = {json_str};"
    output_html = template.replace(PLACEHOLDER, data_block)

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(output_html)

    size_kb = len(output_html.encode('utf-8')) / 1024
    print(f"Output written: {output_path} ({size_kb:.1f} KB)")


def main():
    parser = argparse.ArgumentParser(description='Claude Architect Quiz App builder')
    parser.add_argument('--input', required=True, help='Source markdown file')
    parser.add_argument('--template', help='HTML template file')
    parser.add_argument('--output', help='Output HTML file')
    parser.add_argument('--validate-only', action='store_true', help='Parse and validate, no output')
    parser.add_argument('--parse-only', action='store_true', help='Parse, validate, write questions.json')
    parser.add_argument('--no-minify', action='store_true', help='Pretty-print JSON in output')
    args = parser.parse_args()

    # Read source
    print(f"Reading: {args.input}")
    with open(args.input, 'r', encoding='utf-8') as f:
        text = f.read()

    # Parse
    print("Parsing questions...")
    questions, errors = parse_markdown(text)
    print(f"Parsed {len(questions)} questions ({len(errors)} errors)")

    # Validate
    valid = validate(questions, errors)

    if args.validate_only:
        sys.exit(0 if valid else 1)

    if not valid:
        print("ERROR: Validation failed. Fix parser issues before building.")
        sys.exit(1)

    if args.parse_only:
        out_path = Path(args.input).parent / 'questions.json'
        with open(out_path, 'w', encoding='utf-8') as f:
            json.dump(questions[:10], f, ensure_ascii=False, indent=2)
        print(f"First 10 questions written to: {out_path}")
        sys.exit(0)

    # Inject into template
    if not args.template or not args.output:
        print("ERROR: --template and --output required for full build")
        sys.exit(1)

    inject_into_template(
        questions,
        args.template,
        args.output,
        minify=not args.no_minify
    )
    print("Build complete.")


if __name__ == '__main__':
    main()
