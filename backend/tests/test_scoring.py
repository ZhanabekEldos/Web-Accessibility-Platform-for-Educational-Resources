import unittest

from app.a11y.registry import REGISTRY
from app.a11y.scoring import RuleResult, conformance_level, rule_score, weighted_score


def R(rule_id, applicable, violations, reviews=0):
    return RuleResult(REGISTRY.get(rule_id), applicable, violations, reviews)


class ScoringTests(unittest.TestCase):
    def test_not_applicable_rules_do_not_count(self):
        self.assertIsNone(rule_score(R("image-alt", 0, 0)))
        self.assertIsNone(weighted_score([R("image-alt", 0, 0)]))

    def test_manual_rules_do_not_count(self):
        self.assertIsNone(rule_score(R("audio-transcript", 1, 0, 1)))

    def test_partial_credit_is_capped(self):
        self.assertEqual(rule_score(R("image-alt", 10, 0)), 1.0)
        self.assertEqual(rule_score(R("image-alt", 10, 1)), 0.45)
        self.assertEqual(rule_score(R("image-alt", 10, 10)), 0.0)
        self.assertLess(rule_score(R("image-alt", 2, 1)), 0.5)

    def test_score_is_monotonic_with_fixes(self):
        before = weighted_score([R("image-alt", 10, 6), R("form-label", 4, 2)])
        after = weighted_score([R("image-alt", 10, 3), R("form-label", 4, 2)])
        done = weighted_score([R("image-alt", 10, 0), R("form-label", 4, 0)])
        self.assertTrue(before < after < done == 100.0)

    def test_severity_weighting(self):
        critical = weighted_score([R("image-alt", 4, 4), R("heading-order", 4, 0)])
        minor_fail = weighted_score([R("image-alt", 4, 0), R("heading-order", 4, 4)])
        self.assertLess(critical, minor_fail)

    def test_conformance_levels(self):
        self.assertEqual(conformance_level([R("image-alt", 1, 0), R("color-contrast", 1, 0)]), "AA")
        self.assertEqual(conformance_level([R("image-alt", 1, 0), R("color-contrast", 1, 1)]), "A")
        self.assertIsNone(conformance_level([R("image-alt", 1, 1)]))
        # нарушение «лучшей практики» уровень не снижает
        self.assertEqual(conformance_level([R("heading-order", 1, 1)]), "AA")


if __name__ == "__main__":
    unittest.main()
