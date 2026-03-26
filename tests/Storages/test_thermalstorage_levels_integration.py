import pandas as pd
from pathlib import Path
import pytest

from optihood.energy_network import EnergyNetworkIndiv as EnergyNetwork
import tests.xls_helpers as xlsh

class TestThermalStorageIntegration:
    def test_storage_excel_to_node_pipeline(self):
        base_path = Path(__file__).parent / "data" / "test_storage_integration"
        excel_path = base_path / "scenario.xls"

        time_index = pd.date_range('2018-01-01 00:00:00', periods=24, freq='H')
        network = EnergyNetwork(time_index)

        network.setFromExcel(str(excel_path), numberOfBuildings=1)

        oemof_nodes = network.nodes

        storage_node = next((n for n in oemof_nodes if "shStorage" in str(n.label)), None)

        if storage_node is None:
            pytest.fail(f"Storage node not found! Available: {[str(n.label) for n in oemof_nodes]}")

        errors = []

        xlsh.check_condition(errors, storage_node.min_storage_level[0] == 0.1,
                             "min_storage_level from scenario file was not applied!")
        xlsh.check_condition(errors, storage_node.max_storage_level[0] == 0.9,
                             "max_storage_level from scenario file was not applied!")
        xlsh.check_condition(errors, storage_node.initial_storage_level == 0.5,
                             "initial capacity from scenario file was not applied!")

        if errors:
            raise ExceptionGroup(f"found {len(errors)} issues in node pipeline:", errors)