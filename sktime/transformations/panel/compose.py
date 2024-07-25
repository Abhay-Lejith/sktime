"""Meta Transformers module.

This module has meta-transformations that is build using the pre-existing
transformations as building blocks.
"""

__author__ = ["mloning", "sajaysurya", "fkiraly"]
__all__ = ["ColumnTransformer", "ColumnConcatenator"]

from warnings import warn

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer as _ColumnTransformer

from sktime.transformations.base import BaseTransformer, _PanelToPanelTransformer
from sktime.utils.dependencies import _check_soft_dependencies
from sktime.utils.multiindex import flatten_multiindex
from sktime.utils.validation.panel import check_X


class ColumnTransformer(_ColumnTransformer, _PanelToPanelTransformer):
    """Column-wise application of transformers.

    Applies transformations to columns of an array or pandas DataFrame. Simply
    takes the column transformer from sklearn
    and adds capability to handle pandas dataframe.

    This estimator allows different columns or column subsets of the input
    to be transformed separately and the features generated by each transformer
    will be concatenated to form a single feature space.
    This is useful for heterogeneous or columnar data, to combine several
    feature extraction mechanisms or transformations into a single transformer.

    Parameters
    ----------
    transformers : list of tuples
        List of (name, transformer, column(s)) tuples specifying the
        transformer objects to be applied to subsets of the data.
        name : string
            Like in Pipeline and FeatureUnion, this allows the transformer and
            its parameters to be set using ``set_params`` and searched in grid
            search.
        transformer : estimator or {"passthrough", "drop"}
            Estimator must support ``fit`` and ``transform``. Special-cased
            strings "drop" and "passthrough" are accepted as well, to
            indicate to drop the columns or to pass them through untransformed,
            respectively.
        column(s) : str or int, array-like of string or int, slice, boolean
        mask array or callable
            Indexes the data on its second axis. Integers are interpreted as
            positional columns, while strings can reference DataFrame columns
            by name.  A scalar string or int should be used where
            ``transformer`` expects X to be a 1d array-like (vector),
            otherwise a 2d array will be passed to the transformer.
            A callable is passed the input data ``X`` and can return any of the
            above.
    remainder : {"drop", "passthrough"} or estimator, default "drop"
        By default, only the specified columns in ``transformations`` are
        transformed and combined in the output, and the non-specified
        columns are dropped. (default of ``"drop"``).
        By specifying ``remainder="passthrough"``, all remaining columns that
        were not specified in ``transformations`` will be automatically passed
        through. This subset of columns is concatenated with the output of
        the transformations.
        By setting ``remainder`` to be an estimator, the remaining
        non-specified columns will use the ``remainder`` estimator. The
        estimator must support ``fit`` and ``transform``.
    sparse_threshold : float, default = 0.3
        If the output of the different transformations contains sparse matrices,
        these will be stacked as a sparse matrix if the overall density is
        lower than this value. Use ``sparse_threshold=0`` to always return
        dense.  When the transformed output consists of all dense data, the
        stacked result will be dense, and this keyword will be ignored.
    n_jobs : int or None, optional (default=None)
        Number of jobs to run in parallel.
        ``None`` means 1 unless in a :obj:`joblib.parallel_backend` context.
        ``-1`` means using all processors.
    transformer_weights : dict, optional
        Multiplicative weights for features per transformer. The output of the
        transformer is multiplied by these weights. Keys are transformer names,
        values the weights.
    preserve_dataframe : boolean
        If True, pandas dataframe is returned.
        If False, numpy array is returned.

    Attributes
    ----------
    transformers_ : list
        The collection of fitted transformations as tuples of
        (name, fitted_transformer, column). ``fitted_transformer`` can be an
        estimator, "drop", or "passthrough". In case there were no columns
        selected, this will be the unfitted transformer.
        If there are remaining columns, the final element is a tuple of the
        form:
        ("remainder", transformer, remaining_columns) corresponding to the
        ``remainder`` parameter. If there are remaining columns, then
        ``len(transformers_)==len(transformations)+1``, otherwise
        ``len(transformers_)==len(transformations)``.
    named_transformers_ : Bunch object, a dictionary with attribute access
        Read-only attribute to access any transformer by given name.
        Keys are transformer names and values are the fitted transformer
        objects.
    sparse_output_ : bool
        Boolean flag indicating whether the output of ``transform`` is a
        sparse matrix or a dense numpy array, which depends on the output
        of the individual transformations and the ``sparse_threshold`` keyword.
    """

    _tags = {
        "authors": ["mloning", "sajaysurya", "fkiraly"],
        "python_dependencies": ["scipy", "scikit-learn<1.4"],
    }

    def __init__(
        self,
        transformers,
        remainder="drop",
        sparse_threshold=0.3,
        n_jobs=1,
        transformer_weights=None,
        preserve_dataframe=True,
    ):
        self.preserve_dataframe = preserve_dataframe

        warn(
            "ColumnTransformer is not fully compliant with the sktime interface "
            "and will be replaced by sktime.transformations.ColumnEnsembleTransformer "
            "in a future version. Deprecation horizon and instructions will "
            "be added to this message, once ColumnEnsembleTransformer can replace "
            "key parameters of ColumnTransformer. If not using parameters remainder, "
            "sparse_threshold, n_jobs, transformer_weights, or preserve_dataframe, "
            "ColumnTransformer can simply be replaced by ColumnEnsembleTransformer."
        )

        sklearn_lneq_14 = _check_soft_dependencies(
            "scikit-learn<1.4",
            severity="none",
            package_import_alias={"scikit-learn": "sklearn"},
        )

        if not sklearn_lneq_14:
            raise ModuleNotFoundError(
                "ColumnTransformer is not fully compliant with the sktime interface "
                "and distributed only for reasons of downwards compatibility. "
                "ColumnTransformer requires scikit-learn<1.4 "
                "to be present in the python environment, with version, "
                "due to reliance on sklearn.compose.ColumnTransformer, "
                "and is not compatible with scikit-learn>=1.4. "
                "Please use sktime.transformations.ColumnEnsembleTransformer instead, "
                "if you have scikit-learn>=1.4 installed."
            )

        super().__init__(
            transformers=transformers,
            remainder=remainder,
            sparse_threshold=sparse_threshold,
            n_jobs=n_jobs,
            transformer_weights=transformer_weights,
        )
        BaseTransformer.__init__(self)

        self._is_fitted = False

    def _hstack(self, Xs):
        """Stacks X horizontally.

        Supports input types (X): list of numpy arrays, sparse arrays and DataFrames
        """
        types = {type(X) for X in Xs}

        if self.sparse_output_:
            from scipy import sparse

            return sparse.hstack(Xs).tocsr()
        if self.preserve_dataframe and (pd.Series in types or pd.DataFrame in types):
            vars = [y for x in self.transformers for y in x[2]]
            vars_unique = len(set(vars)) == len(vars)
            names = [str(x[0]) for x in self.transformers]
            if vars_unique:
                return pd.concat(Xs, axis="columns")
            else:
                Xt = pd.concat(Xs, axis="columns", keys=names)
                Xt.columns = flatten_multiindex(Xt.columns)
                return Xt
        return np.hstack(Xs)

    def _validate_output(self, result):
        """Validate output of every transformer.

        Ensure that the output of each transformer is 2D. Otherwise hstack can raise an
        error or produce incorrect results.

        Output can also be a pd.Series which is actually a 1D
        """
        names = [
            name for name, _, _, _ in self._iter(fitted=True, replace_strings=True)
        ]
        for Xs, name in zip(result, names):
            if not (getattr(Xs, "ndim", 0) == 2 or isinstance(Xs, pd.Series)):
                raise ValueError(
                    f"The output of the '{name}' transformer should be 2D (scipy "
                    "matrix, array, or pandas DataFrame)."
                )

    @classmethod
    def get_test_params(cls):
        """Return testing parameter settings for the estimator.

        Returns
        -------
        params : dict or list of dict, default = {}
            Parameters to create testing instances of the class
            Each dict are parameters to construct an "interesting" test instance, i.e.,
            ``MyClass(**params)`` or ``MyClass(**params[i])`` creates a valid test
            instance.
            ``create_test_instance`` uses the first (or only) dictionary in ``params``
        """
        from sktime.transformations.series.exponent import ExponentTransformer

        TRANSFORMERS = [
            ("transformer1", ExponentTransformer()),
            ("transformer2", ExponentTransformer()),
        ]

        return {
            "transformers": [(name, estimator, [0]) for name, estimator in TRANSFORMERS]
        }

    def fit(self, X, y=None):
        """Fit the transformer."""
        X = check_X(X, coerce_to_pandas=True)
        super().fit(X, y)
        self._is_fitted = True
        return self

    def transform(self, X, y=None):
        """Transform the data."""
        self.check_is_fitted()
        X = check_X(X, coerce_to_pandas=True)
        return super().transform(X)

    def fit_transform(self, X, y=None):
        """Fit and transform, shorthand."""
        # Wrap fit_transform to set _is_fitted attribute
        Xt = super().fit_transform(X, y)
        self._is_fitted = True
        return Xt


class ColumnConcatenator(BaseTransformer):
    """Concatenate multivariate series to a long univariate series.

    Transformer that concatenates multivariate time series/panel data
    into single univariate time series/panel data by concatenating
    each individual series on top of each other from left to right.

    Uses pandas method stack() to do the concatenating

    Examples
    --------
    >>> from sktime.transformations.panel.compose import ColumnConcatenator # noqa: E501
    >>> import numpy as np
    >>> data = np.array([[1, 2, 3],
    ...                  [4, 5, 6],
    ...                  [7, 8, 9]])
    >>> concatenator = ColumnConcatenator()
    >>> concatenator.fit_transform(data)
    array([[1.],
           [4.],
           [7.],
           [2.],
           [5.],
           [8.],
           [3.],
           [6.],
           [9.]])

    Another example with panel data.

    >>> from sktime.utils._testing.panel import _make_panel
    >>> panel_data = _make_panel(n_columns = 2,
    ...                          n_instances = 2,
    ...                          n_timepoints = 3)
    >>> panel_data = concatenator.fit_transform(panel_data)
    """

    _tags = {
        "scitype:transform-input": "Series",
        # what is the scitype of X: Series, or Panel
        "scitype:transform-output": "Series",
        # what scitype is returned: Primitives, Series, Panel
        "scitype:instancewise": False,  # is this an instance-wise transform?
        "X_inner_mtype": ["pd-multiindex", "pd_multiindex_hier"],
        # which mtypes do _fit/_predict support for X?
        "y_inner_mtype": "None",  # which mtypes do _fit/_predict support for X?
        "fit_is_empty": True,  # is fit empty and can be skipped? Yes = True
        "capability:categorical_in_X": True,
    }

    def _transform(self, X, y=None):
        """Transform the data.

        Concatenate multivariate time series/panel data into long
        univariate time series/panel
        data by simply concatenating times series in time.

        Parameters
        ----------
        X : nested pandas DataFrame of shape [n_samples, n_features]
            Nested dataframe with time-series in cells.

        Returns
        -------
        Xt : pandas DataFrame
          Transformed pandas DataFrame with same number of rows and single
          column
        """
        Xst = pd.DataFrame(X.stack())
        Xt = Xst.swaplevel(-2, -1).sort_index().droplevel(-2)

        # the above has the right structure, but the wrong index
        # the time index is in general non-unique now, we replace it by integer index
        inst_idx = Xt.index.get_level_values(0)
        t_idx = [range(len(Xt.loc[x])) for x in inst_idx.unique()]
        t_idx = np.concatenate(t_idx)

        Xt.index = pd.MultiIndex.from_arrays([inst_idx, t_idx])
        Xt.index.names = X.index.names
        return Xt
