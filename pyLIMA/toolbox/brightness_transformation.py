import numpy as np

# magnitude reference
ZERO_POINT = 27.4

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
