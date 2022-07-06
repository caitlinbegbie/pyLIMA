import numpy as np
import pyLIMA.toolbox.brightness_transformation


def astrometric_residuals(astrometry, astrometric_model):


    residuals = astrometry - astrometric_model

    return residuals


def all_telescope_astrometric_residuals(model, pyLIMA_parameters, norm=False, rescaling_astrometry_parameters=None):
    """ Compute the residuals of all telescopes according to the model.

    :param object pyLIMA_parameters: object containing the model parameters, see microlmodels for more details

    :return: the residuals in flux,
    :rtype: list, a list of array of residuals in flux
    """

    Residuals_ra = []
    err_ra_astrometry = []

    Residuals_dec = []
    err_dec_astrometry = []

    ind = 0

    for telescope in model.event.telescopes:

        if telescope.astrometry is not None:

            # Find the residuals of telescope observation regarding the parameters and model
            astrometry = telescope.astrometry

            astro_ra = astrometry['delta_ra'].value
            astro_dec = astrometry['delta_dec'].value
            microlensing_model = model.compute_the_microlensing_model(telescope, pyLIMA_parameters)

            residus_ra = astrometric_residuals(astro_ra, microlensing_model['astrometry'][0])
            residus_dec = astrometric_residuals(astro_dec, microlensing_model['astrometry'][1])

            if rescaling_astrometry_parameters is not None:

                err_ra = astrometry['err_delta_ra'].value+rescaling_astrometry_parameters[ind]
                err_dec = astrometry['err_delta_dec'].value+rescaling_astrometry_parameters[ind]

            else:

                err_ra = astrometry['err_delta_ra'].value
                err_dec = astrometry['err_delta_dec'].value

            if norm:

                residus_ra /= err_ra
                residus_dec /= err_dec

            Residuals_ra = np.append(Residuals_ra, residus_ra)
            Residuals_dec = np.append(Residuals_dec, residus_dec)

            err_ra_astrometry = np.append(err_ra_astrometry, err_ra)
            err_dec_astrometry = np.append(err_dec_astrometry, err_dec)

            ind += 1

    residus = np.c_[Residuals_ra, err_ra_astrometry, Residuals_dec, err_dec_astrometry]

    return residus


def photometric_residuals(flux, photometric_model):
    """ Compute the residuals of a telescope lightcurve according to the model.

    :param object telescope: a telescope object. More details in telescopes module.
    :param object pyLIMA_parameters: object containing the model parameters, see microlmodels for more details

    :return: the residuals in flux, the priors
    :rtype: array_like, float
    """

    residuals = flux - photometric_model

    return residuals


def all_telescope_photometric_residuals(model, pyLIMA_parameters, norm=False, rescaling_photometry_parameters=None):
    """ Compute the residuals of all telescopes according to the model.

    :param object pyLIMA_parameters: object containing the model parameters, see microlmodels for more details

    :return: the residuals in flux,
    :rtype: list, a list of array of residuals in flux
    """

    residuals = []
    errfluxes = []

    ind = 0

    for telescope in model.event.telescopes:

        if telescope.lightcurve_flux is not None:

            # Find the residuals of telescope observation regarding the parameters and model
            lightcurve = telescope.lightcurve_flux

            flux = lightcurve['flux'].value

            microlensing_model = model.compute_the_microlensing_model(telescope, pyLIMA_parameters)

            residus = photometric_residuals(flux, microlensing_model['photometry'])

            if rescaling_photometry_parameters is not None:

                err_flux = lightcurve['err_flux'].value+rescaling_photometry_parameters[ind] * \
                           microlensing_model['photometry']

            else:

                err_flux = lightcurve['err_flux'].value

            if norm:

                residus /= err_flux

            residuals = np.append(residuals, residus)
            errfluxes = np.append(errfluxes, err_flux)

            ind += 1

    return residuals, errfluxes


def photometric_chi2(telescope, model, pyLIMA_parameters):

    pass

def all_telescope_photometric_chi2(model, pyLIMA_parameters,rescaling_parameters=None):

    pass


def all_telescope_photometric_likelihood(model, pyLIMA_parameters, rescaling_photometry_parameters=None):

    residus, errflux = all_telescope_photometric_residuals(model, pyLIMA_parameters, norm=True,
                                                  rescaling_photometry_parameters=rescaling_photometry_parameters)

    chi2 = np.sum(residus**2)+2*np.sum(np.log(errflux))+len(errflux)*np.log(2*np.pi)

    return chi2


def photometric_residuals_in_magnitude(telescope, model, pyLIMA_parameters):
    """ Compute the residuals of a telescope lightcurve according to the model.

    :param object telescope: a telescope object. More details in telescopes module.
    :param object pyLIMA_parameters: object containing the model parameters, see microlmodels for more details

    :return: the residuals in flux, the priors
    :rtype: array_like, float
    """
    try:
        lightcurve = telescope.lightcurve_magnitude

        mag = lightcurve['mag'].value

        microlensing_model = model.compute_the_microlensing_model(telescope, pyLIMA_parameters)

        microlensing_model = pyLIMA.toolbox.brightness_transformation.ZERO_POINT-2.5*np.log10(microlensing_model['photometry'])

        residuals = mag - microlensing_model

        return residuals

    except:

        return []