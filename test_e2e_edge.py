#!/usr/bin/env python3
"""
test_e2e_edge.py — Full E2E tests on Microsoft Edge
"""
import os, sys
from playwright.sync_api import sync_playwright

APP_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), 'claude_architect_quiz.html'))
APP_URL   = f'file://{APP_PATH}'
EDGE      = '/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge'

results = []

def test(name, fn):
    try:
        fn()
        results.append((True, name, ''))
        print(f'  \033[92mPASS\033[0m {name}')
    except Exception as e:
        results.append((False, name, str(e)))
        print(f'  \033[91mFAIL\033[0m {name} — {e}')

def run_all():
    with sync_playwright() as pw:
        browser = pw.chromium.launch(
            executable_path=EDGE,
            headless=True,
            args=['--disable-web-security', '--allow-file-access-from-files']
        )
        ctx = browser.new_context()
        page = ctx.new_page()
        page.goto(APP_URL, wait_until='domcontentloaded', timeout=20000)
        page.wait_for_selector('h1', timeout=10000)

        # ─── 1. DASHBOARD ────────────────────────────────────────────
        print('\n=== 1. Dashboard ===')
        def t_loads():               assert 'Study Dashboard' in page.inner_text('h1')
        def t_dark_mode():           assert page.evaluate("document.documentElement.getAttribute('data-theme')") == 'dark'
        def t_question_count():      assert '1157' in page.inner_text('body')
        def t_start_btn():           assert page.locator('button:has-text("Start Quiz")').count() > 0
        def t_export_btn():          assert page.locator('button:has-text("Export")').count() > 0
        def t_theme_toggle():
            page.click('#theme-toggle')
            assert page.evaluate("document.documentElement.getAttribute('data-theme')") == 'light'
            page.click('#theme-toggle')

        test('Dashboard loads', t_loads)
        test('Dark mode default', t_dark_mode)
        test('1157 count visible', t_question_count)
        test('Start Quiz button present', t_start_btn)
        test('Export button present', t_export_btn)
        test('Theme toggle works', t_theme_toggle)

        # ─── 2. MODE SELECT ──────────────────────────────────────────
        print('\n=== 2. Mode selection ===')
        def t_three_modes():
            page.click('button:has-text("Start Quiz")')
            page.wait_for_selector('.mode-card', timeout=5000)
            assert page.locator('.mode-card').count() == 3
        def t_back():
            page.click('button:has-text("← Dashboard")')
            page.wait_for_selector('h1', timeout=3000)
            assert 'Study Dashboard' in page.inner_text('h1')

        test('3 mode cards shown', t_three_modes)
        test('Back to dashboard works', t_back)

        # ─── 3. EXAM CONFIG ──────────────────────────────────────────
        print('\n=== 3. Exam config ===')
        def t_exam_config():
            page.click('button:has-text("Start Quiz")')
            page.wait_for_selector('.mode-card')
            page.click('.mode-card:has-text("Exam Simulation")')
            page.wait_for_selector('.config-panel')
            assert page.locator('.config-panel').count() > 0
        def t_default_preset():      assert '60' in page.locator('.preset-btn.active').inner_text()
        def t_custom_count():
            page.fill('#exam-count-custom', '42')
            page.wait_for_timeout(300)
            assert '42 questions' in page.inner_text('#exam-count-display')
        def t_invalid_count():
            page.fill('#exam-count-custom', '0')
            page.wait_for_timeout(300)
            assert page.locator('#exam-count-error').is_visible()
        def t_per_q_timer():
            page.click('#timer-perq')
            assert 'selected' in page.get_attribute('#timer-perq', 'class')
        def t_overall_timer():
            page.click('#timer-overall')
            assert page.locator('#overall-minutes').is_visible()

        test('Exam config loads', t_exam_config)
        test('60q preset active by default', t_default_preset)
        test('Custom count accepted', t_custom_count)
        test('Invalid count shows error', t_invalid_count)
        test('Per-question timer selectable', t_per_q_timer)
        test('Overall timer shows minutes input', t_overall_timer)

        # ─── 4. EXAM QUIZ ────────────────────────────────────────────
        print('\n=== 4. Exam quiz flow ===')
        def start_exam(count=5, timer='overall', mins=60):
            page.evaluate("Router.navigate('exam_config')")
            page.wait_for_selector('.config-panel', timeout=5000)
            page.fill('#exam-count-custom', str(count))
            page.wait_for_timeout(200)
            if timer == 'per_question':
                page.click('#timer-perq')
            else:
                page.click('#timer-overall')
                page.fill('#overall-minutes', str(mins))
            page.click('button:has-text("Start Exam")')
            page.wait_for_selector('.question-text', timeout=8000)

        def t_quiz_loads():
            page.evaluate("Router.navigate('mode_select')")
            page.wait_for_selector('.mode-card')
            start_exam(5)
            assert page.locator('.question-text').is_visible()
        def t_counter():             assert 'Question 1 of 5' in page.inner_text('.q-counter')
        def t_four_choices():        assert page.locator('.choice-btn').count() == 4
        def t_no_feedback():
            page.click('.choice-btn[data-letter="A"]')
            page.wait_for_timeout(300)
            assert page.locator('.choice-btn.correct').count() == 0
            assert page.locator('.choice-btn.wrong').count() == 0
        def t_next_btn():            assert page.locator('button:has-text("Next →")').count() > 0
        def t_flag():
            page.click('button:has-text("⚑ Flag")')
            assert page.locator('button:has-text("🚩 Flagged")').count() > 0
        def t_navigator():
            page.click('button:has-text("Navigator")')
            page.wait_for_selector('#q-navigator.open', timeout=3000)
            assert page.locator('#q-navigator.open').count() > 0
        def t_keyboard_a():
            page.click('.nav-cell:nth-child(2)')
            page.wait_for_timeout(200)
            page.keyboard.press('a')
            page.wait_for_timeout(200)
            assert page.locator('.choice-btn.selected').get_attribute('data-letter') == 'A'
        def t_kbd_hint():            assert page.locator('.kbd-hint').is_visible()

        test('Exam quiz loads', t_quiz_loads)
        test('Question counter shows 1 of 5', t_counter)
        test('4 choices rendered', t_four_choices)
        test('No feedback in exam mode', t_no_feedback)
        test('Next button after answering', t_next_btn)
        test('Flag button works', t_flag)
        test('Navigator opens', t_navigator)
        test('Keyboard A selects A', t_keyboard_a)
        test('Keyboard hint shown', t_kbd_hint)

        # ─── 5. EXAM RESULTS ─────────────────────────────────────────
        print('\n=== 5. Exam results ===')
        def complete_exam():
            page.evaluate("Router.navigate('mode_select')")
            page.wait_for_selector('.mode-card')
            start_exam(5)
            for i in range(5):
                page.wait_for_selector('.question-text', timeout=3000)
                page.click('.choice-btn[data-letter="A"]')
                page.wait_for_timeout(200)
                nxt = page.locator('button:has-text("Next →")')
                sub = page.locator('button:has-text("Submit →")')
                if sub.count() > 0: sub.click(); break
                elif nxt.count() > 0: nxt.click()
                page.wait_for_timeout(200)
            page.wait_for_selector('.score-hero', timeout=5000)

        def t_results():             complete_exam(); assert page.locator('.score-hero').is_visible()
        def t_score_range():
            s = int(page.inner_text('.score-number').strip())
            assert 100 <= s <= 1000
        def t_pass_fail():           assert page.locator('.pass-badge').is_visible()
        def t_domain_table():        assert page.locator('.results-table').is_visible()
        def t_review_list():         assert page.locator('.review-item').count() > 0
        def t_session_on_dash():
            page.click('button:has-text("Dashboard")')
            page.wait_for_selector('h1', timeout=3000)
            assert 'Exam Sim' in page.inner_text('body')

        test('Results screen shown', t_results)
        test('Score is 100-1000', t_score_range)
        test('Pass/Fail badge shown', t_pass_fail)
        test('Domain breakdown table', t_domain_table)
        test('Review list shown', t_review_list)
        test('Session saved to dashboard', t_session_on_dash)

        # ─── 6. DOMAIN DRILL ─────────────────────────────────────────
        print('\n=== 6. Domain Drill ===')
        def start_drill(count=3):
            page.evaluate("Router.navigate('drill_config')")
            page.wait_for_selector('.domain-option', timeout=5000)
            page.click('#do-D1')
            page.wait_for_timeout(200)
            page.fill('#drill-count-custom', str(count))
            page.wait_for_timeout(300)
            page.click('button:has-text("Start Drill")')
            page.wait_for_selector('.question-text', timeout=8000)

        def t_drill_loads():         start_drill(3); assert page.locator('.question-text').is_visible()
        def t_no_timer():            assert page.locator('#timer-display').count() == 0
        def t_immediate_feedback():
            page.click('.choice-btn[data-letter="A"]')
            page.wait_for_timeout(400)
            assert page.locator('.choice-btn.correct').count() > 0 or page.locator('.choice-btn.wrong').count() > 0
        def t_explanation():         assert page.locator('.explanation-panel').is_visible()
        def t_space_advances():
            page.click('button:has-text("Next →")')
            page.wait_for_timeout(300)
            page.click('.choice-btn[data-letter="B"]')
            page.wait_for_timeout(300)
            page.keyboard.press('Space')
            page.wait_for_timeout(400)
            assert 'Question 3 of 3' in page.inner_text('.q-counter')
        def t_drill_summary():
            page.click('.choice-btn[data-letter="C"]')
            page.wait_for_timeout(300)
            page.click('button:has-text("Submit →")')
            page.wait_for_selector('.score-hero', timeout=4000)
            assert 'correct out of' in page.inner_text('body')

        test('Drill loads', t_drill_loads)
        test('No timer in drill', t_no_timer)
        test('Immediate feedback shown', t_immediate_feedback)
        test('Explanation panel shown', t_explanation)
        test('Space key advances', t_space_advances)
        test('Summary screen shown', t_drill_summary)

        # ─── 7. WEAK AREAS ───────────────────────────────────────────
        print('\n=== 7. Weak Areas ===')
        def t_weak_loads():
            page.evaluate("Router.navigate('weak_config')")
            page.wait_for_selector('.config-panel', timeout=5000)
            assert page.locator('.config-panel').is_visible()
        def t_weak_starts():
            page.fill('#weak-count-custom', '3')
            page.wait_for_timeout(300)
            page.click('button:has-text("Start Practice")')
            page.wait_for_selector('.question-text', timeout=8000)
            assert page.locator('.question-text').is_visible()
        def t_weak_no_timer():       assert page.locator('#timer-display').count() == 0

        test('Weak Areas config loads', t_weak_loads)
        test('Weak Areas starts', t_weak_starts)
        test('No timer in Weak Areas', t_weak_no_timer)

        # ─── 8. PROGRESS & EDGE CASES ───────────────────────────────
        print('\n=== 8. Progress & edge cases ===')
        def t_dashboard_stats():
            page.evaluate("Router.navigate('dashboard')")
            page.wait_for_selector('h1', timeout=5000)
            assert '%' in page.inner_text('body')
        def t_export():
            with page.expect_download(timeout=5000) as dl:
                page.click('button:has-text("Export")')
            assert dl.value.suggested_filename.endswith('.json')
        def t_inline_tests():
            assert page.evaluate('runTests()') == True
        def t_invalid_import():
            r = page.evaluate("""(() => { try { Storage.importProgress('bad{json'); return 'ok'; } catch(e) { return e.message; } })()""")
            assert 'Invalid JSON' in r or 'JSON' in r.upper()
        def t_score_formula():
            r = page.evaluate('[Engine.calculateScaledScore(60,60), Engine.calculateScaledScore(0,60), Engine.calculateScaledScore(47,60), Engine.isPassing(720), Engine.isPassing(719)]')
            assert r == [1000, 100, 805, True, False]

        test('Dashboard stats update', t_dashboard_stats)
        test('Export downloads JSON', t_export)
        test('runTests() all pass', t_inline_tests)
        test('Invalid import handled', t_invalid_import)
        test('Score formula correct', t_score_formula)

        # ─── 9. TIMERS ───────────────────────────────────────────────
        print('\n=== 9. Timer behavior ===')
        def t_perq_timer():
            page.evaluate("Router.navigate('mode_select')")
            page.wait_for_selector('.mode-card')
            page.evaluate("Router.navigate('exam_config')")
            page.wait_for_selector('.config-panel')
            page.fill('#exam-count-custom', '2')
            page.wait_for_timeout(200)
            page.click('#timer-perq')
            page.click('button:has-text("Start Exam")')
            page.wait_for_selector('.question-text', timeout=8000)
            assert page.locator('#timer-display').is_visible()
            assert ':' in page.inner_text('#timer-display')
        def t_timer_decrements():
            t1 = page.inner_text('#timer-display')
            page.wait_for_timeout(2200)
            t2 = page.inner_text('#timer-display')
            assert t1 != t2, f'Timer stuck: {t1}'
        def t_overall_timer():
            page.evaluate("Router.navigate('exam_config')")
            page.wait_for_selector('.config-panel')
            page.fill('#exam-count-custom', '2')
            page.wait_for_timeout(200)
            page.click('#timer-overall')
            page.fill('#overall-minutes', '5')
            page.click('button:has-text("Start Exam")')
            page.wait_for_selector('.question-text', timeout=8000)
            assert page.locator('#timer-display').is_visible()
            assert ':' in page.inner_text('#timer-display')

        test('Per-question timer visible mm:ss', t_perq_timer)
        test('Timer counts down', t_timer_decrements)
        test('Overall timer visible', t_overall_timer)

        ctx.close()
        browser.close()

run_all()

passed = sum(1 for p,_,_ in results if p)
total  = len(results)
print(f'\n{"="*60}')
print(f'EDGE RESULTS: {passed}/{total} passed')
if passed == total:
    print('ALL EDGE TESTS PASSED ✓')
else:
    print('\nFailed:')
    for p,n,e in results:
        if not p: print(f'  ✗ {n}\n    {e}')
print('='*60)
sys.exit(0 if passed == total else 1)
