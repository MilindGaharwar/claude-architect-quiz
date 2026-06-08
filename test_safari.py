#!/usr/bin/env python3
"""
test_safari.py — Safari tests via AppleScript JS injection
Drives the real Safari app, runs JS assertions, reads results back.
"""
import os, sys, subprocess, json, time

APP_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), 'claude_architect_quiz.html'))
APP_URL  = f'file://{APP_PATH}'

results = []

def test(name, fn):
    try:
        fn()
        results.append((True, name, ''))
        print(f'  \033[92mPASS\033[0m {name}')
    except Exception as e:
        results.append((False, name, str(e)))
        print(f'  \033[91mFAIL\033[0m {name} — {e}')

def run_js(js):
    """Run JS in the frontmost Safari tab and return the result as a string."""
    # Escape backslashes and double-quotes for AppleScript
    escaped = js.replace('\\', '\\\\').replace('"', '\\"')
    script = f'''
tell application "Safari"
    set result to do JavaScript "{escaped}" in front document
    return result
end tell
'''
    r = subprocess.run(['osascript', '-e', script], capture_output=True, text=True, timeout=15)
    if r.returncode != 0:
        raise RuntimeError(f'AppleScript error: {r.stderr.strip()}')
    return r.stdout.strip()

def wait_for_js(js_condition, timeout=10, poll=0.5):
    """Poll until JS expression returns truthy."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            val = run_js(f'String({js_condition})')
            if val.lower() not in ('false', 'null', 'undefined', '0', ''):
                return val
        except Exception:
            pass
        time.sleep(poll)
    raise TimeoutError(f'Timed out waiting for: {js_condition}')

def navigate_js(screen):
    run_js(f"Router.navigate('{screen}')")
    time.sleep(0.8)

def open_safari():
    """Open the app URL in Safari."""
    script = f'''
tell application "Safari"
    activate
    open location "{APP_URL}"
    delay 3
end tell
'''
    subprocess.run(['osascript', '-e', script], timeout=15)
    # Wait for app JS to boot
    wait_for_js("typeof Router !== 'undefined'", timeout=20)
    time.sleep(1)

def run_all():
    print('Opening Safari...')
    open_safari()

    # ─── 1. DASHBOARD ────────────────────────────────────────────
    print('\n=== 1. Dashboard ===')

    def t_loads():
        val = run_js("document.querySelector('h1') ? document.querySelector('h1').innerText : ''")
        assert 'Study Dashboard' in val, f'Got: {val}'

    def t_dark_mode():
        val = run_js("document.documentElement.getAttribute('data-theme')")
        assert val == 'dark', f'Got: {val}'

    def t_question_count():
        val = run_js("document.body.innerText.includes('1157')")
        assert val == 'true', 'Count not shown'

    def t_start_btn():
        val = run_js("!!document.querySelector('button')")
        assert val == 'true'

    def t_theme_toggle():
        run_js("document.getElementById('theme-toggle').click()")
        time.sleep(0.3)
        val = run_js("document.documentElement.getAttribute('data-theme')")
        assert val == 'light', f'Expected light, got {val}'
        run_js("document.getElementById('theme-toggle').click()")
        time.sleep(0.3)

    def t_localStorage_works():
        run_js("localStorage.setItem('safari_test','ok')")
        val = run_js("localStorage.getItem('safari_test')")
        assert val == 'ok', f'localStorage not working: {val}'
        run_js("localStorage.removeItem('safari_test')")

    test('Dashboard loads', t_loads)
    test('Dark mode is default', t_dark_mode)
    test('1157 count visible', t_question_count)
    test('Buttons present', t_start_btn)
    test('Theme toggle works', t_theme_toggle)
    test('localStorage works on file://', t_localStorage_works)

    # ─── 2. MODE SELECT ──────────────────────────────────────────
    print('\n=== 2. Mode selection ===')

    def t_mode_cards():
        navigate_js('mode_select')
        val = run_js("document.querySelectorAll('.mode-card').length")
        assert val == '3', f'Expected 3 mode cards, got {val}'

    def t_exam_card():
        val = run_js("document.body.innerText.includes('Exam Simulation')")
        assert val == 'true'

    def t_drill_card():
        val = run_js("document.body.innerText.includes('Domain Drill')")
        assert val == 'true'

    def t_weak_card():
        val = run_js("document.body.innerText.includes('Weak Areas')")
        assert val == 'true'

    test('3 mode cards shown', t_mode_cards)
    test('Exam Simulation card present', t_exam_card)
    test('Domain Drill card present', t_drill_card)
    test('Weak Areas card present', t_weak_card)

    # ─── 3. EXAM CONFIG ──────────────────────────────────────────
    print('\n=== 3. Exam config ===')

    def t_exam_config_loads():
        navigate_js('exam_config')
        val = run_js("document.querySelectorAll('.config-panel').length")
        assert val == '1', f'Config panel not found'

    def t_default_60():
        val = run_js("document.querySelector('.preset-btn.active') ? document.querySelector('.preset-btn.active').innerText : ''")
        assert '60' in val, f'Expected 60 active, got: {val}'

    def t_custom_count():
        run_js("document.getElementById('exam-count-custom').value = '33'; document.getElementById('exam-count-custom').dispatchEvent(new Event('input'))")
        time.sleep(0.3)
        val = run_js("document.getElementById('exam-count-display').innerText")
        assert '33' in val, f'Custom count not reflected: {val}'

    def t_timer_modes():
        run_js("document.getElementById('timer-perq').click()")
        time.sleep(0.2)
        val = run_js("document.getElementById('timer-perq').className")
        assert 'selected' in val
        run_js("document.getElementById('timer-overall').click()")
        time.sleep(0.2)
        val = run_js("document.getElementById('overall-minutes') ? 'visible' : 'hidden'")
        assert val == 'visible'

    test('Exam config panel loads', t_exam_config_loads)
    test('60q preset active by default', t_default_60)
    test('Custom count accepted', t_custom_count)
    test('Timer modes selectable', t_timer_modes)

    # ─── 4. QUIZ FLOW ────────────────────────────────────────────
    print('\n=== 4. Quiz flow ===')

    def start_exam_js(count=5, timer='overall', mins=60):
        navigate_js('exam_config')
        time.sleep(0.5)
        run_js(f"document.getElementById('exam-count-custom').value='{count}'; document.getElementById('exam-count-custom').dispatchEvent(new Event('input'))")
        time.sleep(0.3)
        if timer == 'overall':
            run_js("document.getElementById('timer-overall').click()")
            run_js(f"document.getElementById('overall-minutes').value='{mins}'")
        else:
            run_js("document.getElementById('timer-perq').click()")
        run_js("startExam()")
        time.sleep(1)
        wait_for_js("document.querySelector('.question-text')", timeout=8)

    def t_quiz_loads():
        start_exam_js(5)
        val = run_js("document.querySelector('.question-text') ? 'yes' : 'no'")
        assert val == 'yes'

    def t_counter():
        val = run_js("document.querySelector('.q-counter') ? document.querySelector('.q-counter').innerText : ''")
        assert 'Question 1 of 5' in val, f'Got: {val}'

    def t_four_choices():
        val = run_js("document.querySelectorAll('.choice-btn').length")
        assert val == '4', f'Got {val} choices'

    def t_no_feedback():
        run_js("document.querySelector('.choice-btn[data-letter=\"A\"]').click()")
        time.sleep(0.4)
        correct = run_js("document.querySelectorAll('.choice-btn.correct').length")
        wrong   = run_js("document.querySelectorAll('.choice-btn.wrong').length")
        assert correct == '0' and wrong == '0', f'Feedback shown: correct={correct} wrong={wrong}'

    def t_next_btn():
        val = run_js("Array.from(document.querySelectorAll('button')).some(b => b.innerText.includes('Next')) ? 'yes' : 'no'")
        assert val == 'yes'

    def t_question_text_not_empty():
        val = run_js("document.querySelector('.question-text').innerText.length")
        assert int(val) > 10, f'Question text too short: {val}'

    test('Quiz loads with question text', t_quiz_loads)
    test('Question counter shows 1 of 5', t_counter)
    test('4 choices rendered', t_four_choices)
    test('No feedback in exam mode', t_no_feedback)
    test('Next button appears after answering', t_next_btn)
    test('Question text not empty', t_question_text_not_empty)

    # ─── 5. EXAM RESULTS ─────────────────────────────────────────
    print('\n=== 5. Exam results ===')

    def complete_exam_safari():
        start_exam_js(5)
        for i in range(5):
            wait_for_js("document.querySelector('.question-text')", timeout=5)
            run_js("document.querySelector('.choice-btn[data-letter=\"A\"]').click()")
            time.sleep(0.3)
            has_submit = run_js("Array.from(document.querySelectorAll('button')).some(b=>b.innerText.includes('Submit')) ? 'yes':'no'")
            has_next   = run_js("Array.from(document.querySelectorAll('button')).some(b=>b.innerText.includes('Next')) ? 'yes':'no'")
            if has_submit == 'yes':
                run_js("Array.from(document.querySelectorAll('button')).find(b=>b.innerText.includes('Submit')).click()")
                break
            elif has_next == 'yes':
                run_js("Array.from(document.querySelectorAll('button')).find(b=>b.innerText.includes('Next')).click()")
            time.sleep(0.3)
        wait_for_js("document.querySelector('.score-hero')", timeout=8)

    def t_results_screen():
        complete_exam_safari()
        val = run_js("document.querySelector('.score-hero') ? 'yes' : 'no'")
        assert val == 'yes'

    def t_score_range():
        val = run_js("parseInt(document.querySelector('.score-number').innerText.trim())")
        score = int(val)
        assert 100 <= score <= 1000, f'Score {score} out of range'

    def t_pass_fail_badge():
        val = run_js("document.querySelector('.pass-badge') ? 'yes' : 'no'")
        assert val == 'yes'

    def t_review_list():
        val = run_js("document.querySelectorAll('.review-item').length")
        assert int(val) > 0, f'No review items'

    def t_domain_table():
        val = run_js("document.querySelector('.results-table') ? 'yes' : 'no'")
        assert val == 'yes'

    test('Results screen shown', t_results_screen)
    test('Score is 100-1000', t_score_range)
    test('Pass/Fail badge shown', t_pass_fail_badge)
    test('Review list shown', t_review_list)
    test('Domain breakdown table', t_domain_table)

    # ─── 6. DOMAIN DRILL ─────────────────────────────────────────
    print('\n=== 6. Domain Drill ===')

    def start_drill_safari(count=3):
        navigate_js('drill_config')
        time.sleep(0.5)
        run_js("document.getElementById('do-D1').click()")
        time.sleep(0.3)
        run_js(f"document.getElementById('drill-count-custom').value='{count}'; document.getElementById('drill-count-custom').dispatchEvent(new Event('input'))")
        time.sleep(0.3)
        run_js("startDrill()")
        time.sleep(1)
        wait_for_js("document.querySelector('.question-text')", timeout=8)

    def t_drill_loads():
        start_drill_safari(3)
        val = run_js("document.querySelector('.question-text') ? 'yes' : 'no'")
        assert val == 'yes'

    def t_no_timer_drill():
        val = run_js("document.getElementById('timer-display') ? 'yes' : 'no'")
        assert val == 'no', 'Timer should not be present in drill'

    def t_immediate_feedback():
        run_js("document.querySelector('.choice-btn[data-letter=\"A\"]').click()")
        time.sleep(0.5)
        correct = int(run_js("document.querySelectorAll('.choice-btn.correct').length"))
        wrong   = int(run_js("document.querySelectorAll('.choice-btn.wrong').length"))
        assert correct > 0 or wrong > 0, 'No immediate feedback'

    def t_explanation_panel():
        val = run_js("document.querySelector('.explanation-panel') ? 'yes' : 'no'")
        assert val == 'yes'

    test('Drill loads', t_drill_loads)
    test('No timer in drill mode', t_no_timer_drill)
    test('Immediate feedback after answer', t_immediate_feedback)
    test('Explanation panel shown', t_explanation_panel)

    # ─── 7. WEAK AREAS ───────────────────────────────────────────
    print('\n=== 7. Weak Areas ===')

    def t_weak_config():
        navigate_js('weak_config')
        time.sleep(0.5)
        val = run_js("document.querySelector('.config-panel') ? 'yes' : 'no'")
        assert val == 'yes'

    def t_weak_starts():
        run_js("document.getElementById('weak-count-custom').value='3'; document.getElementById('weak-count-custom').dispatchEvent(new Event('input'))")
        time.sleep(0.3)
        pool = int(run_js("Engine.getWeakPoolSize()"))
        count = min(3, pool)
        if count > 0:
            run_js(f"startWeak({pool})")
            time.sleep(1)
            wait_for_js("document.querySelector('.question-text')", timeout=8)
            val = run_js("document.querySelector('.question-text') ? 'yes' : 'no'")
            assert val == 'yes'
        else:
            # Pool empty — just check the empty state is handled gracefully
            val = run_js("document.querySelector('.empty-state') ? 'yes' : 'no'")
            assert val == 'yes', 'Empty pool not handled gracefully'

    test('Weak Areas config loads', t_weak_config)
    test('Weak Areas starts or shows empty state', t_weak_starts)

    # ─── 8. PROGRESS & EDGE CASES ───────────────────────────────
    print('\n=== 8. Progress & edge cases ===')

    def t_dashboard_stats():
        navigate_js('dashboard')
        time.sleep(0.5)
        val = run_js("document.body.innerText.includes('%')")
        assert val == 'true', 'No % on dashboard'

    def t_session_history():
        val = run_js("document.body.innerText.includes('Exam Sim') || document.body.innerText.includes('Domain Drill')")
        assert val == 'true', 'No session history'

    def t_inline_tests():
        val = run_js("runTests()")
        assert val == 'true', f'runTests() returned: {val}'

    def t_score_formula():
        r = run_js("JSON.stringify([Engine.calculateScaledScore(60,60), Engine.calculateScaledScore(0,60), Engine.calculateScaledScore(47,60), Engine.isPassing(720), Engine.isPassing(719)])")
        data = json.loads(r)
        assert data == [1000, 100, 805, True, False], f'Got: {data}'

    def t_invalid_import():
        r = run_js("(function(){ try{ Storage.importProgress('bad{json'); return 'ok'; } catch(e){ return e.message; } })()")
        assert 'Invalid JSON' in r or 'JSON' in r.upper(), f'Got: {r}'

    def t_bucket_counts():
        r = run_js("JSON.stringify(Storage.getBucketCounts())")
        data = json.loads(r)
        total = data['new'] + data['learning'] + data['mastered']
        assert total == 1157, f'Bucket total {total} != 1157'

    test('Dashboard shows % stats', t_dashboard_stats)
    test('Session history present', t_session_history)
    test('runTests() all pass', t_inline_tests)
    test('Score formula correct', t_score_formula)
    test('Invalid import handled', t_invalid_import)
    test('Bucket counts total 1157', t_bucket_counts)

    # ─── 9. TIMERS ───────────────────────────────────────────────
    print('\n=== 9. Timer behavior ===')

    def t_perq_timer():
        navigate_js('exam_config')
        time.sleep(0.5)
        run_js("document.getElementById('exam-count-custom').value='2'; document.getElementById('exam-count-custom').dispatchEvent(new Event('input'))")
        time.sleep(0.2)
        run_js("document.getElementById('timer-perq').click()")
        run_js("startExam()")
        time.sleep(1)
        wait_for_js("document.querySelector('.question-text')", timeout=8)
        val = run_js("document.getElementById('timer-display') ? document.getElementById('timer-display').innerText : ''")
        assert ':' in val, f'Timer not mm:ss: {val}'

    def t_timer_decrements():
        t1 = run_js("document.getElementById('timer-display').innerText")
        time.sleep(2.2)
        t2 = run_js("document.getElementById('timer-display').innerText")
        assert t1 != t2, f'Timer stuck at {t1}'

    def t_overall_timer():
        navigate_js('exam_config')
        time.sleep(0.5)
        run_js("document.getElementById('exam-count-custom').value='2'; document.getElementById('exam-count-custom').dispatchEvent(new Event('input'))")
        time.sleep(0.2)
        run_js("document.getElementById('timer-overall').click()")
        run_js("document.getElementById('overall-minutes').value='5'")
        run_js("startExam()")
        time.sleep(1)
        wait_for_js("document.querySelector('.question-text')", timeout=8)
        val = run_js("document.getElementById('timer-display') ? document.getElementById('timer-display').innerText : ''")
        assert ':' in val, f'Overall timer not mm:ss: {val}'

    test('Per-question timer visible mm:ss', t_perq_timer)
    test('Timer counts down', t_timer_decrements)
    test('Overall timer visible', t_overall_timer)

    # Close Safari when done
    subprocess.run(['osascript', '-e', 'tell application "Safari" to close front window'], timeout=5)

run_all()

passed = sum(1 for p,_,_ in results if p)
total  = len(results)
print(f'\n{"="*60}')
print(f'SAFARI RESULTS: {passed}/{total} passed')
if passed == total:
    print('ALL SAFARI TESTS PASSED ✓')
else:
    print('\nFailed:')
    for p,n,e in results:
        if not p: print(f'  ✗ {n}\n    {e}')
print('='*60)
sys.exit(0 if passed == total else 1)
