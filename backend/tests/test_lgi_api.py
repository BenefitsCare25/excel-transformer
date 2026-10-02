"""HTTP contract checks for LGI upload validation and generation blocking."""

from io import BytesIO
import json
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
        self.assertTrue(lgi['input_validation'])
        self.assertEqual(len(lgi['claim_validation']['rules']), 28)
        other = next(rule for rule in lgi['claim_validation']['rules']
                     if rule['claim_type'] == 'Other Benefit')
        self.assertEqual((other['taxable'], other['cpf'], other['relations']), ('Yes', 'Yes', None))
        response = self.upload()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {'valid': True, 'claims': 2, 'validation': []})

    def test_other_benefit_upload_accepts_both_labels_and_checks_flags(self):
        for label in ['Other Benefit', 'Other Benefits']:
            with self.subTest(label=label):
                self.fixture.claims.loc[0, ['Claim Type', 'TAX', 'CPF']] = [label, 'Yes', 'Yes']
                response = self.upload()
                self.assertEqual(response.status_code, 200)
                self.assertTrue(response.get_json()['valid'])
                self.fixture.claims.loc[0, ['TAX', 'CPF']] = ['No', 'No']
                result = self.upload().get_json()
                self.assertFalse(result['valid'])
                self.assertEqual([issue['field'] for issue in result['validation']], ['TAX', 'CPF'])

    def test_all_claim_issues_are_returned_without_truncation(self):
        self.fixture.claims.loc[0, ['Claim Type', 'TAX', 'CPF']] = [
            "Children\u2019s Education/ Tuition Fees", 'No', 'No']
        self.fixture.claims.loc[1, 'Claim Type'] = 'Unknown category'
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

    def check_inputs(self, decisions=None, endpoint='validate-inputs'):
        data = {'pay_month': '2026-07-01', 'policy_decisions': json.dumps(decisions or {})}
        for key in ['claims', 'listing', 'utilization']:
            data[key] = (BytesIO((self.fixture.root / f'{key}.xlsx').read_bytes()), f'{key}.xlsx')
        return self.client.post(f'/api/flex/{endpoint}/lgi', data=data)

    def test_preflight_checks_all_files_without_creating_reports(self):
        self.fixture.prepare_utilization()
        with patch('app.flex_services.create_run') as create_run:
            response = self.check_inputs()
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.get_json()['valid'])
        create_run.assert_not_called()

    def test_policy_exclusion_is_not_reported_as_missing_from_listing(self):
        self.fixture.prepare_utilization()
        self.fixture.utilization.loc[0, 'Benefit Start Date'] = pd.Timestamp('2024-10-01')
        self.fixture.utilization.to_excel(self.fixture.root / 'utilization.xlsx', index=False)
        response = self.check_inputs()
        self.assertEqual(response.status_code, 400)
        feedback = response.get_json()['feedback']
        self.assertEqual(feedback['employee_ids'], ['LCM-001'])
        self.assertTrue(feedback['policy_choice_required'])
        self.assertEqual(feedback['policy_review'][0]['claims'], 2)
        self.assertEqual(feedback['files'], ['utilization'])
        self.assertEqual(feedback['records'][0]['benefit_start'], '01 Oct 2024')
        self.assertIn('01 Oct 2025', feedback['records'][0]['reason'])
        self.assertNotIn('outputs', response.get_json())

    def test_missing_employee_and_missing_utilisation_are_distinct(self):
        self.fixture.prepare_utilization()
        self.fixture.claims.loc[0, 'Staff ID'] = 'LCM-ABSENT'
        self.fixture.claims.to_excel(self.fixture.root / 'claims.xlsx', index=False)
        feedback = self.check_inputs().get_json()['feedback']
        self.assertIn('could not be found in the uploaded employee listing', feedback['message'])
        self.assertEqual(feedback['employee_ids'], ['LCM-ABSENT'])
        self.fixture.listing.loc[1] = self.fixture.listing.iloc[0].copy()
        self.fixture.listing.loc[1, 'Employee ID No.'] = 'LCM-ABSENT'
        self.fixture.listing.to_excel(self.fixture.root / 'listing.xlsx', index=False)
        feedback = self.check_inputs().get_json()['feedback']
        self.assertIn('in the employee listing', feedback['message'])
        self.assertEqual(feedback['records'][0]['reason'], 'Employee ID not found in the utilisation summary.')

    def test_preflight_rejects_missing_files_bad_dates_and_invalid_workbooks(self):
        self.assertEqual(self.client.post('/api/flex/validate-inputs/lgi').status_code, 400)
        self.assertEqual(self.client.post('/api/flex/validate-inputs/lgi', data={'pay_month': '2026-07-01'}).status_code, 400)
        response = self.client.post('/api/flex/validate-inputs/lgi', data={
            'pay_month': '2026-07-01', 'claims': (BytesIO(b'bad workbook'), 'claims.xlsx')})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.client.post('/api/flex/validate-inputs/unknown').status_code, 404)

    def test_employee_choices_reach_generation_and_are_saved(self):
        self.fixture.prepare_utilization()
        self.fixture.utilization.loc[0, 'Benefit Start Date'] = pd.Timestamp('2024-10-01')
        self.fixture.utilization.to_excel(self.fixture.root / 'utilization.xlsx', index=False)
        with patch('app.PROCESSED_FOLDER', str(self.fixture.root / 'runs')):
            self.assertEqual(self.check_inputs(endpoint='run').status_code, 400)
            for choice, count in [('include', 2), ('exclude', 0)]:
                decisions = {'LCM-001': choice}
                checked = self.check_inputs(decisions)
                self.assertEqual(checked.status_code, 200, checked.get_json())
                self.assertEqual(checked.get_json()['claims'], count)
                generated = self.check_inputs(decisions, 'run')
                self.assertEqual(generated.status_code, 200, generated.get_json())
                result = generated.get_json()
                self.assertEqual(result['stats']['breakdown_rows'], count)
                self.assertEqual(result['policy_review'][0]['decision'], choice)
                manifests = list((self.fixture.root / 'runs').rglob('manifest.json'))
                self.assertTrue(any(json.loads(path.read_text())['policy_review'][0]['decision'] == choice for path in manifests))

    def test_invalid_and_stale_employee_choices_are_rejected(self):
        self.fixture.prepare_utilization()
        for decisions in [{'LCM-001': 'include'}, {'LCM-001': 'exclude'}, {'LCM-ABSENT': 'include'}, {'LCM-001': 'anything'}]:
            self.assertEqual(self.check_inputs(decisions).status_code, 400)


if __name__ == '__main__':
    unittest.main()
