import pytest
import numpy as np
from oemof.solph import Bus

from optihood.converters import HeatPumpLinear
import tests.xls_helpers as xlsh


class TestHeatPumpLinearParams:

    @pytest.fixture
    def base_hp_kwargs(self):
        elec_bus = Bus(label="electricityBus")
        sh_bus = Bus(label="shBus")
        return {
            "label": "HP",
            "operationTemperatures": [35],
            "temperatureLow": np.array([10.0, 12.0, 10.0]),
            "input": [elec_bus],
            "output": [sh_bus],
            "coef_W": [0.1, 0.2, 0.3, 0.4, 0.5, 0.6],
            "coef_Q": [0.1, 0.2, 0.3, 0.4, 0.5, 0.6],
            "capacityMin": 0,
            "capacityMax": 100,
            "nomEff": 3.0,
            "cop": None,
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

    def test_user_defined_cop_conversion_factors(self, base_hp_kwargs):
        """
        Tests that when a custom COP array is passed, the heat pump correctly
        assigns it to the output efficiency.
        This ensures the equation (Output = Input*COP) is satisfied.
        """
        n_timesteps = 3
        cop_array_for_sh_bus = np.array([3.5, 3.8, 3.2])

        custom_cop = [cop_array_for_sh_bus]
        base_hp_kwargs["cop"] = custom_cop

        hp = HeatPumpLinear(**base_hp_kwargs)

        sh_bus = base_hp_kwargs["output"][0]

        errors = []

        efficiency = hp._heatpump.efficiency

        actual_out_eff = [efficiency[sh_bus][i] for i in range(n_timesteps)]

        expected_cop = list(custom_cop[0])
        xlsh.check_condition(
            errors,
            np.allclose(actual_out_eff, expected_cop),
            f"Expected output conversion factors to match custom COP {expected_cop}, but got {actual_out_eff}"
        )

        if errors:
            raise ExceptionGroup(f"found {len(errors)} issues:", errors)

    def test_user_defined_cop_conversion_factors_multiple_buses(self, base_hp_kwargs):
        """
        Tests that when a custom COP array is passed, the heat pump correctly
        assigns it to the output efficiency.
        This ensures the equation (Output = Input*COP) is satisfied.
        """
        # TODO: adjust this to the correct way of having multiple buses.
        n_timesteps = 3
        cop_array_for_sh_bus = np.array([3.5, 3.8, 3.2])
        base_hp_kwargs["output"].append(Bus(label="dhwBus"))
        base_hp_kwargs["operationTemperatures"].append(60.)

        custom_cop = [cop_array_for_sh_bus]
        base_hp_kwargs["cop"] = custom_cop

        hp = HeatPumpLinear(**base_hp_kwargs)

        sh_bus = base_hp_kwargs["output"][0]

        errors = []

        efficiency = hp._heatpump.efficiency

        actual_out_eff = [efficiency[sh_bus][i] for i in range(n_timesteps)]

        expected_cop = list(custom_cop[0])
        xlsh.check_condition(
            errors,
            np.allclose(actual_out_eff, expected_cop),
            f"Expected output conversion factors to match custom COP {expected_cop}, but got {actual_out_eff}"
        )

        if errors:
            raise ExceptionGroup(f"found {len(errors)} issues:", errors)