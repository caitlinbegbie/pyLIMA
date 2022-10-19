import numpy as np


def xy_shifts_to_NE_shifts(xy_shifts, piEN, piEE):

    centroid_x = xy_shifts[0]
    centroid_y = xy_shifts[1]

    angle = np.arctan2(piEE,piEN)

    Delta_dec = centroid_x * np.cos(angle) - np.sin(angle) * centroid_y
    Delta_ra = centroid_x * np.sin(angle) + np.cos(angle) * centroid_y

    return Delta_ra, Delta_dec


def astrometric_position(telescope, pyLIMA_parameters, time_ref=None):

    time = telescope.astrometry['time'].value

    if time_ref is None:

        time_ref = pyLIMA_parameters.t0


    ref_N = getattr(pyLIMA_parameters, 'position_source_N_' + telescope.name)
    ref_E = getattr(pyLIMA_parameters, 'position_source_E_' + telescope.name)
    mu_N = pyLIMA_parameters.mu_source_N
    mu_E = pyLIMA_parameters.mu_source_E
    position_N = mu_N / 365.25 * (time - time_ref) + ref_N
    position_E = mu_E / 365.25 * (time - time_ref) + ref_E

    earth_vector = telescope.Earth_positions['astrometry']
    parallax_source = pyLIMA_parameters.parallax_source
    Earth_projected = earth_vector*parallax_source #mas

    if telescope.astrometry['delta_ra'].unit == 'mas':

        position_dec = position_N - Earth_projected[0]
        position_ra = position_E - Earth_projected[1]

    else:

        position_dec = position_N-Earth_projected[0]/telescope.pixel_scale
        position_ra = position_E-Earth_projected[1]/telescope.pixel_scale

    return position_ra, position_dec


def source_astrometric_position(telescope, pyLIMA_parameters, shifts=None, time_ref=None):

    if shifts is None:

        shifts = np.zeros(2)

    position_E, position_N = astrometric_position(telescope, pyLIMA_parameters, time_ref)

    if telescope.astrometry['delta_ra'].unit == 'mas':

        position_ra = shifts[0] + position_E
        position_dec = shifts[1] + position_N

    else:

        position_ra = shifts[0] / telescope.pixel_scale + position_E
        position_dec = shifts[1] / telescope.pixel_scale + position_N

    return position_ra, position_dec

def lens_astrometric_position(model, telescope, pyLIMA_parameters, shifts=None):

    source_NE = source_astrometric_position(telescope, pyLIMA_parameters, shifts=shifts)

    source_relative_to_lens = model.source_trajectory(telescope, pyLIMA_parameters,data_type='astrometry')

    source_relative_to_lens_NE = xy_shifts_to_NE_shifts((source_relative_to_lens[0],source_relative_to_lens[1])
                                                         , pyLIMA_parameters.piEN, pyLIMA_parameters.piEE)


    lens_NE = np.array(source_relative_to_lens_NE)*pyLIMA_parameters.theta_E

    if telescope.astrometry['delta_ra'].unit == 'mas':

        lens_NE = source_NE-lens_NE

    else:

        lens_NE = source_NE-lens_NE/telescope.pixel_scale

    return lens_NE
