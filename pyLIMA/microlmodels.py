# -*- coding: utf-8 -*-
"""
Created on Mon Dec  7 10:32:13 2015

@author: ebachelet
"""

from __future__ import division
from collections import OrderedDict
import os.path
import abc
import sys

thismodule = sys.modules[__name__]

import numpy as np
from scipy import interpolate, misc
import collections
import time as python_time

import microlguess
import microlmagnification
import microlpriors

full_path = os.path.abspath(__file__)
directory, filename = os.path.split(full_path)

### THIS NEED TO BE SORTED ####
try:

    # yoo_table = np.loadtxt('b0b1.dat')
    yoo_table = np.loadtxt(os.path.join(directory, 'data/Yoo_B0B1.dat'))
except:

    print 'ERROR : No b0b1.dat file found, please check!'

b0b1 = yoo_table
zz = b0b1[:, 0]
b0 = b0b1[:, 1]
b1 = b0b1[:, 2]
# db0 = b0b1[:,4]
# db1 = b0b1[:, 5]
interpol_b0 = interpolate.interp1d(zz, b0, kind='linear')
interpol_b1 = interpolate.interp1d(zz, b1, kind='linear')
# import pdb; pdb.set_trace()

dB0 = misc.derivative(lambda x: interpol_b0(x), zz[1:-1], dx=10 ** -4, order=3)
dB1 = misc.derivative(lambda x: interpol_b1(x), zz[1:-1], dx=10 ** -4, order=3)
dB0 = np.append(2.0, dB0)
dB0 = np.concatenate([dB0, [dB0[-1]]])
dB1 = np.append((2.0 - 3 * np.pi / 4), dB1)
dB1 = np.concatenate([dB1, [dB1[-1]]])
interpol_db0 = interpolate.interp1d(zz, dB0, kind='linear')
interpol_db1 = interpolate.interp1d(zz, dB1, kind='linear')
yoo_table = [zz, interpol_b0, interpol_b1, interpol_db0, interpol_db1]


class ModelException(Exception):
    pass


def create_model(model_type, event, parallax=['None', 0.0], xallarap=['None', 0.0],
                 orbital_motion=['None', 0.0], source_spots='None'):
    """
    Load a model according to the supplied model_type. Models are expected to be named
    Model<model_type> e.g. ModelPSPL

    :param string model_type: Model type e.g. PSPL
    :return: Model object for given model_type
    """

    try:

        model = getattr(thismodule, 'Model{}'.format(model_type))

    except AttributeError:

        raise ModelException('Unknown model "{}"'.format(model_type))

    return model(event, parallax, xallarap,
                 orbital_motion, source_spots)


class Model2(object):
    __metaclass__ = abc.ABCMeta

    def __init__(self, event, parallax=['None', 0.0], xallarap=['None', 0.0],
                 orbital_motion=['None', 0.0], source_spots='None'):
        """ Initialization of the attributes described above.
        """

        self.event = event
        self.parallax_model = parallax
        self.xallarap_model = xallarap
        self.orbital_motion_model = orbital_motion
        self.source_spots_model = source_spots
        self.yoo_table = yoo_table
        self.Jacobian_flag = 'OK'

        self.model_dictionnary = {}
        self.pyLIMA_standards_dictionnary = {}

        self.fancy_to_pyLIMA_dictionnary = {}
        self.pyLIMA_to_fancy = {}
        self.fancy_to_pyLIMA = {}

        self.define_pyLIMA_standard_parameters()

    @abc.abstractproperty
    def model_type(self):
        pass

    @abc.abstractmethod
    def paczynski_model_parameters(self):
        return

    @abc.abstractmethod
    def model_magnification(self, pyLIMA_parameters, source_trajectory, gamma, yoo_table):
        return

    def define_pyLIMA_standard_parameters(self):

        self.model_dictionnary = self.paczynski_model_parameters()

        if self.parallax_model[0] != 'None':

            self.Jacobian_flag = 'No way'
            self.model_dictionnary['piEN'] = len(self.model_dictionnary)
            self.model_dictionnary['piEE'] = len(self.model_dictionnary)

            self.event.compute_parallax_all_telescopes(self.parallax_model)

        if self.xallarap_model[0] != 'None':

            self.Jacobian_flag = 'No way'
            self.model_dictionnary['XiEN'] = len(self.model_dictionnary)
            self.model_dictionnary['XiEE'] = len(self.model_dictionnary)

        if self.orbital_motion_model[0] != 'None':

            self.Jacobian_flag = 'No way'
            self.model_dictionnary['dsdt'] = len(self.model_dictionnary)
            self.model_dictionnary['dalphadt'] = len(self.model_dictionnary)

        if self.source_spots_model != 'None':

            self.Jacobian_flag = 'No way'
            self.model_dictionnary['spot'] = len(self.model_dictionnary) + 1

        for telescope in self.event.telescopes:
            self.model_dictionnary['fs_' + telescope.name] = len(self.model_dictionnary)
            self.model_dictionnary['g_' + telescope.name] = len(self.model_dictionnary)

        self.model_dictionnary = OrderedDict(
            sorted(self.model_dictionnary.items(), key=lambda x: x[1]))

        self.pyLIMA_standards_dictionnary = self.model_dictionnary.copy()

        self.parameters_boundaries = microlguess.differential_evolution_parameters_boundaries(self)

    def define_model_parameters(self):

        if len(self.pyLIMA_to_fancy) != 0:

            self.Jacobian_flag = 'No way'
            for key_parameter in self.fancy_to_pyLIMA_dictionnary.keys():
                self.model_dictionnary[key_parameter] = self.model_dictionnary.pop(
                    self.fancy_to_pyLIMA_dictionnary[key_parameter])

            self.model_dictionnary = OrderedDict(
                sorted(self.model_dictionnary.items(), key=lambda x: x[1]))

    def compute_the_microlensing_model(self, telescope, pyLIMA_parameters):

        amplification, u = self.model_magnification(telescope, pyLIMA_parameters)
        return self._default_microlensing_model(telescope, pyLIMA_parameters, amplification)

    def _default_microlensing_model(self, telescope, pyLIMA_parameters, amplification):

        try:

            # Fluxes parameters are fitted
            f_source = getattr(pyLIMA_parameters, 'fs_' + telescope.name)
            f_blending = f_source * getattr(pyLIMA_parameters, 'g_' + telescope.name)

        except TypeError:

            # Fluxes parameters are estimated through np.polyfit
            lightcurve = telescope.lightcurve_flux
            flux = lightcurve[:, 1]
            errflux = lightcurve[:, 2]
            f_source, f_blending = np.polyfit(amplification, flux, 1, w=1 / errflux)

        microlensing_model = f_source * amplification + f_blending

        # Prior here
        priors = microlpriors.microlensing_flux_priors(len(microlensing_model), f_source, f_blending)
        # print 'the microl model', python_time.time() - start_time
        return microlensing_model, priors

    def compute_pyLIMA_parameters(self, fancy_parameters):
        """ Realize the transformation between the fancy parameters to fit to the
        standard pyLIMA parameters needed for computing a model.

        :param list fancy_parameters: the parameters you fit
        :return: pyLIMA parameters
        :rtype: object (namedtuple)
        """
        # start_time = python_time.time()
        model_parameters = collections.namedtuple('parameters', self.model_dictionnary)

        for key_parameter in self.model_dictionnary.keys():

            try:

                setattr(model_parameters, key_parameter, fancy_parameters[self.model_dictionnary[key_parameter]])

            except:

                pass

        # print 'arange', python_time.time() - start_time

        pyLIMA_parameters = self.fancy_parameters_to_pyLIMA_standard_parameters(model_parameters)

        # print 'conversion', python_time.time() - start_time
        return pyLIMA_parameters

    def fancy_parameters_to_pyLIMA_standard_parameters(self, fancy_parameters):
        """ Transform the fancy parameters to the pyLIMA standards. The output got all
        the necessary standard attributes, example to, uo, tE...


        :param object fancy_parameters: the fancy_parameters as namedtuple
        :return: the pyLIMA standards are added to the fancy parameters
        :rtype: object
        """
        # start_time = python_time.time()
        if len(self.fancy_to_pyLIMA) != 0:

            for key_parameter in self.fancy_to_pyLIMA.keys():
                setattr(fancy_parameters, key_parameter, self.fancy_to_pyLIMA[key_parameter](fancy_parameters))

        # print 'fancy to PYLIMA', python_time.time() - start_time
        return fancy_parameters

    def pyLIMA_standard_parameters_to_fancy_parameters(self, pyLIMA_parameters):
        """ Transform the  the pyLIMA standards parameters to the fancy parameters. The output got all
            the necessary fancy attributes.


        :param object pyLIMA_parameters: the  standard pyLIMA parameters as namedtuple
        :return: the fancy parameters are added to the fancy parameters
        :rtype: object
        """
        if len(self.pyLIMA_to_fancy) != 0:

            for key_parameter in self.pyLIMA_to_fancy.keys():
                setattr(pyLIMA_parameters, key_parameter, self.pyLIMA_to_fancy[key_parameter](pyLIMA_parameters))

        return pyLIMA_parameters

    def source_trajectory(self, telescope, pyLIMA_parameters):
        """ Compute the microlensing source trajectory associated to a telescope for the given parameters.


        :param object telescope: a telescope object. More details in telescope module.
        :param float to: the time of maximum magnification.
        :param float uo: the minimum impact parameter, associated to to.
        :param float tE: the angular Einstein ring crossing time
        :param float alpha: the angle of the source trajectory, define in trigonometric convention.
        :param array_like parallax: the parallax vector piE if needed
        :param float orbital_motion: the angle shift dalphadt due to lens rotation

        :return: source_trajectory_x, source_trajectory_y the x,y compenents of the source trajectory
        :rtype: array_like,array_like
        """
        # Linear basic trajectory

        lightcurve = telescope.lightcurve_flux
        time = lightcurve[:, 0]

        to = pyLIMA_parameters.to
        uo = pyLIMA_parameters.uo
        tE = pyLIMA_parameters.tE

        tau = (time - to) / tE
        uo = np.array([uo] * len(tau))

        # These following second order induce curvatures in the source trajectory
        # Parallax?
        if 'piEN' in pyLIMA_parameters._fields:

            piE = np.array([pyLIMA_parameters.piEN, pyLIMA_parameters.piEE])
            parallax_delta_tau, parallax_delta_uo = compute_parallax_curvature(piE, telescope.deltas_positions)

            tau += parallax_delta_tau
            uo += parallax_delta_uo

        # Orbital motion?
        # Xallarap?

        if 'alpha' in pyLIMA_parameters._fields:

            alpha = pyLIMA_parameters.alpha
            source_trajectory_x = tau * np.cos(alpha) - uo * np.sin(alpha)
            source_trajectory_y = tau * np.sin(alpha) + uo * np.cos(alpha)

        else:

            source_trajectory_x = tau
            source_trajectory_y = uo


        return source_trajectory_x, source_trajectory_y


class ModelPSPL(Model2):
    @property
    def model_type(self):
        return 'PSPL'

    def paczynski_model_parameters(self):
        model_dictionary = {'to': 0, 'uo': 1, 'tE': 2}

        return model_dictionary

    def model_magnification(self, telescope, pyLIMA_parameters):
        source_trajectory = self.source_trajectory(telescope, pyLIMA_parameters)
        return microlmagnification.amplification_PSPL(*source_trajectory)

    def model_Jacobian(self, telescope, pyLIMA_parameters):


        # Derivatives of the residuals_LM objective function, PSPL version

        lightcurve = telescope.lightcurve_flux

        time = lightcurve[:, 0]
        errflux = lightcurve[:, 2]

        # Derivative of A = (u^2+2)/(u(u^2+4)^0.5). Amplification[0] is A(t).
        # Amplification[1] is U(t).
        Amplification = self.model_magnification(telescope, pyLIMA_parameters)
        dAmplificationdU = (-8) / (Amplification[1] ** 2 * (Amplification[1] ** 2 + 4) ** 1.5)

        # Derivative of U = (uo^2+(t-to)^2/tE^2)^0.5
        dUdto = -(time - pyLIMA_parameters.to) / \
                (pyLIMA_parameters.tE ** 2 * Amplification[1])
        dUduo = pyLIMA_parameters.uo / Amplification[1]
        dUdtE = -(time - pyLIMA_parameters.to) ** 2 / \
                (pyLIMA_parameters.tE ** 3 * Amplification[1])

        # Derivative of the objective function

        dresdto = -getattr(pyLIMA_parameters, 'fs_' + telescope.name) * dAmplificationdU * dUdto / errflux
        dresduo = getattr(pyLIMA_parameters, 'fs_' + telescope.name) * dAmplificationdU * dUduo / errflux
        dresdtE = -getattr(pyLIMA_parameters, 'fs_' + telescope.name) * dAmplificationdU * dUdtE / errflux
        dresdfs = -(Amplification[0] + getattr(pyLIMA_parameters, 'g_' + telescope.name)) / errflux
        dresdg = -getattr(pyLIMA_parameters, 'fs_' + telescope.name) / errflux

        jacobi = np.array([dresdto, dresduo, dresdtE, dresdfs, dresdg])

        return jacobi


class ModelFSPL(Model2):
    @property
    def model_type(self):
        return 'FSPL'

    def paczynski_model_parameters(self):
        model_dictionary = {'to': 0, 'uo': 1, 'tE': 2, 'rho': 3}

        return model_dictionary

    def model_magnification(self, telescope, pyLIMA_parameters):
        source_trajectory_x, source_trajectory_y = self.source_trajectory(telescope, pyLIMA_parameters)
        rho = pyLIMA_parameters.rho
        gamma = telescope.gamma

        return microlmagnification.amplification_FSPL(source_trajectory_x, source_trajectory_y, rho,
                                                      gamma, self.yoo_table)

    def model_Jacobian(self, telescope, pyLIMA_parameters):
        # Derivatives of the residuals_LM objective function, FSPL version

        fake_model = ModelPSPL(self.event)

        lightcurve = telescope.lightcurve_flux
        time = lightcurve[:, 0]
        errflux = lightcurve[:, 2]
        gamma = telescope.gamma

        # Derivative of A = Yoo et al (2004) method.
        Amplification_PSPL = fake_model.model_magnification(telescope, pyLIMA_parameters)

        dAmplification_PSPLdU = (-8) / (Amplification_PSPL[1] ** 2 * (Amplification_PSPL[1] ** 2 + 4) ** (1.5))

        # z_yoo=U/rho
        z_yoo = Amplification_PSPL[1] / pyLIMA_parameters.rho

        dadu = np.zeros(len(Amplification_PSPL[0]))
        dadrho = np.zeros(len(Amplification_PSPL[0]))

        # Far from the lens (z_yoo>>1), then PSPL.
        ind = np.where((z_yoo > self.yoo_table[0][-1]))[0]
        dadu[ind] = dAmplification_PSPLdU[ind]
        dadrho[ind] = -0.0

        # Very close to the lens (z_yoo<<1), then Witt&Mao limit.
        ind = np.where((z_yoo < self.yoo_table[0][0]))[0]
        dadu[ind] = dAmplification_PSPLdU[ind] * (2 * z_yoo[ind] - gamma * (2 - 3 * np.pi / 4) * z_yoo[ind])

        dadrho[ind] = -Amplification_PSPL[0][ind] * Amplification_PSPL[1][ind] / pyLIMA_parameters.rho ** 2 * \
                      (2 - gamma * (2 - 3 * np.pi / 4))

        # FSPL regime (z_yoo~1), then Yoo et al derivatives
        ind = np.where((z_yoo <= self.yoo_table[0][-1]) & (z_yoo >= self.yoo_table[0][0]))[0]

        dadu[ind] = dAmplification_PSPLdU[ind] * (self.yoo_table[1](z_yoo[ind]) - \
                                                  gamma * self.yoo_table[2](z_yoo[ind])) + \
                                                  Amplification_PSPL[0][ind] * \
                                                  (self.yoo_table[3](z_yoo[ind]) - \
                                                   gamma * self.yoo_table[4](z_yoo[ind])) * 1 / pyLIMA_parameters.rho

        dadrho[ind] = -Amplification_PSPL[0][ind] * Amplification_PSPL[1][ind] / pyLIMA_parameters.rho ** 2 * \
                      (self.yoo_table[3](z_yoo[ind]) - gamma * self.yoo_table[4](z_yoo[ind]))

        dUdto = -(time - pyLIMA_parameters.to) / (pyLIMA_parameters.tE ** 2 * Amplification_PSPL[1])

        dUduo = pyLIMA_parameters.uo / Amplification_PSPL[1]

        dUdtE = -(time - pyLIMA_parameters.to) ** 2 / (pyLIMA_parameters.tE ** 3 * Amplification_PSPL[1])

        # Derivative of the objective function
        dresdto = -getattr(pyLIMA_parameters, 'fs_' + telescope.name) * dadu * dUdto / errflux

        dresduo = -getattr(pyLIMA_parameters, 'fs_' + telescope.name) * dadu * dUduo / errflux

        dresdtE = -getattr(pyLIMA_parameters, 'fs_' + telescope.name) * dadu * dUdtE / errflux

        dresdrho = -getattr(pyLIMA_parameters, 'fs_' + telescope.name) * dadrho / errflux

        Amplification_FSPL = self.model_magnification(telescope, pyLIMA_parameters)

        dresdfs = -(Amplification_FSPL[0] + getattr(pyLIMA_parameters, 'g_' + telescope.name)) / errflux

        dresdg = -getattr(pyLIMA_parameters, 'fs_' + telescope.name) / errflux

        jacobi = np.array([dresdto, dresduo, dresdtE, dresdrho, dresdfs, dresdg])

        return jacobi




def compute_parallax_curvature(piE, delta_positions):
    """ Compute the curvature induce by the parallax of from
    deltas_positions of a telescope.

    :param array_like piE: the microlensing parallax vector. Have a look :
                           http://adsabs.harvard.edu/abs/2004ApJ...606..319G
    :param array_like delta_positions: the delta_positions of the telescope. More details in microlparallax module.
    :return: delta_tau and delta_u, the shift introduce by parallax
    :rtype: array_like,array_like
    """

    delta_tau = -np.dot(piE, delta_positions)
    delta_u = -np.cross(piE, delta_positions.T)

    return delta_tau, delta_u


class MLModels(object):
    """
    ######## MLModels module ########

    This module defines the model you want to fit your data to.

    Attributes :

        event : A event class which describe your event that you want to model. See the event module.

        paczynski_model : The microlensing model you want. Has to be a string :

                 'PSPL' --> Point Source Point Lens. The amplification is taken from :
                 "Gravitational microlensing by the galactic halo" Paczynski,B. 1986ApJ...304....1P

                 'FSPL' --> Finite Source Point Lens. The amplification is taken from :
                 "OGLE-2003-BLG-262: Finite-Source Effects from a Point-Mass Lens' Yoo,
                 J. et al.2004ApJ...603..139Y
                 Note that the LINEAR LIMB-DARKENING is used, where the table b0b1.dat is interpolated
                 to compute B0(z) and B1(z).

                 'DSPL'  --> not available now
                 'Binary' --> not available now
                 'Triple' --> not available now

        parallax_model : Parallax model you want to use for the Earth types telescopes.
                   Has to be a list containing the model in the available_parallax
                   parameter and the value of topar. Have a look here for more details :
                   http://adsabs.harvard.edu/abs/2011ApJ...738...87S

                    'Annual' --> Annual parallax
                    'Terrestrial' --> Terrestrial parallax
                    'Full' --> combination of previous

                    topar --> a time in HJD choosed as the referenced time fot the parallax

                  If you have some Spacecraft types telescopes, the space based parallax
                  is computed if parallax is different of 'None'
                  More details in the microlparallax module

        xallarap_model : not available yet

        orbital_motion_model : not available yet

                'None' --> No orbital motion
                '2D' --> Classical orbital motion
                '3D' --> Full Keplerian orbital motion

                toom --> a time in HJD choosed as the referenced time fot the orbital motion
                        (Often choose equal to topar)

                More details in the microlomotion module

        source_spots_model : not available yet

                'None' --> No source spots

                 More details in the microlsspots module

    :param object event: a event object. More details on the event module.
    :param string model: the microlensing model you want.
    :param list parallax: a list of [string,float] indicating the parallax model you want and to_par
    :param list xallarap: a list of [string,float] indicating the xallarap mode.l. NOT WORKING NOW.
    :param list orbital_motion: a list of [string,float] indicating the parallax model you want and to_om.
                                NOT WORKING NOW.
    :param string source_spots: a string indicated the source_spots you want. NOT WORKING.
    """

    def __init__(self, event, model, parallax=['None', 0.0], xallarap=['None', 0.0],
                 orbital_motion=['None', 0.0], source_spots='None'):
        """ Initialization of the attributes described above.
        """

        self.event = event
        self.paczynski_model = create_model(model)
        self.parallax_model = parallax
        self.xallarap_model = xallarap
        self.orbital_motion_model = orbital_motion
        self.source_spots_model = source_spots

        self.yoo_table = yoo_table

        self.model_dictionnary = {}
        self.pyLIMA_standards_dictionnary = {}

        self.fancy_to_pyLIMA_dictionnary = {}
        self.pyLIMA_to_fancy = {}
        self.fancy_to_pyLIMA = {}

        self.define_pyLIMA_standard_parameters()

    def define_model_parameters(self):

        if len(self.pyLIMA_to_fancy) != 0:

            for key_parameter in self.fancy_to_pyLIMA_dictionnary.keys():
                self.model_dictionnary[key_parameter] = self.model_dictionnary.pop(
                    self.fancy_to_pyLIMA_dictionnary[key_parameter])

            self.model_dictionnary = OrderedDict(
                sorted(self.model_dictionnary.items(), key=lambda x: x[1]))

    def define_pyLIMA_standard_parameters(self):
        """ Create the model_dictionnary which explain to the different modules which parameter
        is what (
        Paczynski parameters+second_order+fluxes
        """
        self.model_dictionnary = self.paczynski_model.paczynski_model_parameters()

        if self.parallax_model[0] != 'None':
            self.model_dictionnary['piEN'] = len(self.model_dictionnary)
            self.model_dictionnary['piEE'] = len(self.model_dictionnary)

            self.event.compute_parallax_all_telescopes(self.parallax_model)

        if self.xallarap_model[0] != 'None':
            self.model_dictionnary['XiEN'] = len(self.model_dictionnary)
            self.model_dictionnary['XiEE'] = len(self.model_dictionnary)

        if self.orbital_motion_model[0] != 'None':
            self.model_dictionnary['dsdt'] = len(self.model_dictionnary)
            self.model_dictionnary['dalphadt'] = len(self.model_dictionnary)

        if self.source_spots_model != 'None':
            self.model_dictionnary['spot'] = len(self.model_dictionnary) + 1

        for telescope in self.event.telescopes:
            self.model_dictionnary['fs_' + telescope.name] = len(self.model_dictionnary)
            self.model_dictionnary['g_' + telescope.name] = len(self.model_dictionnary)

        self.model_dictionnary = OrderedDict(
            sorted(self.model_dictionnary.items(), key=lambda x: x[1]))

        self.pyLIMA_standards_dictionnary = self.model_dictionnary.copy()

        self.parameters_boundaries = microlguess.differential_evolution_parameters_boundaries(self)

    def magnification(self, parameters, time, gamma=0.0, delta_positions=0):

        """ Compute the magnification  associated to the model.
        ##THIS IS DEPCRIATED< ONLY USED IN JACOBIAN##
        :param list parameters: the model parameters you want to compute the magnification around
        :param array_like time: the time you want to obtain the magnification
        :param float gamma: the limb-darkening coefficient
        :param array_like delta_positions: the deltas_position from the parallax
        :return: the amplification A(time) and the impact parameter U(time)
        :rtype: float,float
        """

        to = parameters[self.model_dictionnary['to']]
        uo = parameters[self.model_dictionnary['uo']]
        tE = parameters[self.model_dictionnary['tE']]

        tau = (time - to) / tE

        delta_tau = 0
        delta_uo = 0

        if self.parallax_model[0] != 'None':
            piE = np.array([parameters[self.model_dictionnary['piEN']],
                            parameters[self.model_dictionnary['piEE']]])
            # import pdb; pdb.set_trace()
            parallax_delta_tau, parallax_delta_uo = self.compute_parallax_curvature(piE, delta_positions)
            delta_tau += parallax_delta_tau
            delta_uo += parallax_delta_uo

        tau += delta_tau
        uo = delta_uo + uo

        if self.paczynski_model.model_type == 'PSPL':
            amplification, u = microlmagnification.amplification_PSPL(tau, uo)
            return amplification, u

        if self.paczynski_model.model_type == 'FSPL':
            rho = parameters[self.model_dictionnary['rho']]
            amplification, u = microlmagnification.amplification_FSPL(tau, uo, rho, gamma,
                                                                      self.yoo_table)
            return amplification, u

    def compute_parallax_curvature(self, piE, delta_positions):
        """ Compute the curvature induce by the parallax of from
        deltas_positions of a telescope.

        :param array_like piE: the microlensing parallax vector. Have a look :
                               http://adsabs.harvard.edu/abs/2004ApJ...606..319G
        :param array_like delta_positions: the delta_positions of the telescope. More details in microlparallax module.
        :return: delta_tau and delta_u, the shift introduce by parallax
        :rtype: array_like,array_like
        """

        delta_tau = -np.dot(piE, delta_positions)
        delta_u = -np.cross(piE, delta_positions.T)

        return delta_tau, delta_u

    def compute_pyLIMA_parameters(self, fancy_parameters):
        """ Realize the transformation between the fancy parameters to fit to the
        standard pyLIMA parameters needed for computing a model.

        :param list fancy_parameters: the parameters you fit
        :return: pyLIMA parameters
        :rtype: object (namedtuple)
        """
        # start_time = python_time.time()
        model_parameters = collections.namedtuple('parameters', self.model_dictionnary)

        for key_parameter in self.model_dictionnary.keys():

            try:

                setattr(model_parameters, key_parameter, fancy_parameters[self.model_dictionnary[key_parameter]])

            except:

                pass

        # print 'arange', python_time.time() - start_time

        pyLIMA_parameters = self.fancy_parameters_to_pyLIMA_standard_parameters(model_parameters)

        # print 'conversion', python_time.time() - start_time
        return pyLIMA_parameters

    def model_magnification(self, telescope, pyLIMA_parameters):
        """ Compute the magnification associated to the microlensing model.


        :param object telescope: a telescope object. More details in telescope module.
        :param object pyLIMA_parameters: the standard pyLIMA parameters
        :return: amplification A(t) and the impact parameter U(t)
        :rtype: array_like, array_like
        """
        piE = None
        dalphadt = None

        if self.parallax_model[0] != 'None':
            piE = np.array([pyLIMA_parameters.piEN,
                            pyLIMA_parameters.piEE])

        if self.orbital_motion_model[0] != 'None':
            pass

        to = pyLIMA_parameters.to
        uo = pyLIMA_parameters.uo
        tE = pyLIMA_parameters.tE
        source_trajectory = self.source_trajectory(telescope, to, uo, tE, alpha=0.0,
                                                   parallax=piE, orbital_motion=dalphadt)
        return self.paczynski_model.model_magnification(pyLIMA_parameters, source_trajectory,
                                                        telescope.gamma, self.yoo_table)

    def compute_the_microlensing_model(self, telescope, pyLIMA_parameters):
        """ Compute the microlensing model of the corresponding telescope.


        :param object telescope: a telescope object. More details in telescope module.
        :param object pyLIMA_parameters: the standard pyLIMA parameters
        :return: the microlensing model in flux and the piors
        :rtype: array_like, float
        """

        # start_time = python_time.time()
        amplification, u = self.model_magnification(telescope, pyLIMA_parameters)
        return self.paczynski_model.compute_the_microlensing_model(amplification, u,
                                                                   pyLIMA_parameters,
                                                                   telescope)

    def fancy_parameters_to_pyLIMA_standard_parameters(self, fancy_parameters):
        """ Transform the fancy parameters to the pyLIMA standards. The output got all
        the necessary standard attributes, example to, uo, tE...


        :param object fancy_parameters: the fancy_parameters as namedtuple
        :return: the pyLIMA standards are added to the fancy parameters
        :rtype: object
        """
        # start_time = python_time.time()
        if len(self.fancy_to_pyLIMA) != 0:

            for key_parameter in self.fancy_to_pyLIMA.keys():
                setattr(fancy_parameters, key_parameter, self.fancy_to_pyLIMA[key_parameter](fancy_parameters))

        # print 'fancy to PYLIMA', python_time.time() - start_time
        return fancy_parameters

    def pyLIMA_standard_parameters_to_fancy_parameters(self, pyLIMA_parameters):
        """ Transform the  the pyLIMA standards parameters to the fancy parameters. The output got all
            the necessary fancy attributes.


        :param object pyLIMA_parameters: the  standard pyLIMA parameters as namedtuple
        :return: the fancy parameters are added to the fancy parameters
        :rtype: object
        """
        if len(self.pyLIMA_to_fancy) != 0:

            for key_parameter in self.pyLIMA_to_fancy.keys():
                setattr(pyLIMA_parameters, key_parameter, self.pyLIMA_to_fancy[key_parameter](pyLIMA_parameters))

        return pyLIMA_parameters

    def source_trajectory(self, telescope, to, uo, tE, alpha=0.0, parallax=None, orbital_motion=None):
        """ Compute the microlensing source trajectory associated to a telescope for the given parameters.


        :param object telescope: a telescope object. More details in telescope module.
        :param float to: the time of maximum magnification.
        :param float uo: the minimum impact parameter, associated to to.
        :param float tE: the angular Einstein ring crossing time
        :param float alpha: the angle of the source trajectory, define in trigonometric convention.
        :param array_like parallax: the parallax vector piE if needed
        :param float orbital_motion: the angle shift dalphadt due to lens rotation

        :return: source_trajectory_x, source_trajectory_y the x,y compenents of the source trajectory
        :rtype: array_like,array_like
        """
        # start_time = python_time.time()
        lightcurve = telescope.lightcurve_flux
        time = lightcurve[:, 0]

        tau = (time - to) / tE
        uo = np.array([uo] * len(tau))

        delta_tau = 0
        delta_uo = 0

        if parallax is not None:
            piE = parallax
            parallax_delta_tau, parallax_delta_uo = self.compute_parallax_curvature(piE, telescope.deltas_positions)
            delta_tau += parallax_delta_tau
            delta_uo += parallax_delta_uo

        tau += delta_tau
        uo += delta_uo

        source_trajectory_x = tau * np.cos(alpha) - uo * np.sin(alpha)
        source_trajectory_y = tau * np.sin(alpha) + uo * np.cos(alpha)

        # print 'trajectory', python_time.time() - start_time
        return source_trajectory_x, source_trajectory_y

    def model_Jacobian(self, fit_process_parameters):

        """Return the analytical Jacobian matrix, if requested by method LM.
        Available only for PSPL and FSPL without second_order.

        :param list fit_process_parameters: the model parameters ingested by the correpsonding
        fitting routine.

        :return: a numpy array which represents the jacobian matrix
        :rtype: array_like
        """

        # TODO :PROBABLY NEED REWORK
        if self.paczynski_model.model_type == 'PSPL':

            # Derivatives of the residuals_LM objective function, PSPL version

            dresdto = np.array([])
            dresduo = np.array([])
            dresdtE = np.array([])
            dresdfs = np.array([])
            dresdeps = np.array([])

            for telescope in self.event.telescopes:
                lightcurve = telescope.lightcurve_flux

                time = lightcurve[:, 0]
                errflux = lightcurve[:, 2]
                gamma = telescope.gamma

                # Derivative of A = (u^2+2)/(u(u^2+4)^0.5). Amplification[0] is A(t).
                # Amplification[1] is U(t).
                Amplification = self.magnification(fit_process_parameters, time, gamma)
                dAmplificationdU = (-8) / \
                                   (Amplification[1] ** 2 * (Amplification[1] ** 2 + 4) ** 1.5)

                # Derivative of U = (uo^2+(t-to)^2/tE^2)^0.5
                dUdto = -(time - fit_process_parameters[self.model_dictionnary['to']]) / \
                        (fit_process_parameters[self.model_dictionnary['tE']] ** 2 * Amplification[1])
                dUduo = fit_process_parameters[self.model_dictionnary['uo']] / Amplification[1]
                dUdtE = -(time - fit_process_parameters[self.model_dictionnary['to']]) ** 2 / \
                        (fit_process_parameters[self.model_dictionnary['tE']] ** 3 * Amplification[1])

                # Derivative of the objective function

                dresdto = np.append(dresdto,
                                    -fit_process_parameters[
                                        self.model_dictionnary['fs_' + telescope.name]] *
                                    dAmplificationdU * dUdto / errflux)
                dresduo = np.append(dresduo,
                                    -fit_process_parameters[
                                        self.model_dictionnary['fs_' + telescope.name]] *
                                    dAmplificationdU * dUduo / errflux)
                dresdtE = np.append(dresdtE,
                                    -fit_process_parameters[
                                        self.model_dictionnary['fs_' + telescope.name]] *
                                    dAmplificationdU * dUdtE / errflux)
                dresdfs = np.append(dresdfs, -(
                    Amplification[0] + fit_process_parameters[
                        self.model_dictionnary['g_' + telescope.name]]) / errflux)
                dresdeps = np.append(dresdeps, -fit_process_parameters[
                    self.model_dictionnary['fs_' + telescope.name]] / errflux)

            jacobi = np.array([dresdto, dresduo, dresdtE])

        if self.paczynski_model.model_type == 'FSPL':

            # Derivatives of the residuals_LM objective function, FSPL version
            dresdto = np.array([])
            dresduo = np.array([])
            dresdtE = np.array([])
            dresdrho = np.array([])
            dresdfs = np.array([])
            dresdeps = np.array([])

            fake_model = MLModels(self.event, 'PSPL')
            fake_params = np.delete(fit_process_parameters, self.model_dictionnary['rho'])

            for telescope in self.event.telescopes:
                lightcurve = telescope.lightcurve_flux
                time = lightcurve[:, 0]
                errflux = lightcurve[:, 2]
                gamma = telescope.gamma

                # Derivative of A = Yoo et al (2004) method.
                Amplification_PSPL = fake_model.magnification(fake_params, time, gamma)

                dAmplification_PSPLdU = (-8) / (Amplification_PSPL[1] ** 2 * \
                                                (Amplification_PSPL[1] ** 2 + 4) ** (1.5))

                # z_yoo=U/rho
                z_yoo = Amplification_PSPL[1] / fit_process_parameters[
                    self.model_dictionnary['rho']]

                dadu = np.zeros(len(Amplification_PSPL[0]))
                dadrho = np.zeros(len(Amplification_PSPL[0]))

                # Far from the lens (z_yoo>>1), then PSPL.
                ind = np.where((z_yoo > self.yoo_table[0][-1]))[0]
                dadu[ind] = dAmplification_PSPLdU[ind]
                dadrho[ind] = -0.0

                # Very close to the lens (z_yoo<<1), then Witt&Mao limit.
                ind = np.where((z_yoo < self.yoo_table[0][0]))[0]
                dadu[ind] = dAmplification_PSPLdU[ind] * \
                            (2 * z_yoo[ind] - gamma * (2 - 3 * np.pi / 4) * z_yoo[ind])

                dadrho[ind] = -Amplification_PSPL[0][ind] * Amplification_PSPL[1][ind] / \
                              fit_process_parameters[self.model_dictionnary['rho']] ** 2 * \
                              (2 - gamma * (2 - 3 * np.pi / 4))

                # FSPL regime (z_yoo~1), then Yoo et al derivatives
                ind = np.where((z_yoo <= self.yoo_table[0][-1]) & (z_yoo >= self.yoo_table[0][0]))[0]
                dadu[ind] = dAmplification_PSPLdU[ind] * (self.yoo_table[1](z_yoo[ind]) - \
                                                          gamma * self.yoo_table[2](z_yoo[ind])) + \
                            Amplification_PSPL[0][ind] * \
                            (self.yoo_table[3](z_yoo[ind]) - gamma * self.yoo_table[4](z_yoo[ind])) * \
                            1 / fit_process_parameters[self.model_dictionnary['rho']]

                dadrho[ind] = -Amplification_PSPL[0][ind] * Amplification_PSPL[1][ind] / \
                              fit_process_parameters[self.model_dictionnary['rho']] ** 2 * \
                              (self.yoo_table[3](z_yoo[ind]) - gamma * self.yoo_table[4](z_yoo[ind]))

                dUdto = -(time - fit_process_parameters[self.model_dictionnary['to']]) / \
                        (fit_process_parameters[self.model_dictionnary['tE']] ** 2 * \
                         Amplification_PSPL[1])

                dUduo = fit_process_parameters[self.model_dictionnary['uo']] / \
                        Amplification_PSPL[1]

                dUdtE = -(time - fit_process_parameters[self.model_dictionnary['to']]) ** 2 / \
                        (fit_process_parameters[self.model_dictionnary['tE']] ** 3 * \
                         Amplification_PSPL[1])

                # Derivative of the objective function
                dresdto = np.append(dresdto, -fit_process_parameters[
                    self.model_dictionnary['fs_' + telescope.name]] * dadu *
                                    dUdto / errflux)
                dresduo = np.append(dresduo, -fit_process_parameters[
                    self.model_dictionnary['fs_' + telescope.name]] * dadu *
                                    dUduo / errflux)
                dresdtE = np.append(dresdtE, -fit_process_parameters[
                    self.model_dictionnary['fs_' + telescope.name]] * dadu *
                                    dUdtE / errflux)

                dresdrho = np.append(dresdrho,
                                     -fit_process_parameters[
                                         self.model_dictionnary['fs_' + telescope.name]] *
                                     dadrho / errflux)

                Amplification_FSPL = self.magnification(fit_process_parameters, time, gamma)
                dresdfs = np.append(dresdfs, -(
                    Amplification_FSPL[0] + fit_process_parameters[
                        self.model_dictionnary['g_' + telescope.name]]) / errflux)
                dresdeps = np.append(dresdeps, -fit_process_parameters[
                    self.model_dictionnary['fs_' + telescope.name]] / errflux)

            jacobi = np.array([dresdto, dresduo, dresdtE, dresdrho])

        # Split the fs and g derivatives in several columns correpsonding to
        # each observatories
        start_index = 0

        for telescope in self.event.telescopes:
            dFS = np.zeros((len(dresdto)))
            dG = np.zeros((len(dresdto)))
            index = np.arange(start_index, start_index + len(telescope.lightcurve_flux[:, 0]))
            dFS[index] = dresdfs[index]
            dG[index] = dresdeps[index]
            jacobi = np.vstack([jacobi, dFS])
            jacobi = np.vstack([jacobi, dG])

            start_index = index[-1] + 1

        return jacobi
