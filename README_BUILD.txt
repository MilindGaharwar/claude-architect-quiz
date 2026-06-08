Claude Certified Architect – Foundations Practice Quiz
======================================================

QUICK START (for study)
-----------------------
Just open: claude_architect_quiz.html
Double-click it, or File → Open in any browser.
No install. No server. No internet needed.

Works in Chrome, Firefox, Safari, and Edge on Windows, macOS, and Linux.

REBUILDING FROM SOURCE
----------------------
If you want to rebuild the app (e.g. after updating the question file):

Requirements: Python 3.8 or later (standard library only, no pip installs)

Command:
  python3 build.py \
    --input Claude_Architect_Exam_FINAL.md \
    --template quiz_template.html \
    --output claude_architect_quiz.html

This parses all 1157 questions, validates counts, and produces a new self-contained HTML file.

TESTS
-----
Run parser unit tests:
  python3 test_parser.py    (should show 35/35 PASSED)

Run in-browser data/logic tests:
  Open claude_architect_quiz.html in Chrome/Firefox
  Press F12 → Console tab
  Type: runTests()
  Should show all PASSED

SAFARI / FIREFOX NOTE
---------------------
If progress does not save on first open (rare in some privacy modes):
  python3 -m http.server 8000
  Then open: http://localhost:8000/claude_architect_quiz.html

FEATURES
--------
- 1157 questions across 5 domains (+ 12 official sample questions)
- 3 study modes: Exam Simulation, Domain Drill, Weak Areas
- Exam mode: domain-weighted questions, scaled 100-1000 scoring, pass=720
- Two timer modes: per-question (1.5 min) or overall countdown
- Spaced repetition: questions bucket into New / Learning / Mastered
- SM-2 algorithm tracks review intervals
- Analytics dashboard: readiness score, domain accuracy, session history
- Keyboard shortcuts: A/B/C/D select, Enter confirm/next, Space advance, F flag
- Dark mode default, light mode toggle
- Export/Import progress as JSON (for cross-machine backup)

FILES IN THIS ZIP
-----------------
  claude_architect_quiz.html    <- THE APP (share this)
  build.py                      <- build script (Python, no dependencies)
  quiz_template.html            <- HTML template (source)
  test_parser.py                <- parser unit tests
  Claude_Architect_Exam_FINAL.md <- source question bank (1.2MB)
  README_BUILD.txt              <- this file
