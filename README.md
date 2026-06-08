# Claude Certified Architect – Foundations Practice Quiz

Created by: Milind

A portable, single-file HTML quiz app for the Claude Certified Architect – Foundations exam.
1157 questions across 5 domains. No install required.

## Usage

Open `claude_architect_quiz.html` in any browser. No server or install needed.

## How it's built

`build.py` parses `Claude_Architect_Exam_FINAL.md` and injects all questions into
`quiz_template.html` to produce `claude_architect_quiz.html`.

The GitHub Actions workflow in `.github/workflows/build.yml` runs this automatically
whenever `quiz_template.html`, `Claude_Architect_Exam_FINAL.md`, or `build.py` is updated.
Netlify deploys the result automatically.

## Manual build

```bash
python3 build.py \
  --input Claude_Architect_Exam_FINAL.md \
  --template quiz_template.html \
  --output claude_architect_quiz.html
```

## Running tests

```bash
python3 test_parser.py     # parser unit tests
python3 test_e2e.py        # end-to-end browser tests (requires Chrome)
```
