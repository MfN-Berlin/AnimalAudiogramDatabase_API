"""
API queries.
* Implements the template method pattern
* Connects to the MySQL database using pymysql

API requirements see:
https://code.naturkundemuseum.berlin/Alvaro.Ortiz/Pinguine/wikis/Requirements-Audiogram-Frontend

Created on 15.01.2020
@author: Alvaro.Ortiz for Museum fuer Naturkunde Berlin
"""

import abc
import pymysql
import logging
from SPL_converter import SPL_converter


class Query(abc.ABC):
    """Base class for database queries called from the API."""

    connection = None
    """Database connection."""

    def __init__(self, config):
        self.host = config.get('DEFAULT', 'DB_HOST')
        self.password = config.get('DEFAULT', 'DB_PASSWORD')
        self.username = config.get('DEFAULT', 'DB_USERNAME')
        self.database = config.get('DEFAULT', 'DB_DATABASE')

    def run(self, param=None):
        self.connection = self._get_connection()
        results = self._run(param)
        return(self._jsonize(results))

    @abc.abstractmethod
    def _run(self, param=None):
        pass

    def _get_connection(self):
        """Open a database connection."""
        return pymysql.connect(
            self.host, self.username, self.password, self.database)

    def _jsonize(self, results):
        """Convert result object to json."""
        json_data = []
        for result in results['results']:
            # combine headers and data (zip is not the compression utility)
            json_data.append(dict(zip(results['headers'], result)))
        return json_data


class SPLUnits_query(Query):
    """Get a list of the SPL units of a list of audiograms"""

    def _run(self, param=None):
        """@param list of ids as string, comma-separated"""
        with self.connection as cursor:
            cursor.execute(
                """
                select
                   sound_pressure_level_reference_id
                from
                   audiogram_data_point
                where
                   audiogram_experiment_id in %(list)s
                group by
                   audiogram_experiment_id
            """,
                {'list': param})
            row_headers = [x[0] for x in cursor.description]
            all_results = cursor.fetchall()
        return {'headers': row_headers, 'results': all_results}


class All_experiments_query(Query):
    """List all experiment ids."""

    def _run(self, param=None):
        with self.connection as cursor:
            cursor.execute(
                """
            select
                exp.id
            from
                audiogram_experiment exp
            """)
            row_headers = [x[0] for x in cursor.description]
            all_results = cursor.fetchall()
        return {'headers': row_headers, 'results': all_results}


class List_query(Query):
    """
    Get a complete list of short audiogram descriptions.

    i.e.:
    * Experiment id
    * Short citation
    * Facility
    * English vernacular and scientific name of species

    @param list of ids as string, comma-separated
    """

    def _run(self, param=None):
        with self.connection as cursor:
            cursor.execute(
                """
            select
                exp.id,
                publication_id, citation_short,
                vernacular_name_english,
                unique_name as species_name,
                concat(m2.denomination, ": ", m1.denomination) as measurement_method
            from
                audiogram_experiment exp
                left join method m1 on m1.id=exp.measurement_method_id
                left join method m2 on m2.id=m1.parent_method_id,
                audiogram_publication,
                publication,
                test_animal as t,
                individual_animal as i,
                taxon
            where
                audiogram_publication.audiogram_experiment_id=exp.id
                and publication.id=audiogram_publication.publication_id
                and t.audiogram_experiment_id=exp.id
                and i.id=t.individual_animal_id
                and taxon.ott_id=i.taxon_id
                and exp.id in %(list)s
            group by
                   exp.id
            """,
                {'list': param})
            row_headers = [x[0] for x in cursor.description]
            all_results = cursor.fetchall()
        return {'headers': row_headers, 'results': all_results}


class Summary_query(Query):
    """Summarize the data in the database"""

    def _run(self, param=None):
        with self.connection as cursor:
            cursor.execute(
                """
                select
                    (select count(distinct id) from audiogram_experiment where medium='water'
                    ) as in_water,
                    (select
                         count(distinct unique_name)
                      from
                         taxon,audiogram_experiment,test_animal,individual_animal
                      where
                         audiogram_experiment.medium='water'
                         and
                         test_animal.audiogram_experiment_id=audiogram_experiment.id
                         and
                         test_animal.individual_animal_id=individual_animal.id
                         and
                         individual_animal.taxon_id=taxon.ott_id
                         and
                         taxon.rank='species') as in_water_species,
                    (select count(distinct id) from audiogram_experiment where medium='air'
                    ) as in_air,
                    (select
                         count(distinct unique_name)
                      from
                         taxon,audiogram_experiment,test_animal,individual_animal
                      where
                         audiogram_experiment.medium='air'
                         and
                         test_animal.audiogram_experiment_id=audiogram_experiment.id
                         and
                         test_animal.individual_animal_id=individual_animal.id
                         and
                         individual_animal.taxon_id=taxon.ott_id
                         and
                         taxon.rank='species') as in_air_species,
                    (select count(distinct id) from audiogram_experiment where medium='air'
                    ) as in_air
                """
            )
            row_headers = [x[0] for x in cursor.description]
            all_results = cursor.fetchall()
        return {'headers': row_headers, 'results': all_results}


class Data_points_query_convert(Query):
    """Get data points for experiment id, convert SPL units on-the-fly."""

    def _run(self, param=None):
        with self.connection as cursor:
            cursor.execute(
                """
                select *
                from
                   audiogram_data_point
                where
                   audiogram_experiment_id=%(audiogram_experiment_id)s
                """,  # noqa: E501
                {'audiogram_experiment_id': param})
            row_headers = [x[0] for x in cursor.description]
            all_results = cursor.fetchall()

        converter = SPL_converter()
        all_converted = []
        for r in all_results:
            l = list(r)
            value = l[3]  # sound_pressure_level_in_decibel
            from_id = l[4]  # sound_pressure_level_reference_id
            l[3] = converter.convert(value, from_id)
            l[4] = 1
            c = tuple(l)
            all_converted.append(c)

        return {'headers': row_headers, 'results': all_converted}


class Data_points_query(Query):
    """Get data points for experiment id."""

    def _run(self, param=None):
        with self.connection as cursor:
            cursor.execute(
                """
                select *
                from
                   audiogram_data_point
                where
                   audiogram_experiment_id=%(audiogram_experiment_id)s
                """,  # noqa: E501
                {'audiogram_experiment_id': param})
            row_headers = [x[0] for x in cursor.description]
            all_results = cursor.fetchall()
        return {'headers': row_headers, 'results': all_results}


class Data_points_values_only_query(Query):
    """used for checking for duplicates"""

    def _run(self, param=None):
        with self.connection as cursor:
            cursor.execute(
                """
                select *
                from
                   audiogram_data_point
                where
                   audiogram_experiment_id=%(audiogram_experiment_id)s
                """,  # noqa: E501
                {'audiogram_experiment_id': param})
            row_headers = [x[0] for x in cursor.description]
            all_results = cursor.fetchall()
        return {'headers': row_headers, 'results': all_results}


class Download_query(Query):
    """Get original data for experiment id, values in the original, uncorverted units."""

    def _run(self, param=None):
        with self.connection as cursor:
            cursor.execute(
                """
    select
        exp.id as 'Audiogram ID',
        taxon.unique_name as 'Latin name',
        publication.citation_long as 'Source long',
        publication.citation_short as 'Source short',
        publication.doi as DOI,
        number_of_measurements as Measurements,
        sex,
        individual_name as 'Name of the animal',
        t.life_stage as 'Life stage',
        t.age_min_in_month as 'Age min in months',
        t.age_max_in_month as 'Age max in months',
        t.liberty_status as 'Status of liberty',
        t.captivity_duration_in_month as 'Duration in captivity in months',
        f1.name as 'Name of the Facility',
        latitude_in_decimal_degree as Latitude,
        longitude_in_decimal_degree as Longitude,
        position_of_animal as 'Position of the animal',
        distance_to_sound_source_in_meter as 'Distance to sound source in m',
        test_environment_description as 'Test environment',
        medium as Medium,
        concat(m3.denomination, ": ", m1.denomination) as 'Method',
        position_first_electrode as 'Position of the 1st electrode',
        position_second_electrode as 'Position of the 2nd electrode',
        position_third_electrode as 'Position of the 3rd electrode',
        year_of_experiment_start as 'Year of experiment start',
        year_of_experiment_end as 'Year of experiment end',
        calibration as Calibration,
        threshold_determination_method as 'Threshold determination info in percent',
        testtone_duration_in_millisecond as 'Duration of test tone',
        m2.denomination as 'Form of the tone',
        testtone_presentation_staircase as 'Staircase procedure',
        testtone_presentation_method_constants as 'Method of constants',
        testtone_presentation_sound_form as 'Form of the sound',
        sedated as Sedated,
        sedation_details as 'Sedation details',
        testtone_frequency_in_khz as 'Frequency in kHz',
        sound_pressure_level_in_decibel as SPL,
        replace(spl_reference_display_label,"Î¼","μ") as 'SPL reference'
    from
        audiogram_experiment exp
        left join method m1 on m1.id=exp.measurement_method_id
        left join method m2 on m2.id=exp.testtone_form_method_id
        left join method m3 on m3.id=m1.parent_method_id
        left join facility f1 on f1.id=exp.facility_id,
        audiogram_publication, publication, audiogram_data_point,
        sound_pressure_level_reference,
        test_animal as t,individual_animal as i,
        taxon
    where
        exp.id=%(id)s
        and
        audiogram_data_point.audiogram_experiment_id=exp.id
        and
        sound_pressure_level_reference.id=audiogram_data_point.sound_pressure_level_reference_id
        and audiogram_publication.audiogram_experiment_id=exp.id
        and publication.id=audiogram_publication.publication_id
        and t.audiogram_experiment_id=exp.id
        and i.id=t.individual_animal_id
        and taxon.ott_id=i.taxon_id
            """,  # noqa: E501
            {'id': param})

            row_headers = [x[0] for x in cursor.description]
            all_results = cursor.fetchall()
            # logging.warning(all_results)
        return {'headers': row_headers, 'results': all_results}


class Experiment_query(Query):
    """Get experiment metadata for experiment id."""

    def _run(self, param=None):
        with self.connection as cursor:
            cursor.execute(
                """
            select
                latitude_in_decimal_degree,
                longitude_in_decimal_degree,
                position_of_animal,
                distance_to_sound_source_in_meter,
                test_environment_description,
                medium,
                position_first_electrode,
                position_second_electrode,
                position_third_electrode,
                concat(year_of_experiment_start, " - ", year_of_experiment_end) as year_of_experiment,
                background_noise_in_decibel,
                calibration,
                threshold_determination_method,
                testtone_presentation_staircase,
                testtone_presentation_method_constants,
                testtone_presentation_sound_form,
                sedated, sedation_details,
                number_of_measurements,
                f1.name as facility_name,
                concat(m3.denomination, ": ", m1.denomination) as measurement_method,
                m2.denomination as testtone_form_method,
                measurement_type
            from
                audiogram_experiment exp
                left join method m1 on m1.id=exp.measurement_method_id
                left join method m2 on m2.id=exp.testtone_form_method_id
                left join method m3 on m3.id=m1.parent_method_id
                left join facility f1 on f1.id=exp.facility_id,
                audiogram_publication, publication
            where
                exp.id=%(id)s
            and
                audiogram_publication.audiogram_experiment_id=exp.id
                and publication.id=audiogram_publication.publication_id
                group by exp.id;
            """,
                {'id': param})
            row_headers = [x[0] for x in cursor.description]
            all_results = cursor.fetchall()
        return {'headers': row_headers, 'results': all_results}


class Caption_query(Query):
    """Get caption for audiogram by experiment id."""

    def _run(self, param=None):
        with self.connection as cursor:
            cursor.execute(
                """
            select distinct
                citation_short,
                vernacular_name_english,
                unique_name as species_name,
                measurement_type
            from
                audiogram_experiment exp,
                audiogram_publication, publication,
                test_animal as t,individual_animal as i,
                taxon
            where
                exp.id=%(id)s
                and audiogram_publication.audiogram_experiment_id=exp.id
                and publication.id=audiogram_publication.publication_id
                and t.audiogram_experiment_id=exp.id
                and i.id=t.individual_animal_id
                and taxon.ott_id=i.taxon_id;
                """,
                {'id': param})
            row_headers = [x[0] for x in cursor.description]
            all_results = cursor.fetchall()
        return {'headers': row_headers, 'results': all_results}


class Animal_query(Query):
    """Get details of animal(s) involved in this experiment."""

    def _run(self, param=None):
        with self.connection as cursor:
            cursor.execute(
                """
            select
                individual_name,
                vernacular_name_english,
                unique_name as species_name,
                sex,
                life_stage,
                floor(age_min_in_month) as age_in_month,
                liberty_status,
                captivity_duration_in_month,
                biological_season
            from
                test_animal as t,
                individual_animal as i,
                taxon
            where
                audiogram_experiment_id=%(id)s
                and i.id=t.individual_animal_id
                and taxon.ott_id=i.taxon_id;
                """,
                {'id': param})
            row_headers = [x[0] for x in cursor.description]
            all_results = cursor.fetchall()
        return {'headers': row_headers, 'results': all_results}


class Species_query(Query):
    """Get species name(s) of animal(s) involved in this experiment."""

    def _run(self, param=None):
        with self.connection as cursor:
            cursor.execute(
                """
            select distinct
                vernacular_name_english,unique_name as species_name
            from
                test_animal as t,
                individual_animal as i,
                taxon
            where
                audiogram_experiment_id=%(id)s
                and i.id=t.individual_animal_id
                and taxon.ott_id=i.taxon_id;
                """,
                {'id': param})
            row_headers = [x[0] for x in cursor.description]
            all_results = cursor.fetchall()
        return {'headers': row_headers, 'results': all_results}


class All_taxa_query(Query):
    """Get taxon taxon id, taxon name and animal count for all taxa in the database.

    for the time being: return only species and subspecies
    """

    def _run(self, param=None):
        with self.connection as cursor:
            cursor.execute(
                """
                select
                   taxon.unique_name as taxon_name,
                   taxon.ott_id,
                   count(individual_animal.id) as total
                from
                   taxon
                left join
                   individual_animal on taxon.ott_id = individual_animal.taxon_id
                where
                   taxon.rank in ('species', 'subspecies')
                group by
                   taxon.ott_id
                order by
                   taxon_name
                """
            )
            row_headers = [x[0] for x in cursor.description]
            all_results = cursor.fetchall()
        return {'headers': row_headers, 'results': all_results}


class All_taxa_vernacular_query(Query):
    """Get taxon taxon id, English name and animal count for all taxa in the database.

    for the time being: return only species and subspecies
    """

    def _run(self, param=None):
        with self.connection as cursor:
            cursor.execute(
                """
                select
                   taxon.vernacular_name_english as vernacular_name_english,
                   taxon.ott_id,
                   count(individual_animal.id) as total
                from
                   taxon
                left join
                   individual_animal on taxon.ott_id = individual_animal.taxon_id
                where
                   taxon.rank in ('species', 'subspecies')
                group by
                   taxon.ott_id
                order by
                   vernacular_name_english
                """
            )
            row_headers = [x[0] for x in cursor.description]
            all_results = cursor.fetchall()
        return {'headers': row_headers, 'results': all_results}


class All_measurement_methods_query(Query):
    """Get method id and full method name for all measurement methods in the database."""

    def _run(self, param=None):
        with self.connection as cursor:
            cursor.execute(
                """
                select
                   method.id as method_id,
                   concat(m2.denomination, ": ", m1.denomination) as method_name
                from
                   audiogram_experiment exp
                   left join method m1 on m1.id=exp.measurement_method_id
                   left join method m2 on m2.id=m1.parent_method_id,
                   method
                where
                   exp.measurement_method_id=method.id
                   and m2.denomination is not NULL
                group by
                   method_id
                order by
                   method_name
                """
            )
            row_headers = [x[0] for x in cursor.description]
            all_results = cursor.fetchall()
        return {'headers': row_headers, 'results': all_results}


class Parent_measurement_methods_query(Query):
    """Get method id and full method name for parent measurement methods in the database."""

    def _run(self, param=None):
        with self.connection as cursor:
            cursor.execute(
                """
                select
                   id as method_id,
                   denomination as method_name
                from
                   method
                where
                   denomination in ('behavioral', 'electrophysiological')
                order by
                   denomination
                """
            )
            row_headers = [x[0] for x in cursor.description]
            all_results = cursor.fetchall()
        return {'headers': row_headers, 'results': all_results}


class All_tone_methods_query(Query):
    """Get method id and full method name for all measurement methods in the database."""

    def _run(self, param=None):
        with self.connection as cursor:
            cursor.execute(
                """
                select
                   method.id as method_id,
                   method.denomination as method_name
                from
                   audiogram_experiment exp
                   left join method m1 on m1.id=exp.testtone_form_method_id,
                   method
                where
                   exp.testtone_form_method_id=method.id
                group by
                   method_id
                order by
                   method_name
                """
            )
            row_headers = [x[0] for x in cursor.description]
            all_results = cursor.fetchall()
        return {'headers': row_headers, 'results': all_results}


class All_publications_query(Query):
    """Get publication id and short citation for all publications in the database."""

    def _run(self, param=None):
        with self.connection as cursor:
            cursor.execute(
                """
                select
                   id,
                   citation_short
                from
                   publication
                order by
                   citation_short;
                """
            )
            row_headers = [x[0] for x in cursor.description]
            all_results = cursor.fetchall()
        return {'headers': row_headers, 'results': all_results}


class All_facilities_query(Query):
    """Get all facilities in the database."""

    def _run(self, param=None):
        with self.connection as cursor:
            cursor.execute(
                """
                select
                   id,
                   name
                from
                   facility
                order by
                   name;
                """
            )
            row_headers = [x[0] for x in cursor.description]
            all_results = cursor.fetchall()
        return {'headers': row_headers, 'results': all_results}


class Browse_query(Query):
    """
    Get a complete list of short audiogram descriptions.

    i.e.:
    * Experiment id
    * Short citation
    * Facility
    * English vernacular and scientific name of species

    @param dict - order_by and/or filter
    """

    def _str2tuple(self, val):
        return tuple(val.split(','))

    def _run(self, param=None):
        query = """
            select
                exp.id,
                publication_id, citation_short,
                vernacular_name_english,
                unique_name as species_name,
                concat(m2.denomination, ": ", m1.denomination) as measurement_method
            from
                audiogram_experiment exp
                left join method m1 on m1.id=exp.measurement_method_id
                left join method m2 on m2.id=m1.parent_method_id,
                audiogram_publication,
                publication,
                test_animal as t,
                individual_animal as i,
                taxon, facility
            where
                audiogram_publication.audiogram_experiment_id=exp.id
                and publication.id=audiogram_publication.publication_id
                and t.audiogram_experiment_id=exp.id
                and i.id=t.individual_animal_id
                and taxon.ott_id=i.taxon_id
                """

        ### add subquery for each parameter that has a value ###

        species = None
        if self._check_key_in_param(param, 'species'):
            species = self._str2tuple(param['species'])
            query += "and taxon.ott_id in %(species)s\n"

        taxon = None
        if self._check_key_in_param(param, 'taxon'):
            taxon = self._str2tuple(param['taxon'])
            query += "and taxon.ott_id in %(taxon)s\n"

        method = None
        if self._check_key_in_param(param, 'method'):
            method = self._str2tuple(param['method'])
            query += "and (exp.measurement_method_id in %(method)s or m2.id in %(method)s)\n"

        publication = None
        if self._check_key_in_param(param, 'publication'):
            publication = self._str2tuple(param['publication'])
            query += "and audiogram_publication.publication_id in %(publication)s\n"

        facility = None
        if self._check_key_in_param(param, 'facility'):
            facility = self._str2tuple(param['facility'])
            query += "and exp.facility_id = facility.id and facility.id in %(facility)s\n"

        year_from = None
        if self._check_key_in_param(param, 'year_from'):
            year_from = param['year_from']
            query += "and exp.year_of_experiment_start >= %(year_from)s\n"

        year_to = None
        if self._check_key_in_param(param, 'year_to'):
            year_to = param['year_to']
            query += "and exp.year_of_experiment_end <= %(year_to)s\n"

        medium = None
        if self._check_key_in_param(param, 'medium'):
            medium = self._str2tuple(param['medium'])
            query += "and exp.medium in %(medium)s\n"

        sex = None
        if self._check_key_in_param(param, 'sex'):
            sex = self._str2tuple(param['sex'])
            query += "and i.sex in %(sex)s\n"

        liberty = None
        if self._check_key_in_param(param, 'liberty'):
            liberty = self._str2tuple(param['liberty'])
            query += "and t.liberty_status in %(liberty)s\n"

        lifestage = None
        if self._check_key_in_param(param, 'lifestage'):
            lifestage = self._str2tuple(param['lifestage'])
            query += "and t.life_stage in %(lifestage)s\n"

        captivity_from = None
        if self._check_key_in_param(param, 'captivity_from'):
            captivity_from = param['captivity_from']
            query += "and t.captivity_duration_in_month >= %(captivity_from)s\n"

        captivity_to = None
        if self._check_key_in_param(param, 'captivity_to'):
            captivity_to = param['captivity_to']
            query += "and t.captivity_duration_in_month <= %(captivity_to)s\n"

        sedated = None
        if self._check_key_in_param(param, 'sedated'):
            sedated = self._str2tuple(param['sedated'])
            query += "and exp.sedated in %(sedated)s\n"

        age_from = None
        if self._check_key_in_param(param, 'age_from'):
            age_from = param['age_from']
            query += "and t.age_min_in_month >= %(age_from)s\n"

        age_to = None
        if self._check_key_in_param(param, 'age_to'):
            age_to = param['age_to']
            query += "and t.age_max_in_month <= %(age_to)s\n"

        position = None
        if self._check_key_in_param(param, 'position'):
            position = self._str2tuple(param['position'])
            query += "and exp.position_of_animal in %(position)s\n"

        distance_from = None
        if self._check_key_in_param(param, 'distance_from'):
            distance_from = param['distance_from']
            query += "and exp.distance_to_sound_source_in_meter >= %(distance_from)s\n"

        distance_to = None
        if self._check_key_in_param(param, 'distance_to'):
            distance_to = param['distance_to']
            query += "and exp.distance_to_sound_source_in_meter <= %(distance_to)s\n"

        threshold_from = None
        if self._check_key_in_param(param, 'threshold_from'):
            threshold_from = param['threshold_from']
            query += "and exp.threshold_determination_method >= %(threshold_from)s\n"

        threshold_to = None
        if self._check_key_in_param(param, 'threshold_to'):
            threshold_to = param['threshold_to']
            query += "and exp.threshold_determination_method <= %(threshold_to)s\n"

        tone = None
        if self._check_key_in_param(param, 'tone'):
            tone = self._str2tuple(param['tone'])
            query += "and exp.testtone_form_method_id in %(tone)s\n"

        staircase = None
        if self._check_key_in_param(param, 'staircase'):
            staircase = self._str2tuple(param['staircase'])
            query += "and exp.testtone_presentation_staircase in %(staircase)s\n"

        form = None
        if self._check_key_in_param(param, 'form'):
            form = self._str2tuple(param['form'])
            query += "and exp.testtone_presentation_sound_form in %(form)s\n"

        constants = None
        if self._check_key_in_param(param, 'constants'):
            constants = self._str2tuple(param['constants'])
            query += "and exp.testtone_presentation_method_constants in %(constants)s\n"

        measurement_type = None
        if self._check_key_in_param(param, 'measurement_type'):
            measurement_type = self._str2tuple(param['measurement_type'])
            query += "and exp.measurement_type in %(measurement_type)s\n"

        query += "group by exp.id\n"

        # set the order of the results, depending on the parameters #

        if self._check_key_in_param(param, 'order_by'):
            if param['order_by'] == 'citation_short':
                query += "order by citation_short"
            elif param['order_by'] == 'measurement_method':
                query += "order by measurement_method"
            elif param['order_by'] == 'vernacular_name_english':
                query += "order by vernacular_name_english"
            elif param['order_by'] == 'species_name':
                query += "order by species_name"
            else:
                query += "order by species_name"
        else:
            query += "order by vernacular_name_english"

        # logging.warning(param)
        logging.warning(query)

        # Execute the query, pass the GET parameter values,
        # relying on the database API to do proper escaping

        with self.connection as cursor:
            cursor.execute(
                query,
                {
                    'species': species,
                    'taxon': taxon,
                    'method': method,
                    'publication': publication,
                    'facility': facility,
                    'year_from': year_from,
                    'year_to': year_to,
                    'medium': medium,
                    'sex': sex,
                    'liberty': liberty,
                    'lifestage': lifestage,
                    'captivity_from': captivity_from,
                    'captivity_to': captivity_to,
                    'sedated': sedated,
                    'age_from': age_from,
                    'age_to': age_to,
                    'position': position,
                    'distance_from': distance_from,
                    'distance_to': distance_to,
                    'threshold_from': threshold_from,
                    'threshold_to': threshold_to,
                    'tone': tone,
                    'staircase': staircase,
                    'form': form,
                    'constants': constants,
                    'measurement_type': measurement_type
                })
            row_headers = [x[0] for x in cursor.description]
            all_results = cursor.fetchall()

        # logging.warning(all_results)

        return {'headers': row_headers, 'results': all_results}

    def _check_key_in_param(self, param, key):
        return (key in param and param[key] is not None and param[key] != 'null' and param[key] != '' and param[key] != 'undefined')


class Data_query(Query):
    """Get all data points for a given experiment, converted to modern units."""

    def _run(self, param=None):
        with self.connection as cursor:
            cursor.execute(
                """
            select
                testtone_duration_in_millisecond,
                testtone_frequency_in_khz,
                sound_pressure_level_in_decibel,
                sound_pressure_level_reference_id,
                sound_pressure_level_reference_method,
                audiogram_experiment_id,
                spl_reference_value,spl_reference_unit,spl_reference_significance,
                conversion_factor_airborne_sound_in_decibel,
                conversion_factor_waterborne_sound_in_decibel,
                spl_reference_display_label
            from
                audiogram_data_point point
            left join
                sound_pressure_level_reference spl
            on
                spl.id=point.sound_pressure_level_reference_id
            where
                audiogram_experiment_id=%(id)s
                """,
                {'id': param})
            row_headers = [x[0] for x in cursor.description]
            all_results = cursor.fetchall()

        converter = SPL_converter()
        all_converted = []
        for r in all_results:
            l = list(r)
            value = l[2]  # sound_pressure_level_in_decibel
            from_id = l[3]  # sound_pressure_level_reference_id
            if from_id in [2, 3, 5, 6, 7]:
                l[2] = converter.convert(value, from_id)
            # water
            if from_id in [1, 2, 3, 6]:
                l[3] = 1
                l[11] = "re 1 μPa"
            # air
            elif from_id in [4, 5]:
                l[3] = 4
                l[11] = "re 20 μPa"
            c = tuple(l)
            #logging.warning("tuple" + str(c))
            all_converted.append(c)
        return {'headers': row_headers, 'results': all_converted}


class Publication_query(Query):
    """Get all publications for a given experiment."""

    def _run(self, param=None):
        with self.connection as cursor:
            cursor.execute(
                """
            select
                citation_long, DOI
            from
                audiogram_experiment exp,
                audiogram_publication,
                publication
            where
                exp.id=%(id)s
            and
                audiogram_publication.audiogram_experiment_id=exp.id
                and publication.id=audiogram_publication.publication_id
                """,
                {'id': param})
            row_headers = [x[0] for x in cursor.description]
            all_results = cursor.fetchall()
        return {'headers': row_headers, 'results': all_results}


class Birds_query(Query):
    """Get all experiment id's (with medium) for birds"""

    def _run(self, param=None):
        with self.connection as cursor:
            cursor.execute(
                """
            select
                unique_name,ott_id,audiogram_experiment_id,medium
            from
                taxon,individual_animal,test_animal,audiogram_experiment
            where
                lft > (select lft from taxon where unique_name='Aves')
            and
                rgt < (select rgt from taxon where unique_name='Aves')
                and
                rank="species"
                and individual_animal.taxon_id=taxon.ott_id
                and test_animal.individual_animal_id=individual_animal.id
                and audiogram_experiment.id=test_animal.audiogram_experiment_id
                """
            )
            row_headers = [x[0] for x in cursor.description]
            all_results = cursor.fetchall()
        return {'headers': row_headers, 'results': all_results}


class Mammals_query(Query):
    """Get all experiment id's (with medium) for mammals"""

    def _run(self, param=None):
        with self.connection as cursor:
            cursor.execute(
                """
            select
                unique_name,ott_id,audiogram_experiment_id,medium
            from
                taxon,individual_animal,test_animal,audiogram_experiment
            where
                lft > (select lft from taxon where unique_name='Mammalia')
            and
                rgt < (select rgt from taxon where unique_name='Mammalia')
                and
                rank="species"
                and individual_animal.taxon_id=taxon.ott_id
                and test_animal.individual_animal_id=individual_animal.id
                and audiogram_experiment.id=test_animal.audiogram_experiment_id
                """
            )
            row_headers = [x[0] for x in cursor.description]
            all_results = cursor.fetchall()
        return {'headers': row_headers, 'results': all_results}


class Reptiles_query(Query):
    """Get all experiment id's (with medium) for reptiles"""

    def _run(self, param=None):
        with self.connection as cursor:
            cursor.execute(
                """
            select
                unique_name,ott_id,audiogram_experiment_id,medium
            from
                taxon,individual_animal,test_animal,audiogram_experiment
            where
                lft > (select lft from taxon where unique_name='Reptilia')
            and
                rgt < (select rgt from taxon where unique_name='Reptilia')
                and
                rank="species"
                and individual_animal.taxon_id=taxon.ott_id
                and test_animal.individual_animal_id=individual_animal.id
                and audiogram_experiment.id=test_animal.audiogram_experiment_id
                """
            )
            row_headers = [x[0] for x in cursor.description]
            all_results = cursor.fetchall()
        return {'headers': row_headers, 'results': all_results}


class Cetaceans_query(Query):
    """
    Get all experiment id's (with medium) for cetaceans
    NOTE: at the moment, the database only have cetaceans of families: Phocoenidae, Monodontidae, Delphinidae, Ziphiidae
    """

    def _run(self, param=None):
        with self.connection as cursor:
            cursor.execute(
                """
            select
                unique_name,ott_id,audiogram_experiment_id,medium
            from
                taxon,individual_animal,test_animal,audiogram_experiment
            where
                (
                    lft>(select lft from taxon where unique_name='Delphinidae')
                    and
                    rgt<(select rgt from taxon where unique_name='Delphinidae')
                or
                    lft>(select lft from taxon where unique_name='Monodontidae')
                    and
                    rgt<(select rgt from taxon where unique_name='Monodontidae')
                or
                    lft>(select lft from taxon where unique_name='Phocoenidae') 
                    and
                    rgt<(select rgt from taxon where unique_name='Phocoenidae')
                or
                    lft>(select lft from taxon where unique_name='Ziphiidae') 
                    and
                    rgt<(select rgt from taxon where unique_name='Ziphiidae')
                )
                and
                rank="species"
                and individual_animal.taxon_id=taxon.ott_id
                and test_animal.individual_animal_id=individual_animal.id
                and audiogram_experiment.id=test_animal.audiogram_experiment_id
                """
            )
            row_headers = [x[0] for x in cursor.description]
            all_results = cursor.fetchall()
        return {'headers': row_headers, 'results': all_results}


class Fishes_query(Query):
    """
    Get all experiment id's (with medium) for fishes
    NOTE: at the moment, the database only have fishes of class Actinopteri
    """

    def _run(self, param=None):
        with self.connection as cursor:
            cursor.execute(
                """
            select
                unique_name,ott_id,audiogram_experiment_id,medium
            from
                taxon,individual_animal,test_animal,audiogram_experiment
            where
                lft > (select lft from taxon where unique_name='Actinopteri')
            and
                rgt < (select rgt from taxon where unique_name='Actinopteri')
                and
                rank="species"
                and individual_animal.taxon_id=taxon.ott_id
                and test_animal.individual_animal_id=individual_animal.id
                and audiogram_experiment.id=test_animal.audiogram_experiment_id
                """
            )
            row_headers = [x[0] for x in cursor.description]
            all_results = cursor.fetchall()
        return {'headers': row_headers, 'results': all_results}


class Seals_query(Query):
    """
    Get all experiment id's (with medium) for seals
    """

    def _run(self, param=None):
        with self.connection as cursor:
            cursor.execute(
                """
            select
                unique_name,ott_id,audiogram_experiment_id,medium
            from
                taxon,individual_animal,test_animal,audiogram_experiment
            where
                (
                    lft>(select lft from taxon where unique_name='Odobenidae') 
                    and
                    rgt<(select rgt from taxon where unique_name='Odobenidae') 
                or
                    lft>(select lft from taxon where unique_name='Otariidae') 
                    and
                    rgt<(select rgt from taxon where unique_name='Otariidae') 
                or
                    lft>(select lft from taxon where unique_name='Phocidae') 
                    and
                    rgt<(select rgt from taxon where unique_name='Phocidae')
                )
                and
                rank="species"
                and individual_animal.taxon_id=taxon.ott_id
                and test_animal.individual_animal_id=individual_animal.id
                and audiogram_experiment.id=test_animal.audiogram_experiment_id
                """
            )
            row_headers = [x[0] for x in cursor.description]
            all_results = cursor.fetchall()
        return {'headers': row_headers, 'results': all_results}


class Taxonomy_query(Query):
    """get full taxonomic tree in the database"""

    def _run(self, param=None):
        with self.connection as cursor:
            cursor.execute(
                """
                select
                   *
                from
                   taxon
                order by
                   unique_name
                """
            )
            row_headers = [x[0] for x in cursor.description]
            all_results = cursor.fetchall()
        return {'headers': row_headers, 'results': all_results}
