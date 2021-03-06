import unittest

from nose.tools import raises

from stratified_bayesian_optimization.kernels.abstract_kernel import AbstractKernel


class B(AbstractKernel):
    def __init__(self):
        super(B, self).__init__(2, 3, 2)

    @property
    def hypers(self):
        super(B, self).hypers

    def set_parameters(self,  *params):
        super(B, self).set_parameters(*params)

    def cov(self, inputs):
        super(B, self).cov(inputs)

    def cross_cov(self, inputs_1, inputs_2):
        super(B, self).cross_cov(inputs_1, inputs_2)

    def gradient_respect_parameters(self, inputs):
        super(B, self).gradient_respect_parameters(inputs)

    def grad_respect_point(self, point, inputs):
        super(B, self).grad_respect_point(point, inputs)

    def get_bounds_parameters(self):
        super(B, self).get_bounds_parameters()

    def sample_parameters(self, n_samples, random_seed):
        super(B, self).sample_parameters(n_samples, random_seed)

    def update_value_parameters(self, value):
        super(B, self).update_value_parameters(value)


class TestAbstractKernel(unittest.TestCase):

    def setUp(self):
        self.test = B()

    @raises(NotImplementedError)
    def test_hypers(self):
        self.test.hypers

    @raises(NotImplementedError)
    def test_name_parameters_as_list(self):
        self.test.name_parameters_as_list

    @raises(NotImplementedError)
    def test_set_parameters(self):
        self.test.set_parameters({'a': 2})

    @raises(NotImplementedError)
    def test_define_kernel_from_array(self):
        self.test.define_kernel_from_array(2, 2)

    @raises(NotImplementedError)
    def test_cov(self):
        self.test.cov(2)

    @raises(NotImplementedError)
    def test_cross_cov(self):
        self.test.cross_cov(2, 3)

    @raises(NotImplementedError)
    def test_gradient_respect_parameters(self):
        self.test.gradient_respect_parameters(2)

    @raises(NotImplementedError)
    def test_grad_respect_point(self):
        self.test.grad_respect_point(2, 3)

    @raises(NotImplementedError)
    def test_get_bounds_parameters(self):
        self.test.get_bounds_parameters()

    @raises(NotImplementedError)
    def test_sample_parameters(self):
        self.test.sample_parameters(2, 1)

    @raises(NotImplementedError)
    def test_update_value_parameters(self):
        self.test.update_value_parameters(2)

    @raises(NotImplementedError)
    def test_evaluate_grad_defined_by_params_respect_params(self):
        self.test.evaluate_grad_defined_by_params_respect_params(2, 3, 4)

    @raises(NotImplementedError)
    def test_hypers_as_list(self):
        self.test.hypers_as_list

    @raises(NotImplementedError)
    def test_hypers_values_as_array(self):
        self.test.hypers_values_as_array()

    @raises(NotImplementedError)
    def test_define_default_kernel(self):
        self.test.define_default_kernel(1, 1, 1, 1)

    @raises(NotImplementedError)
    def test_evaluate_cov_defined_by_params(self):
        self.test.evaluate_cov_defined_by_params(1, 1, 1)

    @raises(NotImplementedError)
    def test_compare_kernels(self):
        self.test.compare_kernels(1, 2)

    @raises(NotImplementedError)
    def test_parameters_from_list_to_dict(self):
        self.test.parameters_from_list_to_dict(1)

    @raises(NotImplementedError)
    def test_evaluate_cross_cov_defined_by_params(self):
        self.test.evaluate_cross_cov_defined_by_params(1, 1, 1, 1)

    @raises(NotImplementedError)
    def test_evaluate_grad_respect_point(self):
        self.test.evaluate_grad_respect_point(1, 1, 1, 1)
