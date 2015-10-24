# -*- coding: utf-8 -*-

from urllib.request import urlopen
from urllib.error import HTTPError
from datetime import datetime, timedelta
import os

from settings import GFS_FOLDER
from utils import logger

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
    six_hours  = timedelta(hours=6)
    nine_hours = timedelta(hours=9)
    d = datetime.utcnow()
    
    # Possible values for hour: [0, 6, 12, 18]
    # We do integer division by 6 to round to 6.
    d_rounded = d.replace(hour=(d.hour // 6)*6)
    
    while True:
        """
        Possible values for hour: [0, 6, 12, 18]
        
        If we don’t find the latest forecast we’ll try to go six hours each time until we get
        one that does exist (or one that we have already downloaded).
        """
        res, res6, res9 = None, None, None
        
        logger.debug("rounding %s hours UTC at %s to %s hours UTC at %s" % 
                     (d.strftime("%H"), d.strftime("%d"), d_rounded.strftime("%H"), d_rounded.strftime("%d")))

        d6 = d_rounded + six_hours
        d9 = d_rounded + nine_hours
        
        slug  = d_rounded.strftime("%Y%m%d%H") # '2014040812'
        slug6 = d6.strftime("%Y%m%d%H")        # '2014040818'
        slug9 = d9.strftime("%Y%m%d%H")        # '2014040821'
        
        target_folder6 = os.path.join(GFS_FOLDER, slug6)
        target_folder9 = os.path.join(GFS_FOLDER, slug9)
        
        output_file6 = os.path.join(target_folder6, "GFS_half_degree.%s.pwat.grib" % slug6)
        output_file9 = os.path.join(target_folder9, "GFS_half_degree.%s.pwat.grib" % slug9)
        
        if os.path.exists(output_file9):
            # There is no need to continue looking, as we have this file already,
            # and apparently it is the most recent forecast.
            logger.debug("file %s exists already" % output_file9)
            break
        
        # We get forecasts for 6 and 9 hours later:
        uri6 = "http://nomads.ncep.noaa.gov/cgi-bin/filter_gfs_0p50.pl?file=gfs.t" + d_rounded.strftime("%H") + "z.pgrb2full.0p50.f000&lev_entire_atmosphere_%5C%28considered_as_a_single_layer%5C%29=on&var_PWAT=on&leftlon=0&rightlon=360&toplat=90&bottomlat=-90&dir=%2Fgfs." + slug
        uri9 = "http://nomads.ncep.noaa.gov/cgi-bin/filter_gfs_0p50.pl?file=gfs.t" + d_rounded.strftime("%H") + "z.pgrb2full.0p50.f000&lev_entire_atmosphere_%5C%28considered_as_a_single_layer%5C%29=on&var_PWAT=on&leftlon=0&rightlon=360&toplat=90&bottomlat=-90&dir=%2Fgfs." + slug

        try:
            logger.debug("retrieving file %s" % uri9)
            res9 = urlopen(uri9)
        except HTTPError as e:
            logger.debug("uri error {}: {}".format(uri9, e))

        try:
            logger.debug("retrieving file %s" % uri6)
            res6 = urlopen(uri6)
        except HTTPError as e:
            logger.debug("uri error {}: {}".format(uri6, e))

        if res9 and res6:
            break

        d_rounded = d_rounded - six_hours
    
    if res9 and res6:
        for target_folder in [target_folder9, target_folder6]:
            if not os.path.exists(target_folder):
                os.makedirs(target_folder)
        with open(output_file6, 'wb') as f:
            logger.debug("writing file %s" % output_file6)
            f.write(res6.read())
        with open(output_file9, 'wb') as f:
            logger.debug("writing file %s" % output_file9)
            f.write(res9.read())

if __name__ == '__main__':
    fetch_gfs()
