# -*- coding: utf-8 -*-

import os
from urllib.request import urlopen
from urllib.error import HTTPError
from datetime import datetime, timedelta

from settings import GFS_FOLDER
from utils import install_logger

logger = install_logger()


def forecast_url(forecast_delta):
    """ return list of (slug, url) """
    now = datetime.utcnow()
    d = now - timedelta(hours=forecast_delta)
    d_rounded = d.replace(hour=(d.hour // 6)*6)
    forecast_hour = ((d.hour % 6 + forecast_delta) // 3) * 3
    slug = now.strftime("%Y%m%d%H")
    slug_rounded = d_rounded.strftime("%Y%m%d%%2F%H")

    url = "https://nomads.ncep.noaa.gov/cgi-bin/filter_gfs_0p50.pl?file=gfs.t%sz.pgrb2full.0p50.f%03d&lev_entire_atmosphere_%%5C%%28considered_as_a_single_layer%%5C%%29=on&var_PWAT=on&leftlon=0&rightlon=360&toplat=90&bottomlat=-90&dir=%%2Fgfs.%s" % (d_rounded.strftime("%H"), forecast_hour, slug_rounded)

    return slug, url

"""
This is the code that serves to download the raw precipitation data.

Run it as such: python fetch.py

It tries to find the most recent GRIB file as available from the
Global Forecast System.

No dependencies outside the Python Standard Library
"""

def fetch_gfs():
    """
    Download the latest weather forecast from the Global Forecast System.
    There are some 300 different tables in the GFS data, so we ask it to
    filtered for Precipitable Water (PWAT), the information that interests us.

    The GFS data is produced every six hours. It contains information about
    the current weather situation and for 3, 6, 9, 12 etc. hours into
    the future. Because the GFS is not immediately available (in general
    several hours after the time indicated as ‘now’), we use the predictions
    of 6 hours and 9 hours into the future. This way we have a time point for
    every 3 hours.
    """

    urls = [forecast_url(0), forecast_url(6)]

    for slug, url in urls:
        target_folder = os.path.join(GFS_FOLDER, slug)
        output_file = os.path.join(target_folder, "GFS_half_degree.%s.pwat.grib" % slug)

        if os.path.exists(output_file):
            # There is no need to continue looking, as we have this file already,
            # and apparently it is the most recent forecast.
            logger.debug("file %s exists already" % output_file)
            break

        res = None
        try:
            logger.debug("retrieving file %s" % url)
            res = urlopen(url)
        except HTTPError as e:
            logger.debug("uri error {}: {}".format(url, e))
            continue

        if not os.path.exists(target_folder):
            os.makedirs(target_folder)
        with open(output_file, 'wb') as f:
            logger.debug("writing file %s" % output_file)
            f.write(res.read())

if __name__ == '__main__':
    fetch_gfs()
