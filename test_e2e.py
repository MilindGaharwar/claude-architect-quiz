#!/usr/bin/env python3
"""
test_e2e.py — End-to-end browser tests using Playwright + system Chrome
Run: python3 test_e2e.py
"""
import os, sys, time
from playwright.sync_api import sync_playwright, expect

APP_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), 'claude_architect_quiz.html'))
APP_URL   = f'file://{APP_PATH}'
CHROME    = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'

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
            executable_path=CHROME,
            headless=True,
            args=['--disable-web-security', '--allow-file-access-from-files']
        )
        ctx = browser.new_context()
        page = ctx.new_page()

        # ─── 1. DASHBOARD ────────────────────────────────────────────
        print('\n=== 1. Dashboard loads ===')

        def t_loads():
            page.goto(APP_URL)
            page.wait_for_selector('h1', timeout=8000)
            assert 'Study Dashboard' in page.inner_text('h1')

        def t_dark_mode_default():
            theme = page.evaluate("document.documentElement.getAttribute('data-theme')")
            assert theme == 'dark', f'Expected dark, got {theme}'

        def t_question_counts_shown():
            text = page.inner_text('body')
            assert '1157' in text, 'Total question count not shown'

        def t_start_quiz_btn():
            btn = page.locator('button', has_text='Start Quiz')
            assert btn.count() > 0

        def t_export_btn():
            assert page.locator('button', has_text='Export').count() > 0

        def t_import_btn():
            assert page.locator('label', has_text='Import').count() > 0

        def t_theme_toggle():
            page.click('#theme-toggle')
            theme = page.evaluate("document.documentElement.getAttribute('data-theme')")
            assert theme == 'light', f'Expected light after toggle, got {theme}'
            page.click('#theme-toggle')  # back to dark

        test('App loads, shows Study Dashboard', t_loads)
        test('Dark mode is default', t_dark_mode_default)
        test('1157 question count visible', t_question_counts_shown)
        test('Start Quiz button present', t_start_quiz_btn)
        test('Export button present', t_export_btn)
        test('Import button present', t_import_btn)
        test('Theme toggle switches light/dark', t_theme_toggle)

        # ─── 2. MODE SELECT ──────────────────────────────────────────
        print('\n=== 2. Mode selection ===')

        def t_mode_select_shows_3_modes():
            page.click('button:has-text("Start Quiz")')
            page.wait_for_selector('.mode-card', timeout=4000)
            assert page.locator('.mode-card').count() == 3

        def t_exam_card_present():
            assert page.locator('.mode-card', has_text='Exam Simulation').count() > 0

        def t_drill_card_present():
            assert page.locator('.mode-card', has_text='Domain Drill').count() > 0

        def t_weak_card_present():
            assert page.locator('.mode-card', has_text='Weak Areas').count() > 0

        def t_back_to_dashboard():
            page.click('button:has-text("← Dashboard")')
            page.wait_for_selector('h1', timeout=3000)
            assert 'Study Dashboard' in page.inner_text('h1')

        test('Mode select shows 3 mode cards', t_mode_select_shows_3_modes)
        test('Exam Simulation card present', t_exam_card_present)
        test('Domain Drill card present', t_drill_card_present)
        test('Weak Areas card present', t_weak_card_present)
        test('Back button returns to dashboard', t_back_to_dashboard)

        # ─── 3. EXAM CONFIG ──────────────────────────────────────────
        print('\n=== 3. Exam config ===')

        def goto_exam_config():
            page.goto(APP_URL)
            page.click('button:has-text("Start Quiz")')
            page.wait_for_selector('.mode-card')
            page.click('.mode-card:has-text("Exam Simulation")')
            page.wait_for_selector('.config-panel')

        def t_exam_config_loads():
            goto_exam_config()
            assert page.locator('.config-panel').count() > 0

        def t_preset_60_active_by_default():
            active = page.locator('.preset-btn.active')
            assert '60' in active.inner_text()

        def t_preset_25_selectable():
            page.click('.preset-btn:has-text("25")')
            assert '25 questions' in page.inner_text('#exam-count-display')

        def t_preset_100_selectable():
            page.click('.preset-btn:has-text("100")')
            assert '100 questions' in page.inner_text('#exam-count-display')

        def t_custom_count_valid():
            page.fill('#exam-count-custom', '37')
            page.wait_for_timeout(300)
            assert '37 questions' in page.inner_text('#exam-count-display')

        def t_custom_count_invalid():
            page.fill('#exam-count-custom', '9999')
            page.wait_for_timeout(300)
            err = page.locator('#exam-count-error')
            assert err.is_visible()

        def t_timer_per_question_selectable():
            page.click('#timer-perq')
            assert 'selected' in page.get_attribute('#timer-perq', 'class')

        def t_timer_overall_shows_minutes_input():
            page.click('#timer-overall')
            assert page.locator('#overall-minutes').is_visible()

        test('Exam config panel loads', t_exam_config_loads)
        test('60q preset active by default', t_preset_60_active_by_default)
        test('25q preset selectable', t_preset_25_selectable)
        test('100q preset selectable', t_preset_100_selectable)
        test('Custom count 37 accepted', t_custom_count_valid)
        test('Custom count 9999 shows error', t_custom_count_invalid)
        test('Per-question timer selectable', t_timer_per_question_selectable)
        test('Overall timer shows minutes input', t_timer_overall_shows_minutes_input)

        # ─── 4. EXAM QUIZ FLOW ───────────────────────────────────────
        print('\n=== 4. Exam quiz flow ===')

        def start_exam(count=5, timer_mode='overall', minutes=60):
            page.goto(APP_URL)
            page.click('button:has-text("Start Quiz")')
            page.wait_for_selector('.mode-card')
            page.click('.mode-card:has-text("Exam Simulation")')
            page.wait_for_selector('.config-panel')
            page.fill('#exam-count-custom', str(count))
            page.wait_for_timeout(300)
            if timer_mode == 'overall':
                page.click('#timer-overall')
                page.fill('#overall-minutes', str(minutes))
            else:
                page.click('#timer-perq')
            page.click('button:has-text("Start Exam")')
            page.wait_for_selector('.question-text', timeout=5000)

        def t_exam_quiz_loads():
            start_exam(count=5)
            assert page.locator('.question-text').is_visible()

        def t_question_counter_shows():
            assert 'Question 1 of 5' in page.inner_text('.q-counter')

        def t_choices_rendered():
            assert page.locator('.choice-btn').count() == 4

        def t_no_feedback_in_exam_mode():
            # Click answer A
            page.click('.choice-btn[data-letter="A"]')
            page.wait_for_timeout(300)
            # Should NOT see green/red correct/wrong styling
            correct_visible = page.locator('.choice-btn.correct').count()
            wrong_visible   = page.locator('.choice-btn.wrong').count()
            assert correct_visible == 0 and wrong_visible == 0, \
                f'Feedback shown in exam mode: correct={correct_visible} wrong={wrong_visible}'

        def t_next_btn_after_answer():
            assert page.locator('button:has-text("Next →")').count() > 0

        def t_flag_button_works():
            page.click('button:has-text("⚑ Flag")')
            assert page.locator('button:has-text("🚩 Flagged")').count() > 0

        def t_navigator_opens():
            page.click('button:has-text("Navigator")')
            page.wait_for_selector('#q-navigator.open', timeout=2000)
            assert page.locator('#q-navigator.open').count() > 0

        def t_keyboard_a_selects():
            # Navigate to question 2 first (fresh, no answer)
            page.keyboard.press('Escape')
            page.click(f'.nav-cell:nth-child(2)')
            page.wait_for_timeout(300)
            page.keyboard.press('a')
            page.wait_for_timeout(300)
            selected = page.locator('.choice-btn.selected')
            assert selected.count() > 0
            assert selected.get_attribute('data-letter') == 'A'

        def t_keyboard_b_selects():
            page.keyboard.press('b')
            page.wait_for_timeout(300)
            selected = page.locator('.choice-btn.selected')
            assert selected.get_attribute('data-letter') == 'B'

        def t_keyboard_hint_shown():
            assert page.locator('.kbd-hint').is_visible()

        def t_progress_bar_shown():
            assert page.locator('.progress-bar').count() > 0

        def t_domain_badge_shown():
            assert page.locator('.q-domain-badge').count() > 0

        test('Exam quiz loads with question text', t_exam_quiz_loads)
        test('Question counter shows "1 of 5"', t_question_counter_shows)
        test('4 choice buttons rendered', t_choices_rendered)
        test('No correct/wrong feedback shown in exam mode', t_no_feedback_in_exam_mode)
        test('Next button appears after answering', t_next_btn_after_answer)
        test('Flag button works', t_flag_button_works)
        test('Navigator opens', t_navigator_opens)
        test('Keyboard A selects choice A', t_keyboard_a_selects)
        test('Keyboard B changes selection to B', t_keyboard_b_selects)
        test('Keyboard hint shown below choices', t_keyboard_hint_shown)
        test('Progress bar visible', t_progress_bar_shown)
        test('Domain badge visible', t_domain_badge_shown)

        # ─── 5. EXAM RESULTS ─────────────────────────────────────────
        print('\n=== 5. Exam results ===')

        def complete_exam_and_get_results():
            start_exam(count=5)
            # Answer all 5 questions and navigate through
            for i in range(5):
                page.wait_for_selector('.question-text', timeout=3000)
                page.click('.choice-btn[data-letter="A"]')
                page.wait_for_timeout(200)
                next_btn = page.locator('button:has-text("Next →")')
                submit_btn = page.locator('button:has-text("Submit →")')
                if next_btn.count() > 0:
                    next_btn.click()
                elif submit_btn.count() > 0:
                    submit_btn.click()
                    break
                page.wait_for_timeout(200)
            page.wait_for_selector('.score-hero', timeout=5000)

        def t_results_screen_shows():
            complete_exam_and_get_results()
            assert page.locator('.score-hero').is_visible()

        def t_score_number_shown():
            score_text = page.inner_text('.score-number')
            score = int(score_text.strip())
            assert 100 <= score <= 1000, f'Score {score} out of range'

        def t_pass_fail_badge_shown():
            assert page.locator('.pass-badge').is_visible()

        def t_domain_breakdown_table():
            assert page.locator('.results-table').is_visible()

        def t_question_review_list():
            assert page.locator('.review-item').count() > 0

        def t_filter_incorrect():
            page.click('.filter-btn:has-text("Incorrect")')
            page.wait_for_timeout(300)
            # Filter button should be active
            assert 'active' in page.locator('.filter-btn:has-text("Incorrect")').get_attribute('class')

        def t_filter_all():
            page.click('.filter-btn:has-text("All")')
            page.wait_for_timeout(300)
            assert page.locator('.review-item').count() == 5

        def t_new_quiz_btn():
            assert page.locator('button:has-text("New Quiz")').count() > 0

        def t_dashboard_btn():
            assert page.locator('button:has-text("Dashboard")').count() > 0

        def t_session_saved_to_dashboard():
            page.click('button:has-text("Dashboard")')
            page.wait_for_selector('h1', timeout=3000)
            # Session history should show the exam we just did
            text = page.inner_text('body')
            assert 'Exam Sim' in text

        test('Results screen shows after completing exam', t_results_screen_shows)
        test('Score number is 100-1000', t_score_number_shown)
        test('Pass/Fail badge shown', t_pass_fail_badge_shown)
        test('Domain breakdown table shown', t_domain_breakdown_table)
        test('Question review list shown', t_question_review_list)
        test('Filter Incorrect works', t_filter_incorrect)
        test('Filter All restores full list', t_filter_all)
        test('New Quiz button present', t_new_quiz_btn)
        test('Dashboard button present', t_dashboard_btn)
        test('Session saved and shown on dashboard', t_session_saved_to_dashboard)

        # ─── 6. DOMAIN DRILL ─────────────────────────────────────────
        print('\n=== 6. Domain Drill flow ===')

        def start_drill(domain='D1', count=3):
            page.goto(APP_URL)
            page.click('button:has-text("Start Quiz")')
            page.wait_for_selector('.mode-card')
            page.click('.mode-card:has-text("Domain Drill")')
            page.wait_for_selector('.domain-option')
            page.click(f'#do-{domain}')
            page.wait_for_timeout(200)
            page.fill('#drill-count-custom', str(count))
            page.wait_for_timeout(300)
            page.click('button:has-text("Start Drill")')
            page.wait_for_selector('.question-text', timeout=5000)

        def t_drill_loads():
            start_drill(count=3)
            assert page.locator('.question-text').is_visible()

        def t_drill_no_timer():
            assert page.locator('#timer-display').count() == 0

        def t_drill_immediate_feedback_correct():
            # Find correct answer from DOM
            # We need to look at review after — just click A and check feedback appears
            page.click('.choice-btn[data-letter="A"]')
            page.wait_for_timeout(400)
            # Either .correct or .wrong should appear
            correct = page.locator('.choice-btn.correct').count()
            wrong   = page.locator('.choice-btn.wrong').count()
            assert correct > 0 or wrong > 0, 'No immediate feedback shown'

        def t_drill_explanation_shown():
            assert page.locator('.explanation-panel').is_visible()

        def t_drill_next_question():
            page.click('button:has-text("Next →")')
            page.wait_for_timeout(300)
            assert 'Question 2 of 3' in page.inner_text('.q-counter')

        def t_drill_space_advances():
            # Answer question 2
            page.click('.choice-btn[data-letter="B"]')
            page.wait_for_timeout(300)
            page.keyboard.press('Space')
            page.wait_for_timeout(400)
            assert 'Question 3 of 3' in page.inner_text('.q-counter')

        def t_drill_summary_shown():
            # Answer last question
            page.click('.choice-btn[data-letter="C"]')
            page.wait_for_timeout(300)
            page.click('button:has-text("Submit →")')
            page.wait_for_selector('.score-hero', timeout=4000)
            assert page.locator('.score-hero').is_visible()

        def t_drill_retry_missed_btn():
            # Only shows if there are misses — just check the summary screen loaded
            text = page.inner_text('body')
            assert 'correct out of' in text

        test('Drill quiz loads', t_drill_loads)
        test('No timer in drill mode', t_drill_no_timer)
        test('Immediate feedback after answering', t_drill_immediate_feedback_correct)
        test('Explanation panel shown after answer', t_drill_explanation_shown)
        test('Next button advances to Q2', t_drill_next_question)
        test('Space key advances to Q3', t_drill_space_advances)
        test('Summary screen shown at completion', t_drill_summary_shown)
        test('Summary shows score text', t_drill_retry_missed_btn)

        # ─── 7. WEAK AREAS ───────────────────────────────────────────
        print('\n=== 7. Weak Areas flow ===')

        def t_weak_config_loads():
            page.goto(APP_URL)
            page.click('button:has-text("Start Quiz")')
            page.wait_for_selector('.mode-card')
            page.click('.mode-card:has-text("Weak Areas")')
            page.wait_for_selector('.config-panel')
            assert page.locator('.config-panel').is_visible()

        def t_weak_pool_size_shown():
            text = page.inner_text('body')
            assert 'questions' in text.lower()

        def t_weak_starts():
            page.fill('#weak-count-custom', '3')
            page.wait_for_timeout(300)
            page.click('button:has-text("Start Practice")')
            page.wait_for_selector('.question-text', timeout=5000)
            assert page.locator('.question-text').is_visible()

        def t_weak_no_timer():
            assert page.locator('#timer-display').count() == 0

        test('Weak Areas config loads', t_weak_config_loads)
        test('Pool size shown', t_weak_pool_size_shown)
        test('Weak Areas quiz starts', t_weak_starts)
        test('No timer in Weak Areas mode', t_weak_no_timer)

        # ─── 8. PROGRESS TRACKING ───────────────────────────────────
        print('\n=== 8. Progress tracking & dashboard stats ===')

        def t_dashboard_updates_after_session():
            page.goto(APP_URL)
            text = page.inner_text('body')
            # After all the quiz sessions we ran, mastered/learning counts should be non-zero
            assert 'Mastered' in text or 'Learning' in text

        def t_readiness_score_present():
            page.goto(APP_URL)
            text = page.inner_text('body')
            assert '%' in text  # readiness score or domain accuracy shows %

        def t_session_history_populated():
            page.goto(APP_URL)
            text = page.inner_text('body')
            assert 'Exam Sim' in text or 'Domain Drill' in text

        def t_export_triggers_download():
            page.goto(APP_URL)
            with page.expect_download(timeout=5000) as dl_info:
                page.click('button:has-text("Export")')
            dl = dl_info.value
            assert dl.suggested_filename.startswith('claude_quiz_progress')
            assert dl.suggested_filename.endswith('.json')

        def t_inline_tests_pass():
            page.goto(APP_URL)
            result = page.evaluate('runTests()')
            assert result == True, 'runTests() returned False — some inline tests failed'

        test('Dashboard shows updated progress after sessions', t_dashboard_updates_after_session)
        test('Readiness score / % visible on dashboard', t_readiness_score_present)
        test('Session history populated', t_session_history_populated)
        test('Export triggers JSON download', t_export_triggers_download)
        test('runTests() inline suite all pass', t_inline_tests_pass)

        # ─── 9. EDGE CASES ──────────────────────────────────────────
        print('\n=== 9. Edge cases ===')
        # Use JS router to navigate back to dashboard — avoids expensive page reload
        page.evaluate("Router.navigate('dashboard')")
        page.wait_for_selector('h1', timeout=5000)

        def t_invalid_import_shows_error():
            result = page.evaluate("""
                (() => {
                    try {
                        Storage.importProgress('not valid json{{{');
                        return 'no error';
                    } catch(e) { return e.message; }
                })()
            """)
            assert 'Invalid JSON' in result or 'JSON' in result.upper(), f'Got: {result}'

        def t_score_formula_correct():
            res = page.evaluate("""[
                Engine.calculateScaledScore(60,60),
                Engine.calculateScaledScore(0,60),
                Engine.calculateScaledScore(47,60),
                Engine.calculateScaledScore(42,60),
                Engine.isPassing(730),
                Engine.isPassing(719)
            ]""")
            assert res[0] == 1000, f'Expected 1000 got {res[0]}'
            assert res[1] == 100,  f'Expected 100 got {res[1]}'
            assert res[2] == 805,  f'Expected 805 got {res[2]}'
            assert res[3] == 730,  f'Expected 730 got {res[3]}'
            assert res[4] == True, f'730 should pass'
            assert res[5] == False,f'719 should fail'

        def t_no_console_errors():
            errors = []
            page.on('console', lambda msg: errors.append(msg.text) if msg.type == 'error' else None)
            # Navigate via JS router — no page reload needed
            page.evaluate("Router.navigate('mode_select')")
            page.wait_for_selector('.mode-card', timeout=5000)
            page.wait_for_timeout(200)
            assert len(errors) == 0, f'Console errors: {errors}'

        test('Invalid JSON import throws descriptive error', t_invalid_import_shows_error)
        test('Score formula correct for all test cases', t_score_formula_correct)
        test('No JS console errors on load/navigate', t_no_console_errors)

        # ─── 10. TIMER TESTS ────────────────────────────────────────
        print('\n=== 10. Timer behavior ===')
        # We're on mode_select from section 9 — start exam with per-question timer

        def start_timer_exam(timer_mode='per_question', minutes=5):
            page.evaluate("Router.navigate('exam_config')")
            page.wait_for_selector('.config-panel', timeout=5000)
            page.fill('#exam-count-custom', '2')
            page.wait_for_timeout(200)
            if timer_mode == 'per_question':
                page.click('#timer-perq')
            else:
                page.click('#timer-overall')
                page.fill('#overall-minutes', str(minutes))
            page.click('button:has-text("Start Exam")')
            page.wait_for_selector('.question-text', timeout=8000)

        def t_per_question_timer_visible():
            start_timer_exam('per_question')
            assert page.locator('#timer-display').is_visible()
            timer_text = page.inner_text('#timer-display')
            assert ':' in timer_text, f'Timer not mm:ss: {timer_text}'

        def t_timer_counts_down():
            t1 = page.inner_text('#timer-display')
            page.wait_for_timeout(2200)
            t2 = page.inner_text('#timer-display')
            assert t1 != t2, f'Timer stuck: {t1} == {t2}'

        def t_overall_timer_visible():
            # Navigate back to exam config via JS router
            page.evaluate("Router.navigate('exam_config')")
            page.wait_for_selector('.config-panel', timeout=5000)
            start_timer_exam('overall', 5)
            assert page.locator('#timer-display').is_visible()
            txt = page.inner_text('#timer-display')
            assert ':' in txt, f'Overall timer not mm:ss: {txt}'

        test('Per-question timer visible in mm:ss format', t_per_question_timer_visible)
        test('Per-question timer is counting down', t_timer_counts_down)
        test('Overall timer visible after exam start', t_overall_timer_visible)

        # ─── DONE ────────────────────────────────────────────────────
        ctx.close()
        browser.close()

run_all()

passed = sum(1 for p, _, _ in results if p)
total  = len(results)
print(f'\n{"="*60}')
print(f'E2E RESULTS: {passed}/{total} passed')
if passed == total:
    print('ALL E2E TESTS PASSED ✓')
else:
    print(f'\nFailed tests:')
    for p, name, err in results:
        if not p:
            print(f'  ✗ {name}')
            print(f'    {err}')
print('='*60)
sys.exit(0 if passed == total else 1)
