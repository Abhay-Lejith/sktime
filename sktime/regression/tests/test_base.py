"""Unit tests for regression base class functionality."""

__author__ = ["ksharma6"]

import pickle

import numpy as np
import pandas as pd
import pytest

from sktime.regression.base import BaseRegressor
from sktime.regression.deep_learning.base import BaseDeepRegressor
from sktime.regression.distance_based import KNeighborsTimeSeriesRegressor
from sktime.regression.dummy import DummyRegressor
from sktime.utils._testing.panel import (
    _make_panel,
    _make_regression_y,
    make_regression_problem,
)
from sktime.utils.validation._dependencies import _check_soft_dependencies


class _DummyRegressor(BaseRegressor):
    """Dummy regressor for testing base class fit/predict."""

    def _fit(self, X, y):
        """Fit dummy."""
        return self

    def _predict(self, X):
        """Predict dummy."""
        return self


class _DummyComposite(_DummyRegressor):
    """Dummy regressor for testing base class fit/predict."""

    def __init__(self, foo):
        self.foo = foo


class _DummyDeepRegressorEmpty(BaseDeepRegressor):
    """Dummy Deep Regressor for testing empty base deep class save utilities."""

    def __init__(self):
        super().__init__()

    def build_model(self, input_shape, **kwargs):
        return None

    def _fit(self, X, y):
        return self


class _DummyDeepRegressorFull(BaseDeepRegressor):
    """Dummy Deep Regressor to test serialization capabilities."""

    def __init__(
        self,
        optimizer,
    ):
        super().__init__()
        self.optimizer = optimizer

    def build_model(self, input_shape, **kwargs):
        return None

    def _fit(self, X, y):
        return self


class _DummyHandlesAllInput(BaseRegressor):
    """Dummy regressor for testing base class fit/predict."""

    _tags = {
        "capability:multivariate": True,
        "capability:unequal_length": True,
        "capability:missing_values": True,
    }

    def _fit(self, X, y):
        """Fit dummy."""
        return self

    def _predict(self, X):
        """Predict dummy."""
        return self


class _DummyConvertPandas(BaseRegressor):
    """Dummy regressor for testing base class fit/predict."""

    _tags = {
        "X_inner_mtype": "nested_univ",  # which type do _fit/_predict, support for X?
    }

    def _fit(self, X, y):
        """Fit dummy."""
        return self

    def _predict(self, X):
        """Predict dummy."""
        return self


multivariate_message = r"multivariate series"
missing_message = r"missing values"
unequal_message = r"unequal length series"


def test_base_regressor_fit():
    """Test function for the BaseRegressor class fit.

    Test fit. It should:
    1. Work with 2D, 3D and DataFrame for X and nparray for y.
    2. Record the fit time.
    3. Have self.n_jobs set or throw  an exception if the regressor can
    multithread.
    4. Set the class dictionary correctly.
    5. Set is_fitted after a call to _fit.
    6. Return self.
    """
    dummy = _DummyRegressor()
    cases = 5
    length = 10
    test_X1 = np.random.uniform(-1, 1, size=(cases, length))
    test_X2 = np.random.uniform(-1, 1, size=(cases, 2, length))
    test_X3 = _create_example_dataframe(cases=cases, dimensions=1, length=length)
    test_X4 = _create_example_dataframe(cases=cases, dimensions=3, length=length)
    test_y1 = np.random.randint(0, 2, size=(cases))
    test_y2 = pd.DataFrame({"0": [1] * cases, "1": [0] * cases})
    result = dummy.fit(test_X1, test_y1)
    assert result is dummy
    result = dummy.fit(test_X3, test_y2)
    assert result is dummy
    with pytest.raises(ValueError, match=multivariate_message):
        result = dummy.fit(test_X2, test_y1)
    assert result is dummy
    result = dummy.fit(test_X3, test_y1)
    assert result is dummy
    with pytest.raises(ValueError, match=multivariate_message):
        result = dummy.fit(test_X4, test_y1)
    assert result is dummy


TF = [True, False]


@pytest.mark.parametrize("missing", TF)
@pytest.mark.parametrize("multivariate", TF)
@pytest.mark.parametrize("unequal", TF)
def test_check_capabilities(missing, multivariate, unequal):
    """Test the checking of capabilities.

    There are eight different combinations to be tested with a regressor that can
    handle it and that cannot. Obvs could loop, but I think its clearer to just
    explicitly test;
    """
    X_metadata = {
        "has_nans": missing,
        "is_univariate": not multivariate,
        "is_equal_length": not unequal,
    }
    handles_none = _DummyRegressor()
    handles_none_composite = _DummyComposite(_DummyRegressor())

    # checks that errors are raised
    if missing:
        with pytest.raises(ValueError, match=missing_message):
            handles_none._check_capabilities(X_metadata)
    if multivariate:
        with pytest.raises(ValueError, match=multivariate_message):
            handles_none._check_capabilities(X_metadata)
    if unequal:
        with pytest.raises(ValueError, match=unequal_message):
            handles_none._check_capabilities(X_metadata)
    if not missing and not multivariate and not unequal:
        handles_none._check_capabilities(X_metadata)

    if missing:
        with pytest.warns(UserWarning, match=missing_message):
            handles_none_composite._check_capabilities(X_metadata)
    if multivariate:
        with pytest.warns(UserWarning, match=multivariate_message):
            handles_none_composite._check_capabilities(X_metadata)
    if unequal:
        with pytest.warns(UserWarning, match=unequal_message):
            handles_none_composite._check_capabilities(X_metadata)
    if not missing and not multivariate and not unequal:
        handles_none_composite._check_capabilities(X_metadata)

    handles_all = _DummyHandlesAllInput()
    handles_all._check_capabilities(X_metadata)


def test_convert_input():
    """Test the conversions from dataframe to numpy.

    1. Pass a 2D numpy X, get a 3D numpy X
    2. Pass a 3D numpy X, get a 3D numpy X
    3. Pass a pandas numpy X, equal length, get a 3D numpy X
    4. Pass a pd.Series y, get a pd.Series back
    5. Pass a np.ndarray y, get a pd.Series back
    """

    def _internal_convert(X, y=None):
        return BaseRegressor._internal_convert(None, X, y)

    cases = 5
    length = 10
    test_X1 = np.random.uniform(-1, 1, size=(cases, length))
    test_X2 = np.random.uniform(-1, 1, size=(cases, 2, length))
    tester = _DummyRegressor()
    tempX = tester._convert_X(test_X2, "numpy3D")
    assert tempX.shape[0] == cases and tempX.shape[1] == 2 and tempX.shape[2] == length
    instance_list = []
    for _ in range(0, cases):
        instance_list.append(pd.Series(np.random.randn(10)))
    test_X3 = _create_example_dataframe(cases=cases, dimensions=1, length=length)
    test_X4 = _create_example_dataframe(cases=cases, dimensions=3, length=length)
    tempX = tester._convert_X(test_X3, "nested_univ")
    assert tempX.shape[0] == cases and tempX.shape[1] == 1 and tempX.shape[2] == length
    tempX = tester._convert_X(test_X4, "nested_univ")
    assert tempX.shape[0] == cases and tempX.shape[1] == 3 and tempX.shape[2] == length
    tester = _DummyConvertPandas()
    tempX = tester._convert_X(test_X2, "numpy3D")
    assert isinstance(tempX, pd.DataFrame)
    assert tempX.shape[0] == cases
    assert tempX.shape[1] == 2
    test_y1 = np.random.randint(0, 1, size=(cases))
    test_y1 = pd.Series(test_y1)
    tempX, tempY = _internal_convert(test_X1, test_y1)
    assert isinstance(tempY, pd.Series)
    assert isinstance(tempX, np.ndarray)
    assert tempX.ndim == 3


def test__check_regressor_input():
    """Test for valid estimator format.

    1. Test correct: X: np.array of 2 and 3 dimensions vs y:np.array and np.Series
    2. Test correct: X: pd.DataFrame with 1 and 3 cols vs y:np.array and np.Series
    3. Test incorrect: X with fewer cases than y
    4. Test incorrect: y as a list
    5. Test incorrect: too few cases or too short a series
    """
    clf = _DummyRegressor()

    def _check_regressor_input(X, y=None, enforce_min_instances=1):
        return clf._check_input(X, y, enforce_min_instances)

    # 1. Test correct: X: np.array of 2 and 3 dimensions vs y:np.array and np.Series
    test_X1 = np.random.uniform(-1, 1, size=(5, 10))
    test_X2 = np.random.uniform(-1, 1, size=(5, 2, 10))
    test_y1 = np.random.randint(0, 1, size=5)
    test_y2 = pd.Series(np.random.randn(5))
    _check_regressor_input(test_X2)
    _check_regressor_input(test_X2, test_y1)
    _check_regressor_input(test_X2, test_y2)
    # 2. Test correct: X: pd.DataFrame with 1 (univariate) and 3 cols(multivariate) vs
    # y:np.array and np.Series
    test_X3 = _create_nested_dataframe(5, 1, 10)
    test_X4 = _create_nested_dataframe(5, 3, 10)
    _check_regressor_input(test_X3, test_y1)
    _check_regressor_input(test_X4, test_y1)
    _check_regressor_input(test_X3, test_y2)
    _check_regressor_input(test_X4, test_y2)
    # 3. Test incorrect: X with fewer cases than y
    test_X5 = np.random.uniform(-1, 1, size=(3, 4, 10))
    with pytest.raises(ValueError, match=r".*Mismatch in number of cases*."):
        _check_regressor_input(test_X5, test_y1)
    # 4. Test incorrect data type: y is a List
    test_y3 = [1, 2, 3, 4, 5]
    with pytest.raises(TypeError, match="must be in an sktime compatible format"):
        _check_regressor_input(test_X1, test_y3)
    # 5. Test incorrect: too few cases or too short a series
    with pytest.raises(ValueError, match=r".*Minimum number of cases required*."):
        _check_regressor_input(test_X2, test_y1, enforce_min_instances=6)


def _create_example_dataframe(cases=5, dimensions=1, length=10):
    """Create a simple data frame set of time series (X) for testing."""
    test_X = pd.DataFrame(dtype=np.float32)
    for i in range(0, dimensions):
        instance_list = []
        for _ in range(0, cases):
            instance_list.append(pd.Series(np.random.randn(length)))
        test_X["dimension_" + str(i)] = instance_list
    return test_X


def _create_nested_dataframe(cases=5, dimensions=1, length=10):
    testy = pd.DataFrame(dtype=np.float32)
    for i in range(0, dimensions):
        instance_list = []
        for _ in range(0, cases):
            instance_list.append(pd.Series(np.random.randn(length)))
        testy["dimension_" + str(i + 1)] = instance_list
    return testy


def _create_unequal_length_nested_dataframe(cases=5, dimensions=1, length=10):
    testy = pd.DataFrame(dtype=np.float32)
    for i in range(0, dimensions):
        instance_list = []
        for _ in range(0, cases - 1):
            instance_list.append(pd.Series(np.random.randn(length)))
        instance_list.append(pd.Series(np.random.randn(length - 1)))
        testy["dimension_" + str(i + 1)] = instance_list

    return testy


MTYPES = ["numpy3D", "pd-multiindex", "df-list", "numpyflat", "nested_univ"]


@pytest.mark.parametrize("mtype", MTYPES)
def test_input_conversion_fit_predict(mtype):
    """Test that base class lets all Panel mtypes through."""
    y = _make_regression_y()
    X = _make_panel(return_mtype=mtype)

    clf = DummyRegressor()
    clf.fit(X, y)
    clf.predict(X)

    clf = _DummyConvertPandas()
    clf.fit(X, y)
    clf.predict(X)


@pytest.mark.parametrize("method", ["predict"])
def test_predict_single_class(method):
    """Test return of predict in case only single class seen in fit."""
    X, y = make_regression_problem()
    y[:] = 42
    n_instances = 10
    X_test = X[:n_instances]

    clf = KNeighborsTimeSeriesRegressor()

    clf.fit(X, y)
    y_pred = getattr(clf, method)(X_test)

    if method == "predict":
        assert isinstance(y_pred, np.ndarray)
        assert y_pred.ndim == 1
        assert y_pred.shape == (n_instances,)
        assert all(list(y_pred == 42))


@pytest.mark.skipif(
    not _check_soft_dependencies("tensorflow", severity="none"),
    reason="skip test if required soft dependency not available",
)
def test_deep_estimator_empty():
    """Check if serialization works for empty dummy."""
    empty_dummy = _DummyDeepRegressorEmpty()
    serialized_empty = pickle.dumps(empty_dummy)
    deserialized_empty = pickle.loads(serialized_empty)
    assert empty_dummy.__dict__ == deserialized_empty.__dict__


@pytest.mark.xfail(reason="known failure, see #6153")
@pytest.mark.skipif(
    not _check_soft_dependencies("tensorflow", severity="none"),
    reason="skip test if required soft dependency not available",
)
@pytest.mark.parametrize("optimizer", [None, "adam", "object-adamax"])
def test_deep_estimator_full(optimizer):
    """Check if serialization works for full dummy."""
    from tensorflow.keras.optimizers import Adamax, Optimizer, serialize

    if optimizer == "object-adamax":
        optimizer = Adamax()

    full_dummy = _DummyDeepRegressorFull(optimizer)
    serialized_full = pickle.dumps(full_dummy)
    deserialized_full = pickle.loads(serialized_full)

    if isinstance(optimizer, Optimizer):
        # assert same configuration of optimizer
        assert serialize(full_dummy.__dict__["optimizer"]) == serialize(
            deserialized_full.__dict__["optimizer"]
        )
        assert serialize(full_dummy.optimizer) == serialize(deserialized_full.optimizer)

        # assert weights of optimizers are same
        assert (
            full_dummy.optimizer.variables() == deserialized_full.optimizer.variables()
        )

        # remove optimizers from both to do full dict check,
        # since two different objects
        del full_dummy.__dict__["optimizer"]
        del deserialized_full.__dict__["optimizer"]

    # check if components are same
    assert full_dummy.__dict__ == deserialized_full.__dict__


DUMMY_EST_PARAMETERS_FOO = [None, 10.3, "string", {"key": "value"}, lambda x: x**2]


@pytest.mark.skipif(
    not _check_soft_dependencies("cloudpickle", severity="none"),
    reason="skip test if required soft dependency not available",
)
@pytest.mark.parametrize("foo", DUMMY_EST_PARAMETERS_FOO)
def test_save_estimator_using_cloudpickle(foo):
    """Check if serialization works with cloudpickle."""
    from sktime.base._serialize import load

    est = _DummyComposite(foo)

    serialized = est.save(serialization_format="cloudpickle")
    loaded_est = load(serialized)

    if callable(foo):
        assert est.foo(2) == loaded_est.foo(2)
    else:
        assert est.foo == loaded_est.foo
