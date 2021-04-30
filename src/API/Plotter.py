"""
Wrapper around plotnine and pandas, for plotting ggplot-style graphics.

Created on 27.11.2019
@author: Alvaro Ortiz, Museum fuer Naturkunde Berlin
"""
import pandas as pd
from plotnine import *  # noqa: F403
import json
import os
import hashlib
import logging


class Plotter():
    def __init__(self):
        # default labels
        self.title = ""

    def plot(self, data_points, url):
        """
        Plot an audiogram and save it.

        @param data_points: data to be plotted
        @param url: will be used for cache key. Only GET requests!
        @return: path to image file
        """

        # OS path
        cache_key = self.cache_key(url)
        filename = "audiogram_" + cache_key + ".png"
        path = os.path.join("./static", filename)

        # if file doesn't already exist, plot at save it
        # if not os.path.exists(path):
        if True:  # switch off caching
            data_points_json = json.loads(str(data_points))
            data_points_df = pd.DataFrame.from_dict(data_points_json)
            x_label = "Frequency (kHz)"
            unit = data_points_json[0]['spl_reference_display_label']
            if (unit):
                y_label = "Threshold (dB %s)" % (unit.replace("Î¼", "\u03BC"))
            else:
                y_label = "Threshold (dB unspecified unit)"
            fig = (
                ggplot(data_points_df)  # noqa: F405
                + aes(  # noqa: F405 W503
                    x='testtone_frequency_in_khz',
                    y='sound_pressure_level_in_decibel')
                + geom_line(color='black')  # noqa: F405 W503
                + geom_point(color='black', fill='black')  # noqa: F405 W503
                + labs(title=self.title, x=x_label, y=y_label)  # noqa: F405 E501 W503
                + scale_x_log10(limits=(0.05, 200))  # noqa: F405 W503
                + scale_y_continuous(limits=(-50, 160))  # noqa: F405 W503
                + theme_bw()  # noqa: F405 W503
            )

            fig.save(
                filename=path,
                height=5, width=5, units="in", dpi=300
            )

        # URL of image src
        return "/".join(["/static", filename])

    def test_panda(self, data_points_array):
        return self._convert_points_array_to_panda(data_points_array)

    def plotlayers(self, data_points_array, url):
        """
        Plot an audiogram and save it.

        @param data_points: array of data to be plotted
        @param url: will be used for cache key. Only GET requests!
        @return: path to image file
        """
        # OS path
        cache_key = self.cache_key(url)
        filename = "audiogram_" + cache_key + ".png"
        path = os.path.join("./static", filename)

        # if file doesn't already exist, plot and save it
        if not os.path.exists(path):
            data_points_df = self._convert_points_array_to_panda(
                data_points_array)
            x_label = "Frequency (kHz)"
            unit = data_points_df['spl_reference_display_label'][0]
            if (unit):
                y_label = "Threshold (dB %s)" % (unit.replace("Î¼", "\u03BC"))
            else:
                y_label = "Threshold (dB unspecified unit)"

            fig = (
                # The palette with black:
                ggplot(data_points_df)  # noqa: F405
                + aes(  # noqa: F405 W503
                    x='testtone_frequency_in_khz',
                    y='sound_pressure_level_in_decibel',
                    color='label')
                + geom_line()  # noqa: F405 W503
                + geom_point()  # noqa: F405 W503
                + scale_colour_manual(values=(
                    "#000000", "#E69F00", "#56B4E9", "#009E73", "#F0E442", "#0072B2", "#D55E00", "#CC79A7",
                    "#000000", "#E69F00", "#56B4E9", "#009E73", "#F0E442", "#0072B2", "#D55E00", "#CC79A7",
                    "#000000", "#E69F00", "#56B4E9", "#009E73", "#F0E442", "#0072B2", "#D55E00", "#CC79A7",
                    "#000000", "#E69F00", "#56B4E9", "#009E73", "#F0E442", "#0072B2", "#D55E00", "#CC79A7",
                    "#000000", "#E69F00", "#56B4E9", "#009E73", "#F0E442", "#0072B2", "#D55E00", "#CC79A7",
                    "#000000", "#E69F00", "#56B4E9", "#009E73", "#F0E442", "#0072B2", "#D55E00", "#CC79A7",
                    "#000000", "#E69F00", "#56B4E9", "#009E73", "#F0E442", "#0072B2", "#D55E00", "#CC79A7",
                    "#000000", "#E69F00", "#56B4E9", "#009E73", "#F0E442", "#0072B2", "#D55E00", "#CC79A7",
                    "#000000", "#E69F00", "#56B4E9", "#009E73", "#F0E442", "#0072B2", "#D55E00", "#CC79A7",
                    "#000000", "#E69F00", "#56B4E9", "#009E73", "#F0E442", "#0072B2", "#D55E00", "#CC79A7"
                ))
                + theme_bw()  # noqa: F405 W503
                + labs(title=self.title, x=x_label, y=y_label)  # noqa: F405 E501 W503
                + scale_x_log10(limits=(0.1, 200))  # noqa: F405 W503
                + scale_y_continuous(limits=(-50, 160))  # noqa: F405 W503
            )

            fig.save(
                filename=path,
                height=5, width=5, units="in", dpi=300
            )

        # URL of image src
        return "/".join(["/static", filename])

    def _convert_points_array_to_panda(self, data_points_array):
        data_points_json = json.loads(str(data_points_array))
        i = 65
        df = []
        for point in data_points_json:
            for entry in point:
                entry['label'] = chr(i)
                df.append(entry)
            i += 1
        panda = pd.DataFrame.from_dict(df)
        return panda

    def cache_key(self, url):
        e_url = url.encode('utf-8')
        hash_url = hashlib.blake2b(e_url, digest_size=4)
        return str(hash_url.hexdigest())
