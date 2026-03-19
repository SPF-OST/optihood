import pytest
import logging
import pandas as pd
from oemof.solph import Bus

from optihood.storages import ThermalStorage


class TestThermalStorageUnit:

    @pytest.fixture
    def dummy_args(self):
        mock_stratified_df = pd.DataFrame(
            {
                'temp_h': [60],
                'temp_c': [20],
                'temp_env': [20],
                's_iso': [0.1],
                'lamb_iso': [0.03],
                'alpha_inside': [5],
                'alpha_outside': [5],
                'diameter': [1.5],
                'inflow_conversion_factor': [1.0],
                'outflow_conversion_factor': [1.0]
            },
            index=['TS']
        )

        return {
            'stratifiedStorageParams': mock_stratified_df,
            'volume_cost': 0,
            'base': 0,
            'varc': 0,
            'env_flow': 0,
            'env_cap': 0,
            'dispatchMode': False
        }

    def test_initial_level_clipping_low(self, dummy_args, caplog):
        """Test that initial_storage is clipped up to min_storage_level"""
        with caplog.at_level(logging.WARNING):
            ts = ThermalStorage(
                label_str='TS__1',
                input=Bus(label='in_bus'),
                output=Bus(label='out_bus'),
                capacity_max=1000,
                initial_storage=0.1,
                capacity_min=0,
                **dummy_args,
                min_storage_level=0.2
            )

        assert ts.initial_storage_level == 0.2

        expected_msg = (
            "Storage 'TS': Initial level 0.1 is outside bounds [0.2, 1]. "
            "Clipped to 0.2 to prevent solver infeasibility."
        )
        assert expected_msg in caplog.text



    def test_storage_defaults(self, dummy_args):
        """Verify that default min_storage_level/max_storage_level are 0 and 1"""
        ts = ThermalStorage(
            label_str='TS__1',
            input=Bus(label='in_bus'),
            output=Bus(label='out_bus'),
            capacity_max=1000,
            initial_storage=0.5,
            capacity_min=0,
            **dummy_args
        )

        assert ts.min_storage_level[0] == 0
        assert ts.max_storage_level[0] == 1