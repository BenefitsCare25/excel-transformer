"""Exercise the complete upload/check/correct flow with synthetic employee data."""
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
        errors = []
        page.on('pageerror', lambda error: errors.append(str(error)))
        await page.goto('http://127.0.0.1:3019')
        await page.get_by_role('button', name='Flex Report', exact=True).click()
        await page.get_by_role('button', name='Lion Global Investors (LGI)').click()
        generate = page.get_by_role('button', name='Generate Output Files', exact=True)
        for key in ['claims', 'listing']:
            await page.locator(f'#upload-{key}').set_input_files(str(fixture.root / f'{key}.xlsx'))
        await page.locator('#upload-utilization').set_input_files(str(fixture.root / 'old-policy.xlsx'))
        choices = page.get_by_role('region', name='Choose employees for these reports', exact=True)
        employee = choices.get_by_role('group', name='LCM-001 · Sample Employee', exact=True)
        await expect(choices).to_be_visible()
        await expect(employee).to_contain_text('01 Oct 2024')
        await expect(choices.locator('input:checked')).to_have_count(0)
        await expect(generate).to_be_disabled()
        await employee.get_by_role('radio', name='Include in reports', exact=True).check()
        await expect(generate).to_be_enabled()
        await expect(choices.get_by_role('status')).to_contain_text('1 included · 0 excluded · 0 still to choose')
        await page.get_by_role('heading', name='LGI claim checks').scroll_into_view_if_needed()
        await page.screenshot(path=str(ROOT / 'tmp' / 'flex-feedback-desktop.png'), full_page=True)
        await page.set_viewport_size({'width': 390, 'height': 844})
        await page.screenshot(path=str(ROOT / 'tmp' / 'flex-feedback-mobile.png'), full_page=True)
        assert await page.evaluate('document.documentElement.scrollWidth <= window.innerWidth'), 'Mobile page overflows'
        await expect(employee.get_by_role('radio', name='Exclude from reports', exact=True)).to_be_visible()
        print('PASS explicit employee choice required, source dates and desktop/mobile layout', flush=True)
        if '--layout-only' in sys.argv:
            assert not errors, errors
            await browser.close()
            return

        for choice, expected_rows, expected_total, summary in [
            ('Include in reports', 2, 160.3, 'Included in all three reports'),
            ('Exclude from reports', 0, 0, 'Excluded from all three reports'),
        ]:
            await employee.get_by_role('radio', name=choice, exact=True).check()
            await expect(generate).to_be_enabled()
            async with page.expect_response('**/api/flex/run/lgi') as response_info:
                await generate.click()
            response = await response_info.value
            result = await response.json()
            assert response.status == 200 and len(result['outputs']) == 3, result
            assert result['stats']['breakdown_rows'] == expected_rows, result
            assert result['stats']['grand_total'] == expected_total, result
            await expect(page.get_by_role('region', name='Employee choices used in these reports')).to_contain_text(summary)
        print('PASS Include and Exclude choices generate three reports with matching totals', flush=True)

        await page.locator('#upload-utilization').set_input_files(str(fixture.root / 'utilization.xlsx'))
        await expect(generate).to_be_enabled()
        await expect(choices).to_have_count(0)
        async with page.expect_response('**/api/flex/run/lgi') as response_info:
            await generate.click()
        response = await response_info.value
        result = await response.json()
        assert response.status == 200 and len(result['outputs']) == 3
        print('PASS corrected upload rechecks automatically and generates three reports', flush=True)

        await page.get_by_role('button', name='Reset', exact=True).click()
        for key in ['claims', 'listing', 'utilization']:
            name = 'missing-employee.xlsx' if key == 'claims' else f'{key}.xlsx'
            await page.locator(f'#upload-{key}').set_input_files(str(fixture.root / name))
        await expect(page.get_by_text('These employee IDs could not be found', exact=False)).to_be_visible()
        await expect(page.get_by_role('list', name='Employee IDs to check')).to_contain_text('LCM-ABSENT')
        await expect(generate).to_be_disabled()
        print('PASS missing employee IDs block generation with actionable feedback', flush=True)

        async def unavailable(route):
            await route.fulfill(status=503, content_type='application/json', body=json.dumps({'error': 'We could not finish checking your files. Please try again.'}))
        await page.route('**/api/flex/validate-inputs/lgi', unavailable)
        await page.locator('#upload-claims').set_input_files(str(fixture.root / 'claims.xlsx'))
        await expect(page.get_by_text('Your files have not been checked', exact=True)).to_be_visible()
        await expect(generate).to_be_disabled()
        await page.unroute('**/api/flex/validate-inputs/lgi', unavailable)
        await page.get_by_role('button', name='Check files again', exact=True).click()
        await expect(generate).to_be_enabled()
        print('PASS unavailable validation blocks generation and retry recovers', flush=True)

        entered, release, complete = asyncio.Event(), asyncio.Event(), asyncio.Event()
        async def delayed(route):
            entered.set()
            await release.wait()
            await route.fulfill(status=200, content_type='application/json', body=json.dumps({'valid': True, 'claims': 2}))
            complete.set()
        await page.route('**/api/flex/validate-inputs/lgi', delayed)
        await page.locator('#upload-utilization').set_input_files(str(fixture.root / 'old-policy.xlsx'))
        await asyncio.wait_for(entered.wait(), timeout=15)
        await expect(generate).to_be_disabled()
        await page.get_by_role('button', name='Reset', exact=True).click()
        release.set()
        await asyncio.wait_for(complete.wait(), timeout=10)
        await expect(generate).to_be_disabled()
        await expect(page.locator('#upload-utilization')).to_have_value('')
        await expect(page.get_by_text('Your files are ready.', exact=False)).to_have_count(0)
        print('PASS a stale successful check after reset cannot enable generation', flush=True)

        await page.locator('#upload-claims').set_input_files(str(fixture.root / 'invalid-claims.xlsx'))
        await expect(page.get_by_text('1 claim needs attention', exact=False)).to_be_visible()
        await expect(page.get_by_text('This benefit is taxable', exact=False)).to_be_visible()
        await expect(generate).to_be_disabled()
        assert not errors, errors
        print('PASS plain-language tax, CPF and claimant corrections; no browser errors', flush=True)
        await browser.close()


fixture = LGIClaimsTests()
fixture.setUp()
fixture.prepare_utilization()
old = fixture.utilization.copy()
old.loc[0, 'Benefit Start Date'] = pd.Timestamp('2024-10-01')
old.to_excel(fixture.root / 'old-policy.xlsx', index=False)
missing = fixture.claims.copy()
missing.loc[0, 'Staff ID'] = 'LCM-ABSENT'
missing.to_excel(fixture.root / 'missing-employee.xlsx', index=False)
invalid = fixture.claims.copy()
invalid.loc[0, ['Claim Type', 'TAX', 'CPF', 'Relation']] = ["Children's Education Tuition Fees", 'No', 'No', 'Self']
invalid.to_excel(fixture.root / 'invalid-claims.xlsx', index=False)
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
