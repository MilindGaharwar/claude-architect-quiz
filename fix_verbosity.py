#!/usr/bin/env python3
"""
fix_verbosity.py — Fix answer verbosity bias in Claude_Architect_Exam_FINAL.md

Strategy: For questions where correct answer is >1.8x longer than avg incorrect,
rewrite the 3 wrong answers to match the correct answer's length and style using
the Claude API via the GenAI Nexus gateway.

Usage:
  python3 fix_verbosity.py --input Claude_Architect_Exam_FINAL.md \
                            --output Claude_Architect_Exam_FIXED.md \
                            --api-key YOUR_KEY [--dry-run] [--limit 50]
"""

import re, json, sys, os, time, argparse, random
from pathlib import Path

# ─── Parser (reuse build.py logic) ───────────────────────────────────────────

DOMAIN_RANGES = [
    ("D1", 1,   325,  "Agentic Architecture & Orchestration",   0.27),
    ("D2", 326, 515,  "Tool Design & MCP Integration",          0.18),
    ("D3", 516, 715,  "Claude Code Configuration & Workflows",  0.20),
    ("D4", 716, 915,  "Prompt Engineering & Structured Output", 0.20),
    ("D5", 916, 1145, "Context Management & Reliability",       0.15),
]

def get_domain(qid):
    if qid.startswith("SQ"): return "SQ"
    num = int(qid[1:])
    for code, lo, hi, _, _ in DOMAIN_RANGES:
        if lo <= num <= hi: return code
    return "??"

def parse_questions(text):
    questions = []
    pattern = re.compile(r'^\*\*((?:SQ|Q)\d+)\.\*\*\s*(.+?)$', re.MULTILINE)
    headers = list(pattern.finditer(text))
    for i, match in enumerate(headers):
        qid = match.group(1)
        first_line = match.group(2).strip()
        block_start = match.end()
        block_end = headers[i+1].start() if i+1 < len(headers) else len(text)
        block = text[block_start:block_end]
        try:
            q = parse_block(qid, first_line, block)
            q['raw_block_start'] = match.start()
            q['raw_block_end'] = block_end
            questions.append(q)
        except Exception as e:
            print(f"  Parse error {qid}: {e}")
    return questions

def parse_block(qid, first_line, block):
    lines = block.split('\n')
    question_lines = [first_line] if first_line else []
    choice_lines = {}
    answer = None
    explanation_lines = []
    state = "question"

    for raw_line in lines:
        line = raw_line.rstrip()
        choice_match = re.match(r'^([ABCD])\)\s*(.+)$', line)
        if choice_match:
            state = "choices"
            choice_lines[choice_match.group(1)] = choice_match.group(2).strip()
            continue
        answer_match = re.match(r'^\*\*Correct Answer:\s*([ABCD])\*\*', line)
        if answer_match:
            state = "answer"
            answer = answer_match.group(1)
            continue
        if re.match(r'^-{3,}$', line.strip()):
            if state == "explanation": break
            continue
        if re.match(r'^#{1,6}\s', line) or re.match(r'^\*\*(Domain|Scenario).*\*\*', line):
            continue
        if state == "question":
            stripped = line.strip()
            if stripped: question_lines.append(stripped)
        elif state == "answer":
            stripped = line.strip()
            if stripped:
                state = "explanation"
                explanation_lines.append(stripped)
        elif state == "explanation":
            stripped = line.strip()
            if stripped: explanation_lines.append(stripped)

    return {
        "id": qid,
        "domain": get_domain(qid),
        "question": ' '.join(q.strip() for q in question_lines if q.strip()),
        "choices": {l: choice_lines[l] for l in 'ABCD' if l in choice_lines},
        "answer": answer,
        "explanation": ' '.join(explanation_lines),
    }

# ─── Bias detection ──────────────────────────────────────────────────────────

def verbosity_ratio(q):
    correct = q['choices'].get(q['answer'], '')
    wrong = [v for k, v in q['choices'].items() if k != q['answer']]
    if not wrong: return 1.0
    avg_wrong = sum(len(w) for w in wrong) / len(wrong)
    if avg_wrong == 0: return 999.0
    return len(correct) / avg_wrong

def is_biased(q, threshold=1.8):
    return verbosity_ratio(q) >= threshold

# ─── Rewriter using Claude API ───────────────────────────────────────────────

def build_rewrite_prompt(q):
    correct_letter = q['answer']
    correct_text   = q['choices'][correct_letter]
    wrong_letters  = [l for l in 'ABCD' if l != correct_letter]
    wrong_texts    = [q['choices'][l] for l in wrong_letters]
    correct_len    = len(correct_text)

    prompt = f"""You are fixing a multiple-choice exam question where the correct answer is much longer than the wrong answers, making it easy to guess without knowing the content.

QUESTION: {q['question']}

CORRECT ANSWER ({correct_letter}): {correct_text}

WRONG ANSWERS TO REWRITE:
{wrong_letters[0]}) {wrong_texts[0]}
{wrong_letters[1]}) {wrong_texts[1]}
{wrong_letters[2]}) {wrong_texts[2]}

TARGET LENGTH: Each rewritten wrong answer should be approximately {correct_len} characters (±30%).

RULES:
1. Each wrong answer must remain CLEARLY WRONG to someone who knows the subject
2. Match the style of the correct answer — use similar sentence structure, em-dashes for elaboration, and explanatory clauses
3. Wrong answers should sound plausible to someone who doesn't know the material
4. Do NOT change the correct answer
5. Keep the same general approach/concept as the original wrong answer, just expand it
6. Return ONLY a JSON object, no other text

Return this exact JSON format:
{{
  "{wrong_letters[0]}": "rewritten text for option {wrong_letters[0]}",
  "{wrong_letters[1]}": "rewritten text for option {wrong_letters[1]}",
  "{wrong_letters[2]}": "rewritten text for option {wrong_letters[2]}"
}}"""
    return prompt

def call_claude_api(prompt, api_key, base_url, model):
    """
    Call Claude API.
    - If base_url contains 'corpinter' (corporate VPN gateway): uses claude CLI subprocess
      because the gateway is only reachable inside the corporate network.
    - Otherwise: uses standard HTTP with x-api-key or Bearer auth.
    """
    import urllib.request, urllib.error, subprocess, tempfile

    base_lower = base_url.lower().rstrip('/')

    # Corporate VPN gateway — use the claude CLI which already has gateway access
    if 'corpinter' in base_lower:
        return _call_via_claude_cli(prompt)

    # Standard Anthropic API or other bearer-auth gateway
    use_bearer = 'minimax' in base_lower or 'dashscope' in base_lower

    # Build URL
    if base_url.endswith('/messages') or base_url.endswith('/messages/'):
        url = base_url
    elif re.search(r'/v\d+$', base_url):
        url = base_url + '/messages'
    else:
        url = base_url.rstrip('/') + '/v1/messages'

    headers = {'Content-Type': 'application/json'}
    if use_bearer:
        headers['Authorization'] = f'Bearer {api_key}'
    else:
        headers['x-api-key'] = api_key
        headers['anthropic-version'] = '2023-06-01'

    body = json.dumps({
        'model': model,
        'max_tokens': 1024,
        'messages': [{'role': 'user', 'content': prompt}]
    }).encode('utf-8')

    req = urllib.request.Request(url, data=body, headers=headers, method='POST')
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            return data['content'][0]['text']
    except urllib.error.HTTPError as e:
        err_body = e.read().decode('utf-8')
        raise RuntimeError(f"HTTP {e.code}: {err_body[:200]}")


def _call_via_claude_cli(prompt):
    """Use the claude CLI subprocess — works when gateway is only reachable inside corporate VPN."""
    import subprocess, shutil, os

    claude_bin = shutil.which('claude') or '/opt/homebrew/lib/node_modules/@anthropic-ai/claude-code/bin/claude.exe'

    # Retry with aggressive backoff on rate limit (429)
    for attempt in range(10):
        try:
            result = subprocess.run(
                [claude_bin, '-p', prompt],
                capture_output=True, text=True, timeout=60,
                env={**os.environ}
            )
            if result.returncode == 0:
                return result.stdout.strip()
            out = result.stdout + result.stderr
            if '429' in out or 'rate limit' in out.lower():
                # Exponential backoff: 60s, 120s, 240s, ... up to 15 minutes
                wait = min(60 * (2 ** attempt), 900)
                print(f"\n    [Rate limited — waiting {wait}s (attempt {attempt+1}/10)]", flush=True)
                time.sleep(wait)
                continue
            raise RuntimeError(f"claude CLI error: {out[:200]}")
        except subprocess.TimeoutExpired:
            raise RuntimeError("claude CLI timed out after 60s")
    raise RuntimeError("claude CLI rate limited after 10 retries")

def rewrite_wrong_answers(q, api_key, base_url, model, dry_run=False):
    """Returns dict of {letter: new_text} for wrong answers only."""
    if dry_run:
        # Simulate expansion: pad wrong answers to ~correct length
        correct_len = len(q['choices'][q['answer']])
        result = {}
        for letter in 'ABCD':
            if letter != q['answer']:
                orig = q['choices'][letter]
                result[letter] = orig + f" — this approach does not address the core requirement and would introduce additional complexity without solving the underlying problem in the way the architecture requires"
                result[letter] = result[letter][:int(correct_len * 1.1)]
        return result

    prompt = build_rewrite_prompt(q)
    response_text = call_claude_api(prompt, api_key, base_url, model)

    # Try multiple JSON extraction strategies
    # Strategy 1: find outermost { ... } block
    try:
        start = response_text.index('{')
        end   = response_text.rindex('}') + 1
        return json.loads(response_text[start:end])
    except (ValueError, json.JSONDecodeError):
        pass

    # Strategy 2: strip markdown code fences and retry
    cleaned = re.sub(r'```(?:json)?|```', '', response_text).strip()
    try:
        start = cleaned.index('{')
        end   = cleaned.rindex('}') + 1
        return json.loads(cleaned[start:end])
    except (ValueError, json.JSONDecodeError):
        pass

    # Strategy 3: extract per-key values with regex fallback
    wrong_letters = [l for l in 'ABCD' if l != q['answer']]
    result = {}
    for letter in wrong_letters:
        m = re.search(rf'"{letter}"\s*:\s*"((?:[^"\\]|\\.)*)"', response_text)
        if m:
            result[letter] = m.group(1).replace('\\"', '"').replace('\\n', ' ')
    if len(result) == 3:
        return result

    raise ValueError(f"Could not parse JSON from response: {response_text[:300]}")

# ─── Markdown reconstructor ──────────────────────────────────────────────────

def reconstruct_question_block(q, new_choices):
    """Rebuild the markdown block for one question with updated choices."""
    lines = []
    lines.append(f"**{q['id']}.** {q['question']}")
    lines.append("")
    for letter in 'ABCD':
        text = new_choices.get(letter, q['choices'][letter])
        lines.append(f"{letter}) {text}  ")
    lines.append("")
    lines.append(f"**Correct Answer: {q['answer']}**")
    lines.append(q['explanation'])
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("---")
    lines.append("")
    return '\n'.join(lines)

# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input',   required=True)
    parser.add_argument('--output',  required=True)
    parser.add_argument('--api-key', default=os.environ.get('AWS_BEARER_TOKEN_BEDROCK',''))
    parser.add_argument('--base-url', default=os.environ.get('ANTHROPIC_BEDROCK_BASE_URL', 'https://api.anthropic.com'))
    parser.add_argument('--model',   default=os.environ.get('ANTHROPIC_MODEL', 'claude-haiku-4-5-20251001'))
    parser.add_argument('--threshold', type=float, default=1.8,
                        help='Verbosity ratio threshold to trigger rewrite (default 1.8)')
    parser.add_argument('--limit',   type=int, default=0,
                        help='Max questions to rewrite (0 = all biased)')
    parser.add_argument('--dry-run', action='store_true',
                        help='Run without calling API (uses padding heuristic)')
    parser.add_argument('--resume-from', default='',
                        help='Question ID to resume from (skip already-done questions)')
    args = parser.parse_args()

    print(f"Reading: {args.input}")
    text = Path(args.input).read_text(encoding='utf-8')

    print("Parsing questions...")
    questions = parse_questions(text)
    print(f"Parsed {len(questions)} questions")

    # Find biased questions
    biased = [q for q in questions if is_biased(q, args.threshold)]
    # Skip SQ (Anthropic-authored) — they're already balanced
    biased = [q for q in biased if q['domain'] != 'SQ']
    print(f"Biased questions (ratio ≥ {args.threshold}x): {len(biased)}")

    if args.limit > 0:
        biased = biased[:args.limit]
        print(f"Limited to first {args.limit}")

    if args.resume_from:
        ids = [q['id'] for q in biased]
        if args.resume_from in ids:
            idx = ids.index(args.resume_from)
            biased = biased[idx:]
            print(f"Resuming from {args.resume_from} ({len(biased)} remaining)")

    print(f"\nRewriting {len(biased)} questions...")
    if args.dry_run:
        print("DRY RUN MODE — no API calls")

    # Build a mutable copy of the text to patch in-place
    # We'll do string replacement of the original choice lines
    new_text = text
    done = 0
    errors = 0

    for i, q in enumerate(biased):
        ratio = verbosity_ratio(q)
        print(f"  [{i+1}/{len(biased)}] {q['id']} (ratio {ratio:.1f}x)...", end=' ', flush=True)

        try:
            new_choices = rewrite_wrong_answers(q, args.api_key, args.base_url, args.model, args.dry_run)

            # Patch each wrong answer in the text
            # Find and replace each original choice line
            patched = 0
            for letter, new_text_choice in new_choices.items():
                orig_choice = q['choices'][letter]
                # Match the exact choice line (handles trailing spaces from markdown)
                old_line = re.escape(f"{letter}) {orig_choice}")
                new_line = f"{letter}) {new_text_choice}"
                result, n = re.subn(old_line + r'\s*$', new_line, new_text, count=1, flags=re.MULTILINE)
                if n > 0:
                    new_text = result
                    patched += 1
                else:
                    # Try without trailing whitespace constraint
                    result2, n2 = re.subn(re.escape(f"{letter}) {orig_choice}"), new_line, new_text, count=1)
                    if n2 > 0:
                        new_text = result2
                        patched += 1

            print(f"✓ ({patched}/3 choices patched)")
            done += 1

            # Save progress every 50 questions
            if done % 50 == 0:
                checkpoint = args.output.replace('.md', f'_checkpoint_{done}.md')
                Path(checkpoint).write_text(new_text, encoding='utf-8')
                print(f"  [Checkpoint saved: {checkpoint}]")

            # Rate limiting — be polite to the API
            if not args.dry_run:
                time.sleep(2.0)

        except Exception as e:
            print(f"✗ ERROR: {e}")
            errors += 1
            if errors > 20:
                print("Too many errors — saving progress and stopping")
                break

    # Write final output
    Path(args.output).write_text(new_text, encoding='utf-8')
    print(f"\nDone. Rewrote {done} questions ({errors} errors)")
    print(f"Output: {args.output}")

    # Quick validation
    print("\nValidating output...")
    new_questions = parse_questions(new_text)
    new_biased = [q for q in new_questions if is_biased(q, args.threshold) and q['domain'] != 'SQ']
    improvement = len(biased) - len(new_biased)
    print(f"Before: {len(biased)} biased questions")
    print(f"After:  {len(new_biased)} biased questions")
    print(f"Fixed:  {improvement} questions ({improvement/len(biased)*100:.1f}%)")


if __name__ == '__main__':
    main()
