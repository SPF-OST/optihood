"""
This example shows how to use the MPC interface.
After the imports, there are a few example functions, which the User should provide:
get_current_system_state
define_desired_flows_and_their_new_names
translate_flows_to_control_signals
control_system
"""

# ================
# required imports
import pathlib as _pl

import pandas as _pd
import numpy as _np

from optihood.MPC.interface import MpcHandler
from optihood.energy_network import OptimizationProperties


# required imports
# ================


# =========================
# functions the User should provide
def get_current_system_state(system_state: dict[str, dict[str, float]]) -> dict[str, dict[str, float]]:
    """Required function to interface with real/virtual system.
    As such a system is not the focus of this example, we will update the system using random numbers.
    In a real case, the User will need to connect the real/virtual system here.
    """
    system_state['electricalStorage__B001']['initial capacity'] = round(_np.random.random(), 2)
    system_state['shStorage__B001']['initial capacity'] = round(_np.random.random(), 2)
    return system_state


def define_desired_flows_and_their_new_names() -> dict[str, str]:
    """The MPC will predict flows for every time step in the predicted window.
    Only a subset of those flows will be needed to control the system.

    The names of these flows is very cumbersome, so renaming them here makes life easier when
    translating the flows to control signals.
    {"HP__B001__To__shSourceBus__B001": "HP_out",
    "shSourceBus__B001__To__shStorage__B001": "HP_into_storage"}

    To keep the same name, just use it twice:
    {"HP__B001__To__shSourceBus__B001": "HP__B001__To__shSourceBus__B001"}
    """
    return {
        # ================================
        # electrical part till heat pump (HP)
        # --------------------------------
        # electricity produced by photovoltaics (pv)
        "pv__B001__To__electricityProdBus__B001": "el_pv_produced",

        # surplus PV electricity exported to the grid
        "electricityBus__B001__To__excesselectricityBus__B001": "el_to_grid",

        # PV electricity stored in the battery
        "electricityProdBus__B001__To__electricalStorage__B001": "el_pv_to_battery",

        # electricity provided by the battery for own consumption
        "electricalStorage__B001__To__electricityBus__B001": "el_battery_discharge",

        # PV + battery electricity used for own consumption in this timestep
        "electricityBus__B001__To__producedElectricity__B001": "el_produced",

        # electricity taken from the grid for own consumption in this timestep
        "electricityResource__B001__To__gridBus__B001": "el_from_grid",

        # electricity flowing into the heat pump
        "electricityInBus__B001__To__HP__B001": "HP_el_in",
        # ====================================

        # ===================================
        # heat part starting at the heat pump
        # -----------------------------------
        # full heat flow out of the heat pump
        "HP__B001__To__shSourceBus__B001": "HP_heat_out",

        # part of "HP_out" going into the storage
        "shSourceBus__B001__To__shStorage__B001": "HP_to_TES",

        # part of "HP_out" providing heat directly
        "shSourceBus__B001__To__shSource__B001": "HP_to_demand",

        # heat demand supplied by the storage
        "shStorage__B001__To__spaceHeatingBus__B001": "TES_to_demand",

        # space heating delivered
        "spaceHeatingBus__B001__To__spaceHeating__B001": "sh_delivered",
        # ===================================
    }


def translate_flows_to_control_signals(energy_flows):
    """Required function to interface with real/virtual system.
    The MPC returns energy flows between components.
    These need to be translated to e.g. pumping rates, valve positions, etc.
    For this example, we will ignore this step.
    """
    control_signals = _pd.DataFrame(index=energy_flows.index)

    # Get a True/False boolean for each time step, where the HP produces heat.
    HP_out = energy_flows["HP_heat_out"] > 1e-4

    # Apply this on both the HP and the pump supplying fluid to the HP.
    control_signals["HP_is_on"] = HP_out
    control_signals["HP_pump_is_on"] = HP_out

    return control_signals


def control_system(control_signals):
    """Required function to interface with real/virtual system.
    For this example, all inputs are ignored and the next time step can start.
    In a real case, the User will need to connect the real/virtual system here.
    """
    pass


# functions the User should provide
# =========================

# =========================
# define paths for input and result files
current_dir = _pl.Path(__file__).resolve().parent
input_folder_path = current_dir / ".." / "CSVs" / "MPC_example_CSVs"

result_dir_path = current_dir / ".." / "results" / "MPC_example"
result_file_name = "results_MPC_example"
# define paths for input and result files
# =========================

# =========================
# Usage of the MPC interface, which uses the above.
if __name__ == '__main__':
    # Would you like to visualize the energy network?
    visualize = False
    # This will abort the MPC simulation after visualizing.

    # set a time period for the optimization problem
    time_step_in_minutes = 60
    prediction_window_in_hours = 24

    # initialize parameters
    number_of_buildings = 1

    # We will use 4 time steps of 1 hour
    example_time_steps = _pd.date_range("2018-01-01 00:00:00", "2018-01-01 02:00:00",
                                        freq=f"{str(time_step_in_minutes)}min")

    # The MpcHandler will take care of many things for us.
    mpc = MpcHandler(prediction_window_in_hours=prediction_window_in_hours, time_step_in_minutes=time_step_in_minutes,
                     nr_of_buildings=number_of_buildings)

    # Provide the full time period of the data.
    mpc.set_full_time_period(
        start_year=2018,
        start_month=1,
        start_day=1,
        end_year=2018,
        end_month=1,
        end_day=31,
    )

    # We set the optimization properties, that would normally be given to the Network directly.
    mpc.optimization_settings = OptimizationProperties(
        optimization_type="costs",  # set as "env" for environmental optimization,
        merge_link_buses=False,
        merge_buses=None,
        merge_heat_source_sink=False,
        temperature_levels=False,
        cluster_size=None,
        dispatch_mode=True,
        include_carbon_benefits=False,
    )

    # We prepare the scenario in the MpcHandler and get the initial state from the scenario file.
    system_state = mpc.get_mpc_scenario_from_csv(input_folder_path)
    print("")
    print(system_state)
    print("")
    # {'electricalStorage__B001': {'initial capacity': 0},
    #  'shStorage__B001': {'initial capacity': 0}
    #  }
    # This can be used to define the function "get_current_system_state"

    # The MPC will output energy flows. Here, we decide which ones we need and what to call them.
    desired_flows_with_new_names = define_desired_flows_and_their_new_names()

    if visualize:
        mpc.visualize_example()
        exit()

    if not result_dir_path.exists():
        result_dir_path.mkdir(parents=True, exist_ok=True)

    _np.random.seed(0)  # ensure reproducibility of results

    for current_time_step in example_time_steps:
        # ===============
        # responsibility of the User.
        current_state = get_current_system_state(system_state)
        # ===============

        network = mpc.update_network(current_time_step, current_state)

        _, _, _ = network.optimize(solver='gurobi', numberOfBuildings=number_of_buildings)
        results = network.saveUnprocessedResults()

        # ========================================================================
        # logged automatically?
        mpc.log_processing(network, costs=True, env_impacts=True, meta=True)
        # ========================

        result_file_path = result_dir_path / f"{result_file_name}_{current_time_step.strftime("%Y_%m_%d__%H_%M_%S")}.xlsx"
        network.exportToExcel(result_file_path)

        energy_flows = mpc.get_desired_energy_flows(results, desired_flows_with_new_names)
        energy_flows.to_csv(result_file_path.with_suffix('.csv'))

        # ===============
        # responsibility of the User.
        control_signals = translate_flows_to_control_signals(energy_flows)
        control_system(control_signals)
        # ===============
