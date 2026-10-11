import unittest
from backend.app import analyze, classify_category, classify_severity, make_summary

class IncidentAnalysisTests(unittest.TestCase):
    def test_oil_spill_environment_high(self):
        result = analyze("Oil spill observed near turbine; containment started")
        self.assertEqual(result["category"], "environment")
        self.assertEqual(result["severity"], "high")
        self.assertTrue(result["recommended_actions"])

    def test_ppe_safety(self):
        category, _, _, _ = classify_category("PPE non-compliance during panel cleaning")
        self.assertEqual(category, "safety")

    def test_waste_segregation_compliance(self):
        category, _, _, _ = classify_category("Repeated waste segregation deviation")
        self.assertEqual(category, "esg_compliance")

    def test_unknown_severity_is_provisional_medium(self):
        severity, reason, _ = classify_severity("An unusual observation was recorded")
        self.assertEqual(severity, "medium")
        self.assertIn("Insufficient detail", reason)

    def test_summary_preserves_original_text(self):
        text = "Water usage spike during module cleaning due to valve leakage"
        self.assertEqual(make_summary(text), text[0].upper() + text[1:])

if __name__ == "__main__":
    unittest.main()
