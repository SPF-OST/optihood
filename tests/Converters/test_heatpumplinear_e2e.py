import pytest
import pandas as pd
import numpy as np
from pathlib import Path
from oemof.solph import processing

from optihood.energy_network import EnergyNetworkIndiv as EnergyNetwork


class TestHeatPumpLinearE2E:

    ATOL = 1e-4

    @pytest.fixture(scope="class", params=["excel", "csv"])
    def optimized_network(self, request):
        """Runs the optimization for the 24-hour scenario using both Excel and CSV inputs."""
        base_path = Path(__file__).parent / "data" / "test_heatpumplinear_integration"

        time_index = pd.date_range('2018-01-01 00:00:00', periods=24, freq='H')
        network = EnergyNetwork(time_index)

        if request.param == "excel":
            excel_path = base_path / "scenario.xls"
            network.setFromExcel(str(excel_path), numberOfBuildings=1)

        elif request.param == "csv":
            csv_path = base_path / "scenario_csvs"
            network.set_from_csv(csv_path, nr_of_buildings=1)

        network.optimize(solver="gurobi", numberOfBuildings=1)
        assert network.results is not None, f"Optimization failed for {request.param} input."

        return network


    def test_heatpump_op_args_constraints(self, optimized_network):
        """Explicitly verifies that the solver respected the min_flow and minimum_uptime constraints"""
        #TODO: Add other checks as well --> for other Flow and NonConvex args
        oemof_results = processing.results(optimized_network._optimizationModel)

        hp_node = next(n for n in optimized_network.nodes if "HP" in str(n.label))
        input_bus = list(hp_node.inputs.keys())[0]

        # Extract the flow using the processed results dictionary
        flow_values = oemof_results[(input_bus, hp_node)]['sequences']['flow'].values

        # ---------------------------------------------------------
        # 1. ASSERT MINIMUM FLOW CONSTRAINT
        # ---------------------------------------------------------
        # Based on integration test: min_flow = 0.25 (25% of nominal capacity)
        input_flow_obj = hp_node.inputs[input_bus]

        # Check if capacity was fixed or if it was optimized (Investment mode)
        if input_flow_obj.nominal_value is not None:
            nominal_capacity = input_flow_obj.nominal_value
        else:
            nominal_capacity = oemof_results[(input_bus, hp_node)]['scalars']['invest']

        expected_min_flow = 0.25 * nominal_capacity

        active_flows = flow_values[flow_values > self.ATOL]

        if len(active_flows) > 0:
            assert np.all(active_flows >= (expected_min_flow - self.ATOL)), \
                f"Minimum flow constraint violated! Minimum expected: {expected_min_flow}, but found: {active_flows}"

        # ---------------------------------------------------------
        # 2. ASSERT MINIMUM UPTIME CONSTRAINT
        # ---------------------------------------------------------
        # Based on integration test: minimum_uptime = 4
        expected_minimum_uptime = 4
        is_on = flow_values > self.ATOL

        on_blocks = []
        current_streak = 0

        for i, state in enumerate(is_on):
            if state:
                current_streak += 1
            else:
                if current_streak > 0:
                    on_blocks.append((current_streak, i))
                    current_streak = 0

        if current_streak > 0:
            on_blocks.append((current_streak, len(is_on)))

        for streak, end_idx in on_blocks:
            # We only check streaks that didn't hit the very end of the 24-hour simulation,
            # because the simulation ending forces the heat pump to shut off regardless of uptime.
            if end_idx < len(is_on):
                assert streak >= expected_minimum_uptime, \
                    f"Minimum uptime violated! HP was only on for {streak} consecutive hours."

    def test_heatpump_excel_export_output_flows(self, optimized_network, tmp_path):
        """Matches the output heat flows (both outputs) from the exported Excel file"""
        out_dir = tmp_path / "results_export"
        out_dir.mkdir()
        excel_file = out_dir / "results.xlsx"

        optimized_network.exportToExcel(str(excel_file))
        assert excel_file.exists(), "Optihood failed to generate the results Excel file!"

        # Read the Space Heating bus sheet and extract the HP flow
        df_sh = pd.read_excel(excel_file, sheet_name="shSourceBus__Building1")
        actual_output_sh = df_sh["(('HP__Building1', 'shSourceBus__Building1'), 'flow')"].values

        # Read the Domestic Hot Water bus sheet and extract the HP flow
        df_dhw = pd.read_excel(excel_file, sheet_name="domesticHotWaterBus__Building1")
        actual_output_dhw = df_dhw["(('HP__Building1', 'dhwStorageBus__Building1'), 'flow')"].values

        # Expected output flows for space heating and domestic hot water
        expected_output_sh = np.array([
            0.0, 0.0, 0.0, 0.0,
            6.005278, 6.054624, 6.054624, 6.071129,
            6.104225, 6.170761, 5.962684, 0.291021,
            0.0,
            3.008083, 4.653648, 6.441583, 6.390225,
            6.322167, 6.339137, 6.373166,
            0.0, 0.0, 0.0, 0.0
        ])

        expected_output_dhw = np.array([
            0.0, 0.0, 0.0, 0.0,
            0.0, 0.0, 0.0, 0.0,
            0.0, 0.0, 0.0,
            2.956429, 3.156496, 1.665078, 0.879803,
            0.0, 0.0, 0.0, 0.0,
            0.0, 0.0, 0.0, 0.0, 0.0
        ])

        np.testing.assert_allclose(
            actual_output_sh,
            expected_output_sh,
            atol=self.ATOL,
            err_msg="Output SH flows did not match expected!"
        )

        np.testing.assert_allclose(
            actual_output_dhw,
            expected_output_dhw,
            atol=self.ATOL,
            err_msg="Output DHW flows did not match expected!"
        )

    def test_heatpump_excel_export_input_flows(self, optimized_network, tmp_path):
        """Matches the input electricity flow from the exported Excel file"""
        out_dir = tmp_path / "results_export"
        out_dir.mkdir()
        excel_file = out_dir / "results.xlsx"

        optimized_network.exportToExcel(str(excel_file))
        assert excel_file.exists(), "Optihood failed to generate the results Excel file!"

        df_elec = pd.read_excel(excel_file, sheet_name="electricityInBus__Building1")
        actual_input_flow = df_elec["(('electricityInBus__Building1', 'HP__Building1'), 'flow')"].values

        expected_input_flow = np.array([
            0.0, 0.0, 0.0, 0.0,
            1.428571, 1.428571, 1.428571, 1.428571,
            1.428571, 1.428571, 1.376673, 1.428571,
            1.428571, 1.428571, 1.428571, 1.428571,
            1.428571, 1.428571, 1.428571, 1.428571,
            0.0, 0.0, 0.0, 0.0
        ])

        np.testing.assert_allclose(
            actual_input_flow,
            expected_input_flow,
            atol=self.ATOL,
            err_msg="Input electricity flows did not match expected!"
        )