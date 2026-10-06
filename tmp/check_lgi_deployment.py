"""Smoke-check the deployed LGI validator with synthetic employee data."""
from io import BytesIO
from pathlib import Path
import sys

import requests
from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))
from tests.test_lgi import LGIClaimsTests

BASE = 'https://excel-transformer-rg.azurewebsites.net'
session = requests.Session()
health = session.get(BASE + '/api/flex/health', timeout=60)
health.raise_for_status()
assert health.json()['status'] == 'healthy', health.text
assert not health.json()['adapter_errors'], health.text
catalog = session.get(BASE + '/api/flex/companies', timeout=60)
catalog.raise_for_status()
lgi = next(c for c in catalog.json()['companies'] if c['id'] == 'lgi')
assert len(lgi['claim_validation']['rules']) == 28
other_benefit = next(rule for rule in lgi['claim_validation']['rules'] if rule['claim_type'] == 'Other Benefit')
assert (other_benefit['taxable'], other_benefit['cpf']) == ('Yes', 'Yes'), other_benefit
print('PASS live health and LGI catalog: 28 checklist rules including Other Benefit', flush=True)

fixture = LGIClaimsTests()
fixture.setUp()
try:
    fixture.claims.loc[0, ['Claim Type', 'TAX', 'CPF']] = [
        "Children\u2019s Education/ Tuition Fees", 'Yes', 'Yes']
    stream = BytesIO()
    fixture.claims.to_excel(stream, index=False)
    response = session.post(BASE + '/api/flex/validate/lgi',
                            files={'claims': ('synthetic-claims.xlsx', stream.getvalue())}, timeout=60)
    response.raise_for_status()
    assert response.json() == {'valid': True, 'claims': 2, 'validation': []}, response.text
    print('PASS live upload: education export label accepted', flush=True)

    fixture.claims.loc[0, ['CPF', 'Relation']] = ['No', 'Self']
    path = fixture.root / 'synthetic-invalid.xlsx'
    fixture.claims.to_excel(path, index=False)
    response = session.post(BASE + '/api/flex/validate/lgi',
                            files={'claims': (path.name, path.read_bytes())}, timeout=60)
    response.raise_for_status()
    result = response.json()
    assert result['valid'] is False
    assert [issue['field'] for issue in result['validation']] == ['CPF', 'Relation'], result
    print('PASS live upload: CPF and eligibility discrepancies returned together', flush=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={'width': 1440, 'height': 1100})
        page.goto(BASE, wait_until='networkidle', timeout=60000)
        page.get_by_role('button', name='Flex Report', exact=True).click()
        page.get_by_role('button', name='Lion Global Investors (LGI)').click()
        page.locator('#upload-claims').set_input_files(str(path))
        checks = page.get_by_role('region', name='LGI claim checks', exact=True)
        expect(checks.get_by_role('status')).to_contain_text('1 claim needs attention', timeout=30000)
        expect(checks.get_by_role('status')).to_contain_text('(2 corrections)')
        expect(page.get_by_role('region', name='Claims requiring correction').locator('tbody tr')).to_have_count(2)
        expect(page.get_by_role('button', name='Generate Output Files', exact=True)).to_be_disabled()
        page.get_by_role('heading', name='LGI claim checks').scroll_into_view_if_needed()
        page.screenshot(path=str(ROOT / 'tmp' / 'lgi-live-validation.png'), full_page=True)
        print('PASS live frontend: row-level errors displayed and generation blocked', flush=True)
        browser.close()
finally:
    fixture.doCleanups()
