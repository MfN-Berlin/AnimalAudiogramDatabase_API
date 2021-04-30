"""
Convert SPL units

Created on 05.05.2020
@author: Alvaro.Ortiz for Museum fuer Naturkunde Berlin
"""
import logging


class SPL_converter:

    def __init__(self):
        self.sound_pressure_level_reference = [
            {'id': 1, 'spl_reference_value': 1, 'spl_reference_unit': "μPa",
             'spl_reference_significance': "current SPL reference in water"},
            {'id': 2, 'spl_reference_value': 1, 'spl_reference_unit': "μbar",
             'spl_reference_significance': "deprecated SPL reference in water",
             'conversion_factor_airborne_sound_in_decibel': 'NA',
             'conversion_factor_waterborne_sound_in_decibel': 100},
            {'id': 3, 'spl_reference_value': 1, 'spl_reference_unit': "1mPa",
             'spl_reference_significance': "deprecated SPL reference in water",
             'conversion_factor_airborne_sound_in_decibel': 34,
             'conversion_factor_waterborne_sound_in_decibel': 60},
            {'id': 4, 'spl_reference_value': 20, 'spl_reference_unit': "μPa",
             'spl_reference_significance': "current SPL reference in air",
             'conversion_factor_airborne_sound_in_decibel': 'NA',
             'conversion_factor_waterborne_sound_in_decibel': 26},
            {'id': 5, 'spl_reference_value': 0.0002, 'spl_reference_unit': "dyne/cm<sup>2</sup>",
             'spl_reference_significance': "deprecated SPL reference in air",
             'conversion_factor_airborne_sound_in_decibel': 0,
             'conversion_factor_waterborne_sound_in_decibel': 'NA'},
            {'id': 6, 'spl_reference_value': 1, 'spl_reference_unit': "dyne/cm<sup>2</sup>",
             'spl_reference_significance': "deprecated SPL reference in water",
             'conversion_factor_airborne_sound_in_decibel': 74,
             'conversion_factor_waterborne_sound_in_decibel': 100},
            {'id': 7, 'spl_reference_value': 2e-4, 'spl_reference_unit': "μbar",
             'spl_reference_significance': "",
             'conversion_factor_airborne_sound_in_decibel': 'NA',
             'conversion_factor_waterborne_sound_in_decibel': 'NA'},
        ]

    def check(self, units):
        """
        Check if SPL units are compatible, i.e. they are equal or can be converted.

        @param units list of sound_pressure_level_reference_id's, e.g. [{'sound_pressure_level_reference_id': 1}, {'sound_pressure_level_reference_id': 1}, {'sound_pressure_level_reference_id': 6}],
        as obtained from Query.SPLUnits_query
        @return boolean true if units are compatible.

        """
        waterborne = [1, 2, 3, 6]
        airborne = [4, 5]
        logging.warning("+++++++++++++++++++++++++++++++++++++++")
        logging.warning(units)
        # some audiograms have no unit, these should never be overlayed
        for u in units:
            if u['sound_pressure_level_reference_id'] is None:
                return False
        # all audiograms are in water
        if units[0]['sound_pressure_level_reference_id'] in waterborne:
            for u in units:
                if u['sound_pressure_level_reference_id'] not in waterborne:
                    return False
        # all audiograms are in air
        if units[0]['sound_pressure_level_reference_id'] in airborne:
            for u in units:
                if u['sound_pressure_level_reference_id'] not in airborne:
                    return False
        return True

    def is_converted(self, unit):
        # logging.warning(unit)
        unit_id = unit[0]['sound_pressure_level_reference_id']
        if unit_id in [1, 4]:
            return False
        else:
            from_unit = None
            for r in self.sound_pressure_level_reference:
                if r['id'] == unit_id:
                    from_unit = r
            return from_unit

    def convert(self, value, from_id):
        """
        Convert a dB SPL value from historical units to current units.
        @param value double value to convert
        @param from_id int sound_pressure_level_reference_id, see list below
        """
        factor = 0

        # do not convert current units
        for r in self.sound_pressure_level_reference:
            if r['id'] == from_id:
                # water
                if from_id in [1, 2, 3, 6]:
                    if 'conversion_factor_waterborne_sound_in_decibel' in r:
                        factor = r['conversion_factor_waterborne_sound_in_decibel']
                        break
                # air
                elif from_id in [4, 5]:
                    if 'conversion_factor_airborne_sound_in_decibel' in r:
                        factor = r['conversion_factor_airborne_sound_in_decibel']
                        break

        if factor and factor != 'NA':
            resp = value + factor
        else:
            resp = value
        logging.warning("convert value %d resp %d" %
                        (value, resp))
        return resp
