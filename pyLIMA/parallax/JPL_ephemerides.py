import numpy as np
from astroquery.jplhorizons import Horizons

TIMEOUT_JPL = 120  # seconds. The time you allow telnetlib to discuss with JPL,
# see space_parallax.
JPL_TYPICAL_REQUEST_TIME_PER_LINE = 0.002  # seconds.

JPL_HORIZONS_ID = {
    'Geocentric': '500',
    'Kepler': '-227',
    'Spitzer': '-79',
    'HST': '-48',
    'Gaia': '-139479',
    'New Horizons': '-98',
    'L2': '32',
    'TESS': '-95'

}


def horizons_obscodes(observatory):
    """
    Transform observatory names to JPL int codes

    Parameters
    ----------
    observatory : str, observatory name

    Returns
    -------
    OBSERVATORY_ID : str, the JPL code in str format
    """

    # Check if we were passed the JPL site code directly
    if (observatory in list(JPL_HORIZONS_ID.values())):

        OBSERVATORY_ID = observatory

    else:
        # Lookup observatory name in map, use ELP's code as a default if not found
        OBSERVATORY_ID = JPL_HORIZONS_ID.get(observatory, 'V37')

    return OBSERVATORY_ID


def horizons_API(body, time_to_treat, observatory='Geocentric'):
    """
    Find the satellite ephemerides at JPL

    Parameters
    ----------
    body : str, the satellite name
    time_to_treat : array, array of time to treat
    observatory :  the reference frame

    Returns
    -------
    flag : str, success flag
    positions : array, [time,ra,dec,distance]
    """
    OBSERVATORY_ID = horizons_obscodes(observatory)
    body = horizons_obscodes(body)

    tstart = 'JD' + str(time_to_treat.min() - 1)

    tstop = 'JD' + str(time_to_treat.max() + 1)

    obj = Horizons(id=body, location=OBSERVATORY_ID,
                   epochs={'start': tstart, 'stop': tstop,
                           'step': '1440m'})  # daily cadence for interpolation
    ephemerides = obj.ephemerides()

    dates = ephemerides['datetime_jd'].data.data
    ra = ephemerides['RA'].data.data
    dec = ephemerides['DEC'].data.data
    distances = ephemerides['delta'].data.data

    if distances.min() < 0.002:  # Low orbits

        # adding exact telescopes dates
        DATES = [dates.tolist()]
        RA = [ra.tolist()]
        DEC = [dec.tolist()]
        DISTANCES = [distances.tolist()]

        start = 0

        while start < len(time_to_treat):  # Split the time request in chunk of 50.

            end = start + 50
            obj = Horizons(id=body, location=OBSERVATORY_ID,
                           epochs=time_to_treat[start:end])
            ephemerides = obj.ephemerides()

            dates = ephemerides['datetime_jd'].data.data
            ra = ephemerides['RA'].data.data
            dec = ephemerides['DEC'].data.data
            distances = ephemerides['delta'].data.data

            DATES.append(dates)
            RA.append(ra)
            DEC.append(dec)
            DISTANCES.append(distances)

            start = end

        dates = np.concatenate(DATES)
        ra = np.concatenate(RA)
        dec = np.concatenate(DEC)
        distances = np.concatenate(DISTANCES)

    flag = 'Succes connection to JPL'
    print('Successfully ephemeris from JPL!')

    positions = np.c_[dates, ra, dec, distances]

    return flag, positions