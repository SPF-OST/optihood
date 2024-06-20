import pandas as pd
import pathlib as _pl
import os
try:
    import matplotlib.pyplot as plt
except ImportError:
    plt = None

## import energy network class
# EnergyNetworkIndiv for individual optimization
# EnergyNetworkGroup for grouped optimization

from optihood.energy_network import EnergyNetworkIndiv as EnergyNetwork

# import plotting methods for Sankey and detailed plots

import optihood.plot_sankey as snk
import optihood.plot_functions as fnc


def run_example(show_plots=True):
    # set a time period for the optimization problem
    timePeriod = pd.date_range("2018-01-01 00:00:00", "2018-01-31 23:00:00", freq="60min")

    # define paths for input and result files
    curDir = _pl.Path(__file__).resolve().parent
    inputFilePath = curDir / ".." / "excels" / "basic_example"
    inputfileName = "scenario.xls"

    resultFilePath = curDir / ".." / "results"
    resultFileName ="results_basic_example.xls"

    # initialize parameters
    numberOfBuildings = 4
    optimizationType = "costs"  # set as "env" for environmental optimization

    # create an energy network and set the network parameters from an excel file
    network = EnergyNetwork(timePeriod)
    network.setFromExcel(os.path.join(inputFilePath, inputfileName), numberOfBuildings, opt=optimizationType)

    # optimize the energy network
    limit, capacitiesTransformers, capacitiesStorages = network.optimize(solver='gurobi', numberOfBuildings=numberOfBuildings)

    # print optimization outputs i.e. costs, environmental impact and capacities selected for different components (with investment optimization)
    network.printInvestedCapacities(capacitiesTransformers, capacitiesStorages)
    network.printCosts()
    network.printEnvImpacts()
    network.printMetaresults()

    # save results
    if not os.path.exists(resultFilePath):
        os.makedirs(resultFilePath)
    network.exportToExcel(os.path.join(resultFilePath, resultFileName))

    if show_plots:
        show_plots_basic_example(curDir, numberOfBuildings, optimizationType, resultFileName, resultFilePath)


def show_plots_basic_example(curDir, numberOfBuildings, optimizationType, resultFileName, resultFilePath):
    figureFilePath = curDir / ".." / "figures"

    plot_sankey_diagram(figureFilePath, numberOfBuildings, optimizationType, resultFileName, resultFilePath, show_figs=True)

    plot_bokeh(figureFilePath, numberOfBuildings, resultFileName, resultFilePath)


def plot_bokeh(figureFilePath, numberOfBuildings, resultFileName, resultFilePath):
    # plot detailed energy flow
    plotLevel = "allMonths"  # permissible values (for energy balance plot): "allMonths" {for all months}
    # or specific month {"Jan", "Feb", "Mar", etc. three letter abbreviation of the month name}
    # or specific date {format: YYYY-MM-DD}
    plotType = "bokeh"  # permissible values: "energy balance", "bokeh"
    flowType = "electricity"  # permissible values: "all", "electricity", "space heat", "domestic hot water"
    fnc.plot(os.path.join(resultFilePath, resultFileName), figureFilePath, numberOfBuildings, plotLevel, plotType,
             flowType)


def plot_sankey_diagram(figureFilePath, numberOfBuildings, optimizationType, resultFileName, resultFilePath, show_figs: bool):
    # plot sankey diagram
    UseLabelDict = True  # a dictionary defining the labels to be used for different flows

    if not os.path.exists(figureFilePath):
        os.makedirs(figureFilePath)
    sankeyFileName = f"Sankey_{numberOfBuildings}_{optimizationType}.html"
    if not os.path.exists(figureFilePath):
        os.makedirs(figureFilePath)
    snk.plot(os.path.join(resultFilePath, resultFileName), os.path.join(figureFilePath, sankeyFileName),
             numberOfBuildings, UseLabelDict, labels='default', optimType='indiv', show_figs=show_figs)


if __name__ == '__main__':
    run_example()
