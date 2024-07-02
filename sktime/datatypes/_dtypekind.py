from enum import IntEnum

import numpy as np
import pandas as pd
from pandas.api.types import (
    is_bool_dtype,
    is_datetime64_any_dtype,
    is_float_dtype,
    is_signed_integer_dtype,
    is_string_dtype,
    is_unsigned_integer_dtype,
)


class DtypeKind(IntEnum):
    """
    Integer enum for data types.

    Attributes
    ----------
    INT : int
        Matches to signed integer data type.
    UINT : int
        Matches to unsigned integer data type.
    FLOAT : int
        Matches to floating point data type.
    BOOL : int
        Matches to boolean data type.
    STRING : int
        Matches to string data type (UTF-8 encoded).
    DATETIME : int
        Matches to datetime data type.
    CATEGORICAL : int
        Matches to categorical data type.
    """

    INT = 0
    UINT = 1
    FLOAT = 2
    BOOL = 20
    STRING = 21  # UTF-8
    DATETIME = 22
    CATEGORICAL = 23


def _pandas_dtype_to_kind(col_dtypes):
    for i, dtype in enumerate(col_dtypes):
        if is_float_dtype(dtype):
            col_dtypes[i] = DtypeKind.FLOAT
        elif is_signed_integer_dtype(dtype):
            col_dtypes[i] = DtypeKind.INT
        elif is_unsigned_integer_dtype(dtype):
            col_dtypes[i] = DtypeKind.UINT
        elif dtype == "object" or dtype == "category":
            col_dtypes[i] = DtypeKind.CATEGORICAL
        elif is_bool_dtype(dtype):
            col_dtypes[i] = DtypeKind.BOOL
        elif is_datetime64_any_dtype(dtype):
            col_dtypes[i] = DtypeKind.DATETIME
        elif is_string_dtype(dtype):
            col_dtypes[i] = DtypeKind.STRING
    return col_dtypes


# function for series scitype
def _get_series_dtypekind(obj, mtype):
    if mtype == np.ndarray:
        if len(obj.shape) == 2:
            return [DtypeKind.FLOAT] * obj.shape[1]
        else:
            return [DtypeKind.FLOAT]
    elif mtype == pd.Series:
        col_dtypes = [obj.dtypes]
    elif mtype == pd.DataFrame:
        col_dtypes = obj.dtypes.to_list()

    col_DtypeKinds = _pandas_dtype_to_kind(col_dtypes)

    return col_DtypeKinds


def _get_panel_dtypekind(obj, mtype):
    if mtype == "numpy3D":
        return [DtypeKind.FLOAT] * obj.shape[1]
    elif mtype == "numpyflat":
        return [DtypeKind.FLOAT]
    elif mtype == "df-list":
        return _get_series_dtypekind(obj[0], pd.DataFrame)
    elif mtype == "pd-multiindex":
        col_dtypes = obj.dtypes.to_list()
    elif mtype == "nested_univ":
        col_names = obj.columns.to_list()
        col_dtypes = [obj[col][0].dtype for col in col_names]

    col_DtypeKinds = _pandas_dtype_to_kind(col_dtypes)

    return col_DtypeKinds


# This function is to broadly classify all dtypekinds into CATEGORICAL or FLOAT
def _get_feature_kind(col_dtypekinds):
    feature_kind_map = {
        DtypeKind.CATEGORICAL: DtypeKind.CATEGORICAL,
        DtypeKind.STRING: DtypeKind.CATEGORICAL,
        DtypeKind.BOOL: DtypeKind.CATEGORICAL,
        DtypeKind.DATETIME: DtypeKind.CATEGORICAL,
        DtypeKind.FLOAT: DtypeKind.FLOAT,
        DtypeKind.INT: DtypeKind.FLOAT,
        DtypeKind.UINT: DtypeKind.FLOAT,
    }

    feature_kind = []
    for kind in col_dtypekinds:
        feature_kind.append(feature_kind_map[kind])

    return feature_kind
