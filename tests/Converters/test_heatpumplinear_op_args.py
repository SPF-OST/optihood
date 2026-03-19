import pytest
import numpy as np
from oemof.solph import Bus
from oemof.solph._options import NonConvex

from optihood.converters import HeatPumpLinear


class TestHeatPumpLinearOpArgs:

    @pytest.fixture
    def base_hp_kwargs(self):
        elec_bus = Bus(label="electricityBus")
        sh_bus = Bus(label="shBus")
        return {
            "label": "HP",
            "operationTemperatures": [35],
            # FIX: Use a numpy array to simulate a timeseries, so len() and sum() work
            "temperatureLow": np.array([10.0, 12.0, 10.0]),
            "input": [elec_bus],
            "output": [sh_bus],
            "coef_W": [0.1, 0.2, 0.3, 0.4, 0.5, 0.6],
            "coef_Q": [0.1, 0.2, 0.3, 0.4, 0.5, 0.6],
            "capacityMin": 0,
            "capacityMax": 100,
            "nomEff": 3.0,
            "epc": 100,
            "base": 500,
            "varc": 0.05,
            "env_flow": 0,
            "env_capa": 0,
            "dispatchMode": False
        }

    # ==========================================
    # UNIT TESTS
    # ==========================================

    def test_default_initialization_no_op_args(self, base_hp_kwargs):
        hp = HeatPumpLinear(**base_hp_kwargs)
        elec_bus = base_hp_kwargs["input"][0]
        input_flow = hp._heatpump.inputs[elec_bus]

        assert input_flow.nonconvex is None

    def test_op_args_flow_routing(self, base_hp_kwargs):
        base_hp_kwargs["op_args"] = {'min_flow': 0.15}
        hp = HeatPumpLinear(**base_hp_kwargs)
        elec_bus = base_hp_kwargs["input"][0]
        input_flow = hp._heatpump.inputs[elec_bus]

        assert isinstance(input_flow.nonconvex, NonConvex)
        assert input_flow.min[0] == 0.15

    def test_op_args_temporal_routing(self, base_hp_kwargs):
        base_hp_kwargs["op_args"] = {'min_flow': 0.1, 'minimum_uptime': 3}
        hp = HeatPumpLinear(**base_hp_kwargs)
        elec_bus = base_hp_kwargs["input"][0]
        input_flow = hp._heatpump.inputs[elec_bus]

        assert input_flow.min[0] == 0.1
        assert isinstance(input_flow.nonconvex, NonConvex)
        assert input_flow.nonconvex.minimum_uptime == 3
