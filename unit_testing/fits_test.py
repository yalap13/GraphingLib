import unittest

from numpy import e, exp, linspace, log, pi, random, sin

from graphinglib.data_plotting_1d import *
from graphinglib.fits import *
from graphinglib.graph_elements import *


class TestFitFromPolynomial(unittest.TestCase):
    def setUp(self):
        x = linspace(0, 3 * pi, 200)
        self.scatter_first_degree = Scatter(x, 3 * x + 2, "k", "Test Curve")
        self.scatter_second_degree = Scatter(
            x, 4 * x**2 - 3 * x - 2, "k", "Test Curve"
        )
        self.fit_first_degree = FitFromPolynomial(
            self.scatter_first_degree, 1, "k", "First degree fit"
        )
        self.fit_second_degree = FitFromPolynomial(
            self.scatter_second_degree, 2, "k", "Second degree fit"
        )

    def test_first_degree_coeffs(self):
        self.assertListEqual(
            [round(i, 5) for i in list(self.fit_first_degree.coeffs)], [2, 3]
        )

    def test_first_degree_cov(self):
        self.assertIsInstance(self.fit_first_degree.cov_matrix, np.ndarray)
        self.assertEqual(self.fit_first_degree.cov_matrix.shape, (2, 2))

    def test_first_degree_std_dev(self):
        self.assertIsInstance(self.fit_first_degree.standard_deviation, np.ndarray)
        self.assertEqual(self.fit_first_degree.standard_deviation.shape, (2,))

    def test_first_degree_string(self):
        self.assertEqual(str(self.fit_first_degree), "3.0x^1 + 2.0")

    def test_first_degree_functions(self):
        self.assertAlmostEqual(self.fit_first_degree.function(5), 17)

    def test_second_degree_coeffs(self):
        self.assertListEqual(
            [round(i, 5) for i in list(self.fit_second_degree.coeffs)], [-2, -3, 4]
        )

    def test_second_degree_cov(self):
        self.assertIsInstance(self.fit_second_degree.cov_matrix, np.ndarray)
        self.assertEqual(self.fit_second_degree.cov_matrix.shape, (3, 3))

    def test_second_degree_std_dev(self):
        self.assertIsInstance(self.fit_second_degree.standard_deviation, np.ndarray)
        self.assertEqual(self.fit_second_degree.standard_deviation.shape, (3,))

    def test_second_degree_string(self):
        self.assertEqual(str(self.fit_second_degree), "4.0x^2 - 3.0x^1 - 2.0")

    def test_second_degree_functions(self):
        self.assertAlmostEqual(round(self.fit_second_degree.function(5), 5), 83)


class TestFitFromSine(unittest.TestCase):
    def setUp(self):
        x = linspace(0, 3 * pi, 200)
        self.data = Scatter(x, 2 * sin(3 * x + 4) + 5, "k", "Data")
        self.fit = FitFromSine(
            self.data, "Sinusoidal fit", guesses=[2.09, 3.1, 4.2, 5.2]
        )

    def test_parameters(self):
        self.assertListEqual(
            [
                self.fit.amplitude,
                self.fit.frequency_rad,
                self.fit.phase,
                self.fit.vertical_shift,
            ],
            [2, 3, 4, 5],
        )

    def test_cov(self):
        self.assertIsInstance(self.fit.cov_matrix, np.ndarray)
        self.assertEqual(self.fit.cov_matrix.shape, (4, 4))

    def test_std_dev(self):
        self.assertIsInstance(self.fit.standard_deviation, np.ndarray)
        self.assertEqual(self.fit.standard_deviation.shape, (4,))

    def test_string(self):
        self.assertEqual(str(self.fit), "2.000 sin(3.000x + 4.000) + 5.000")

    def test_function(self):
        self.assertAlmostEqual(self.fit.function(17), 3.00048965)


class TestFitFromExponential(unittest.TestCase):
    def setUp(self):
        x = linspace(0, 10, 200)
        self.data = Scatter(x, 2 * exp(3 * x + 4), "Data")
        self.fit = FitFromExponential(self.data, "Sinusoidal fit")

    def test_parameters(self):
        self.assertListEqual([round(i) for i in list(self.fit.parameters)[1:]], [3, 4])

    def test_cov(self):
        self.assertIsInstance(self.fit.cov_matrix, np.ndarray)
        self.assertEqual(self.fit.cov_matrix.shape, (3, 3))

    def test_std_dev(self):
        self.assertIsInstance(self.fit.standard_deviation, np.ndarray)
        self.assertEqual(self.fit.standard_deviation.shape, (3,))

    def test_string(self):
        self.assertEqual(str(self.fit)[5:-6], " exp(3.000x + ")

    def test_function(self):
        self.assertAlmostEqual(self.fit.function(0.001), 109.524, places=3)


class TestFitFromGaussian(unittest.TestCase):
    def setUp(self) -> None:
        x = linspace(-4, 6, 1000)
        noise = 0.01 * random.rand(len(x)) - 0.005
        self.data = Scatter(x, 5 * np.exp(-(((x - 1) / 1) ** 2) / 2) + noise, "Data")
        self.fit = FitFromGaussian(self.data, "Gaussian fit")

    def test_cov(self):
        self.assertIsInstance(self.fit.cov_matrix, np.ndarray)
        self.assertEqual(self.fit.cov_matrix.shape, (3, 3))

    def test_parameters(self):
        params = [self.fit.amplitude, self.fit.mean, self.fit.standard_deviation]
        rounded_params = [round(i, 3) for i in params]
        self.assertListEqual(rounded_params, [5, 1, 1])

    def test_std_dev(self):
        self.assertIsInstance(self.fit.standard_deviation_of_fit_params, np.ndarray)
        self.assertEqual(self.fit.standard_deviation_of_fit_params.shape, (3,))

    def test_str(self):
        self.assertEqual(str(self.fit), "$\mu$ = 1.000, $\sigma$ = 1.000, $A$ = 5.000")

    def test_function(self):
        self.assertAlmostEqual(self.fit.function(3), 0.676515, places=3)


class TestFitFromSquareRoot(unittest.TestCase):
    def setUp(self) -> None:
        x = linspace(-1, 6, 1000)
        self.data = Scatter(x, 3 * np.sqrt(x + 4) + 5, "Data")
        self.fit = FitFromSquareRoot(self.data, "Square root fit")

    def test_parameters(self):
        rounded_params = [round(i, 3) for i in list(self.fit.parameters)]
        self.assertListEqual(rounded_params, [3, 4, 5])

    def test_cov(self):
        self.assertIsInstance(self.fit.cov_matrix, np.ndarray)
        self.assertEqual(self.fit.cov_matrix.shape, (3, 3))

    def test_std_dev(self):
        self.assertIsInstance(self.fit.standard_deviation, np.ndarray)
        self.assertEqual(self.fit.standard_deviation.shape, (3,))

    def test_str(self):
        self.assertEqual(str(self.fit), "3.000 sqrt(x + 4.000) + 5.000")

    def test_function(self):
        self.assertAlmostEqual(self.fit.function(3), 12.937, places=3)


class TestFitFromLog(unittest.TestCase):
    def setUp(self):
        x = linspace(0, 10, 200)
        self.data = Scatter(x, 2 * log(x + 3) + 4, "Data")
        self.fit = FitFromLog(self.data, "Logarithmic fit")

    def test_parameters(self):
        rounded_params = [round(i) for i in list(self.fit.parameters)]
        self.assertListEqual(rounded_params, [2, 3, 4])

    def test_cov(self):
        self.assertIsInstance(self.fit.cov_matrix, np.ndarray)
        self.assertEqual(self.fit.cov_matrix.shape, (3, 3))

    def test_std_dev(self):
        self.assertIsInstance(self.fit.standard_deviation, np.ndarray)
        self.assertEqual(self.fit.standard_deviation.shape, (3,))

    def test_string(self):
        self.assertEqual(str(self.fit), "2.000 log_e(x + 3.000) + 4.000")

    def test_function(self):
        self.assertAlmostEqual(self.fit.function(0.001), 6.19789, places=3)
