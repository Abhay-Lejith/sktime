"""Testing feature_kind inference with categorical data"""

__author__ = ["Abhay-Lejith"]

import pandas as pd

from sktime.datatypes._dtypekind import (
    DtypeKind,
    _get_feature_kind,
    _get_panel_dtypekind,
    _get_series_dtypekind,
)


def test_feature_kind_for_series():
    # mtype: pd.DataFrame
    df = pd.DataFrame({"a": ["a", "b", "c", "d"], "b": [3, 7, 2, -3 / 7]})
    expected_feature_kind = [DtypeKind.CATEGORICAL, DtypeKind.FLOAT]

    dtype_kind = _get_series_dtypekind(df, pd.DataFrame)
    feature_kind = _get_feature_kind(dtype_kind)

    assert feature_kind == expected_feature_kind, (
        f"feature_kind was not correctly inferred, expected {expected_feature_kind} but"
        f"found {feature_kind}"
    )


def test_feature_kind_for_panel():
    expected_feature_kind = [DtypeKind.FLOAT, DtypeKind.CATEGORICAL]

    # mtype : df-list
    cols = [f"var_{i}" for i in range(2)]
    dflist = [
        pd.DataFrame([[1, "a"], [2, "b"], [3, "c"]], columns=cols),
        pd.DataFrame([[1, "a"], [2, "c"], [3, "d"]], columns=cols),
    ]
    dtype_kind = _get_panel_dtypekind(dflist, "df-list")
    feature_kind = _get_feature_kind(dtype_kind)

    assert feature_kind == expected_feature_kind, (
        f"feature_kind was not correctly inferred, expected {expected_feature_kind} but"
        f"found {feature_kind}"
    )

    # mtype : pd-multiindex
    cols = ["instances", "timepoints"] + [f"var_{i}" for i in range(2)]
    Xlist = [
        pd.DataFrame([[0, 0, 1, "a"], [0, 1, 2, "b"], [0, 2, 3, "c"]], columns=cols),
        pd.DataFrame([[1, 0, 1, "a"], [1, 1, 2, "c"], [1, 2, 3, "d"]], columns=cols),
    ]
    multiindex_df = pd.concat(Xlist)
    multiindex_df = multiindex_df.set_index(["instances", "timepoints"])

    dtype_kind = _get_panel_dtypekind(multiindex_df, "pd-multiindex")
    feature_kind = _get_feature_kind(dtype_kind)

    assert feature_kind == expected_feature_kind, (
        f"feature_kind was not correctly inferred, expected {expected_feature_kind} but"
        f"found {feature_kind}"
    )

    # mtype : nested_univ
    cols = [f"var_{i}" for i in range(2)]
    nested_univ = pd.DataFrame(columns=cols, index=pd.RangeIndex(3))
    nested_univ["var_0"] = pd.Series([pd.Series([1, 2, 3]), pd.Series([1, 2, 3])])
    nested_univ["var_1"] = pd.Series(
        [pd.Series(["a", "b", "c"]), pd.Series(["a", "c", "d"])]
    )

    dtype_kind = _get_panel_dtypekind(nested_univ, "nested_univ")
    feature_kind = _get_feature_kind(dtype_kind)

    assert feature_kind == expected_feature_kind, (
        f"feature_kind was not correctly inferred, expected {expected_feature_kind} but"
        f"found {feature_kind}"
    )


def test_feature_kind_for_hierarchical():
    expected_feature_kind = [DtypeKind.CATEGORICAL, DtypeKind.FLOAT]

    # mtype : pd-multiindex
    cols = ["foo", "bar", "timepoints"] + [f"var_{i}" for i in range(2)]
    Xlist = [
        pd.DataFrame(
            [["a", 0, 0, "x", 4], ["a", 0, 1, "y", 5], ["a", 0, 2, "z", 6]],
            columns=cols,
        ),
        pd.DataFrame(
            [["a", 1, 0, "x", 4], ["a", 1, 1, "y", 55], ["a", 1, 2, "z", 6]],
            columns=cols,
        ),
        pd.DataFrame(
            [["b", 0, 0, "x", 4], ["b", 0, 1, "x", 5], ["b", 0, 2, "z", 6]],
            columns=cols,
        ),
        pd.DataFrame(
            [["b", 1, 0, "y", 4], ["b", 1, 1, "z", 55], ["b", 1, 2, "y", 6]],
            columns=cols,
        ),
    ]
    hierarchical_df = pd.concat(Xlist)
    hierarchical_df = hierarchical_df.set_index(["foo", "bar", "timepoints"])

    dtype_kind = _get_panel_dtypekind(hierarchical_df, "pd-multiindex")
    feature_kind = _get_feature_kind(dtype_kind)

    assert feature_kind == expected_feature_kind, (
        f"feature_kind was not correctly inferred, expected {expected_feature_kind} but"
        f"found {feature_kind}"
    )