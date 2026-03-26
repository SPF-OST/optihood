import importlib as _ilib
import os as _os
import pathlib as _pl
import subprocess as _sp
import sys as _sys
import typing as _tp
import unittest as _ut
import pytest as _pt

import matplotlib as _mpl
import pandas as _pd
from matplotlib import pyplot as _plt

import optihood as oh

ROOT_DIR = _pl.Path(oh.__file__).resolve().parents[1]
TEST_RESULTS_DIR = ROOT_DIR / "results"
ROOT_DATA_DIR = ROOT_DIR / "data"
EXAMPLE_SCRIPT_DIR = ROOT_DATA_DIR / "examples"
EXAMPLE_RESULTS_DIR = ROOT_DATA_DIR / "results"

INPUT_FORMATS = ["excel", "csv"]
ATOL = 1e-4


def get_current_file_dir(file) -> _pl.Path:
    return _pl.Path(file).resolve().parent


def compare_txt_files(testCase: _ut.TestCase, file_path1: _pl.Path, file_path2: _pl.Path):
    with open(file_path1) as f1, open(file_path2) as f2:
        _ut.TestCase.assertListEqual(testCase, list(f1), list(f2))


def check_sheet_names(testCase: _ut.TestCase, data: _pd.ExcelFile, sheet_names_expected: _tp.Sequence[str]):
    """May need to have sheets ordered alphabetically."""
    testCase.assertListEqual(data.sheet_names, sheet_names_expected)


def plot_dfs_and_differences(df_new: _pd.DataFrame, df_expected: _pd.DataFrame, sheet_name: str):
    # =======
    # The following is needed to plot the differences as part of a pycharm test run.
    _mpl.use("QtAgg")
    # =======
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
        file_path: _pl.Path,
        file_path_expected: _pl.Path,
        sheet_names_expected: _tp.Sequence[str],
        abs_tolerance: _tp.Optional[float] = None,
        rel_tolerance: _tp.Optional[float] = None,
        manual_test: bool = False,
):
    """Used to provide better feedback when comparing xls files.
    Assembles all errors before raising them.
    Manual testing allows plotting of the differences, given equal dataframes.

    When providing the abs_tolerance and rel_tolerance, the comparison uses the
    relative tolerance (`rtol`) and absolute tolerance (`atol`)
    parameters to determine if two values are considered close,
    according to the formula: `|a - b| <= (atol + rtol * |b|)
    """
    with _pd.ExcelFile(file_path) as data:
        with _pd.ExcelFile(file_path_expected) as expected_data:
            check_sheet_names(testCase, data, sheet_names_expected)
            errors = []

            print("")
            for sheet in sheet_names_expected:
                print(sheet)
                df_new = data.parse(sheet)
                df_expected = expected_data.parse(sheet)

                compare_dataframes(abs_tolerance, df_expected, df_new, errors, manual_test, rel_tolerance, sheet)
    if errors:
        if manual_test:
            _plt.show(block=True)
        raise ExceptionGroup(f"found {len(errors)} errors in {file_path}", errors)


def compare_csv_files(file_path: _pl.Path,
                      file_path_expected: _pl.Path,
                      name_for_df: str,
                      abs_tolerance: _tp.Optional[float] = None,
                      rel_tolerance: _tp.Optional[float] = None,
                      manual_test: bool = False,
                      ):
    df_new = _pd.read_csv(file_path)
    df_expected = _pd.read_csv(file_path_expected)

    errors = []
    compare_dataframes(abs_tolerance, df_expected, df_new, errors, manual_test, rel_tolerance, name_for_df)

    if errors:
        if manual_test:
            _plt.show(block=True)
        raise ExceptionGroup(f"found {len(errors)} errors in {file_path}", errors)


def compare_dataframes(abs_tolerance, df_expected, df_new, errors, manual_test, rel_tolerance, sheet):
    try:
        if abs_tolerance and rel_tolerance:
            _pd.testing.assert_frame_equal(df_new, df_expected, atol=abs_tolerance, rtol=rel_tolerance,
                                           check_exact=False)
        elif abs_tolerance:
            _pd.testing.assert_frame_equal(df_new, df_expected, atol=abs_tolerance, check_exact=False)
        elif rel_tolerance:
            _pd.testing.assert_frame_equal(df_new, df_expected, rtol=rel_tolerance, check_exact=False)
        else:
            _pd.testing.assert_frame_equal(df_new, df_expected, check_exact=True)
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
            if abs_tolerance and rel_tolerance:
                _pd.testing.assert_frame_equal(df_new, df_expected, atol=abs_tolerance, rtol=rel_tolerance,
                                               check_dtype=False, check_exact=False)
            elif abs_tolerance:
                _pd.testing.assert_frame_equal(df_new, df_expected, atol=abs_tolerance, check_dtype=False,
                                               check_exact=False)
            elif rel_tolerance:
                _pd.testing.assert_frame_equal(df_new, df_expected, rtol=rel_tolerance, check_dtype=False,
                                               check_exact=False)
            else:
                _pd.testing.assert_frame_equal(df_new, df_expected, check_dtype=False, check_exact=True)
        except AssertionError as current_error_2:
            errors.append(current_error)
            errors.append(current_error_2)
            if manual_test:
                """Plot differences in sheet to simplify comparison."""
                plot_dfs_and_differences(df_new, df_expected, sheet)


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


def run_python_script(script_path: _pl.Path) -> None:
    cwd = _os.getcwd()
    _os.chdir(script_path.parent)
    outcome = _sp.run([ROOT_DIR / 'venv' / 'Scripts' / 'python.exe', script_path, '/H'],
                      shell=True, check=False,  # check=True does not provide helpful feedback.
                      capture_output=True, text=True)
    _os.chdir(cwd)

    if outcome.returncode != 0:
        raise AssertionError(outcome.stderr)


def import_example_script(dir_path: _pl.Path, file_name: str):
    """
    TODO: Typing of module???
    """
    _sys.path.append(str(dir_path))
    return _ilib.import_module(file_name)

def plot_series_and_differences(series_new: _pd.Series, series_expected: _pd.Series, series_name: str):
    # =======
    # The following is needed to plot the differences as part of a pycharm test run.
    _mpl.use("QtAgg")
    # =======
    fig, axs = _plt.subplots(3, 1)
    series_new.plot(ax=axs[0])
    series_expected.plot(ax=axs[1])

    if series_new.shape == series_expected.shape:
        # avoids str - str errors
        try:
            series_diff = series_new - series_expected
            series_diff.plot(ax=axs[2])
        except TypeError:
            pass  # Skip plotting difference if types are incompatible
    else:
        series_name += " SHAPE MISMATCH!"

    axs[0].set_title(f"Series name: {series_name}")


def compare_series(
        series_new: _pd.Series,
        series_expected: _pd.Series,
        name: str,
        errors: list,
        abs_tolerance: _tp.Optional[float] = None,
        rel_tolerance: _tp.Optional[float] = None,
        manual_test: bool = False
):
    try:
        if abs_tolerance and rel_tolerance:
            _pd.testing.assert_series_equal(series_new, series_expected, atol=abs_tolerance, rtol=rel_tolerance,
                                            check_exact=False)
        elif abs_tolerance:
            _pd.testing.assert_series_equal(series_new, series_expected, atol=abs_tolerance, check_exact=False)
        elif rel_tolerance:
            _pd.testing.assert_series_equal(series_new, series_expected, rtol=rel_tolerance, check_exact=False)
        else:
            _pd.testing.assert_series_equal(series_new, series_expected, check_exact=True)
    except AssertionError as current_error:
        errors.append(current_error)
        if manual_test:
            plot_series_and_differences(series_new, series_expected, name)


def define_and_optimize_network(
    input_type: str,
    base_path: _pl.Path,
    time_index: _pd.DatetimeIndex,
    nr_of_buildings: int = 1,
    excel_filename: str = "scenario.xls",
    csv_dirname: str = "scenario_csvs",
    dispatch_mode: bool = False,
    solver: str = "gurobi"
):
    """
    This helper function is used in pytest fixtures in E2E tests
    """
    # lazy import to avoid loading the energy_network during pytest collection for tests that don't require optimization
    import optihood.energy_network as oh_en
    network = oh_en.EnergyNetworkIndiv(time_index)

    if input_type == "excel":
        excel_path = base_path / excel_filename
        network.setFromExcel(str(excel_path), numberOfBuildings=nr_of_buildings, dispatchMode=dispatch_mode)
    elif input_type == "csv":
        csv_path = base_path / csv_dirname
        network.set_from_csv(csv_path, nr_of_buildings=nr_of_buildings, dispatchMode=dispatch_mode)

    network.optimize(solver=solver, numberOfBuildings=nr_of_buildings)

    # Explicitly failing the fixture aborts the dependent tests cleanly with a clear message
    if network.results is None:
        _pt.fail(f"Dependent tests aborted: Optimization solver failed to find a solution for {input_type} input.")

    return network


def check_condition(errors: list, condition: bool, error_message: str):
    """Evaluates a condition and appends an AssertionError to the list if it fails"""
    try:
        assert condition, error_message
    except AssertionError as e:
        errors.append(e)
