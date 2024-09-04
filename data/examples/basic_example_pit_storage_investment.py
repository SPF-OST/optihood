# -*- coding: utf-8 -*-

"""
General description
-------------------

A basic example to show how to model a simple energy system with oemof.solph.

The following energy system is modeled:

.. code-block:: text

                     input/output  bgas     bel
                         |          |        |
                         |          |        |
     wind(FixedSource)   |------------------>|
                         |          |        |
     pv(FixedSource)     |------------------>|
                         |          |        |
     rgas(Commodity)     |--------->|        |
                         |          |        |
     demand(Sink)        |<------------------|
                         |          |        |
                         |          |        |
     pp_gas(Converter)   |<---------|        |
                         |------------------>|
                         |          |        |
     storage(Storage)    |<------------------|
                         |------------------>|

Code
----
Download source code: :download:`basic_example.py </../examples/basic_example/basic_example.py>`

.. dropdown:: Click to display code

    .. literalinclude:: /../examples/basic_example/basic_example.py
        :language: python
        :lines: 61-

Data
----
Download data: :download:`basic_example.csv </../examples/basic_example/basic_example.csv>`

Installation requirements
-------------------------
This example requires oemof.solph (v0.5.x), install by:

.. code:: bash

    pip install oemof.solph[examples]

License
-------
`MIT license <https://github.com/oemof/oemof-solph/blob/dev/LICENSE>`_
"""
###########################################################################
# imports
###########################################################################

import logging
import os
import pprint as pp
from datetime import datetime

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pathlib as _pl
from oemof.tools import logger

from oemof.solph import EnergySystem
from oemof.solph import Model
from oemof.solph import buses
from oemof.solph import components
from oemof.solph import create_time_index
from oemof.solph import flows
from oemof.solph import helpers
from oemof.solph import processing
from oemof.solph import views
import oemof.solph as solph
from optihood.genericstorage_pit import GenericStoragePit

STORAGE_LABEL = "thermal_storage"


def plot_figures_for(element: dict) -> None:
    figure, axes = plt.subplots(figsize=(10, 5))
    element["sequences"].plot(ax=axes, kind="line", drawstyle="steps-post")
    plt.legend(
        loc="upper center",
        prop={"size": 8},
        bbox_to_anchor=(0.5, 1.25),
        ncol=2,
    )
    figure.subplots_adjust(top=0.8)
    plt.show()


def main(dump_and_restore=False):
    # For models that need a long time to optimise, saving and loading the
    # EnergySystem might be advised. By default, we do not do this here. Feel
    # free to experiment with this once you understood the rest of the code.
    dump_results = restore_results = dump_and_restore

    # *************************************************************************
    # ********** PART 1 - Define and optimise the energy system ***************
    # *************************************************************************

    # Read data file
    curDir = _pl.Path(__file__).resolve().parent
    inputFilePath = curDir / ".." / "excels" / "basic_example_pit_storage"
    inputfileName = "input_demand.csv"
    data = pd.read_csv(os.path.join(inputFilePath, inputfileName), delimiter=',')

    """file_name = "input_demand.csv"
    data = get_data_from_file_path(file_name)"""

    solver = "gurobi"  # 'glpk', 'gurobi',....
    debug = False  # Set number_of_timesteps to 3 to get a readable lp-file.
    number_of_time_steps = len(data)

    # initiate the logger (see the API docs for more information)
    logger.define_logging(
        logfile="oemof_example.log",
        screen_level=logging.INFO,
        file_level=logging.INFO,
    )

    logging.info("Initialize the energy system")
    date_time_index = create_time_index(2012, number=number_of_time_steps)

    # create the energysystem and assign the time index
    energysystem = EnergySystem(
        timeindex=date_time_index, infer_last_interval=False)

    ##########################################################################
    # Create oemof objects
    ##########################################################################

    logging.info("Create oemof objects")

    # The bus objects were assigned to variables which makes it easier to
    # connect components to these buses (see below).

    # create heat bus
    bus_heat = buses.Bus(label="heat")

    # adding the buses to the energy system
    energysystem.add(bus_heat)

    # create source object representing the gas commodity
    variable_costs = np.random.uniform(low=0.001, high=0.3, size=len(data))
    energysystem.add(
        components.Source(
            label="source",
            outputs={bus_heat: flows.Flow(variable_costs=variable_costs)},
        )
    )

    # create simple sink object representing the electrical demand
    # nominal_value is set to 1 because demand_el is not a normalised series
    energysystem.add(
        components.Sink(
            label="demand",
            inputs={
                bus_heat: flows.Flow(
                    fix=data["demand_heat"], nominal_value=1
                )
            },
        )
    )

    # create storage object representing a pit storage
    volume = 30000 # m3
    rho = 1  # kg/m3
    c = 4.186  # J/(kg*K)
    temp_h = 35  # °C
    temp_c = 25  # °C
    temp_air = 15  # °C
    temp_ground = 5  # °C
    s_iso_top = 240  # mm
    s_iso_wall_bot = 2000  # mm
    lamb_iso_top = 0.104  # W/(m*K)
    lamb_iso_wall_bot = 0.5  # W/(m*K)
    alpha_inside = 1  # W/(m2*K)
    alpha_outside = 1  # W/(m2*K)


    def _precalculate(volume, rho, c, temp_h, temp_c, temp_air, temp_ground,
                      s_iso_top, s_iso_wall_bot, lamb_iso_top, lamb_iso_wall_bot,
                      alpha_inside, alpha_outside, time_increment=1):

        # Nominal capacity in kWh
        nominal_capacity = volume * rho * c * (temp_h - temp_c) / 3600 / 1e3 * 1e6

        # U-value for the top insulation
        denominator_top = 1 / alpha_inside + s_iso_top * 1e-3 / lamb_iso_top + 1 / alpha_outside
        u_value_top = 1 / denominator_top  # W/(m2*K)

        # U-value for the wall/bottom insulation
        denominator_bot = 1 / alpha_inside + s_iso_wall_bot * 1e-3 / lamb_iso_wall_bot + 1 / alpha_outside
        u_value_wall_bot = 1 / denominator_bot  # W/(m2*K)

        # Height multiplication factor
        height_multiplication_factor = (151 / 3) * rho * c * (temp_h - temp_c)

        # Loss rate calculation
        loss_rate = (u_value_wall_bot * 84 * np.sqrt(5) * time_increment * 3600) / (151 * rho * c * 1e6)  # m

        # Fixed losses relative calculation
        fixed_losses_relative = (u_value_top * 243 * (temp_h - temp_air) * time_increment * 3600
                                 + u_value_wall_bot * 75 * (temp_c - temp_ground) * time_increment * 3600
                                 + u_value_wall_bot * 84 * np.sqrt(5) * (temp_c - temp_ground)*time_increment*3600)\
                                 / (151 * rho * c * 1e6 *(temp_h - temp_c))  # m

        return nominal_capacity, u_value_top, u_value_wall_bot, height_multiplication_factor, \
            loss_rate, fixed_losses_relative

    nominal_capacity, u_value_top, u_value_wall_bot, height_multiplication_factor, loss_rate, fixed_losses_relative = \
        _precalculate(volume, rho, c, temp_h, temp_c, temp_air, temp_ground, s_iso_top, s_iso_wall_bot, lamb_iso_top,
                      lamb_iso_wall_bot, alpha_inside, alpha_outside)

    investArgs = {'minimum': 0,
                  'maximum': nominal_capacity,
                  'ep_costs': 170}

    pit_storage = GenericStoragePit(
        label=STORAGE_LABEL,
        inputs={bus_heat: flows.Flow()},
        outputs={
            bus_heat: flows.Flow()
        },
        loss_rate=loss_rate,
        fixed_losses_relative=fixed_losses_relative,
        fixed_losses_absolute=0,
        height_multiplication_factor=height_multiplication_factor,
        temp_h=temp_h,
        temp_c=temp_c,
        rho=rho,
        c=c,
        initial_storage_level=0.0,
        inflow_conversion_factor=1,
        outflow_conversion_factor=0.8,
        invest_relation_input_capacity=1,
        invest_relation_output_capacity=1,
        balanced=False,
        investment=solph.Investment(**investArgs),
    )

    energysystem.add(pit_storage)

    ##########################################################################
    # Optimise the energy system and plot the results
    ##########################################################################

    logging.info("Optimise the energy system")

    # initialise the operational model
    energysystem_model = Model(energysystem)

    # This is for debugging only. It is not(!) necessary to solve the problem
    # and should be set to False to save time and disc space in normal use. For
    # debugging the timesteps should be set to 3, to increase the readability
    # of the lp-file.
    if debug:
        file_path = os.path.join(
            helpers.extend_basic_path("lp_files"), "basic_example.lp"
        )
        logging.info(f"Store lp-file in {file_path}.")
        io_option = {"symbolic_solver_labels": True}
        energysystem_model.write(file_path, io_options=io_option)

    # if tee_switch is true solver messages will be displayed
    logging.info("Solve the optimization problem")
    energysystem_model.solve(
        solver=solver,
    )

    logging.info("Store the energy system with the results.")

    # The processing module of the outputlib can be used to extract the results
    # from the model transfer them into a homogeneous structured dictionary.

    # add results to the energy system to make it possible to store them.
    energysystem.results["main"] = processing.results(energysystem_model)
    energysystem.results["meta"] = processing.meta_results(energysystem_model)

    # The default path is the '.oemof' folder in your $HOME directory.
    # The default filename is 'es_dump.oemof'.
    # You can omit the attributes (as None is the default value) for testing
    # cases. You should use unique names/folders for valuable results to avoid
    # overwriting.
    if dump_results:
        energysystem.dump(dpath=None, filename=None)

    # *************************************************************************
    # ********** PART 2 - Processing the results ******************************
    # *************************************************************************

    # Saved data can be restored in a second script. So you can work on the
    # data analysis without re-running the optimisation every time. If you do
    # so, make sure that you really load the results you want. For example,
    # if dumping fails, you might exidentially load outdated results.
    if restore_results:
        logging.info("**** The script can be divided into two parts here.")
        logging.info("Restore the energy system and the results.")

        energysystem = EnergySystem()
        energysystem.restore(dpath=None, filename=None)

    # define an alias for shorter calls below (optional)
    results = energysystem.results["main"]
    storage = energysystem.groups[STORAGE_LABEL]

    # print a time slice of the state of charge
    start_time = datetime(2012, 2, 25, 8, 0, 0)
    end_time = datetime(2012, 2, 25, 17, 0, 0)

    print("\n********* State of Charge (slice) *********")
    print(f"{results[(storage, None)]['sequences'][start_time: end_time]}\n")

    # get all variables of a specific component/bus
    custom_storage = views.node(results, STORAGE_LABEL)
    heat_bus = views.node(results, "heat")

    # plot the time series (sequences) of a specific component/bus
    plot_figures_for(custom_storage)
    plot_figures_for(heat_bus)

    # print the solver results
    print("********* Meta results *********")
    pp.pprint(f"{energysystem.results['meta']}\n")

    # print the sums of the flows around the electricity bus
    print("********* Main results *********")
    print(heat_bus["sequences"].sum(axis=0))
    results_flows = custom_storage["sequences"]

    # Define the filename for the Excel file
    filename = 'results_flows.xlsx'

    # Export the combined DataFrame to an Excel file
    results_flows.to_excel(filename, index=False, engine='openpyxl')

    print(loss_rate)
    print(fixed_losses_relative)


if __name__ == "__main__":
    main()


