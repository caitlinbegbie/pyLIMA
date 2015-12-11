# -*- coding: utf-8 -*-
"""
Created on Wed Oct 28 11:49:44 2015

@author: ebachelet
"""
from __future__ import division
import numpy as np
from pyslalib import slalib
from astropy import constants as const
from scipy import interpolate



class MLParallaxes(object):

    def __init__(self, event, model):
        ''' Initialization of the attributes described above.
        '''
        self.AU = const.au.value
        self.speed_of_light = const.c.value
        self.Earth_radius = const.R_earth.value
        self.event = event
        self.model= model[0]
        self.topar = model[1]
        self.delta_tau = []
        self.delta_u = []
        self.target_angles=[self.event.ra*np.pi/180,self.event.dec*np.pi/180]


    def N_E_vectors_target(self):

        target_angles=self.target_angles
        Target=np.array([np.cos(target_angles[1])*np.cos(target_angles[0]),np.cos(target_angles[1])*np.sin(target_angles[0]),np.sin(target_angles[1])])

        self.East=np.array([-np.sin(target_angles[0]),np.cos(target_angles[0]),0.0])
        self.North=np.cross(Target,self.East)

    def HJD_to_JD(self, t):

        AU=self.AU
        light_speed=self.speed_of_light

        time_correction=[]
        #DTT=[]
        t=t

        for i in t :

            count=0
            jd=np.copy(i)

            while count<3:

                Earth_position=slalib.sla_epv(jd)
                Sun_position=-Earth_position[0]

                Sun_angles=slalib.sla_dcc2s(Sun_position)
                target_angles=self.target_angles

                t_correction=np.sqrt(Sun_position[0]**2+Sun_position[1]**2+Sun_position[2]**2)*AU/light_speed*(np.sin(Sun_angles[1])*np.sin(target_angles[1])+np.cos(Sun_angles[1])*np.cos(target_angles[1])*np.cos(target_angles[0]-Sun_angles[0]))/(3600*24.0)
                count=count+1

        #DTT.append(slalib.sla_dtt(jd)/(3600*24))
        time_correction.append(t_correction)   

        JD=t+np.array(time_correction)

        return JD

    def parallax_combination(self):

        self.N_E_vectors_target()
        delta_position_North = np.array([])
        delta_position_East = np.array([])

        for i in self.event.telescopes:

            kind = i.kind
            t = self.HJD_to_JD(i.lightcurve_flux[:,0])
            delta_North = np.array([])
            delta_East = np.array([])

            if kind == 'Earth':

                if (self.model == 'Annual'):

                    positions=self.annual_parallax(t)
                    delta_North = np.append(delta_North, positions[0])
                    delta_East = np.append(delta_East, positions[1])

                if (self.model == 'Terrestrial'):

                    altitude=i.altitude
                    longitude=i.longitude
                    latitude=i.latitude

                    positions=self.terrestrial_parallax(t, altitude, longitude, latitude)
                    delta_North = np.append(delta_North, positions[0])
                    delta_East = np.append(delta_East, positions[1])

                if (self.model == 'Full'):

                    positions=self.annual_parallax(t)
                    delta_North = np.append(delta_North, positions[0])
                    delta_East = np.append(delta_East, positions[1])


                    altitude=i.altitude
                    longitude=i.longitude
                    latitude=i.latitude

                    positions=self.terrestrial_parallax(t, altitude, longitude, latitude)
                    delta_North =delta_North+positions[0]
                    delta_East =delta_East+positions[1]


            else:

                name=i.name

                positions=self.space_parallax(t, name)
                delta_North = np.append(delta_North, positions[0])
                delta_East = np.append(delta_East, positions[1])


            delta_position_North = np.append(delta_position_North, delta_North)
            delta_position_East = np.append(delta_position_East, delta_East)

        self.delta_position = -np.array([delta_position_North,delta_position_East])


    def annual_parallax(self, t):

        topar=self.HJD_to_JD(np.array([self.topar]))-2400000.5

        Earth_position_ref=slalib.sla_epv(topar)
        Sun_position_ref=-Earth_position_ref[0]
        Sun_speed_ref=-Earth_position_ref[1]
        delta_Sun=[]

        for i in t:

            tt=i-2400000.5
            
            Earth_position=slalib.sla_epv(tt)
            Sun_position=-Earth_position[0]
            delta_sun= Sun_position-(tt-topar)*Sun_speed_ref-Sun_position_ref
            delta_Sun.append(delta_sun.tolist())

        delta_Sun=np.array(delta_Sun)
        delta_Sun_proj=np.array([np.dot(delta_Sun, self.North),np.dot(delta_Sun, self.East)])

        return delta_Sun_proj

    def terrestrial_parallax(self, t, altitude, longitude, latitude):

        radius = self.Earth_radius+altitude
        Longitude = longitude*np.pi/180.0
        Latitude = latitude*np.pi/180.0

        delta_North = []
        delta_East = []
        for i in t:

            tt = i-2400000.5
            sideral_time = slalib.sla_gmst(tt)
            telescope_longitude =- Longitude-self.target_angles[0]+sideral_time
            delta_North.append(radius*(np.sin(Latitude)*np.cos(self.target_angles[1])-np.cos(Latitude)*np.sin(
                                   self.target_angles[1])*np.cos(telescope_longitude)))
            delta_East.append(radius*np.cos(Latitude)*np.sin(telescope_longitude))

        delta_positions = np.array([delta_North, delta_East])
        return delta_positions

    def space_parallax(self, t, name):

        tstart = self.HJD_to_JD(np.array([t[0]]))
        tend = self.HJD_to_JD(np.array(t[-1]))

        positions = produce_horizons_ephem(name, tstart, tend, observatory='Geocentric',step_size='10m', verbose=False)[1]
        positions = np.array(positions)

        dates = positions[:,0].astype(float)
        ra = positions[:,1].astype(float)
        dec = positions[:,2].astype(float)
        distances = positions[:,3].astype(float)*60.0/self.speed_of_light

        interpol_ra = interpolate(dates, ra)
        interpol_dec = interpolate(dates, dec)
        interpol_dist = interpolate(dates, distances)
        times=self.HJD_to_JD(t)

        ra_interpolated = interpol_ra[times]
        dec_interpolated = interpol_dec[times]
        distance_interpolated = interpol_dist[times]

        delta_North = []
        delta_East = []
        for i in xrange(len(times)):

            tt = i-2400000.5
            
            delta_North.append( distance_interpolated[i]*(np.sin(dec_interpolated[i])*np.cos(
                                self.target_angles[1])-np.cos(dec_interpolated[i])*np.sin(
                                   self.target_angles[1])*np.cos(ra_interpolated[i])))
            delta_East.append( distance_interpolated[i]*np.cos(dec_interpolated[i])*np.sin(ra_interpolated[i]))

        delta_positions = np.array([delta_North, delta_East])
       
        return delta_positions

        
       


    def parallax_outputs(self, PiE):

        piE=np.array(PiE)
        delta_tau = np.dot(piE,self.delta_position)
        delta_u = np.cross(piE,self.delta_position.T)

        return delta_tau, delta_u


    def produce_horizons_ephem(body, start_time, end_time, observatory='ELP', step_size='10m', verbose=False):
        """
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
        1,3,4,9,19,20,23 # RA/DEC and rates (Rarcsec/hour), Az & El, Vis. mag, Helio. range (r), Earth range (delta), Elong.
        space  # to get to next prompt
        q   # quit
        """
    
    # Lookup observatory name
        OBSERVATORY_ID = horizons_obscodes(observatory)
        if (verbose):
            print "Observatory ID= ",OBSERVATORY_ID
    
        #tstart = start_time.strftime('%Y-%m-%d %H:%M')
        tstart='JD'+str(start_time)
        if (verbose):
            print "tstart = ", tstart
        #tstop = end_time.strftime('%Y-%m-%d %H:%M')
        tstop='JD'+str(end_time)
        timeout =4 #seconds
        t = telnetlib.Telnet('horizons.jpl.nasa.gov',6775)
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
        t.write(body+'\n')
        data = t.read_until('Select ... [E]phemeris, [F]tp, [M]ail, [R]edisplay, ?, <cr>: ',timeout)
        if len(data)==0:
            print 'No connection to JPL, sorry :('
            flag='No connection to JPL'
            return flag
        
    
        if (verbose):
            print "data = ", data
        if (data.find('phemeris') < 0):
          if (data.find('EXACT')>=0):
            t.write('\n')
            data = t.read_until('Select ... [E]phemeris, [F]tp, [M]ail, [R]edisplay, ?, <cr>: ', timeout)
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
                        firstline = l+1
                else:
                  tokens = line.split()
                  if (firstline>=0 and lastvalidline == -1):
                    if (len(tokens) < 2):
                      lastvalidline = l-1
                    elif (tokens[1] == body and len(tokens) < 3):
                      # The <3 is necessary to filter out entries for a planet's barycenter
                      useID = int(tokens[0])
                      useBody = tokens[1]
                      if (verbose):
                          print "Use instead the id = %s = %d" % (tokens[0],useID)
                l = l+1
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
                        firstline = l+1
                elif (firstline > 0):
                  if (verbose):
                      print "Splitting this line = %s" % (line)
                  tokens = line.split()
                  if (verbose):
                      print "length=%d,  %d tokens found" % (len(line),len(tokens))
                  if (firstline>=0 and lastvalidline == -1):
                    if (len(tokens) < 2):
                      # this is the final (i.e. blank) line in the list
                      lastvalidline = l-1
                    elif (tokens[1] == body):
    #                  print "%s %s is equal to %s." % (tokens[0],tokens[1],body)
                      useID = int(tokens[0])
                      useBody = tokens[1]
                      if (len(tokens) < 3):
                        if (verbose):
                          print "Use instead the id = %s = %d" % (tokens[0],useID)
                      elif (len(tokens[2].split()) < 1):
                        if (verbose):
                          print "Use instead the id = ",tokens[0]
                    else:
                        if (verbose):
                            print "%s %s is not equal to %s." % (tokens[0],tokens[1],body)
                l = l+1
            if (verbose):
                print "line with first possible source = ", firstline
                print "line with last possible source = ", lastvalidline
                print "first possible source = ", (lines[firstline].split())[1]
                print "last possible source = ", (lines[lastvalidline].split())[1]
                print "Writing ", useID
            t.write(str(useID)+'\n')
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
            return([],[],[])
            
        if (verbose):
            print data
        obsname = ''
        for i in range(4,len(tokens)):
            obsname += tokens[i]
            if (i < len(tokens)+1): obsname += ' '
        print "Confirmed Observatory name = ", obsname
        if (useID != ''):
            print "Confirmed Target ID = %d = %s" % (useID, useBody)
        t.write('y\n')
        data = t.read_until('] : ',1)
        if (verbose):
            print data
      
    
        t.write(tstart+'\n')
        data = t.read_until('] : ',1)
        if (verbose):
            print data
        t.write(tstop+'\n')
        data = t.read_until(' ? ] : ',timeout)
        if (verbose):
            print data
        t.write(step_size+'\n')
        data = t.read_until(', ?] : ',timeout)
        if (verbose):
            print data
        if (1==1):
            #t.write('n\n1,3,4,9,19,20,23,\nJ2000\n\n\nMIN\nDEG\nYES\n\n\nYES\n\n\n\n\n\n\n\n')
            t.write('n\n1,21,\nJ2000\n\n\JD\nMIN\nDEG\nYES\n\n\nYES\n\n\n\n\n\n\n\n')
        else:
            t.write('y\n') # accept default output?
            data = t.read_until(', ?] : ') #,timeout)
            if (verbose):
                print data
            t.write('1,3\n')
    
        t.read_until('$$SOE',timeout)
        data = t.read_until('$$EOE',timeout)
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
            print hor_line
            
    
            if (len(hor_line.split()) == 4):
                
                ( time, raDegrees, decDegrees,  light_dist) = hor_line.split()
            
            elif (len(hor_line.split()) == 0 or len(hor_line.split()) == 1):
                data_line = False
            else:
                data_line = False
                print "Wrong number of fields (",len(hor_line.split()),")"
                print "hor_line=",hor_line
            if (data_line == True):
               
                horemp_line=[time,raDegrees,decDegrees,light_dist]
                if (verbose):
                    print horemp_line
                horemp.append(horemp_line)
    
    # Construct ephem_info 
        ephem_info = { 'obj_id' : body,
                       'emp_sitecode' : OBSERVATORY_ID,
                       'emp_timesys': '(UT)',
                       'emp_rateunits': '"/min'
                     }
        flag='Succes connection to JPL'             
        return flag, horemp