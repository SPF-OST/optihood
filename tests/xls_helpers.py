import importlib as _ilib
import os as _os
import pathlib as _pl
import subprocess as _sp
import sys as _sys
import typing as _tp
import unittest as _ut

import matplotlib as _mpl
import pandas as _pd
from matplotlib import pyplot as _plt

import optihood as oh

ROOT_DIR = _pl.Path(oh.__file__).resolve().parents[1]
TEST_RESULTS_DIR = ROOT_DIR / "results"
ROOT_DATA_DIR = ROOT_DIR / "data"
EXAMPLE_SCRIPT_DIR = ROOT_DATA_DIR / "examples"
EXAMPLE_RESULTS_DIR = ROOT_DATA_DIR / "results"


def get_current_file_dir(file) -> _pl.Path:
    return _pl.Path(file).resolve().parent


def compare_txt_files(testCase: _ut.TestCase, file_path1: _pl.Path, file_path2: _pl.Path):
    with open(file_path1) as f1, open(file_path2) as f2:
        _ut.TestCase.assertListEqual(testCase, list(f1), list(f2))


def check_sheet_names(testCase: _ut.TestCase, data: _pd.ExcelFile, sheet_names_expected: _tp.Sequence[str]):
    """May need to have sheets ordered alphabetically."""
    testCase.assertListEqual(data.sheet_names, sheet_names_expected)


def plot_dfs_and_differences(df_new: _pd.DataFrame, df_expected: _pd.DataFrame, sheet_name: str):
    _mpl.use("QtAgg")
    fig, axs = _plt.subplots(3, 1)
    df_new.plot(ax=axs[0])
    df_expected.plot(ax=axs[1])
    if df_new.shape == df_expected.shape:
        # avoids str - str errors.
        df_diff = df_new.select_dtypes(exclude=[object]) - df_expected.select_dtypes(exclude=[object])
        df_diff.plot(ax=axs[2])
    else:
        sheet_name += " SHAPE MISMATCH!"
    axs[0].set_title(f"sheet name: {sheet_name}")


def compare_xls_files(
    testCase: _ut.TestCase,
    file_path: str,
    file_path_expected: str,
    sheet_names_expected: _tp.Sequence[str],
    abs_tolerance: _tp.Optional[float] = None,
    manual_test: bool = False,
):
    """Used to provide better feedback when comparing xls files.
    Assembles all errors before raising them.
    Manual testing allows plotting of the differences, given equal dataframes.
    """
    data = _pd.ExcelFile(file_path)
    expected_data = _pd.ExcelFile(file_path_expected)

    check_sheet_names(testCase, data, sheet_names_expected)
    errors = []

    print("")
    for sheet in sheet_names_expected:
        print(sheet)
        df_new = data.parse(sheet)
        df_expected = expected_data.parse(sheet)

        try:
            if abs_tolerance:
                _pd.testing.assert_frame_equal(df_new, df_expected, atol=abs_tolerance)
            else:
                _pd.testing.assert_frame_equal(df_new, df_expected)
        except AssertionError as current_error:
            """Optihood doesn't export the results in a consistent way.
            Therefore, this hack reorders the results.
            Instead, the export should be ordered consistently.
            """

            df_new = df_new.sort_values(by=[df_new.columns[0]], ignore_index=True)
            df_expected = df_expected.sort_values(by=[df_new.columns[0]], ignore_index=True)

            """ The dType of a column sometimes gets set to int instead of float. 
                This reduces the feedback of the test to a dType check.
                Ignoring the dType ensures better feedback.
            """
            try:
                if abs_tolerance:
                    _pd.testing.assert_frame_equal(df_new, df_expected, atol=abs_tolerance, check_dtype=False)
                else:
                    _pd.testing.assert_frame_equal(df_new, df_expected, check_dtype=False)
            except AssertionError as current_error_2:
                errors.append(current_error)
                errors.append(current_error_2)
                if manual_test:
                    """Plot differences in sheet to simplify comparison."""
                    plot_dfs_and_differences(df_new, df_expected, sheet)
    if errors:
        if manual_test:
            _plt.show(block=True)
        raise ExceptionGroup(f"found {len(errors)} errors in {file_path}", errors)


def check_assertion(testCase: _ut.TestCase, errors: list, actual, expected):
    try:
        testCase.assertEqual(actual, expected)
    except AssertionError as current_error:
        errors.append(current_error)


def check_dataframe_assertion(
    errors: list,
    actual: _pd.DataFrame,
    expected: _pd.DataFrame,
    absolute_tolerance: float = None,
    check_dtype: bool = True,
):
    try:
        if absolute_tolerance:
            _pd.testing.assert_frame_equal(actual, expected, atol=absolute_tolerance, check_dtype=check_dtype)
        else:
            _pd.testing.assert_frame_equal(actual, expected, atol=absolute_tolerance, check_dtype=check_dtype)
    except AssertionError as current_error:
        errors.append(current_error)


def run_python_script(script_path: _pl.Path):
    cwd = _os.getcwd()
    _os.chdir(script_path.parent)
    _sp.run([ROOT_DIR / 'venv' / 'Scripts' / 'python.exe', script_path, '/H'],
            shell=True, check=True)
    _os.chdir(cwd)


def import_example_script(dir_path: _pl.Path, file_name: str):
    """
    TODO: Typing of module???
    """
    _sys.path.append(str(dir_path))
    return _ilib.import_module(file_name)
