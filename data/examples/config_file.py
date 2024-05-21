import pandas as pd
import os
try:
    import matplotlib.pyplot as plt
except ImportError:
    plt = None

## import energy network class
# EnergyNetworkIndiv for individual optimization
# EnergyNetworkGroup for grouped optimization

from optihood.energy_network import EnergyNetworkGroup as EnergyNetwork

# import plotting methods for Sankey and detailed plots

import optihood.plot_sankey as snk
import optihood.plot_functions as fnc

if __name__ == '__main__':
    type = 'group'
    # set a time period for the optimization problem
    timePeriod = pd.date_range("2018-01-01 00:00:00", "2018-01-31 23:00:00", freq="60min")

    # define paths for input and result files
    configFilePath = r"..\excels\config_file"
    configfileName = "scenario_group.ini"
    excelfileName = "scenario.xls"
    resultFilePath =r"..\results\config_file\{}".format(type)
    resultFileName ="results.xlsx"

    # initialize parameters
    numberOfBuildings = 4
    optimizationType = "costs"  # set as "env" for environmental optimization
    mergeLinkBuses = False
    dispatchMode = False  # Set to True to run the optimization in dispatch mode
    # create an energy network and set the network parameters from an excel file
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
        # "cbc": {"tee": False}
    }

    network = EnergyNetwork(timePeriod, temperatureLevels=False)
    network.createScenarioFile(os.path.join(configFilePath, configfileName), os.path.join(configFilePath, excelfileName), numberOfBuildings)
    network.setFromExcel(os.path.join(configFilePath, excelfileName), numberOfBuildings, opt=optimizationType,
                          mergeLinkBuses=mergeLinkBuses, dispatchMode=dispatchMode)

    # optimize the energy network
    limit, capacitiesTransformers, capacitiesStorages = network.optimize(solver='gurobi',
                                                                         numberOfBuildings=numberOfBuildings,
                                                                         options=optimizationOptions,
                                                                         mergeLinkBuses=mergeLinkBuses)
    # print optimization outputs i.e. costs, environmental impact and capacities selected for different components (with investment optimization)
    network.printInvestedCapacities(capacitiesTransformers, capacitiesStorages)
    network.printCosts()
    network.printEnvImpacts()
    network.printMetaresults()

    # save results
    if not os.path.exists(resultFilePath):
        os.makedirs(resultFilePath)
    network.exportToExcel(os.path.join(resultFilePath, resultFileName), mergeLinkBuses=mergeLinkBuses)


