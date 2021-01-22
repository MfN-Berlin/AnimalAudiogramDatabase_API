"""
Test.

Created on 06.05.2020

@author: Alvaro.Ortiz for Museum fuer Naturkunde Berlin
"""

import unittest
from API.SPL_converter import SPL_converter


class test_SPL_converter(unittest.TestCase):
    def test_1(self):
        """Test if units are compatible"""
        incompatible = [{'sound_pressure_level_reference_id': 1}, {'sound_pressure_level_reference_id': 6}]
        compat = SPL_converter().check(incompatible)
        self.assertFalse(compat)

        compatible = [{'sound_pressure_level_reference_id': 1}, {'sound_pressure_level_reference_id': 1}]
        compat = SPL_converter().check(compatible)
        self.assertTrue(compat)

        single = [{'sound_pressure_level_reference_id': 1}]
        compat = SPL_converter().check(single)
        self.assertTrue(compat)


if __name__ == "__main__":
    unittest.main()
