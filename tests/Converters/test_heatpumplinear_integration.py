import pytest
import pandas as pd
from pathlib import Path
from oemof.solph._options import NonConvex

from optihood.energy_network import EnergyNetworkIndiv as EnergyNetwork
import tests.xls_helpers as xlsh


class TestHeatPumpLinearOpArgsIntegration:
    def test_full_excel_to_oemof_pipeline(self):
        base_path = Path(__file__).parent / "data" / "test_heatpumplinear_integration"
        excel_path = base_path / "scenario.xls"

        time_index = pd.date_range('2018-01-01 00:00:00', periods=24, freq='H')
        network = EnergyNetwork(time_index)

        network.setFromExcel(str(excel_path), numberOfBuildings=1)

        oemof_nodes = network.nodes

        hp_node = next((n for n in oemof_nodes if "HP" in str(n.label)), None)

        if hp_node is None:
            pytest.fail(f"HP not found! Available nodes: {[str(n.label) for n in oemof_nodes]}")

        input_bus = list(hp_node.inputs.keys())[0]
        flow = hp_node.inputs[input_bus]

        errors = []
        xlsh.check_condition(errors, flow.min[0] == 0.25, f"Expected min 0.25, got {flow.min[0]}")
        xlsh.check_condition(errors, isinstance(flow.nonconvex, NonConvex), "Expected NonConvex object")
        xlsh.check_condition(errors, flow.nonconvex.minimum_uptime == 4,
                                f"Expected uptime 4, got {flow.nonconvex.minimum_uptime}")

        if errors:
            raise ExceptionGroup(f"found {len(errors)} issues in excel to oemof pipeline:", errors)