import unittest

from mock import create_autospec
import mock

from doubles import expect

import warnings

import numpy as np
import numpy.testing as npt

from copy import deepcopy

from stratified_bayesian_optimization.acquisition_functions.sbo import SBO
from stratified_bayesian_optimization.entities.domain import DomainEntity
from stratified_bayesian_optimization.lib.constant import (
    PRODUCT_KERNELS_SEPARABLE,
    MATERN52_NAME,
    TASKS_KERNEL_NAME,
    UNIFORM_FINITE,
    TASKS,
    NEWTON_CG_NAME,
    TRUST_N_CG,
    DOGLEG,
)
from stratified_bayesian_optimization.services.bayesian_global_optimization import BGO
from stratified_bayesian_optimization.services.gp_fitting import GPFittingService
from stratified_bayesian_optimization.models.gp_fitting_gaussian import GPFittingGaussian
from stratified_bayesian_optimization.numerical_tools.bayesian_quadrature import BayesianQuadrature
from stratified_bayesian_optimization.kernels.matern52 import Matern52
from stratified_bayesian_optimization.lib.sample_functions import SampleFunctions
from stratified_bayesian_optimization.entities.domain import(
    BoundsEntity,
    DomainEntity,
)
from stratified_bayesian_optimization.entities.run_spec import RunSpecEntity
from stratified_bayesian_optimization.services.domain import DomainService
from stratified_bayesian_optimization.lib.finite_differences import FiniteDifferences
from stratified_bayesian_optimization.lib.affine_break_points import (
    AffineBreakPoints,
)
from stratified_bayesian_optimization.lib.parallel import Parallel
from stratified_bayesian_optimization.lib.util import (
    wrapper_objective_voi,
    wrapper_gradient_voi,
    wrapper_evaluate_sample,
)


def simple_affine_break_points(a, b):
    return [1], 2

class TestSBO(unittest.TestCase):
    def setUp(self):

        np.random.seed(5)
        n_points = 100
        points = np.linspace(0, 100, n_points)
        points = points.reshape([n_points, 1])
        tasks = np.random.randint(2, size=(n_points, 1))

        add = [10, -10]
        kernel = Matern52.define_kernel_from_array(1, np.array([100.0, 1.0]))
        function = SampleFunctions.sample_from_gp(points, kernel)

        for i in xrange(n_points):
            function[0, i] += add[tasks[i, 0]]
        points = np.concatenate((points, tasks), axis=1)
        self.points = points

        function = function[0, :]

        training_data = {
            'evaluations': list(function),
            'points': points,
            "var_noise": [],
        }

        gaussian_p = GPFittingGaussian(
            [PRODUCT_KERNELS_SEPARABLE, MATERN52_NAME, TASKS_KERNEL_NAME],
            training_data, [2, 1, 2], bounds_domain=[[0, 100], [0, 1]], type_bounds=[0, 1])
        gaussian_p = gaussian_p.fit_gp_regression(random_seed=1314938)

        self.gp = BayesianQuadrature(gaussian_p, [0], UNIFORM_FINITE, {TASKS: 2})


        # ver lo de domain entity
        self.bounds_domain_x = BoundsEntity({
            'lower_bound': 0,
            'upper_bound': 100,
        })

        self.spec = {
            'dim_x': 1,
            'choose_noise': True,
            'bounds_domain_x': [self.bounds_domain_x],
            'number_points_each_dimension': [100],
            'problem_name': 'a',
        }

        domain = DomainService.from_dict(self.spec)

        self.sbo = SBO(self.gp, np.array(domain.discretization_domain_x))
        self.sbo.clean_cache()


        self.spec_2 = {
            'dim_x': 1,
            'choose_noise': True,
            'bounds_domain_x': [self.bounds_domain_x],
            'number_points_each_dimension': [50],
            'problem_name': 'a',
        }

        domain_2 = DomainService.from_dict(self.spec_2)

        self.sbo_2 = SBO(self.gp, np.array(domain_2.discretization_domain_x))
        self.sbo_2.clean_cache()


        training_data_simple = {
            'evaluations': list(function[0:1]),
            'points': points[0:1, :],
            "var_noise": [],
        }
        gaussian_p_simple = GPFittingGaussian(
            [PRODUCT_KERNELS_SEPARABLE, MATERN52_NAME, TASKS_KERNEL_NAME],
            training_data_simple, [2, 1, 2], bounds_domain=[[0, 100], [0, 1]], type_bounds=[0, 1])
        gaussian_p_simple.update_value_parameters(self.sbo.bq.gp.get_value_parameters_model)
        gp_simple = BayesianQuadrature(gaussian_p_simple, [0], UNIFORM_FINITE, {TASKS: 2})

        self.sbo_simple = SBO(gp_simple, np.array([[2]]))
        self.sbo_simple.clean_cache()


        training_data_med = {
            'evaluations': list(function[0:5]),
            'points': points[0:5, :],
            "var_noise": [],
        }
        gaussian_p_med = GPFittingGaussian(
            [PRODUCT_KERNELS_SEPARABLE, MATERN52_NAME, TASKS_KERNEL_NAME],
            training_data_med, [2, 1, 2], bounds_domain=[[0, 100], [0, 1]], type_bounds=[0, 1])
        gaussian_p_med.update_value_parameters(self.sbo.bq.gp.get_value_parameters_model)
        gp_med = BayesianQuadrature(gaussian_p_med, [0], UNIFORM_FINITE, {TASKS: 2})

        self.sbo_med = SBO(gp_med, np.array(domain.discretization_domain_x))
        self.sbo_med.clean_cache()


    def test_evaluate(self):
        point = np.array([[52.5, 0]])
        value = self.sbo.evaluate(point)
        discretization = self.sbo.discretization

        bq = self.sbo.bq
        gp = self.sbo.bq.gp
        random_seed = 1
        n_samples = 40
        samples = gp.sample_new_observations(point, n_samples, random_seed)
        np.random.seed(random_seed)
        points_x = deepcopy(gp.data['points'])
        points_x = np.concatenate((points_x, point))

        posterior_means = bq.compute_posterior_parameters(discretization, only_mean=True,
                                                          cache=False)['mean']

        max_mean = posterior_means[np.argmax(posterior_means)]
        max_values = []

        for i in xrange(n_samples):
            evaluations = deepcopy(gp.data['evaluations'])
            evaluations = np.concatenate((evaluations, [samples[i]]))
            val = bq.compute_posterior_parameters(discretization,
                                                  historical_evaluations=evaluations,
                                                  historical_points=points_x, cache=False,
                                                  only_mean=True)
            values = val['mean']
            max_values.append(values[np.argmax(values)])

        kg = np.mean(max_values) - max_mean
        std = np.std(max_values) / n_samples

        assert kg - 1.96 * std <= value <= kg + 1.96 * std

        point = self.points[0:1, :]
        assert self.sbo.evaluate(point) == 0

    def test_evaluate_gradient(self):
        candidate = np.array([[52.5, 0]])
        self.sbo.clean_cache()
        grad = self.sbo.evaluate_gradient(candidate)

        dh = 0.1
        finite_diff = FiniteDifferences.forward_difference(
            lambda point: self.sbo.evaluate(point.reshape((1, len(point)))),
            np.array([52.5, 0]), np.array([dh]))

        npt.assert_almost_equal(finite_diff[1], grad[1], decimal=4)
        npt.assert_almost_equal(finite_diff[0], grad[0], decimal=2)

        point = self.points[0:1, :]
        assert np.all(self.sbo.evaluate_gradient(point) == [0, 0])

    def test_evaluate_gradient_keeping_one_point(self):
        candidate = np.array([[52.5, 0]])

        grad = self.sbo_simple.evaluate_gradient(candidate)
        assert np.all(grad == np.array([0, 0]))

        dh = 0.1
        finite_diff = FiniteDifferences.forward_difference(
            lambda point: self.sbo_simple.evaluate(point.reshape((1, len(point)))),
            np.array([52.5, 0]), np.array([dh]))
        npt.assert_almost_equal(finite_diff[1], grad[1])
        npt.assert_almost_equal(finite_diff[0], grad[0])

    def test_hvoi(self):
        b = np.array([1, 2])
        c = np.array([3, 4])
        keep = [0]
        z = self.sbo.hvoi(b, c, keep)
        assert z == 0

    def test_optimization(self):
        val = self.sbo_med.optimize(random_seed=1, parallel=False, n_restarts=1, start_ei=False)
        # Benchmark numbers obtained after optimizing the function manually, i.e. plot the function
        # and find the maximum.
        npt.assert_almost_equal(2018.8827643498898, val['optimal_value'], decimal=3)
        npt.assert_almost_equal([ 99.98636451, 0], val['solution'], decimal=4)

        self.sbo_med.bq.separate_tasks = False
        self.sbo_med.bq.bounds = [[0, 100], [0, 1]]
        self.sbo_med.bq.type_bounds = [0, 1]
        val = self.sbo_med.optimize(random_seed=1, n_restarts=1, parallel=False, start_ei=False)
        npt.assert_almost_equal([99.98636451, 0], val['solution'], decimal=4)
        npt.assert_almost_equal(2018.8827643498898, val['optimal_value'], decimal=3)

    def test_optimization_error(self):
        expect(Parallel).run_function_different_arguments_parallel.and_return({0: None})
        with self.assertRaises(Exception):
            self.sbo_med.optimize(random_seed=1, parallel=False)

    def test_generate_evaluations(self):
        evaluations = self.sbo_2.generate_evaluations(
            "test_generate_sbo_evals", "gp_fitting_gaussian", "test", 5, 1, 0, [10])

        points_x = [[11.1111111111], [22.2222222222]]

        values = []
        for task in xrange(2):
            for point in points_x:
                point_ = np.concatenate(([point], [[task]]), axis=1)
                values.append(self.sbo_2.evaluate(point_))

        point_ = np.concatenate(([[88.8888888889]], [[1]]), axis=1)
        value = self.sbo_2.evaluate(point_)

        npt.assert_almost_equal(values[0], evaluations[0][1], decimal=4)
        npt.assert_almost_equal(values[1], evaluations[0][2])
        npt.assert_almost_equal(values[2], evaluations[1][1])
        npt.assert_almost_equal(values[3], evaluations[1][2])
        npt.assert_almost_equal(value, evaluations[1][-2])


    def test_evaluate_sample(self):
        np.random.seed(1)
        n_samples = 50
        candidate_point = np.array([[52.5, 0]])

        point = np.array([[49.2]])
        samples = np.random.normal(0, 1, n_samples)
        posterior_values = []
        for sample in samples:
            val = self.sbo.evaluate_sample(point, candidate_point, sample)
            posterior_values.append(val)

        values = self.sbo.bq.compute_posterior_parameters_kg(point, candidate_point, cache=False)
        npt.assert_almost_equal(np.mean(posterior_values), values['a'], decimal=4)
        npt.assert_almost_equal(np.std(posterior_values), abs(values['b']), decimal=4)

        point_2 = np.array([[48.2]])
        samples = np.random.normal(0, 1, n_samples)
        posterior_values = []
        for sample in samples:
            val = self.sbo.evaluate_sample(point_2, candidate_point, sample)
            posterior_values.append(val)

        values = self.sbo.bq.compute_posterior_parameters_kg(point_2, candidate_point, cache=False)
        npt.assert_almost_equal(np.mean(posterior_values), values['a'], decimal=3)
        npt.assert_almost_equal(np.std(posterior_values), abs(values['b']), decimal=3)


    def test_evaluate_gradient_sample(self):
        point = np.array([[49.2]])
        candidate_point = np.array([[52.5, 0]])
        np.random.seed(1)
        sample = 0.5


        gradient = self.sbo.evaluate_gradient_sample(point, candidate_point, sample)

        dh = 0.001
        finite_diff = FiniteDifferences.forward_difference(
            lambda point_: self.sbo.evaluate_sample(
                point_.reshape((1, len(point_))), candidate_point, sample),
            np.array([49.2]), np.array([dh]))

        npt.assert_almost_equal(finite_diff[0], gradient, decimal=2)

        val = self.sbo.evaluate_sample(point, candidate_point, sample)


        sample = -0.8
        point = np.array([[10.2]])
        gradient = self.sbo.evaluate_gradient_sample(point, candidate_point, sample)

        dh = 0.001
        finite_diff = FiniteDifferences.forward_difference(
            lambda point_: self.sbo.evaluate_sample(
                point_.reshape((1, len(point_))), candidate_point, sample),
            np.array([10.2]), np.array([dh]))

        npt.assert_almost_equal(finite_diff[0], gradient, decimal=2)

        sample = -5.1
        point = np.array([[10.2]])
        gradient = self.sbo.evaluate_gradient_sample(point, candidate_point, sample)

        dh = 0.01
        finite_diff = FiniteDifferences.forward_difference(
            lambda point_: self.sbo.evaluate_sample(
                point_.reshape((1, len(point_))), candidate_point, sample),
            np.array([10.2]), np.array([dh]))

        npt.assert_almost_equal(finite_diff[0], gradient, decimal=2)

    def test_evaluate_sbo_by_sample(self):
        candidate_point = np.array([[52.5, 0]])
        np.random.seed(1)
        discretization = self.sbo.discretization

        sample = -2.0
        eval_2 = self.sbo.evaluate_sbo_by_sample(candidate_point, sample, n_restarts=10)

        values = []
        for point in discretization:
            val = self.sbo.evaluate_sample(point, candidate_point, sample)
            values.append(val)
        assert np.max(values) <= eval_2

        sample = 0.5
        eval = self.sbo.evaluate_sbo_by_sample(candidate_point, sample)

        values = []
        for point in discretization:
            val = self.sbo.evaluate_sample(point, candidate_point, sample)
            values.append(val)

        assert np.max(values) <= eval

    def test_evaluate_sbo_by_sample_hessian(self):
        candidate_point = np.array([[52.5, 0]])
        np.random.seed(1)

        sample = -2.0
        eval_2 = self.sbo.evaluate_sbo_by_sample(candidate_point, sample, n_restarts=10)

        eval_3 = self.sbo.evaluate_sbo_by_sample(
            candidate_point, sample, n_restarts=10, parallel=True, method_opt=NEWTON_CG_NAME)
        npt.assert_almost_equal(eval_3['max'], eval_2['max'], decimal=5)
        npt.assert_almost_equal(eval_3['optimum'], eval_2['optimum'], decimal=3)

        eval_4 = self.sbo.evaluate_sbo_by_sample(
            candidate_point, sample, n_restarts=10, parallel=True, method_opt=TRUST_N_CG)

        eval_5 = self.sbo.evaluate_sbo_by_sample(
            candidate_point, sample, n_restarts=10, parallel=True, method_opt=DOGLEG)

        npt.assert_almost_equal(eval_4['max'], eval_3['max'], decimal=5)
        npt.assert_almost_equal(eval_4['optimum'], eval_3['optimum'], decimal=3)

        npt.assert_almost_equal(eval_5['max'], eval_3['max'], decimal=5)
        npt.assert_almost_equal(eval_5['optimum'], eval_3['optimum'], decimal=3)

    def test_evaluate_sbo_mc(self):
        warnings.filterwarnings("ignore")

        spec = {
            'dim_x': 1,
            'choose_noise': True,
            'bounds_domain_x': [self.bounds_domain_x],
            'number_points_each_dimension': [1000],
            'problem_name': 'a',
        }

        domain = DomainService.from_dict(spec)
        sbo = SBO(self.gp, np.array(domain.discretization_domain_x))

        np.random.seed(1)
        point = np.array([[52.5, 0]])
        n_samples = 50
        n_restarts = 30

        value = sbo.evaluate(point)

        value_2 = sbo.evaluate_mc(point, n_samples, n_restarts=n_restarts, random_seed=2,
                                  parallel=True)

        npt.assert_almost_equal(value, value_2['value'], decimal=2)

        np.random.seed(1)

        n_samples = 50
        n_restarts = 50
        sbo.samples = None
        sbo.optimal_samples = {}
        sbo.starting_points_sbo = None

        point = np.array([[80.5, 0]])
        value_2 = sbo.evaluate_mc(point, n_samples, n_restarts=n_restarts, random_seed=1,
                                  parallel=True)
        value = sbo.evaluate(point)
        npt.assert_almost_equal(value_2['value'], value, decimal=3)

        assert value <= value_2['value'] + 1.96 * value_2['std']
        assert value >= value_2['value'] - 1.96 * value_2['std']


    def test_evaluate_gradient_sbo(self):

        candidate = np.array([[52.5, 0]])
        np.random.seed(1)
        grad = self.sbo.evaluate_gradient(candidate)

        n_samples = 50
        n_restarts = 500

        np.random.seed(1)
        grad_mc = self.sbo.gradient_mc(candidate, random_seed=1, n_samples=n_samples,
                                       n_best_restarts=10, n_restarts=n_restarts)

        npt.assert_almost_equal(grad, grad_mc['gradient'], decimal=2)


    def test_evaluate_grad_cache(self):
        candidate = np.array([[52.5, 0]])
        n_samples = 10
        n_restarts = 2
        np.random.seed(1)
        grad_mc = self.sbo.gradient_mc(candidate, random_seed=1, n_samples=n_samples,
                                       n_restarts=n_restarts)

        self.sbo.clean_cache()

        self.sbo.evaluate_mc(candidate, n_samples, n_restarts=n_restarts, random_seed=1,
                        parallel=True)
        grad_mc_2 = self.sbo.gradient_mc(candidate, random_seed=1, n_samples=n_samples,
                                       n_restarts=n_restarts)


        npt.assert_almost_equal(grad_mc_2['gradient'], grad_mc['gradient'], decimal=4)
        npt.assert_almost_equal(grad_mc_2['std'], grad_mc['std'], decimal=5)

    def test_optimize_sbo_mc(self):
        warnings.filterwarnings("ignore")

        spec = {
            'dim_x': 1,
            'choose_noise': True,
            'bounds_domain_x': [self.bounds_domain_x],
            'number_points_each_dimension': [100],
            'problem_name': 'a',
        }

        domain = DomainService.from_dict(spec)
        self.sbo_med.discretization = np.array(domain.discretization_domain_x)

        val = self.sbo_med.optimize(random_seed=1, parallel=False, n_restarts=1)

        val_2 = self.sbo_med.optimize(monte_carlo=True, n_samples=2, n_restarts_mc=2,
                                      random_seed=1, parallel=False, n_restarts=1, maxepoch=20,
                                      **{'factr':1e12,'maxiter':100})
        npt.assert_almost_equal(val['solution'], val_2['solution'], decimal=2)

    def test_optimize_sbo_mc_diff_parameters(self):
        np.random.seed(1)
        val = self.sbo_med.optimize(monte_carlo=True, n_samples=2, n_restarts_mc=2,
                               random_seed=1, parallel=False, n_restarts=1, maxepoch=20,
                                    **{'factr':1e12,'maxiter':100})
        npt.assert_almost_equal(val['optimal_value'], 1923.361435578631, decimal=4)
        npt.assert_almost_equal(val['gradient'], np.array([ -0.0015901,  0.        ]))
        npt.assert_almost_equal(val['solution'], np.array([ 99.990081,   0.  ]))

        # assert 1 ==2

    def test_objective_voi_model_params(self):
        warnings.filterwarnings("ignore")

        spec = {
            'dim_x': 1,
            'choose_noise': True,
            'bounds_domain_x': [self.bounds_domain_x],
            'number_points_each_dimension': [1000],
            'problem_name': 'a',
        }

        domain = DomainService.from_dict(spec)
        sbo = SBO(self.gp, np.array(domain.discretization_domain_x))

        np.random.seed(1)
        point = np.array([[52.5, 0]])
        n_samples = 50
        n_restarts = 30

        value = sbo.evaluate(point)

        point = np.array([[52.5, 0]])



        value_2 = sbo.objective_voi(point[0, :], False, 1, 1, 0, 0, None,
                                    *(1.0, 5.0, np.array([50.0, 9.6, -3.0, -0.1])))

        self.gp.gp.var_noise.value[0] = 1.0
        self.gp.gp.mean.value[0] = 5.0
        self.gp.gp.kernel.update_value_parameters(np.array([50.0, 9.6, -3.0, -0.1]))

        value_3 = sbo.evaluate(point)

        assert value_2 == value_3


    def test_objective_voi_model_params_mc(self):
        warnings.filterwarnings("ignore")

        spec = {
            'dim_x': 1,
            'choose_noise': True,
            'bounds_domain_x': [self.bounds_domain_x],
            'number_points_each_dimension': [1000],
            'problem_name': 'a',
        }

        domain = DomainService.from_dict(spec)
        sbo = SBO(self.gp, np.array(domain.discretization_domain_x))

        np.random.seed(1)
        point = np.array([[52.5, 0]])
        n_samples = 50
        n_restarts = 30

        value = sbo.objective_voi(point[0, :], True, n_samples, n_restarts, 0, 0, None,
                                  *(1.0, 5.0, np.array([50.0, 9.6, -3.0, -0.1])),
                                  **{'factr':1e12,'maxiter':10})

        value_1 = sbo.objective_voi(point[0, :], True, n_samples, n_restarts, 0, 0, None,
                                    **{'factr':1e12,'maxiter':10})


        self.gp.gp.var_noise.value[0] = 1.0
        self.gp.gp.mean.value[0] = 5.0
        self.gp.gp.kernel.update_value_parameters(np.array([50.0, 9.6, -3.0, -0.1]))

        np.random.seed(1)
        value_2 = sbo.objective_voi(point[0, :], True, n_samples, n_restarts, 0, 0, None,
                                    **{'factr':1e12,'maxiter':10})

        npt.assert_almost_equal(value_2, value)

    def test_evaluate_gradient_sbo_params(self):

        candidate = np.array([[52.5, 0]])

        grad_1 = self.sbo.grad_obj_voi(candidate[0, :], False, 1, 1, 0, 0, None,
                                    *(1.0, 5.0, np.array([50.0, 9.6, -3.0, -0.1])))

        grad = self.sbo.grad_obj_voi(candidate[0, :])

        self.gp.gp.var_noise.value[0] = 1.0
        self.gp.gp.mean.value[0] = 5.0
        self.gp.gp.kernel.update_value_parameters(np.array([50.0, 9.6, -3.0, -0.1]))

        grad_2 = self.sbo.grad_obj_voi(candidate[0, :])


        assert np.all(grad_1 == grad_2)

    def test_evaluate_gradient_sbo_params_mc(self):
        warnings.filterwarnings("ignore")
        n_samples = 50
        n_restarts = 10

        candidate = np.array([[52.5, 0]])

        np.random.seed(1)
        grad_1 = self.sbo.grad_obj_voi(candidate[0, :], True, n_samples, n_restarts, 0, 0, None,
                                    *(1.0, 5.0, np.array([50.0, 9.6, -3.0, -0.1])))

        grad = self.sbo.grad_obj_voi(candidate[0, :], True, n_samples, n_restarts, 0, 0)

        np.random.seed(1)

        self.gp.gp.var_noise.value[0] = 1.0
        self.gp.gp.mean.value[0] = 5.0
        self.gp.gp.kernel.update_value_parameters(np.array([50.0, 9.6, -3.0, -0.1]))

        np.random.seed(1)
        grad_2 = self.sbo.grad_obj_voi(candidate[0, :], True, n_samples, n_restarts, 0, 0)

        npt.assert_almost_equal(grad_1, grad_2, decimal=4)


    def test_combine_sbo_gradient(self):

        warnings.filterwarnings("ignore")
        n_samples = 50
        n_restarts = 10

        candidate = np.array([[52.5, 0]])

        np.random.seed(1)

        obj = self.sbo.objective_voi(candidate[0, :], True, n_samples, n_restarts, 0, 0, None,
                                    *(1.0, 5.0, np.array([50.0, 9.6, -3.0, -0.1])))

        grad = self.sbo.grad_obj_voi(candidate[0, :], True, n_samples, n_restarts, 0, 0, None,
                                    *(1.0, 5.0, np.array([50.0, 9.6, -3.0, -0.1])))

        self.sbo.clean_cache()
        np.random.seed(1)
        grad_2 = self.sbo.grad_obj_voi(candidate[0, :], True, n_samples, n_restarts, 0, 0, None,
                                    *(1.0, 5.0, np.array([50.0, 9.6, -3.0, -0.1])))
        npt.assert_almost_equal(grad, grad_2, decimal=4)

    def test_evaluate_sample_sbo_with_best_restarts(self):
        args = (self.sbo, )
        point = [np.array([[ 9.76619979]]),np.array([[52.5, 0]]), -1.2831193615780914]
        val = wrapper_evaluate_sample(point, *args)
        self.sbo.clean_cache()
        val_2 = self.sbo.evaluate_sample(np.array([[ 9.76619979]]), np.array([[52.5, 0]]),
                                         -1.2831193615780914)
        npt.assert_almost_equal(val, val_2, decimal=5)

    def test_evaluate_sbo_sample_parameters(self):

        warnings.filterwarnings("ignore")
        n_samples = 50
        n_restarts = 10
        n_best_restarts_mc = 2
        opt_params_mc = {'factr':1e12, 'maxiter':10}
        candidate = np.array([[52.5, 0]])
        n_samples_parameters = 2
        monte_carlo = True

        np.random.seed(1)
        self.sbo.bq.gp.sample_parameters(n_samples_parameters)

        args = (self.sbo, monte_carlo, n_samples, n_restarts, n_best_restarts_mc, opt_params_mc, 0,
                n_samples_parameters, None)
        # TODO: THINK IN A GOOD TEST. NOW IT ONLY TESTS THAT IT RUNS
        np.random.seed(1)
        obj = wrapper_objective_voi(candidate[0, :], *args)

        np.random.seed(1)
        grad = wrapper_gradient_voi(candidate[0, :], *args)
        np.random.seed(1)

        self.sbo.samples = None
        self.sbo.optimal_samples = {}
        self.sbo.starting_points_sbo = None

        np.random.seed(1)
        answer = self.sbo.optimize(start=None, random_seed=1, parallel=True, monte_carlo=True,
                                   n_samples=2, n_restarts_mc=10, n_best_restarts_mc=5,
                                   n_restarts=3, n_best_restarts=1, start_ei=True, maxepoch=20,
                                   n_samples_parameters=2, compute_max_mean_bayesian=True,
                                   start_new_chain=False,
                                   **{'factr': 1e12, 'maxiter': 10})
        npt.assert_almost_equal(obj, np.array([ -0.5185451893015001]), decimal=5)
        npt.assert_almost_equal(grad, np.array([ 0.00054018, 0]))
        npt.assert_almost_equal(answer['optimal_value'], 0.1124846550005846, decimal=2)


    def test_evaluate_gradient_given_sample_given_parameters(self):
        candidate = np.array([[52.5, 0]])
        np.random.seed(1)

        n_samples = 5
        parameters = np.array([1.0, 5.0, 50.0, 9.6, -3.0, -0.1])

        np.random.seed(1)
        grad_1 = self.sbo_med.grad_obj_voi(candidate[0, :], True, n_samples, 10, 0, 0, None,
                                    *(1.0, 5.0, np.array([50.0, 9.6, -3.0, -0.1])),
                                       **{'factr': 1e12, 'maxiter': 10})

        samples = self.sbo_med.samples
        values = []

        np.random.seed(1)
        for sample in samples:
            value = self.sbo_med.evaluate_gradient_given_sample_given_parameters(
                candidate, sample, parameters, parallel=False, **{'factr': 1e12, 'maxiter': 10})
            values.append(value)

        npt.assert_almost_equal(np.mean(values, axis=0)[0, :], grad_1)

    def test_evaluate_mc_bayesian_candidate_points(self):
        candidate_points = np.array([[52.5, 0], [42.5, 1]])
        np.random.seed(1)
        n_samples_parameters = 2
        n_samples = 5
        compute_max_mean = False
        n_restarts = 10

        self.sbo_med.bq.gp.sample_parameters(n_samples_parameters)

        np.random.seed(1)
        values = self.sbo_med.evaluate_mc_bayesian_candidate_points(
            candidate_points, n_samples_parameters, n_samples, n_restarts=n_restarts,
            n_best_restarts=3, compute_max_mean=compute_max_mean, compute_gradient=True,
            **{'factr': 1e12, 'maxiter': 10})

        self.sbo_med.clean_cache()

        np.random.seed(1)

        samples, start = self.sbo_med.generate_samples_starting_points_evaluate_mc(
            n_samples, n_restarts, cache=True)
        evals = []
        gradients = []
        for i in xrange(2):
            val = self.sbo_med.evaluate_mc_bayesian(
                candidate_points[i:i+1,:], n_samples_parameters, n_samples, n_restarts=n_restarts,
                n_best_restarts=3, n_threads=0, compute_max_mean=compute_max_mean,
                **{'factr': 1e12, 'maxiter': 10})
            evals.append(val)

            grad = self.sbo_med.evaluate_gradient_mc_bayesian(
                candidate_points[i:i+1,:], n_samples_parameters, n_samples, n_restarts=n_restarts,
                n_best_restarts=3, n_threads=0, compute_max_mean=compute_max_mean,
                **{'factr': 1e12, 'maxiter': 10}
            )

            gradients.append(grad)

        evals = np.array(evals)
        gradients = np.array(gradients)
        npt.assert_almost_equal(evals, values['evaluations'])
        npt.assert_almost_equal(gradients, values['gradient'])

    def test_evaluate_mc_bayesian_candidate_points_no_restarts(self):
        candidate_points = np.array([[52.5, 0], [42.5, 1]])
        np.random.seed(1)
        n_samples_parameters = 5
        n_samples = 10
        compute_max_mean = False
        n_restarts = 10

        self.sbo_med.bq.gp.sample_parameters(n_samples_parameters)

        np.random.seed(1)
        values = self.sbo_med.evaluate_mc_bayesian_candidate_points_no_restarts(
            candidate_points, n_samples_parameters, n_samples, n_restarts=n_restarts,
            compute_max_mean=compute_max_mean, compute_gradient=True)
        self.sbo_med.clean_cache()
        values_2 = self.sbo_med.evaluate_mc_bayesian_candidate_points(
            candidate_points, n_samples_parameters, n_samples, n_restarts=n_restarts,
            n_best_restarts=3, compute_max_mean=compute_max_mean, compute_gradient=True,
            **{'factr': 1e12, 'maxiter': 10})

        npt.assert_almost_equal(values['evaluations'], values_2['evaluations'], decimal=4)


    def test_evaluate_hessian_sample(self):
        point = np.array([[49.2]])
        candidate_point = np.array([[52.5, 0]])
        np.random.seed(1)
        sample = 0.5


        gradient = self.sbo.evaluate_hessian_sample(point, candidate_point, sample)

        dh = 0.1
        finite_diff = FiniteDifferences.second_order_central(
            lambda point_: self.sbo.evaluate_sample(
                point_.reshape((1, len(point_))), candidate_point, sample),
            np.array([49.2]), np.array([dh]))

        npt.assert_almost_equal(finite_diff[(0, 0)], gradient, decimal=3)

        val = self.sbo.evaluate_sample(point, candidate_point, sample)

        sample = -0.8
        point = np.array([[10.2]])
        gradient = self.sbo.evaluate_hessian_sample(point, candidate_point, sample)

        dh = 0.1
        finite_diff = FiniteDifferences.second_order_central(
            lambda point_: self.sbo.evaluate_sample(
                point_.reshape((1, len(point_))), candidate_point, sample),
            np.array([10.2]), np.array([dh]))

        npt.assert_almost_equal(finite_diff[(0, 0)], gradient, decimal=3)
        np.random.seed(1)
        sample = -5.1
        point = np.array([[10.2]])
        gradient = self.sbo.evaluate_hessian_sample(point, candidate_point, sample)

        dh = 2.0
        finite_diff = FiniteDifferences.second_order_central(
            lambda point_: self.sbo.evaluate_sample(
                point_.reshape((1, len(point_))), candidate_point, sample),
            np.array([10.2]), np.array([dh]))

        npt.assert_almost_equal(finite_diff[(0, 0)], gradient, decimal=3)

    def test_evaluate_hessian_sample_2(self):
        spec = RunSpecEntity.from_json('movies_50.json')

        gp_model = GPFittingService.from_dict(spec)

        domain = DomainService.from_dict(spec)

        x_domain = spec.get('x_domain')
        distribution = spec.get('distribution')
        parameters_distribution = spec.get('parameters_distribution')
        quadrature = BayesianQuadrature(gp_model, x_domain, distribution,
                                        parameters_distribution=parameters_distribution)

        sbo = SBO(quadrature, np.array(domain.discretization_domain_x))

        sample = 0.5
        candidate_point = np.array([[1.42220760e-03, -9.17324806e-05, 9.87682472e-05,
                           1.00579926e-05, 0.00000000e+00]])
        point = np.array([[0.05, 0.1, 5.0, 10.0]])

        hessian = sbo.evaluate_hessian_sample(point, candidate_point, sample)

        dh = 0.01
        finite_diff = FiniteDifferences.second_order_central(
            lambda point_: sbo.evaluate_sample(
                point_.reshape((1, len(point_))), candidate_point, sample),
            point[0,:], np.array([dh]))

        for i in xrange(4):
            for j in xrange(4):
                npt.assert_almost_equal(finite_diff[(i, j)], hessian[i,j], decimal=3)
