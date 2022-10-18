import pandas as pd
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

if __name__ == '__main__':

    # set a time period for the optimization problem
    timePeriod = pd.date_range("2018-01-01 00:00:00", "2018-01-31 23:00:00", freq="60min")

    # define paths for input and result files
    inputFilePath = r"..\excels\basic_example"
    inputfileName = "scenario.xls"

    resultFilePath =r"..\results"
    resultFileName ="results.xlsx"

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

    # plot sankey diagram
    UseLabelDict = True     # a dictionary defining the labels to be used for different flows
    figureFilePath = r"..\figures"
    sankeyFileName = f"Sankey_{numberOfBuildings}_{optimizationType}.html"

    snk.plot(os.path.join(resultFilePath, resultFileName), os.path.join(figureFilePath, sankeyFileName),
                   numberOfBuildings, UseLabelDict)

    # plot detailed energy flow
    plotLevel = "allMonths"  # permissible values (for energy balance plot): "allMonths" {for all months}
    # or specific month {"Jan", "Feb", "Mar", etc. three letter abbreviation of the month name}
    # or specific date {format: YYYY-MM-DD}
    plotType = "bokeh"  # permissible values: "energy balance", "bokeh"
    flowType = "electricity"  # permissible values: "all", "electricity", "space heat", "domestic hot water"

    fnc.plot(os.path.join(resultFilePath, resultFileName), figureFilePath, plotLevel, plotType, flowType)

