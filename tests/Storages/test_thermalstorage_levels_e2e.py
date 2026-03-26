import pytest
import pandas as pd
import numpy as np
from pathlib import Path
from oemof.solph import processing

import tests.xls_helpers as xlsh


class TestThermalStorageE2E:

    @pytest.fixture(scope="class", params=xlsh.INPUT_FORMATS)
    def optimized_network(self, request):
        """Runs the optimization for the 24-hour storage scenario using both Excel and CSV inputs."""
        base_path = Path(__file__).parent / "data" / "test_storage_integration"
        time_index = pd.date_range('2018-01-01 00:00:00', periods=24, freq='H')

        return xlsh.define_and_optimize_network(
            input_type=request.param,
            base_path=base_path,
            time_index=time_index,
            dispatch_mode=True
        )


    def test_thermalstorage_level_constraints(self, optimized_network):
        """Explicitly verifies that the solver respected the min and max storage limits"""
        errors = []
        oemof_results = processing.results(optimized_network._optimizationModel)

        storage_node = next(n for n in optimized_network.nodes if "shStorage" in str(n.label))
        actual_storage_content = oemof_results[(storage_node, None)]['sequences']['storage_content'].values

        # Strip out the trailing NaN from oemof results
        if np.isnan(actual_storage_content[-1]):
            actual_storage_content = actual_storage_content[:-1]

        if storage_node.nominal_storage_capacity is not None:
            nominal_capacity = storage_node.nominal_storage_capacity
        else:
            nominal_capacity = oemof_results[(storage_node, None)]['scalars']['invest']

        min_level_rel = storage_node.min_storage_level[0]
        max_level_rel = storage_node.max_storage_level[0]

        # Calculate absolute bounds
        min_abs_bound = min_level_rel * nominal_capacity
        max_abs_bound = max_level_rel * nominal_capacity

        # 1. Assert no value dips below the minimum storage limit
        msg = f"Constraint Violated! Minimum allowed storage is {min_abs_bound}, but found lower levels."
        xlsh.check_condition(errors, np.all(actual_storage_content >= (min_abs_bound - xlsh.ATOL)), msg)

        # 2. Assert no value exceeds the maximum storage limit
        msg = f"Constraint Violated! Maximum allowed storage is {max_abs_bound}, but found higher levels."
        xlsh.check_condition(errors, np.all(actual_storage_content <= (max_abs_bound + xlsh.ATOL)), msg)

        if errors:
            raise ExceptionGroup(f"found {len(errors)} issues:", errors)

    def test_thermalstorage_excel_export_content(self, optimized_network, tmp_path):
        """Matches the exact storage content (levels) from the exported Excel file"""
        errors = []
        out_dir = tmp_path / "results_export"
        out_dir.mkdir()
        excel_file = out_dir / "results.xlsx"

        optimized_network.exportToExcel(str(excel_file))
        # Fail fast: Abort immediately if the file is missing, as downstream reads will crash.
        assert excel_file.exists(), "Optihood failed to generate the results Excel file!"

        df_storage = pd.read_excel(excel_file, sheet_name="storage_content__Building1")

        actual_content = df_storage["shStorage__B001_storage_content"]

        expected_content = pd.Series([
            18.93225, 16.64049, 14.42446, 12.19548,
            9.837268, 7.484982, 6.035371, 5.2325,
            5.2325, 5.2325, 5.371412,
            11.41881, 17.85437, 21.20623, 22.9263,
            22.6671, 21.10612, 18.42162, 15.30307,
            14.33997, 14.03796, 12.94302, 9.845141,
            5.2325
        ], name="shStorage__B001_storage_content")

        len_msg = "Storage content array must have exactly 24 elements. Optihood strips the trailing NaN from oemof results."
        xlsh.check_condition(errors, len(actual_content) == 24, len_msg)

        xlsh.compare_series(
            series_new=actual_content,
            series_expected=expected_content,
            name="shStorage__B001_storage_content",
            errors=errors,
            abs_tolerance=xlsh.ATOL,
            manual_test=True  # Enables plotting on failure
        )

        if errors:
            raise ExceptionGroup(f"found {len(errors)} issues:", errors)