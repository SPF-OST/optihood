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
    timePeriod = pd.date_range("2018-01-01 00:00:00", "2018-12-31 23:00:00", freq="60min")

    # define paths for input and result files
    inputFilePath = r"..\excels"
    inputfileName = "scenario.xls"

    resultFilePath =r"..\results"
    resultFileName ="results.xlsx"

    # initialize parameters
    numberOfBuildings = 4
    temperatureSH = 35
    temperatureDHW = 55
    optimizationType = "costs"  # set as "env" for environmental optimization

    # solver specific command line options
    optimizationOptions = {
        "gurobi": {
            "BarConvTol": 0.5,
            # The barrier solver terminates when the relative difference between the primal and dual objective values is less than the specified tolerance (with a GRB_OPTIMAL status)
            "OptimalityTol": 1e-4,
            # Reduced costs must all be smaller than OptimalityTol in the improving direction in order for a model to be declared optimal
            "MIPGap": 1e-2,
            # Relative Tolerance between the best integer objective and the objective of the best node remaining
            "MIPFocus": 2
            # 1 feasible solution quickly. 2 proving optimality. 3 if the best objective bound is moving very slowly/focus on the bound
            # "Cutoff": #Indicates that you aren't interested in solutions whose objective values are worse than the specified value., could be dynamically be used in moo
        }
        # add the command line options of the solver here, For example to use CBC add a new item to the dictionary
        #"cbc": {"tee": False}
    }

    # create an energy network and set the network parameters from an excel file
    network = EnergyNetwork(timePeriod)
    network.setFromExcel(os.path.join(inputFilePath, inputfileName), numberOfBuildings, opt=optimizationType)

    # optimize the energy network
    limit, capacitiesTransformers, capacitiesStorages = network.optimize(solver='gurobi',
                                                                         options=optimizationOptions)

    # print optimization outputs i.e. costs, environmental impact and capacities selected for different components (with investment optimization)
    network.printInvestedCapacities(capacitiesTransformers, capacitiesStorages)
    network.printCosts()
    network.printEnvImpacts()

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

