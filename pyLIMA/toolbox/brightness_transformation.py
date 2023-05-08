import numpy as np

# ZERO POINT AND EXPOSURE TIME MATCH ~Roman telescope by default
ZERO_POINT = 27.4
EXPOSURE_TIME = 50 #s

def magnitude_to_flux(magnitude):
    """ Transform the injected magnitude to the the corresponding flux.

    :param array_like magnitude: the magnitude you want to transform.

    :return: the transformed magnitude in flux unit
    :rtype: array_like
    """

    flux = 10 ** ((ZERO_POINT- magnitude) / 2.5)

    return flux


def flux_to_magnitude(flux):
    """ Transform the injected flux to the the corresponding magnitude.

    :param array_like flux: the flux you want to transform.

    :return: the transformed magnitude
    :rtype: array_like
    """

    mag = ZERO_POINT - 2.5 * np.log10(flux)

    return mag


def error_magnitude_to_error_flux(error_magnitude, flux):
    """ Transform the injected magnitude error to the the corresponding error in flux.

    :param array_like error_magnitude: the magnitude errors measurements you want to transform.
    :param array_like flux: the fluxes corresponding to these errors

    :return: the transformed errors in flux units
    :rtype: array_like
    """

    error_flux = np.abs(error_magnitude * flux * np.log(10) / 2.5)

    return error_flux


def error_flux_to_error_magnitude(error_flux, flux):
    """ Transform the injected flux error to the the corresponding error in magnitude.

    :param array_like error_flux: the flux errors measurements you want to transform.
    :param array_like flux: the fluxes corresponding to these errors

    :return: the transformed errors in magnitude
    :rtype: array_like
    """
    error_magnitude = np.abs(2.5 * error_flux / (flux * np.log(10)))

    return error_magnitude

def noisy_observations(flux, exp_time=None):
    """Add Poisson noise to observations.

        :param array_like flux: the observed flux
        :param array_like error_flux: the error on observed flux

        :return: a numpy array which represents the observed noisy flux

        :rtype: array_like

    """

    if exp_time is not None:

        exposure_time = exp_time

    else:

        exposure_time = EXPOSURE_TIME


    photons = flux*exposure_time

    photons_observed = np.random.poisson(photons)
    err_photons_observed = photons_observed**0.5

    flux_observed = photons_observed/exposure_time
    err_flux_observed = err_photons_observed/exposure_time

    return flux_observed, err_flux_observed