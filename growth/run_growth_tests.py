# -*- coding: utf-8 -*-
"""
run_growth_tests.py
-------------------
Master test runner for the Growth & Content Intelligence suite.
"""

import sys
import unittest
from pathlib import Path

ROOT_DIR = Path(__file__).parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

GROWTH_DIR = Path(__file__).parent


def run_all_growth_tests() -> bool:
    print("=" * 60)
    print("  RUNNING GROWTH & CONTENT INTELLIGENCE TEST SUITE")
    print("=" * 60)

    loader = unittest.TestLoader()
    suite = loader.discover(start_dir=str(GROWTH_DIR / "tests"), pattern="test_*.py")
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    print("=" * 60)
    if result.wasSuccessful():
        print(f"  GROWTH SUITE PASS: {result.testsRun} tests passed (0 failures, 0 errors)")
        print("=" * 60)
        return True
    else:
        print(f"  GROWTH SUITE FAIL: {len(result.failures)} failures, {len(result.errors)} errors")
        print("=" * 60)
        return False


if __name__ == "__main__":
    success = run_all_growth_tests()
    sys.exit(0 if success else 1)
