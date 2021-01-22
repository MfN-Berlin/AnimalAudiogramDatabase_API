"""
Test.

Created on 30.01.2020

@author: Alvaro.Ortiz for Museum fuer Naturkunde Berlin
"""

import unittest
import configparser
from API.Query import *  # noqa: F403
import logging


class test_Query(unittest.TestCase):
    configPath = "/src/API/api.ini"
    """Path to configuration file."""
    api_config = None
    """ConfigParser object will hold the custom API configuration """

    def setUp(self):
        """
        Setup a connection to the database.

        The database itself is created when you do "make test" to run the tests.
        testdata is in /unittests/testdata/Example5.csv
        """
        # Read the configuration file
        self.test_config = configparser.ConfigParser()
        self.test_config.read(test_Query.configPath)
        self.test_config['DEFAULT']['DB_DATABASE'] = "testdb"

    def test_1(self):
        """Test browsing"""
        audiograms = Browse_query(self.test_config).run([])  # noqa: F405
        # test data has 3 audiograms
        self.assertEqual(3, len(audiograms))

    def test_2(self):
        """Test metadata for experiment id=1"""
        experiment = Experiment_query(self.test_config).run(1)[0]  # noqa: F405
        # test metadata is correct
        # rounded to 6 digits as specified in the schema
        self.assertEqual(38.1338, experiment['latitude_in_decimal_degree'])
        # rounded to 6 digits as specified in the schema
        self.assertEqual(122.232, experiment['longitude_in_decimal_degree'])
        self.assertEqual("head just below water surface", experiment['position_of_animal'])
        self.assertEqual(0.5, experiment['distance_to_sound_source_in_meter'])
        self.assertEqual(
            "The test pool, filled with sea water, was about 4 m deep and 15 m in diameter.",
            experiment['test_environment_description'])
        self.assertEqual("electrophysiological: auditory brain stem responses (ABR)", experiment['measurement_method'])
        self.assertEqual("near the blowhole", experiment['position_first_electrode'])
        self.assertEqual("near the dorsal fin", experiment['position_second_electrode'])
        self.assertIsNone(experiment['position_third_electrode'])
        self.assertEqual("1995 - 1996", experiment['year_of_experiment'])
        self.assertIsNone(experiment['background_noise_in_decibel'])
        self.assertEqual("between 6-10", experiment['calibration'])
        self.assertEqual("50-50", experiment['threshold_determination_method'])
        self.assertEqual("cosine-gated tone bursts", experiment['testtone_form_method'])
        self.assertEqual("yes", experiment['testtone_presentation_staircase'])
        self.assertEqual("click", experiment['testtone_presentation_sound_form'])
        self.assertIsNone(experiment['testtone_presentation_method_constants'])
        self.assertEqual("no", experiment['sedated'])
        self.assertIsNone(experiment['sedation_details'])
        self.assertEqual(2, experiment['number_of_measurements'])
        self.assertEqual("Marine World Africa USA", experiment['facility_name'])

    def test_3(self):
        """Test caption for experiment id=1"""
        caption = Caption_query(self.test_config).run(1)[0]  # noqa: F405
        # test caption is correct
        self.assertEqual("Szymanski et al., 1999", caption['citation_short'])
        self.assertEqual("orca", caption['vernacular_name_english'])
        self.assertEqual("Orcinus orca", caption['species_name'])

    def test_4(self):
        """Test return all data points for experiment id=1"""
        data_points = Data_points_query(self.test_config).run(1)  # noqa: F405
        # test data has 12 data points
        self.assertEqual(12, len(data_points))

    def test_5(self):
        """Test animal details for experiment id=1"""
        animal = Animal_query(self.test_config).run(1)  # noqa: F405
        # test 2 animals in experiment
        self.assertEqual(2, len(animal))
        # check details for animal called "Yaka"
        yaka = None
        if (animal[0]['individual_name'] == "Yaka"):
            yaka = animal[0]
        else:
            yaka = animal[1]

        self.assertEqual("orca", yaka['vernacular_name_english'])
        self.assertEqual("Orcinus orca", yaka['species_name'])
        self.assertEqual("female", yaka['sex'])
        self.assertEqual("adult", yaka['life_stage'])
        self.assertEqual("192 - 216", yaka['age_in_month'])
        self.assertEqual("captive", yaka['liberty_status'])
        self.assertEqual(312, yaka['captivity_duration_in_month'])
        self.assertIsNone(yaka['biological_season'])

    def test_6(self):
        """Test species details for experiment id=1"""
        species = Species_query(self.test_config).run(1)[0]  # noqa: F405
        self.assertEqual("orca", species['vernacular_name_english'])
        self.assertEqual("Orcinus orca", species['species_name'])

    def test_7(self):
        """Test publication details for experiment id=1"""
        publication = Publication_query(self.test_config).run(1)[0]  # noqa: F405
        self.assertEqual(
            "Szymanski, M. D., Bain, D. E., Kiehl, K., Pennington, S., Wong, S., & Henry, K. R. (1999). Killer whale (Orcinus orca) hearing: Auditory brainstem response and behavioral audiograms. The Journal of the Acoustical Society of America, 106(2), 1134Ã¢Â€Â“1141. doi:10.1121/1.427121",
            publication['citation_long'])
        self.assertEqual("10.1121/1.427121", publication['DOI'])

    def test_8(self):
        """Subspecies details are correct"""
        species = Species_query(self.test_config).run(3)[0]  # noqa: F405
        self.assertEqual("West Indian manatee", species['vernacular_name_english'])
        self.assertEqual("Trichechus manatus latirostris", species['species_name'])

    def test_9(self):
        """
        Data summary
        +----------+------------------+--------+----------------+
        | in_water | in_water_species | in_air | in_air_species |
        +----------+------------------+--------+----------------+
        |        2 |                1 |      1 |              1 |
        +----------+------------------+--------+----------------+
        """
        summary = Summary_query(self.test_config).run()[0]  # noqa: F405
        self.assertEqual(2, summary['in_water'])
        self.assertEqual(1, summary['in_water_species'])
        self.assertEqual(1, summary['in_air'])
        self.assertEqual(1, summary['in_air_species'])

    def test_10(self):
        """Check that units of a bunch of audiograms are compatible"""
        ids = [1, 3, 221]
        compat = SPLUnits_query(self.test_config).run(ids)  # noqa: F405
        # logging.warning(compat)
        self.assertEqual([{'sound_pressure_level_reference_id': 1}, {'sound_pressure_level_reference_id': 1}, {'sound_pressure_level_reference_id': 6}], compat)

    def test_11(self):
        """List a bunch of audiograms requested in GET parameter ids"""
        ids = [1, 3, 221]
        resp = List_query(self.test_config).run(ids)  # noqa: F405
        self.assertEqual(3, len(resp))


if __name__ == "__main__":
    unittest.main()
