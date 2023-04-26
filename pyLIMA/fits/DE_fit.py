import scipy
import time as python_time
import numpy as np
import sys
from multiprocessing import Manager
from tqdm import tqdm



from pyLIMA.fits.ML_fit import MLfit
from pyLIMA.outputs import pyLIMA_plots


class DEfit(MLfit):

    def __init__(self, model, rescale_photometry=False, rescale_astrometry=False,
                 telescopes_fluxes_method='polyfit', DE_population_size=10, max_iteration=10000,
                 display_progress=False, strategy='rand1bin'):
        """The fit class has to be intialized with an event object."""

        super().__init__(model, rescale_photometry=rescale_photometry,
                         rescale_astrometry=rescale_astrometry, telescopes_fluxes_method=telescopes_fluxes_method)

        self.population = Manager().list() # to be recognize by all process during parallelization
        self.DE_population_size = DE_population_size #Times number of dimensions!
        self.max_iteration = max_iteration
        self.fit_time = 0 #s
        self.display_progress = display_progress
        self.strategy = strategy

    def fit_type(self):
        return "Differential Evolution"

    def objective_function(self, fit_process_parameters):

        likelihood = -self.model_likelihood(fit_process_parameters)

        # Priors
        priors = self.get_priors(fit_process_parameters)

        likelihood += -priors

        self.population.append(fit_process_parameters.tolist() + [likelihood])

        return likelihood

    def fit(self, initial_population=[], computational_pool=None):

        start_time = python_time.time()

        if computational_pool:

            worker = computational_pool.map

        else:

            worker = 1


        if initial_population == []:

            init = 'latinhypercube'

        else:

            init = initial_population

        bounds = [self.fit_parameters[key][1] for key in self.fit_parameters.keys()]

        aa = scipy.optimize._differentialevolution.DifferentialEvolutionSolver(self.objective_function, bounds=bounds,
                                                                               mutation=(0.5, 1.5),
                                                                               popsize=int(self.DE_population_size),
                                                                               maxiter=1, tol=0.00, atol=1.0,
                                                                               strategy=self.strategy,
                                                                               recombination=0.5, polish=False,
                                                                               init=init, disp=self.display_progress,
                                                                               workers=worker)
        popo = []
        popo_e = []
        aa.init_population_random()
        for loop in tqdm(range(self.max_iteration)):
            aa.__next__()
            popo.append(aa._scale_parameters(aa.population))
            popo_e.append(aa.population_energies)

        pop = np.array(popo)
        pope = np.array(popo_e)

        breakpoint()
        differential_evolution_estimation = scipy.optimize.differential_evolution(self.objective_function,
                                                                                  bounds=bounds,
                                                                                  mutation=(0.5, 1.5), popsize=int(self.DE_population_size),
                                                                                  maxiter=self.max_iteration, tol=0.00,
                                                                                  atol=1.0, strategy=self.strategy,
                                                                                  recombination=0.5, polish=False, init=init,
                                                                                  disp=self.display_progress, workers=worker)

        print('DE converge to objective function : f(x) = ', str(differential_evolution_estimation['fun']))
        print('DE converge to parameters : = ', differential_evolution_estimation['x'].astype(str))

        fit_results = differential_evolution_estimation['x']
        fit_log_likelihood = differential_evolution_estimation['fun']

        computation_time = python_time.time() - start_time
        print(sys._getframe().f_code.co_name, ' : '+self.fit_type()+' fit SUCCESS')

        DE_population = np.array(self.population)

        print('best_model:', fit_results, '-ln(likelihood)', fit_log_likelihood)

        self.fit_results = {'best_model': fit_results, '-(ln_likelihood)' : fit_log_likelihood, 'fit_time': computation_time,
                            'DE_population': DE_population}

    def samples_to_plot(self):

        samples = self.fit_results['DE_population']

        return samples
