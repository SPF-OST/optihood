import pytest
import pandas as pd
import numpy as np
from pathlib import Path
from oemof.solph import processing

from optihood.energy_network import EnergyNetworkIndiv as EnergyNetwork


class TestThermalStorageE2E:

    ATOL = 1e-4

    @pytest.fixture(scope="class", params=["excel", "csv"])
    def optimized_network(self, request):
        """Runs the optimization for the 24-hour storage scenario using both Excel and CSV inputs."""
        base_path = Path(__file__).parent / "data" / "test_storage_integration"

        # 24 periods for the optimization
        time_index = pd.date_range('2018-01-01 00:00:00', periods=24, freq='H')
        network = EnergyNetwork(time_index)

        if request.param == "excel":
            excel_path = base_path / "scenario.xls"
            network.setFromExcel(str(excel_path), numberOfBuildings=1, dispatchMode=True)

        elif request.param == "csv":
            csv_path = base_path / "scenario_csvs"
            network.set_from_csv(csv_path, nr_of_buildings=1, dispatchMode=True)

        network.optimize(solver="gurobi", numberOfBuildings=1)
        assert network.results is not None, f"Optimization failed for {request.param} input."

        return network

    def test_thermalstorage_level_constraints(self, optimized_network):
        """Explicitly verifies that the solver respected the min and max storage limits"""
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
        assert np.all(actual_storage_content >= (min_abs_bound - self.ATOL)), \
            f"Constraint Violated! Minimum allowed storage is {min_abs_bound}, but found lower levels."

        # 2. Assert no value exceeds the maximum storage limit
        assert np.all(actual_storage_content <= (max_abs_bound + self.ATOL)), \
            f"Constraint Violated! Maximum allowed storage is {max_abs_bound}, but found higher levels."

    def test_thermalstorage_excel_export_content(self, optimized_network, tmp_path):
        """Matches the exact storage content (levels) from the exported Excel file"""
        out_dir = tmp_path / "results_export"
        out_dir.mkdir()
        excel_file = out_dir / "results.xlsx"

        optimized_network.exportToExcel(str(excel_file))
        assert excel_file.exists(), "Optihood failed to generate the results Excel file!"

        df_storage = pd.read_excel(excel_file, sheet_name="storage_content__Building1")

        actual_content = df_storage["shStorage__B001_storage_content"].values

        expected_content = np.array([
            18.93225, 16.64049, 14.42446, 12.19548,
            9.837268, 7.484982, 6.035371, 5.2325,
            5.2325, 5.2325, 5.371412,
            11.41881, 17.85437, 21.20623, 22.9263,
            22.6671, 21.10612, 18.42162, 15.30307,
            14.33997, 14.03796, 12.94302, 9.845141,
            5.2325
        ])

        assert len(actual_content) == 24, ("Storage content array must have exactly 24 elements. "
                                           "Optihood strips the trailing NaN from oemof results.")

        np.testing.assert_allclose(
            actual_content,
            expected_content,
            atol=self.ATOL,
            err_msg="Exported storage content did not match expected!"
        )