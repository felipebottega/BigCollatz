"""Audit a primitive giant word through production and independent closure."""

from decimal import Decimal
import unittest

from collatz_algebra.search import Run, RunGroup, _evaluate_pattern

try:
    import gmpy2
except ImportError:
    gmpy2 = None


INTEGER_BELOW = 7_975_806_532_734_070_597_447_809_173_720
COPIES_A = 2_283_171_821
COPIES_B = 467_389_065


def _independent_expression(x: int) -> tuple:
    """Enclose the image using exact short coefficients and MPFR logarithms."""
    down = gmpy2.context(precision=512, round=gmpy2.RoundDown)
    up = gmpy2.context(precision=512, round=gmpy2.RoundUp)

    def coefficients(exponents):
        numerator, power = 0, 1
        for exponent in exponents:
            numerator = 3 * numerator + power
            power <<= exponent
        return 3 ** len(exponents), numerator, power

    def bounds(numerator, denominator):
        value = gmpy2.mpq(numerator, denominator)
        with down:
            lo = gmpy2.mpfr(value)
        with up:
            hi = gmpy2.mpfr(value)
        return lo, hi

    a, b, d = coefficients((1, 2) * 23 + (1, 1, 2, 2))
    c_lo, c_hi = bounds(b, a - d)
    a, b, d = coefficients((1, 3) * 23 + (1, 1, 3, 3))
    z_lo, z_hi = bounds(b, d - a)
    assert 2 * a < d and COPIES_B > 512

    k, divisions = 50 * (COPIES_A + COPIES_B), 75 * COPIES_A + 100 * COPIES_B
    log_lo = down.sub(down.mul(k, down.log(3)), up.mul(divisions, up.log(2)))
    log_hi = up.sub(up.mul(k, up.log(3)), down.mul(divisions, down.log(2)))
    slope_lo, slope_hi = down.exp(log_lo), up.exp(log_hi)
    _, remaining_contraction = bounds(1, 1 << 512)
    # After both repeated blocks the image is
    # slope * (x + c) + z - contraction * (c + z).
    # The contraction is positive and below 2^-512.
    lo = down.sub(
        down.add(down.mul(slope_lo, down.add(x, c_lo)), z_lo),
        up.mul(remaining_contraction, up.add(c_hi, z_hi)),
    )
    hi = up.add(up.mul(slope_hi, up.add(x, c_hi)), z_hi)
    a, b, d = coefficients((1,) * 484 + (4,) + (2,) * 527)
    a_lo, a_hi = bounds(a, d)
    b_lo, b_hi = bounds(b, d)
    return down.add(down.mul(a_lo, lo), b_lo), up.add(up.mul(a_hi, hi), b_hi)


class GiantClosureAuditTests(unittest.TestCase):
    def test_primitive_giant_word_reaches_the_production_verifier(self):
        motif_a = (Run(1, 2, 1),) * 23 + (Run(2, 2, 2),)
        motif_b = (Run(1, 3, 1),) * 23 + (Run(2, 3, 2),)
        # The unique exponent 4 makes any whole-word repetition impossible.
        tail = (Run(484, 4, 1, ((2, 527),)),)
        packed = (RunGroup(motif_a, COPIES_A), RunGroup(motif_b, COPIES_B))
        status, report = _evaluate_pattern(tail, 10_000, packed)
        self.assertEqual(status, "rejected")
        self.assertEqual(report["rejection_certificates"], [])
        exact = report["exact_verification"]
        self.assertTrue(exact["definitive"])
        self.assertEqual(exact["method"], "directed_affine_interval")
        self.assertEqual(exact["counts"], {
            "odd_steps": "137528045312",
            "total_divisions": "217976794617",
            "unaccelerated_period": "355504839929",
        })
        interval = exact["closure_interval"]
        self.assertEqual(int(interval["integer_below"]), INTEGER_BELOW)
        self.assertLess(INTEGER_BELOW, Decimal(interval["lower"]))
        self.assertLess(Decimal(interval["upper"]), INTEGER_BELOW + 1)

    @unittest.skipIf(gmpy2 is None, "Install .[large] for the independent MPFR audit")
    def test_independent_geometric_sum_proves_the_same_rejection(self):
        lower_image, _ = _independent_expression(INTEGER_BELOW)
        _, upper_image = _independent_expression(INTEGER_BELOW + 1)
        self.assertGreater(lower_image, INTEGER_BELOW)
        self.assertLess(upper_image, INTEGER_BELOW + 1)
