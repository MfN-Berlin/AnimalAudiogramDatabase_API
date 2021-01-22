"""
Test.

Created on 06.05.2020

@author: Alvaro.Ortiz for Museum fuer Naturkunde Berlin
"""

import unittest
import pandas as pd
import json
from API.Plotter import Plotter


class test_Plotter(unittest.TestCase):
    def test_1(self):
        data_points_array = """[
        [
            {
                "testtone_duration_in_millisecond": 20.00,
                "testtone_frequency_in_khz": 128.0,
                "sound_pressure_level_in_decibel": 92.00,
                "audiogram_experiment_id": 201,
                "spl_reference_value": 1.0,
                "spl_reference_significance": "current SPL reference in water"},
            {
                "testtone_duration_in_millisecond": 20.00,
                "testtone_frequency_in_khz": 120.0,
                "sound_pressure_level_in_decibel": 82.00,
                "audiogram_experiment_id": 201,
                "spl_reference_value": 1.0,
                "spl_reference_significance": "current SPL reference in water"
            }
        ],
        [
            {
                "testtone_duration_in_millisecond": 20.00,
                "testtone_frequency_in_khz": 128.0,
                "sound_pressure_level_in_decibel": 92.00,
                "audiogram_experiment_id": 201,
                "spl_reference_value": 1.0,
                "spl_reference_significance": "current SPL reference in water"},
            {
                "testtone_duration_in_millisecond": 20.00,
                "testtone_frequency_in_khz": 120.0,
                "sound_pressure_level_in_decibel": 82.00,
                "audiogram_experiment_id": 201,
                "spl_reference_value": 1.0,
                "spl_reference_significance": "current SPL reference in water"
            }
        ]
        ]"""
        plotter = Plotter()
        panda = plotter._convert_points_array_to_panda(data_points_array)
        print(panda)
        self.assertEqual(4, len(panda))
        self.assertEqual(128.0, panda["testtone_frequency_in_khz"][0])


if __name__ == "__main__":
    unittest.main()

