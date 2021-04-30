# -*- coding: utf-8 -*-
"""
Audiogrambase http API.

Created on 27.11.2019
@author: Alvaro Ortiz Troncoso, Museum fuer Naturkunde Berlin
"""

from flask import Flask, request, render_template, url_for, jsonify, Response, send_file
from flask_cors import CORS
import configparser
import simplejson
import logging
from Query import *
from celery import Celery
from Plotter import Plotter
from SPL_converter import SPL_converter


configPath = "/src/API/.env"
"""Path to configuration file."""
api_config = None
"""ConfigParser object will hold the custom API configuration """

fapp = Flask(__name__)
CORS(fapp)
fapp.config["DEBUG"] = True
fapp.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
fapp.config['JSON_AS_ASCII'] = False

# Configure and initialize Celery
fapp.config['CELERY_BROKER_URL'] = 'redis://aad_redis:6379/0'
fapp.config['CELERY_RESULT_BACKEND'] = 'redis://aad_redis:6379/0'
client = Celery(fapp.name, broker=fapp.config['CELERY_BROKER_URL'])
client.conf.update(fapp.config)


@fapp.route("/", methods=['GET'])
def home():
    return("Audiogrambase API")


# @fapp.route("/api/v1/test", methods=['GET'])
# def test():
#    return render_template('test.html')

@fapp.route("/api/v1/download", methods=['GET'])
def download():
    """
    Returns downloadable data for given audiogram.
    Downloadable data is in the original units, which may be different
    from the units used to display the audiogram in the Web interface.

    Parameters
    ----------
    id : int, required
       id of an audiogram

    Returns
    ----------
    A file in CSV format with a row for each data point.

    Raises
    ----------
    Exception
       If no audiogram id was given

    Example
    ---------
    https://animalaudiograms.museumfuernaturkunde.berlin/api/v1/download?id=111
    Returns the data for audiogram 111 as a downloadable csv file.
    """
    if 'id' not in request.args:
        raise Exception("No id was given.")
    id = int(request.args['id'])
    data_points = Download_query(api_config).run(id)
    csv = json2csv(data_points)
    response = Response(csv, mimetype="text/csv")
    response.headers["Content-Disposition"] = "attachment;filename=Audiogram_{0}.csv".format(
        id)
    return response


@fapp.route("/api/v1/download_multiple", methods=['GET'])
def download_multiple():
    """Download data for given audiogram"""
    if 'ids' not in request.args:
        raise Exception("No ids were given.")
    ids = request.args['ids'].split(",")
    csv = ""
    for id in ids:
        data_points = Download_query(api_config).run(id)
        csv += json2csv(data_points)
    response = Response(csv, mimetype="text/csv")
    filename = '_'.join(ids)
    response.headers["Content-Disposition"] = "attachment;filename=Audiogram_{0}.csv".format(
        filename)
    return "sep=,\r\n"+response


def json2csv(data_points):
    headers = data_points[0].keys()
    headers_str = ';'.join(headers)
    rows = []
    for p in data_points:
        vals = p.values()
        strvals = []
        for v in vals:
            strvals.append('"{0}"'.format(str(v)))
        rows.append(';'.join(strvals))
    csv = '\n'.join(rows)
    csv = headers_str + '\n' + csv
    return csv


@fapp.route("/api/v1/is_compatible", methods=['GET'])
def is_compatible():
    """
    Checks that requested audiograms have compatible units.
    Units are compatible if the audiograms have been obtained in the same medium (water or air).

    Parameters
    ----------
    ids : comma-separated list of int, required
       ids of audiograms

    Returns
    ----------
    "true" or "false"

    Raises
    ----------
    Exception
       If no audiogram ids were given

    Example
    ---------
    https://animalaudiograms.museumfuernaturkunde.berlin/api/v1/is_compatible?ids=187,186
    Returns "true"
    """
    if 'ids' not in request.args:
        raise Exception("No ids were given.")
    ids = request.args['ids'].split(",")
    # logging.warning(ids)
    units = SPLUnits_query(api_config).run(ids)
    compat = SPL_converter().check(units)
    return jsonify(compat)


@fapp.route("/api/v1/is_converted", methods=['GET'])
def is_converted():
    """
    Checks whether an audiogram has been converted to current units.
    This method is intended for usage in the web interface.
    """
    if 'ids' not in request.args:
        raise Exception("No id given.")
    id = request.args['ids']
    units = SPLUnits_query(api_config).run([id])
    compat = SPL_converter().is_converted(units)
    return jsonify(compat)


@fapp.route("/api/v1/summary", methods=['GET'])
def summary():
    """
    Summarizes the data in the database.

    Parameters
    ----------
    none

    Returns
    ----------
    A string in json format containing:
    # "in_air" : number of audiograms obtained in air
    # "in_air_species" : number of animal species for which in air audiograms are recorded in the database
    # in_water : number of audiograms obtaine in water
    # "in_water_species" : number of animal species for which in water audiograms are recorded in the database

    Raises
    ----------
    none

    Example
    ---------
    https://animalaudiograms.museumfuernaturkunde.berlin/api/v1/summary
    Returns a json string describing the current contents of the database
    """
    summary = Summary_query(api_config).run()
    return jsonify(summary)


@fapp.route("/api/v1/list", methods=['GET'])
def list():
    """
    Returns a list of short audiogram descriptions.

    Parameters
    ----------
    ids : comma-separated list of int, required
       ids of audiograms

    Returns
    ----------
    A string in json format containing for each audiogram requested in the ids parameter:
    # citation_short : citation in short form of the original article
    # id : database id of the audiogram
    # measurement_method : name of the experimental method used to obtain the audiogram
    # species_name : scientific name of the animal species examined
    # vernacular_name-english : english name of the animal species examined

    Raises
    ----------
    Exception
       If no audiogram ids were given

    Example
    ---------
    https://animalaudiograms.museumfuernaturkunde.berlin/api/v1/list?ids=186,187
    Returns a json string with a short description of audiograms 186 and 187
    """
    if 'ids' not in request.args:
        raise Exception("No ids were given.")
    ids = request.args['ids'].split(",")
    # logging.warning(ids)
    audiograms = List_query(api_config).run(ids)
    return jsonify(audiograms)


def _getArg(name):
    resp = None
    if name in request.args:
        resp = request.args[name]
    return resp


@fapp.route("/api/v1/browse", methods=['GET'])
def browse():
    """
    Returns a list of short audiogram descriptions.
    This method can be used to query the database.

    Parameters
    ----------
    # order_by : string vernacular_name_english (default) | species_name (i.e. latin name)| 
       citation_short | measurement_method
    # species : int id of the species in the database
    # taxon : int id of the species in the database (same as species)
    # method : int id of the measurement method in the database 
    # publication : int id of the publication in the database
    # facility : int id of the facility in the database
    # from : year of the experiment (range start)
    # to : year of the experiment (range end)
    # medium : string air | water
    # sex : string male | female
    # liberty : string status of liberty of the animal captive | stranded | wild
    # lifestage : string life stage of the animal juvenile | adult | sub-adult
    # duration_in_captivity_from : int duration in captivity of the animal in months (range start)
    # duration_in_captivity_to : int duration in captivity of the animal in months (range end)
    # sedated : whether the animal was sedated yes | no
    # age_from : int age of the animal in months (range start)
    # age_to : int age of the animal in months (range end)
    # distance_from : int distance to the sound source in meters (range start)
    # distance_to : int distance to the sound source in meters (range end)
    # position: comma-separated list of string position of the animal during the experiment in-air and underwater|totally underwater|head just below water surface|head half out of water|outside of the water|totally above water
    # threshold_from : float Threshold determination info in % (range start)
    # threshold_to : float Threshold determination info in % (range end)
    # tone : int form of the tone
    # staircase : string staircase procedure yes | none
    # form : comma-separated list of string form of the sound click | pipe trains | prolonged |SAM (sinusoidal amplitude modulation)
    # constants : string method of constants yes | no
    # measurement_type: string 'auditory threshold' (default), 'critical ratio', 'critical bandwidth' etc.

    Returns
    ----------
    A string in json format containing for each audiogram requested in the ids parameter:
    # citation_short : citation in short form of the original article
    # id : database id of the audiogram
    # measurement_method : name of the experimental method used to obtain the audiogram
    # species_name : scientific name of the animal species examined
    # vernacular_name-english : english name of the animal species examined

    Raises
    ----------
    Exception
       If no audiogram ids were given

    Example
    ---------
    With no parameters:
    https://animalaudiograms.museumfuernaturkunde.berlin/api/v1/browse
    Returns a json string with a short description of all audiograms in the database,
    ordered by English vernacular name of animal species.

    With parameters: filtering by measurement method
    https://animalaudiograms.museumfuernaturkunde.berlin/api/v1/browse?order_by=species_name&method=1
    Returns a json string with a short description of all audiograms in the database
    obtained through behavioral methods and ordered by scientific name of animal species.

    With parameters: filtering by year
    https://animalaudiograms.museumfuernaturkunde.berlin/api/v1/browse?order_by=measurement_method&from=2018
    Returns a json string with a short description of all audiograms in the database
    obtained since 2018 (included) and ordered by measurement_method.
    """
    param = {
        'order_by': _getArg('order_by'),
        'species': _getArg('species'),
        'taxon': _getArg('taxon'),
        'method': _getArg('method'),
        'publication': _getArg('publication'),
        'facility': _getArg('facility'),
        'year_from': _getArg('from'),
        'year_to': _getArg('to'),
        'medium': _getArg('medium'),
        'sex': _getArg('sex'),
        'liberty': _getArg('liberty'),
        'lifestage': _getArg('lifestage'),
        'captivity_from': _getArg('duration_in_captivity_from'),
        'captivity_to': _getArg('duration_in_captivity_to'),
        'sedated': _getArg('sedated'),
        'age_from': _getArg('age_from'),
        'age_to': _getArg('age_to'),
        'position': _getArg('position'),
        'distance_from': _getArg('distance_from'),
        'distance_to': _getArg('distance_to'),
        'threshold_from': _getArg('threshold_from'),
        'threshold_to': _getArg('threshold_to'),
        'tone': _getArg('tone'),
        'staircase': _getArg('staircase'),
        'form': _getArg('form'),
        'constants': _getArg('constants'),
        'measurement_type': _getArg('measurement_type')
    }
    audiograms = Browse_query(api_config).run(param)
    return jsonify(audiograms)


@fapp.route("/api/v1/audiogram", methods=['GET'])
def get_audiogram_by_experiment_id():
    """
    Returns all data points for a given audiogram.

    Parameters
    ----------
    id : int, required database identifier of an audiogram

    Returns
    ----------
    A string in json format containing for each data point:
    # audiogram_experiment_id : int database identifier of the experiment this data point belongs to
    # id : int database identifier of this data point
    # sound_pressure_level_in_decibel : float SPL relative to sound_pressure_level_reference_id
    # sound_pressure_level_reference_id : int database identifier of the sound pressure level reference
    # sound_pressure_level_reference_method : string root mean squared (RMS) | peak to peak (PP)
    # testtone_duration_in_millisecond : float test tone duration
    # testtone_frequency_in_khz : float test tone frequency

    Raises
    ----------
    Exception if no id was given

    Example
    ---------
    https://animalaudiograms.museumfuernaturkunde.berlin/api/v1/audiogram?id=118
    Returns a json string with all data points of audiogram 118
    """
    if 'id' not in request.args:
        raise Exception("No id was given.")
    id = int(request.args['id'])
    data_points = Data_points_query_convert(api_config).run(id)
    return jsonify(data_points)


@fapp.route("/api/v1/plot", methods=['GET'])
def get_plot():
    """
    Returns information of the plotting process when plotting a single audiogram.

    Parameters
    ----------
    id : int, required database identifier of an audiogram

    Returns
    ----------
    A json object describing the status of the plotting process
    # Location : URL status of the plotting process. 
    Opening this URL gives information whether the plotting process is completed,
    and if so, the URL of the plot image.

    Raises
    ----------
    Exception if no id was given

    Example
    ---------
    https://animalaudiograms.museumfuernaturkunde.berlin/api/v1/audiogram?plot=118
    Returns a json string with the status of the plotting process
    """
    logging.warning('========================')
    if 'id' not in request.args:
        raise Exception("No id was given.")
    id = int(request.args['id'])
    # get the data points
    data_points = Data_query(api_config).run(id)
    # delegate execution
    logging.warning('PLOT')
    task = plot.delay(simplejson.dumps(data_points), request.url)
    # return the url where the status can be read
    return(
        jsonify({'Location': url_for('plotstatus', task_id=task.id)}),
        202,
        {'Location': url_for('plotstatus', task_id=task.id)}
    )


@fapp.route("/api/v1/plotlayers", methods=['GET'])
def get_plotlayers():
    """
    Returns information of the plotting process when plotting audiogram overlays.

    Parameters
    ----------
    ids : comma-separated list of int, required database identifier of audiograms

    Returns
    ----------
    A json object describing the status of the plotting process
    # Location : URL status of the plotting process. 
    Opening this URL gives information whether the plotting process is completed,
    and if so, the URL of the plot image.

    Raises
    ----------
    Exception if no id was given

    Example
    ---------
    https://animalaudiograms.museumfuernaturkunde.berlin/api/v1/audiogram?plot=118
    Returns a json string with the status of the plotting process
    """
    if 'ids' not in request.args:
        raise Exception("No ids were given.")
    ids = request.args['ids'].split(",")
    # sort ids as int when drawing layers, otherwise labels get assigned to wrong colors
    ids = [int(id) for id in ids]
    ids.sort()
    # get the data points
    data_points_array = []
    for id in ids:
        data_points_array.append(Data_query(api_config).run(id))

    # delegate execution
    task = plotlayers.delay(simplejson.dumps(data_points_array), request.url)
    # return the url where the status can be read
    return(
        jsonify({'Location': url_for('plotstatus', task_id=task.id)}),
        202,
        {'Location': url_for('plotstatus', task_id=task.id)}
    )


@client.task(bind=True, name='plot')
def plot(self, data_points, url):
    """
    Background task that runs a long function with progress reports.

    @param data_points: data to be plotted
    @param url: will be used for cache key. Only GET requests!
    """
    # plot the data points
    plotter = Plotter()
    img_file = plotter.plot(data_points, url)
    return {
        'current': 100,
        'total': 100,
        'status': 'Task completed!',
        'result': img_file
    }


@client.task(bind=True, name='plotlayers')
def plotlayers(self, data_points_array, url):
    """
    Background task that runs a long function with progress reports.

    @param data_points: data to be plotted
    @param url: will be used for cache key. Only GET requests!
    """
    # plot the data points
    plotter = Plotter()
    img_file = plotter.plotlayers(data_points_array, url)
    return {
        'current': 100,
        'total': 100,
        'status': 'Task completed!',
        'result': img_file
    }


@fapp.route('/status/<task_id>')
def plotstatus(task_id):
    """
    Return a progress report on the plotting process.

    Parameters
    ----------
    none

    Returns
    ----------
    A progress report in json format
    # state : string 'PENDING' | 'FAILURE' | 'SUCCESS'
    # current : int progress in %
    # total : int progress in % of result
    # status : string verbose descruption of process state
    # result : URL of plot image

    Raises
    ----------
    Exception if no id was given

    Example
    ---------
    see get_plot
    """
    task = plot.AsyncResult(task_id)
    if task.state == 'PENDING':
        response = {
            'state': task.state,
            'current': 0,
            'total': 1,
            'status': 'Pending...'
        }
    elif task.state != 'FAILURE':
        response = {
            'state': task.state,
            'current': task.info.get('current', 0),
            'total': task.info.get('total', 1),
            'status': task.info.get('status', '')
        }
        if 'result' in task.info:
            response['result'] = task.info['result']
    else:
        # something went wrong in the background job
        response = {
            'state': task.state,
            'current': 1,
            'total': 1,
            'status': str(task.info),  # this is the exception raised
        }
    return jsonify(response)


@fapp.route("/api/v1/experiment", methods=['GET'])
def get_experiment_by_id():
    """
    Returns experiment metadata.

    Parameters
    ----------
    id : int, required id of an audiogram

    Returns
    ----------
    Metadata of the experiment perfomed to obtain this audiogram, in json format
    # background_noise_in_decibel : int (mostly empty)
    # calibration : text description of how the experiment was calibrated
    # distance_to_sound_source_in_meter : int
    # facility_name : string name of the institution etc. where the experiment was carried out
    # latitude_in_decimal_degree : float (mostly empty)
    # longitude_in_decimal_degree : float (mostly empty)
    # measurement_method : string name of the measurement method used to obtain this audiogram (e.g. "behavioral: go - no go")
    # medium : string water | air
    # number_of_measurements: int count of measurements, when known
    # position_first_electrode : string placement of the electrode when applying electrophysiological methods
    # position_second_electrode : string placement of the electrode when applying electrophysiological methods
    # position_third_electrode : string placement of the electrode when applying electrophysiological methods
    # position_of_animal : string position of the animal during the experiment (e.g. "totally underwater")
    # sedated : string yes | no 
    # sedation_details : string description of the sedation method
    # test_environment_description : text test environment details and comments
    # testtone_form_method : string e.g. "sinusoidal frequency modulated tone (FM)"
    # testtone_presentation_method_constants : string yes | no
    # testtone_presentation_sound_form : string e.g. "click"
    # testtone_presentation_staircase : string yes | no
    # threshold_determination_method : float in %
    # year_of_experiment : year in YYYY format
    # measurement_type: string 'auditory threshold' (default), 'critical ratio', 'critical bandwidth' etc.

    Raises
    ----------
    Exception if no id was given

    Example
    ---------
    https://animalaudiograms.museumfuernaturkunde.berlin/api/v1/experiment?id=253
    Returns a json string with all available experiment metadata on audiogram 253
    """
    if 'id' not in request.args:
        raise Exception("No id was given.")
    id = int(request.args['id'])
    experiment = Experiment_query(api_config).run(id)
    if len(experiment) > 0:
        return jsonify(experiment[0])
    else:
        return ""


@fapp.route("/api/v1/caption", methods=['GET'])
def get_caption_by_id():
    """
    Returns a caption for an audiogram plot.

    Parameters
    ----------
    id : int, required id of an audiogram

    Returns
    ----------
    Caption of the audiogram, in json format
    # citation_short : citation in short form of the original article
    # species_name : scientific name of the animal species examined
    # vernacular_name-english : english name of the animal species examined
    # measurement_type: string 'auditory threshold' (default), 'critical ratio', 'critical bandwidth' etc.

    Raises
    ----------
    Exception if no id was given

    Example
    ----------
    http://localhost:9082/api/v1/caption?id=111
    Returns a json string with citation in short form, latin and vernacular name of the species.

    """
    if 'id' not in request.args:
        raise Exception("No id was given.")
    id = int(request.args['id'])
    caption = Caption_query(api_config).run(id)
    return jsonify(caption[0])


@fapp.route("/api/v1/data", methods=['GET'])
def get_data_by_experiment_id():
    """
    Returns all data points for a given audiogram and SPL unit used in the experiment.

    Parameters
    ----------
    id : int, required id of an audiogram

    Parameters
    ----------
    id : int, required database identifier of an audiogram

    Returns
    ----------
    A string in json format containing for each data point:
    # audiogram_experiment_id : int database identifier of the experiment this data point belongs to
    # conversion_factor_airborne_sound_in_decibel
    # conversion_factor_waterborne_sound_in_decibel
    # sound_pressure_level_in_decibel : float SPL relative to sound_pressure_level_reference_id
    # sound_pressure_level_reference_id : int database identifier of the sound pressure level reference
    # sound_pressure_level_reference_method : string root mean squared (RMS) | peak to peak (PP)
    # spl_reference_display_label : string human-readable representation of the SPL reference (e.g. re 1 μPa)
    # spl_reference_significance : whether the SPL reference is current or deprecated, in-air or in-water
    # spl_reference_unit : string unit of the SPL reference (e.g. "μPa")
    # spl_reference_value : value of the SPL reference in the given unit (e.g. "1")
    # testtone_duration_in_millisecond : float test tone duration
    # testtone_frequency_in_khz : float test tone frequency

    Raises
    ----------
    Exception if no id was given

    Example
    ---------
    https://animalaudiograms.museumfuernaturkunde.berlin/api/v1/data?id=118
    Returns a json string with all data points of audiogram 118 and corresponding SPL reference unit
    """
    if 'id' not in request.args:
        raise Exception("No id was given.")
    id = int(request.args['id'])
    data_points = Data_query(api_config).run(id)
    return jsonify(data_points)


@fapp.route("/api/v1/animal", methods=['GET'])
def get_animal_by_id():
    """
    Returns data on the  animal involved in this experiment.

    Parameters
    ----------
    id : int, required id of an audiogram

    Parameters
    ----------
    id : int, required database identifier of an audiogram

    Returns
    ----------
    A string in json format containing information on the animal:
    # age_in_month : int age of the animal in months,
    # biological_season : not used, 
    # captivity_duration_in_month : int duration in captivity of the animal in months,
    # individual_name : string name (or identifier) of the animal,
    # liberty_status : string status of liberty of the animal captive | stranded | wild
    # lifestage : string life stage of the animal juvenile | adult | sub-adult
    # sex : string male | female
    # species_name : scientific name of the animal species examined
    # vernacular_name-english : english name of the animal species examined

    Raises
    ----------
    Exception if no id was given

    Example
    ---------
    http://localhost:9082/api/v1/animal?id=111
    Returns a json string with the information on the animal (harbour porpoise in this case),
    its age and captivity status.
    """
    if 'id' not in request.args:
        raise Exception("No experiment id was given.")
    id = int(request.args['id'])
    animal = Animal_query(api_config).run(id)
    return jsonify(animal)


@fapp.route("/api/v1/species", methods=['GET'])
def get_species_by_experiment_id():
    """
    Returns latin name and vernacular name of the species of the animal involved in experiment.

    Parameters
    ----------
    id : int, required database identifier of an audiogram

    Returns
    ----------
    A string in json format containing information on the animal:
    # species_name : scientific name of the animal species examined
    # vernacular_name-english : english name of the animal species examined

    Example
    ---------
    http://localhost:9082/api/v1/species?id=111
    Returns a json string with the information on the animal species (harbour porpoise in this case)
    """
    id = _check_id()
    species = Species_query(api_config).run(id)
    return jsonify(species)


@fapp.route("/api/v1/all_species", methods=['GET'])
def get_all_taxa():
    """
    Returns all animal species in database (latin names), and audiogram counts per species.

    Parameters
    ----------
    id : int, required database identifier of an audiogram

    Returns
    ----------
    A list in json format containing information on the species recorded in the database:
    # ott_id : int species identifier, references the Open Tree of Life database
    # taxon_name : latin name of a species
    # total : int audiogram count for this species

    Example
    ---------
    http://localhost:9082/api/v1/all_species
    Returns a list of species currently recorded in the database.
    """
    species = All_taxa_query(api_config).run(id)
    return jsonify(species)


@fapp.route("/api/v1/all_species_vernacular", methods=['GET'])
def get_all_taxa_vernacular():
    """
    Returns all animal species in database (English names), and audiogram counts per species.

    Parameters
    ----------
    none

    Returns
    ----------
    A list in json format containing information on the species recorded in the database:
    # ott_id : int species identifier, references the Open Tree of Life database
    # vernacular_name_english : latin name of a species
    # total : int audiogram count for this species

    Example
    ---------
    http://localhost:9082/api/v1/all_species_vernacular
    Returns a list of species currently recorded in the database.
    """
    species = All_taxa_vernacular_query(api_config).run(id)
    return jsonify(species)


@fapp.route("/api/v1/all_measurement_methods", methods=['GET'])
def get_all_measurement_methods():
    """
    Returns all measurement methods in database.

    Parameters
    ----------
    none

    Returns
    ----------
    A list in json format containing all measurement methods recorded in the database:
    # method_id : int internal database identifier of this method
    # method_name : string name of the method. Method names are composed of:
    a generic method name ("behavioral" or "electrophysiological") and 
    a specific method name (e.g. "behavioral: go - no go")

    Example
    ---------
    http://localhost:9082/api/v1/all_methods
    Returns a list of measurement methods currently recorded in the database.
    """
    methods = All_measurement_methods_query(api_config).run(id)
    return jsonify(methods)


@fapp.route("/api/v1/parent_measurement_methods", methods=['GET'])
def get_parent_measurement_methods():
    """
    Returns high-level, generic measurement methods in database.

    Parameters
    ----------
    none

    Returns
    ----------
    A list in json format containing all generic measurement methods recorded in the database:
    # method_id : int internal database identifier of this method
    # method_name : string generic method name ("behavioral" or "electrophysiological")

    Example
    ---------
    http://localhost:9082/api/v1/parent_measurement_methods
    Returns a list of generic measurement methods currently recorded in the database.
    """
    methods = Parent_measurement_methods_query(api_config).run(id)
    return jsonify(methods)


@fapp.route("/api/v1/all_tone_methods", methods=['GET'])
def get_all_tone_methods():
    """
    Returns all tone methods in database.

    Parameters
    ----------
    none

    Returns
    ----------
    A list in json format containing all measurement methods recorded in the database:
    # method_id : int internal database identifier of this method
    # method_name : string name of the method.

    Example
    ---------
    http://localhost:9082/api/v1/all_tone_methods
    Returns a list of tone methods currently recorded in the database.
    """
    methods = All_tone_methods_query(api_config).run(id)
    return jsonify(methods)


@fapp.route("/api/v1/all_publications", methods=['GET'])
def get_all_publications():
    """
    Return all publications in database, in short form.

    Parameters
    ----------
    none

    Returns
    ----------
    A list in json format containing all publications recorded in the database:
    # id : int internal database identifier of this publication
    # citation_short : citation in short form of the original article

    Example
    ---------
    http://localhost:9082/api/v1/all_publications
    Returns a list of publications currently recorded in the database.
    """
    publications = All_publications_query(api_config).run(id)
    return jsonify(publications)


@fapp.route("/api/v1/all_facilities", methods=['GET'])
def get_all_facilities():
    """
    Returns all research facilities in database.

    Parameters
    ----------
    none

    Returns
    ----------
    A list in json format containing all facilities recorded in the database:
    # id : int internal database identifier of this facility
    # name : name of the facility

    Example
    ---------
    http://localhost:9082/api/v1/all_facilities
    Returns a list of facilities currently recorded in the database.
    """
    facilities = All_facilities_query(api_config).run(id)
    return jsonify(facilities)


@fapp.route("/api/v1/all_birds", methods=['GET'])
def get_all_birds():
    """
    Returns all audiograms of birds.

    Parameters
    ----------
    none

    Returns
    ----------
    A list in json format containing information on the audiograms of birds recorded in the database:
    # ott_id : int species identifier, references the Open Tree of Life database
    # unique_name : latin name of a species
    # audiogram_experiment_id : int id of an audiogram
    # medium : string "air" | "water"

    Example
    ---------
    http://localhost:9082/api/v1/all_birds
    Returns a list of audiograms of birds.
    """
    resp = Birds_query(api_config).run()
    return jsonify(resp)


@fapp.route("/api/v1/all_reptiles", methods=['GET'])
def get_all_reptiles():
    """
    Returns all audiograms of reptiles.

    Parameters
    ----------
    none

    Returns
    ----------
    A list in json format containing information on the audiograms of reptiles recorded in the database:
    # ott_id : int species identifier, references the Open Tree of Life database
    # unique_name : latin name of a species
    # audiogram_experiment_id : int id of an audiogram
    # medium : string "air" | "water"

    Example
    ---------
    http://localhost:9082/api/v1/all_reptiles
    Returns a list of audiograms of reptiles.
    """
    resp = Reptiles_query(api_config).run()
    return jsonify(resp)


@fapp.route("/api/v1/all_fishes", methods=['GET'])
def get_all_fishes():
    """
    Returns all audiograms of fishes.

    Parameters
    ----------
    none

    Returns
    ----------
    A list in json format containing information on the audiograms of fishes recorded in the database:
    # ott_id : int species identifier, references the Open Tree of Life database
    # unique_name : latin name of a species
    # audiogram_experiment_id : int id of an audiogram
    # medium : string "air" | "water"

    Example
    ---------
    http://localhost:9082/api/v1/all_fishes
    Returns a list of audiograms of fishes.
    """
    resp = Fishes_query(api_config).run()
    return jsonify(resp)


@fapp.route("/api/v1/all_mammals", methods=['GET'])
def get_all_mammals():
    """
    Returns all audiograms of mammals.

    Parameters
    ----------
    none

    Returns
    ----------
    A list in json format containing information on the audiograms of mammals recorded in the database:
    # ott_id : int species identifier, references the Open Tree of Life database
    # unique_name : latin name of a species
    # audiogram_experiment_id : int id of an audiogram
    # medium : string "air" | "water"

    Example
    ---------
    http://localhost:9082/api/v1/all_mammals
    Returns a list of audiograms of mammals.
    """
    resp = Mammals_query(api_config).run()
    return jsonify(resp)


@fapp.route("/api/v1/all_cetaceans", methods=['GET'])
def get_all_cetaceans():
    """
    Returns all audiograms of cetaceans.

    Parameters
    ----------
    none

    Returns
    ----------
    A list in json format containing information on the audiograms of cetaceans recorded in the database:
    # ott_id : int species identifier, references the Open Tree of Life database
    # unique_name : latin name of a species
    # audiogram_experiment_id : int id of an audiogram
    # medium : string "air" | "water"

    Example
    ---------
    http://localhost:9082/api/v1/all_cetaceans
    Returns a list of audiograms of cetaceans.
    """
    resp = Cetaceans_query(api_config).run()
    return jsonify(resp)


@fapp.route("/api/v1/all_seals", methods=['GET'])
def get_all_seals():
    """
    Returns all audiograms of seals.

    Parameters
    ----------
    none

    Returns
    ----------
    A list in json format containing information on the audiograms of seals recorded in the database:
    # ott_id : int species identifier, references the Open Tree of Life database
    # unique_name : latin name of a species
    # audiogram_experiment_id : int id of an audiogram
    # medium : string "air" | "water"

    Example
    ---------
    http://localhost:9082/api/v1/all_seals
    Returns a list of audiograms of seals.
    """
    resp = Seals_query(api_config).run()
    return jsonify(resp)


@fapp.route("/api/v1/publication", methods=['GET'])
def get_publication_by_experiment_id():
    """
    Returns the publication associated with an audiogram.

    Parameters
    ----------
    id : int identifier of an audiogram

    Returns
    ----------
    A string in json format representing teh publication where this audiogram comes from
    # DOI : string DOI of the publication
    # citation_long : string (Harvard) formatted citation of the publication

    Raises
    ----------
    Exception when no id was given

    Example
    ---------
    http://localhost:9082/api/v1/publication?id=5
    Returns citation and DOI for audiogram nr 5.

    """
    id = _check_id()
    publication = Publication_query(api_config).run(id)
    return jsonify(publication)


@fapp.route("/api/v1/taxonomy", methods=['GET'])
def get_taxonomy():
    """
    Returns full taxonomy in database.

    Parameters
    ----------
    none

    Returns
    ----------
    A list of tree nodes in json format. Each node has these attributes:
    # ott_id : int identifier of the taxon in the Open Tree of Life resource
    # parent : int ott_id of the parent node in the tree
    # rank : string taxonomic rank of the node (e.g. "subspecies", "species", "order", "family", "class")
    # unique_name : string latin name of the taxon
    # vernacular_name_english : string common English name of the taxon
    # vernacular_name_german : string common German name of the taxon
    # lft : int nested set left-side index of the node
    # rft : int nested set right-side index of the node

    Example
    ---------
    http://localhost:9082/api/v1/taxonomy
    Returns the complete taxonomy stored in the database
    """
    taxonomy = Taxonomy_query(api_config).run(id)
    return jsonify(taxonomy)


def _check_id():
    if 'id' not in request.args:
        raise Exception("No id was given.")
    return int(request.args['id'])


if __name__ == '__main__':
    try:
        # Read the configuration file
        api_config = configparser.ConfigParser()
        api_config.read(configPath)
        fapp.run(host='0.0.0.0')
    except Exception as e:
        fapp.logger.info(e)
