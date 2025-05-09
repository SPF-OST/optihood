import pathlib as _pl
import os as _os

import pandas as _pd
import numpy as _np

from optihood.MPC.interface import MpcHandler
from optihood.energy_network import OptimizationProperties


def get_current_system_state(system_state: dict[str, float]) -> dict[str, float]:
    """Required function to interface with real/virtual system.
    As such a system is not the focus of this example, we will update the system using random numbers.
    In a real case, the User will need to connect the real/virtual system here.
    """
    system_state['electricalStorage__B001']['initial capacity'] = round(_np.random.random(), 2)
    system_state['shStorage__B001']['initial capacity'] = round(_np.random.random(), 2)
    return system_state


def translate_flows_to_control_signals(energy_flows):
    raise NotImplementedError


def control_system(control_signals):
    """Required function to interface with real/virtual system.
    For this example, all inputs are ignored and the next time step can start.
    In a real case, the User will need to connect the real/virtual system here.
    """
    pass


if __name__ == '__main__':
    # TODO: produce a test for this example.
    # Would you like to visualize the energy network?
    visualize = True
    # This will abort the MPC simulation after visualizing.

    # set a time period for the optimization problem
    time_step_in_minutes = 60
    prediction_window_in_hours = 24

    # define paths for input and result files
    current_dir = _pl.Path(__file__).resolve().parent
    input_folder_path = current_dir / ".." / "CSVs" / "MPC_example_CSVs"

    result_dir_path = current_dir / ".." / "results"
    result_file_name = "results_MPC_example"

    # initialize parameters
    numberOfBuildings = 1

    # We will use 4 time steps of 1 hour
    example_time_steps = _pd.date_range("2018-01-01 00:00:00", "2018-01-01 04:00:00",
                                        freq=f"{str(time_step_in_minutes)}min")

    # The MpcHandler will take care of many things for us.
    mpc = MpcHandler(prediction_window_in_hours=prediction_window_in_hours, time_step_in_minutes=time_step_in_minutes,
                     nr_of_buildings=1)

    # We set the optimization properties, that would normally be given to the Network directly.
    # TODO: figure out the rest of the inputs for this example.
    mpc.optimization_settings = OptimizationProperties(
        optimization_type="costs",  # set as "env" for environmental optimization,
        merge_link_buses=False,
        merge_buses=None,
        merge_heat_source_sink=None,
        temperature_levels=False,
        clusters=None,
        dispatch_mode=True,
        include_carbon_benefits=None,
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

    if visualize:
        mpc.visualize_example()
        exit()

    if not _os.path.exists(result_dir_path):
        _os.makedirs(result_dir_path)

    _np.random.seed(0)  # ensure reproducibility of results

    for current_time_step in example_time_steps:
        # ===============
        # responsibility of the User.
        current_state = get_current_system_state(system_state)
        # ===============

        network = mpc.update_network(current_time_step, current_state)

        _, _, _ = network.optimize(solver='gurobi', numberOfBuildings=numberOfBuildings)
        # results, optimization_meta_data = network.optimize(solver='gurobi', numberOfBuildings=numberOfBuildings)
        # return dataclass
        results = network.saveUnprocessedResults()

        # ========================================================================
        # logged automatically?
        mpc.log_processing(results, costs=True, env_impacts=True, meta=True)
        # ========================

        result_file_path = result_dir_path / f"{result_file_name}_{current_time_step.strftime("%Y_%m_%d__%H_%M_%S")}.xlsx"
        network.exportToExcel(result_file_path)

        control_signals = mpc.get_desired_control_signals(results)

        # ===============
        # responsibility of the User.
        control_system(control_signals)
        # ===============

        # or
        energy_flows = mpc.get_desired_energy_flows(results)

        # ===============
        # responsibility of the User.
        control_signals = translate_flows_to_control_signals(energy_flows)
        control_system(control_signals)
        # ===============
