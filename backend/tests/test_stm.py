import unittest

from flex_services.companies.stm import claim_type_wage_code


class StmClaimTypeMappingTests(unittest.TestCase):
    def test_maps_supported_claim_types_to_their_wage_codes(self):
        expected_codes = {
            'Optical': 'Optical(T)',
            'Childcare': 'HealthS/ChildC(NT)',
            'Health Screening': 'HealthS/ChildC(NT)',
            'Dental': 'N-Medi/Dental(NT)',
            'Medical-related': 'N-Medi/Dental(NT)',
            'Outpatient GP (capped at S$30 per visit)': 'N-Medi/Dental(NT)',
            'Outpatient Medical expenses at Singapore  Government Polyclinics': 'N-Medi/Dental(NT)',
            'Gym/Fitness Membership': 'N-Medi/Dental(NT)',
            'Alternative Treatment (Chiropractic)': 'N-Medi/Dental(NT)',
        }

        for claim_type, expected_code in expected_codes.items():
            with self.subTest(claim_type=claim_type):
                self.assertEqual(claim_type_wage_code(claim_type), expected_code)

    def test_normalises_claim_type_case_and_whitespace(self):
        self.assertEqual(
            claim_type_wage_code('  GYM/FITNESS   MEMBERSHIP  '),
            'N-Medi/Dental(NT)',
        )

    def test_rejects_unmapped_claim_type(self):
        self.assertIsNone(claim_type_wage_code('Unapproved wellness benefit'))


if __name__ == '__main__':
    unittest.main()
