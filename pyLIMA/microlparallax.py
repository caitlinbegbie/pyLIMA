# -*- coding: utf-8 -*-
"""
Created on Wed Oct 28 11:49:44 2015

@author: ebachelet
"""
from __future__ import division
import telnetlib

import numpy as np
from astropy import constants as astronomical_constants
from scipy import interpolate
from astropy.time import Time
from pyslalib import slalib


def horizons_obscodes(observatory):
    """Map LCOGT sitecodes to those needed for JPL HORIZONS.
    McDonald Observatory (ELP/V37) is used as a default if the look-up fails"""

    JPL_HORIZONS_ID = {
                       'Geocentric': '500',
                       'Kepler':'-227'
                       }

    # Check if we were passed the JPL site code directly
    if (observatory in JPL_HORIZONS_ID.values()):
        OBSERVATORY_ID = observatory
    else:
        # Lookup observatory name in map, use ELP's code as a default if not found
        OBSERVATORY_ID = JPL_HORIZONS_ID.get(observatory, 'V37')

    return OBSERVATORY_ID


def optcallback(socket, command, option):
    cnum = ord(command)
    onum = ord(option)
    if cnum == telnetlib.WILL:  # and onum == ECHO:
        socket.write(telnetlib.IAC + telnetlib.DONT + onum)
    if cnum == telnetlib.DO and onum == telnetlib.TTYPE:
        socket.write(telnetlib.IAC + telnetlib.WONT + telnetlib.TTYPE)


class MLParallaxes(object):
    """
    ######## Parallax module ########


    This module compute the parallax shifts due to different parallax effects.

    Attributes :

         event : the event object on which you perform the fit on. More details on the event module.
         parallax_model : the parallax model Has to be "Annual', "Terrestrial" or "Full"

     parallax_model : The parallax effect you want to fit. Have to be a list containing the parallax model name
     and the reference time to_par (in JD unit). Example : ['Annual',2457000.0]

     AU : the astronomical unit,  as defined by astropy (in meter)

     speed_of_light : the speed light c,  as defined by astropy (in meter/second)

     Earth_radius : the Earth equatorial radius,  as defined by astropy (in meter)

     target_angles_in_the_sky : a list containing [RA,DEC] of the target in radians unit.


    """



    def __init__(self, event, parallax_model):
        """Initialization of the attributes described above.
        :param event: the event object on which you perform the fit on. More details on the event module.
        :param parallax_model: The parallax effect you want to fit. Have to be a list containing the parallax model name
        and the to_par value. Example : ['Annual',2457000.0]
        """

        self.event = event
        self.parallax_model = parallax_model[0]
        self.to_par = parallax_model[1]
        self.AU = astronomical_constants.au.value
        self.speed_of_light = astronomical_constants.c.value
        self.Earth_radius = astronomical_constants.R_earth.value

        self.target_angles_in_the_sky = [self.event.ra * np.pi / 180, self.event.dec * np.pi / 180]
        self.North_East_vectors_target()

    def North_East_vectors_target(self):
        """This function define the North and East vectors projected on the sky plane perpendicular to the line
        of sight (i.e the line define by RA,DEC of the event).
        """
        target_angles_in_the_sky = self.target_angles_in_the_sky
        Target = np.array([np.cos(target_angles_in_the_sky[1]) * np.cos(target_angles_in_the_sky[0]),
                           np.cos(target_angles_in_the_sky[1]) * np.sin(target_angles_in_the_sky[0]),
                           np.sin(target_angles_in_the_sky[1])])

        self.East = np.array([-np.sin(target_angles_in_the_sky[0]), np.cos(target_angles_in_the_sky[0]), 0.0])
        self.North = np.cross(Target, self.East)

    def HJD_to_JD(self, time_to_transform):
        """Transform the input time from HJD to JD.
            :param time_to_transform : the numpy array containing the time you want to correct.
            """
        AU = self.AU
        light_speed = self.speed_of_light

        time_correction = []
        # DTT=[]


        for time in time_to_transform:

            count = 0
            jd = np.copy(time)

            while count < 3:

                Earth_position = slalib.sla_epv(jd)
                Sun_position = -Earth_position[0]

                Sun_angles = slalib.sla_dcc2s(Sun_position)
                target_angles_in_the_sky = self.target_angles_in_the_sky

                Time_correction = np.sqrt(Sun_position[0] ** 2 + Sun_position[1] ** 2 + Sun_position[
                    2] ** 2) * AU / light_speed * (
                               np.sin(Sun_angles[1]) * np.sin(target_angles_in_the_sky[1]) + np.cos(
                                   Sun_angles[1]) * np.cos(target_angles_in_the_sky[1]) * np.cos(
                                   target_angles_in_the_sky[0] - Sun_angles[0])) / (3600 * 24.0)
                count = count + 1

        # DTT.append(slalib.sla_dtt(jd)/(3600*24))
        time_correction.append(Time_correction)

        JD = time_to_transform + np.array(time_correction)

        return JD

    def parallax_combination(self, telescope):
        """ Compute, and set, the deltas_positions attributes of the telescope object
       inside the list of telescopes. deltas_positions is the offset between the position of the observatory at the time t, and the
       center of the Earth at the date to_par. More details on each parallax functions.
       
       :param object telescope:  a telescope object on which you want to set the deltas_positions due to parallax.
       
       """


        location = telescope.location

        time = telescope.lightcurve_flux[:,0]
        delta_North = np.array([])
        delta_East = np.array([])

        if location == 'Earth':

            if (self.parallax_model == 'Annual'):

               telescope_positions = self.annual_parallax(time)

               delta_North = np.append(delta_North, telescope_positions[0])
               delta_East = np.append(delta_East, telescope_positions[1])

            if (self.parallax_model == 'Terrestrial'):

               altitude = telescope.altitude
               longitude = telescope.longitude
               latitude = telescope.latitude

               telescope_positions = self.terrestrial_parallax(time, altitude, longitude, latitude)

               delta_North = np.append(delta_North, telescope_positions[0])
               delta_East = np.append(delta_East, telescope_positions[1])

            if (self.parallax_model == 'Full'):

               telescope_positions = self.annual_parallax(time)

               delta_North = np.append(delta_North, telescope_positions[0])
               delta_East = np.append(delta_East, telescope_positions[1])

               altitude = telescope.altitude
               longitude = telescope.longitude
               latitude = telescope.latitude

               telescope_positions = self.terrestrial_parallax(time, altitude, longitude, latitude)

               delta_North = np.append(delta_North, telescope_positions[0])
               delta_East = np.append(delta_East, telescope_positions[1])


        else:

            telescope_positions = self.annual_parallax(time)
            delta_North = np.append(delta_North, telescope_positions[0])
            delta_East = np.append(delta_East, telescope_positions[1])
            name = telescope.name


            telescope_positions = self.space_parallax(time, name)



        delta_North = delta_North + telescope_positions[0]
        delta_East = delta_East + telescope_positions[1]


        deltas_position = np.array([delta_North, delta_East])

        # set the attributes deltas_positions for the telescope object
        telescope.deltas_positions = deltas_position

    def annual_parallax(self, time_to_treat):
        """ Compute the position shift due to the Earth movement. Please have a look on :
        "Resolution of the MACHO-LMC-5 Puzzle: The Jerk-Parallax Microlens Degeneracy"
         Gould, Andrew 2004. http://adsabs.harvard.edu/abs/2004ApJ...606..319G
         
         :param  time_to_treat: a numpy array containing the time where you want to compute this effect.
         :return: the shift induce by the Earth motion around the Sun
         :rtype: array_like

         WARNING :  this is a geocentric point of view.
                slalib use MJD time definition, which is MJD = JD-2400000.5
        """

        to_par_mjd = self.to_par - 2400000.5
        Earth_position_time_reference = slalib.sla_epv(to_par_mjd)
        Sun_position_time_reference  = -Earth_position_time_reference[0]
        Sun_speed_time_reference  = -Earth_position_time_reference[1]
        delta_Sun = []

        for time in  time_to_treat:

            time_mjd = time - 2400000.5

            Earth_position = slalib.sla_epv(time_mjd)
            Sun_position = -Earth_position[0]
            delta_sun = Sun_position - (time_mjd - to_par_mjd) * Sun_speed_time_reference - Sun_position_time_reference


            delta_Sun.append(delta_sun.tolist())

        delta_Sun = np.array(delta_Sun)

        delta_Sun_projected = np.array([np.dot(delta_Sun, self.North), np.dot(delta_Sun, self.East)])

        return delta_Sun_projected

    def terrestrial_parallax(self, time_to_treat, altitude, longitude, latitude):
        """ Compute the position shift due to the distance of the obervatories from the Earth center.
        Please have a look on :
        "Parallax effects in binary microlensing events"
        Hardy, S.J and Walker, M.A. 1995. http://adsabs.harvard.edu/abs/1995MNRAS.276L..79H

        :param  time_to_treat: a numpy array containing the time where you want to compute this effect.
        :param altitude: the altitude of the telescope in meter
        :param longitude: the longitude of the telescope in degree
        :param latitude: the latitude of the telescope in degree
        :return: the shift induce by the distance of the telescope to the Earth center.
        :rtype: array_like

        WARNING : slalib use MJD time definition, which is MJD = JD-2400000.5
        """

        radius = (self.Earth_radius + altitude)/self.AU
        Longitude = longitude * np.pi / 180.0
        Latitude = latitude * np.pi / 180.0

        delta_telescope = []
        for time in  time_to_treat:

            time_mjd = time - 2400000.5
            sideral_time = slalib.sla_gmst(time_mjg)
            telescope_longitude = - Longitude - self.target_angles_in_the_sky[0]*np.pi/180 + sideral_time/24.0*np.pi

        delta_telescope.append(radius*slalib.sla_dcs2c(telescope_longitude,Latitude))


        delta_telescope = np.array(delta_telescope)
        delta_telescope_projected = np.array([np.dot(delta_telescope, self.North), np.dot(delta_telescope, self.East)])
        return delta_telescope_projected

    def space_parallax(self,  time_to_treat, satellite_name):
        """ Compute the position shift due to the distance of the obervatories from the Earth center.
        Please have a look on :
        "Parallax effects in binary microlensing events"
        Hardy, S.J and Walker, M.A. 1995. http://adsabs.harvard.edu/abs/1995MNRAS.276L..79H
        
        :param  time_to_treat: a numpy array containing the time where you want to compute this effect.
        :param satellite_name: the name of the observatory. Have to be recognize by JPL HORIZON.
        :return: the shift induce by the distance of the telescope to the Earth center.
        :rtype: array_like
        WARNING : slalib use MJD time definition, which is MJD = JD-2400000.5
        """

        tstart = min(time_to_treat) - 1
        tend = max(time_to_treat) + 1

        satellite_positions = self.produce_horizons_ephem(satellite_name, tstart, tend, observatory='Geocentric',step_size='60m', verbose=False)[1]

        satellite_positions = np.array(satellite_positions)
        dates = satellite_positions[:, 0].astype(float)
        ra = satellite_positions[:, 1].astype(float)
        dec = satellite_positions[:, 2].astype(float)
        distances = satellite_positions[:, 3].astype(float)

        interpolated_ra = interpolate.interp1d(dates, ra)
        interpolated_dec = interpolate.interp1d(dates, dec)
        interpolated_distance = interpolate.interp1d(dates, distances)

        ra_interpolated = interpolated_ra(time_to_treat)
        dec_interpolated = interpolated_dec(time_to_treat)
        distance_interpolated = interpolated_distance(time_to_treat)


        delta_satellite = []
        for index_time in xrange(len(time_to_treat)):



              delta_satellite.append(distance_interpolated[index_time]*slalib.sla_dcs2c(ra_interpolated[index_time]*np.pi/180,dec_interpolated[index_time]*np.pi/180))

        delta_satellite=np.array(delta_satellite)
        delta_satellite_projected = np.array([np.dot(delta_satellite, self.North), np.dot(delta_satellite, self.East)])


        return delta_satellite_projected



    def produce_horizons_ephem(self, body, start_time, end_time, observatory='ELP', step_size='60m',
                               verbose=False):
        """
        Write by Tim Lister.
        example interactive session:
        telnet://horizons.jpl.nasa.gov:6775
        606 # = Titan
        e  # for ephemeris
        o  # for observables
        -7 # for ALMA
        y  # confirm
        2011-Apr-23 00:00  #  UT
        2011-Apr-23 01:00  #  UT
        10m #  interval
        y  # default output
        1,3,4,9,19,20,23 # RA/DEC and rates (Rarcsec/hour), Az & El, Vis. mag, Helio. range (r),
        Earth range (delta), Elong.
        space  # to get to next prompt
        q   # quit
        """
        body = str(-227)
        # Lookup observatory name
        OBSERVATORY_ID = horizons_obscodes(observatory)
        if (verbose):
            print "Observatory ID= ", OBSERVATORY_ID
    #import pdb; pdb.set_trace()

        tstart ='JD' + str(start_time)


        if (verbose):
            print "tstart = ", tstart
        # tstop = end_time.strftime('%Y-%m-%d %H:%M')
        #tstop = Time(end_time,format='jd')

        tstop = 'JD' + str(end_time)
    #tstop = tstop[:12]+' '+tstop[13:-7]
        timeout = 5  # seconds
        t = telnetlib.Telnet('horizons.jpl.nasa.gov', 6775)
        t.set_option_negotiation_callback(optcallback)
        data = t.read_until('Horizons> ')
        if (verbose):
            print "data = ", data
            #        print "hex string = %s\n\n" % binascii.hexlify(data)
        while (data.find('Horizons>') < 0):
            t.write('\n')
            data = t.read_until('Horizons> ')
            if (verbose):
                print "data = ", data
        t.write(body + '\n')
        data = t.read_until('Select ... [E]phemeris, [F]tp, [M]ail, [R]edisplay, ?, <cr>: ',
                            timeout)
        if len(data) == 0:
            print 'No connection to JPL, sorry :('
            flag = 'No connection to JPL'
            return flag

        if (verbose):
            print "data = ", data
        if (data.find('phemeris') < 0):
            if (data.find('EXACT') >= 0):
                t.write('\n')
                data = t.read_until('Select ... [E]phemeris, [F]tp, [M]ail, [R]edisplay, ?, <cr>: ',
                                    timeout)
                if (verbose):
                    print data
                useID = ''
            else:
                # then we have a conflict in the name.
                # e.g. Titan vs. Titania, or Mars vs. Mars Barycenter
                # Try to resolve by forcing an exact match.
                lines = data.split('\n')
                if (verbose):
                    print "Multiple entries found, using exact match"
                    print "nlines = %d" % (len(lines))
                firstline = -1
                lastvalidline = -1
                l = 0
                useID = -1
                for line in lines:
                    if (verbose):
                        print line
                    if (line.find('-----') >= 0):
                        if (firstline == -1):
                            firstline = l + 1
                    else:
                        tokens = line.split()
                        if (firstline >= 0 and lastvalidline == -1):
                            if (len(tokens) < 2):
                                lastvalidline = l - 1
                            elif (tokens[1] == body and len(tokens) < 3):
                                # The <3 is necessary to filter out entries for a planet's
                                # barycenter
                                useID = int(tokens[0])
                                useBody = tokens[1]
                                if (verbose):
                                    print "Use instead the id = %s = %d" % (tokens[0], useID)
                    l = l + 1
                if (useID == -1):
                    # Try again with only the first letter capitalized, Probably not necessary
                    body = str.upper(body[0]) + str.lower(body[1:])
                    #          print "Try the exact match search again with body = ", body
                    firstline = -1
                    lastvalidline = -1
                    l = 0
                    for line in lines:
                        if (verbose):
                            print line
                        if (line.find('-----') >= 0):
                            if (firstline == -1):
                                firstline = l + 1
                        elif (firstline > 0):
                            if (verbose):
                                print "Splitting this line = %s" % (line)
                            tokens = line.split()
                            if (verbose):
                                print "length=%d,  %d tokens found" % (len(line), len(tokens))
                            if (firstline >= 0 and lastvalidline == -1):
                                if (len(tokens) < 2):
                                    # this is the final (i.e. blank) line in the list
                                    lastvalidline = l - 1
                                elif (tokens[1] == body):
                                    #                  print "%s %s is equal to %s." % (tokens[
                                    # 0],tokens[1],body)
                                    useID = int(tokens[0])
                                    useBody = tokens[1]
                                    if (len(tokens) < 3):
                                        if (verbose):
                                            print "Use instead the id = %s = %d" % (
                                            tokens[0], useID)
                                    elif (len(tokens[2].split()) < 1):
                                        if (verbose):
                                            print "Use instead the id = ", tokens[0]
                                else:
                                    if (verbose):
                                        print "%s %s is not equal to %s." % (
                                        tokens[0], tokens[1], body)
                        l = l + 1
                if (verbose):
                    print "line with first possible source = ", firstline
                    print "line with last possible source = ", lastvalidline
                    print "first possible source = ", (lines[firstline].split())[1]
                    print "last possible source = ", (lines[lastvalidline].split())[1]
                    print "Writing ", useID
                t.write(str(useID) + '\n')
                data = t.read_until('Select ... [E]phemeris, [F]tp, [M]ail, [R]edisplay, ?, <cr>: ')
                if (verbose):
                    print data
        else:
            useID = ''
        t.write('e\n')
        data = t.read_until('Observe, Elements, Vectors  [o,e,v,?] : ')
        if (verbose):
            print data
        t.write('o\n')
        data = t.read_until('Coordinate center [ <id>,coord,geo  ] : ')
        if (verbose):
            print data
        t.write('%s\n' % OBSERVATORY_ID)
        data = t.read_until('[ y/n ] --> ')
        pointer = data.find('----------------')
        ending = data[pointer:]
        lines = ending.split('\n')
        try:
            if (verbose):
                print "Parsing line = %s" % (lines)
            tokens = lines[1].split()
        except:
            print "Telescope code unrecognized by JPL."
            return ([], [], [])

        if (verbose):
            print data
        obsname = ''
        for i in range(4, len(tokens)):
            obsname += tokens[i]
            if (i < len(tokens) + 1):
                obsname += ' '
        print "Confirmed Observatory name = ", obsname
        if (useID != ''):
            print "Confirmed Target ID = %d = %s" % (useID, useBody)
        t.write('y\n')
        data = t.read_until('] : ', 1)
        if (verbose):
            print data

        t.write(tstart + '\n')
        data = t.read_until('] : ', 1)
        if (verbose):
            print data
        t.write(tstop + '\n')
        data = t.read_until(' ? ] : ', timeout)
        if (verbose):
            print data
        t.write(step_size + '\n')
        data = t.read_until(', ?] : ', timeout)
        if (verbose):
            print data
        if (1 == 1):
            # t.write('n\n1,3,4,9,19,20,23,\nJ2000\n\n\nMIN\nDEG\nYES\n\n\nYES\n\n\n\n\n\n\n\n')
            t.write('n\n1,20,\nJ2000\n\n\JD\nMIN\nDEG\nYES\n\n\nYES\n\n\n\n\n\n\n\n')
        else:
            t.write('y\n')  # accept default output?
            data = t.read_until(', ?] : ')  # ,timeout)
            if (verbose):
                print data
            t.write('1,3\n')

        t.read_until('$$SOE', timeout)
        data = t.read_until('$$EOE', timeout)
        if (verbose):
            print data

        t.close()
        lines = data.split('\n')
        horemp = []
        for hor_line in lines:
            if (verbose):
                print "hor_line = ", hor_line
                print len(hor_line.split())
            data_line = True
            # print hor_line


            if (len(hor_line.split()) == 4):

                (time, raDegrees, decDegrees, light_dist) = hor_line.split()

            elif (len(hor_line.split()) == 0 or len(hor_line.split()) == 1):
                data_line = False
            else:
                data_line = False
                print "Wrong number of fields (", len(hor_line.split()), ")"
                print "hor_line=", hor_line
            if (data_line == True):

                horemp_line = [time, raDegrees, decDegrees, light_dist]
                if (verbose):
                    print horemp_line
                horemp.append(horemp_line)

                # Construct ephem_info
        ephem_info = {'obj_id': body,
                      'emp_sitecode': OBSERVATORY_ID,
                      'emp_timesys': '(UT)',
                      'emp_rateunits': '"/min'
                      }
        flag = 'Succes connection to JPL'
        return flag, horemp



    def parallax_outputs(self, PiE):
        '''Depreciated '''
        piE = np.array(PiE)
        delta_tau = np.dot(piE, self.delta_position)
        delta_u = np.cross(piE, self.delta_position.T)

        return delta_tau, delta_u
