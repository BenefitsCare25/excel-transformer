"""Bounded browser checks against the built UI and real local Flask endpoints."""
import asyncio
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import sys
import threading

import pandas as pd
from playwright.async_api import async_playwright, expect
from werkzeug.serving import make_server

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))
import app as backend
from tests.test_lgi import LGIClaimsTests


async def check_ui(fixture):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={'width': 1440, 'height': 1100})
        # Build with REACT_APP_API_URL=http://127.0.0.1:5000 before running.
        errors = []
        page.on('pageerror', lambda error: errors.append(str(error)))
        await page.goto('http://127.0.0.1:3019')
        await page.get_by_role('button', name='Flex Report', exact=True).click()
        await page.get_by_role('button', name='Lion Global Investors (LGI)').click()
        generate = page.get_by_role('button', name='Generate Output Files', exact=True)
        await expect(generate).to_be_disabled()

        checks = page.get_by_role('region', name='LGI claim checks', exact=True)
        # One correction per synthetic claim exercises a large validation result.
        await page.locator('#upload-claims').set_input_files(str(fixture.root / 'many-invalid.xlsx'))
        await expect(checks.get_by_role('status')).to_contain_text('59 claims need attention')
        await expect(checks.get_by_role('status')).to_contain_text('(59 corrections)')
        await expect(page.get_by_role('region', name='Claims requiring correction').locator('tbody tr')).to_have_count(59)
        await expect(generate).to_be_disabled()
        print('PASS synthetic workbook: all 59 checklist issues displayed, generation blocked', flush=True)

        # Use synthetic employee data for screenshots and successful generation.
        await page.get_by_role('button', name='Reset', exact=True).click()
        await page.locator('#upload-listing').set_input_files(str(fixture.root / 'listing.xlsx'))
        await page.locator('#upload-utilization').set_input_files(str(fixture.root / 'utilization.xlsx'))
        await page.locator('#upload-claims').set_input_files(str(fixture.root / 'invalid.xlsx'))
        await expect(checks.get_by_role('status')).to_contain_text('1 claim needs attention')
        await expect(checks.get_by_role('status')).to_contain_text('(3 corrections)')
        await expect(page.get_by_role('region', name='Claims requiring correction').locator('tbody tr')).to_have_count(3)
        await expect(generate).to_be_disabled()
        await page.get_by_role('heading', name='LGI claim checks').scroll_into_view_if_needed()
        await page.screenshot(path=str(ROOT / 'tmp' / 'lgi-validation-desktop.png'), full_page=True)
        await page.set_viewport_size({'width': 390, 'height': 844})
        await page.screenshot(path=str(ROOT / 'tmp' / 'lgi-validation-mobile.png'), full_page=True)
        assert await page.evaluate('document.documentElement.scrollWidth <= window.innerWidth'), 'Page overflows on mobile'
        await page.get_by_text('View LGI tax, CPF and eligibility rules', exact=True).click()
        rules = page.get_by_role('region', name='LGI checklist rules')
        await expect(rules.locator('tbody tr')).to_have_count(28)
        await expect(rules.get_by_role('row', name='Other Benefit Yes Yes Not specified', exact=True)).to_be_visible()
        print('PASS synthetic errors, accessible rules table, desktop/mobile layout', flush=True)

        await page.locator('#upload-claims').set_input_files(str(fixture.root / 'claims.xlsx'))
        await expect(checks.get_by_role('status')).to_contain_text('Tax, CPF and claimant relationship checks passed for 2 claims.')
        await expect(generate).to_be_enabled()
        async with page.expect_response('**/api/flex/run/lgi') as response_info:
            await generate.click()
        response = await response_info.value
        result = await response.json()
        assert response.status == 200 and len(result['outputs']) == 3, result
        print('PASS corrected upload clears issues and generates all three reports', flush=True)

        await page.get_by_role('button', name='Reset', exact=True).click()
        async def failed_check(route):
            await route.fulfill(status=503, content_type='application/json', body=json.dumps({'error': 'Validation service unavailable'}))
        await page.route('**/api/flex/validate/lgi', failed_check)
        await page.locator('#upload-claims').set_input_files(str(fixture.root / 'claims.xlsx'))
        await expect(checks.get_by_role('alert')).to_contain_text('We could not check your claims')
        await expect(generate).to_be_disabled()
        await page.unroute('**/api/flex/validate/lgi', failed_check)
        await page.get_by_role('button', name='Check claims again', exact=True).click()
        await expect(checks.get_by_role('status')).to_contain_text('Tax, CPF and claimant relationship checks passed for 2 claims.')
        print('PASS validation service failure blocks generation and retry recovers', flush=True)

        # Hold a response while resetting to prove stale results cannot restore files/checks.
        entered = asyncio.Event()
        release = asyncio.Event()
        completed = asyncio.Event()
        async def delayed_check(route):
            entered.set()
            await release.wait()
            await route.fulfill(status=200, content_type='application/json', body=json.dumps({'valid': True, 'claims': 2, 'validation': []}))
            completed.set()
        await page.route('**/api/flex/validate/lgi', delayed_check)
        await page.locator('#upload-claims').set_input_files([])
        await page.locator('#upload-claims').set_input_files(str(fixture.root / 'claims.xlsx'))
        await asyncio.wait_for(entered.wait(), timeout=10)
        await expect(generate).to_be_disabled()
        await page.get_by_role('button', name='Reset', exact=True).click()
        release.set()
        await asyncio.wait_for(completed.wait(), timeout=10)
        await expect(page.get_by_text('Upload the claims workbook to check tax, CPF', exact=False)).to_be_visible()
        await expect(generate).to_be_disabled()
        await expect(page.locator('#upload-claims')).to_have_value('')
        print('PASS stale validation response after reset is ignored', flush=True)
        assert not errors, errors
        await browser.close()


fixture = LGIClaimsTests()
fixture.setUp()
fixture.prepare_utilization()
many_invalid = pd.concat([fixture.claims.iloc[[0]]] * 59, ignore_index=True)
many_invalid['Reference No.'] = [f'SYNTHETIC-{index:03d}' for index in range(1, 60)]
many_invalid[['Claim Type', 'TAX', 'CPF']] = ['Other Benefit', 'No', 'Yes']
many_invalid.to_excel(fixture.root / 'many-invalid.xlsx', index=False)
invalid = fixture.claims.copy()
invalid.loc[0, ['Claim Type', 'TAX', 'CPF', 'Relation']] = [
    "Children\u2019s Education/ Tuition Fees", 'No', 'No', 'Self']
invalid.to_excel(fixture.root / 'invalid.xlsx', index=False)
backend.PROCESSED_FOLDER = str(fixture.root / 'runs')
api = make_server('127.0.0.1', 5000, backend.app, threaded=True)
web = ThreadingHTTPServer(('127.0.0.1', 3019), partial(SimpleHTTPRequestHandler, directory=str(ROOT / 'frontend' / 'build')))
for server in [api, web]:
    threading.Thread(target=server.serve_forever, daemon=True).start()
try:
    asyncio.run(check_ui(fixture))
finally:
    api.shutdown()
    web.shutdown()
    fixture.doCleanups()
