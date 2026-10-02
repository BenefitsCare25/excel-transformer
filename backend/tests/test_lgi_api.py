"""HTTP contract checks for LGI upload validation and generation blocking."""

from io import BytesIO
import unittest
from unittest.mock import patch

import pandas as pd

from app import app
from tests import test_lgi


class LGIValidationAPITests(unittest.TestCase):
    def setUp(self):
        self.fixture = test_lgi.LGIClaimsTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.client = app.test_client()

    def upload(self, frame=None):
        stream = BytesIO()
        (self.fixture.claims if frame is None else frame).to_excel(stream, index=False)
        stream.seek(0)
        return self.client.post('/api/flex/validate/lgi', data={'claims': (stream, 'claims.xlsx')})

    def test_catalog_exposes_checklist_and_valid_upload_passes(self):
        catalog = self.client.get('/api/flex/companies').get_json()
        lgi = next(c for c in catalog['companies'] if c['id'] == 'lgi')
        self.assertEqual(lgi['claim_validation']['file_key'], 'claims')
        self.assertEqual(len(lgi['claim_validation']['rules']), 27)
        response = self.upload()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {'valid': True, 'claims': 2, 'validation': []})

    def test_all_claim_issues_are_returned_without_truncation(self):
        self.fixture.claims.loc[0, ['Claim Type', 'TAX', 'CPF']] = [
            "Children\u2019s Education/ Tuition Fees", 'No', 'No']
        self.fixture.claims.loc[1, 'Claim Type'] = 'Other Benefits'
        frame = pd.concat([self.fixture.claims] * 8, ignore_index=True)
        response = self.upload(frame)
        self.assertEqual(response.status_code, 200)
        result = response.get_json()
        self.assertFalse(result['valid'])
        self.assertEqual(len(result['validation']), 24)
        self.assertEqual(result['validation'][-1]['row'], 17)

    def test_bad_uploads_return_actionable_errors(self):
        response = self.upload(self.fixture.claims.drop(columns='CPF'))
        self.assertEqual(response.status_code, 400)
        self.assertIn('missing required column(s): CPF', response.get_json()['details'])
        response = self.client.post('/api/flex/validate/lgi')
        self.assertEqual(response.status_code, 400)
        response = self.client.post('/api/flex/validate/lgi', data={
            'claims': (BytesIO(b'not an Excel file'), 'claims.xlsx')})
        self.assertEqual(response.status_code, 400)
        self.assertIn('valid .xlsx', response.get_json()['details'])
        response = self.client.post('/api/flex/validate/unknown')
        self.assertEqual(response.status_code, 404)

    def test_generation_revalidates_and_returns_structured_issues(self):
        self.fixture.prepare_utilization()
        self.fixture.claims.loc[0, ['Claim Type', 'TAX', 'CPF']] = ['Maternity', 'No', 'No']
        self.fixture.claims.to_excel(self.fixture.root / 'claims.xlsx', index=False)
        data = {'pay_month': '2026-07-01'}
        for key in ['claims', 'listing', 'utilization']:
            data[key] = (BytesIO((self.fixture.root / f'{key}.xlsx').read_bytes()), f'{key}.xlsx')
        with patch('app.PROCESSED_FOLDER', str(self.fixture.root / 'runs')):
            response = self.client.post('/api/flex/run/lgi', data=data)
        self.assertEqual(response.status_code, 400)
        result = response.get_json()
        self.assertEqual([i['field'] for i in result['validation']], ['CPF', 'Relation'])
        self.assertNotIn('outputs', result)
        self.assertFalse(list((self.fixture.root / 'runs').rglob('*.xlsx')))


if __name__ == '__main__':
    unittest.main()
