import pandas as pd
import os
import pathlib as _pl

from optihood.IO.writers import ScenarioFileWriterExcel
from optihood.energy_network import EnergyNetworkGroup as EnergyNetwork

if __name__ == '__main__':
    # set a time period for the optimization problem
    timePeriod = pd.date_range("2018-06-01 00:00:00", "2018-12-31 23:00:00", freq="60min")

    # define paths for input and result files
    curDir = _pl.Path(__file__).resolve().parent
    inputFilePath = curDir / ".." / "excels" / "solar_ice_hp"
    inputfileName = "scenario.xls"

    resultFilePath = curDir / ".." / "results"
    resultFileName = "results_solar_ice_hp.xlsx"

    print("Scenario file path: " + os.path.join(inputFilePath, inputfileName))
    print("Result file path: " + os.path.join(resultFilePath, resultFileName))

    # initialize parameters
    numberOfBuildings = 4
    optimizationType = "costs"  # set as "env" for environmental optimization and "costs" for cost optimization
    mergeLinkBuses = False
    mergeBuses = [] # "electricity", "heatPumpInputBus"
    dispatchMode = True  # Set to True to run the optimization in dispatch mode

    # solver specific command line options
    optimizationOptions = {
        "gurobi": {
            "BarConvTol": 0.5,
            # The barrier solver terminates when the relative difference between the primal and dual objective values
            # is less than the specified tolerance (with a GRB_OPTIMAL status)
            "OptimalityTol": 1e-4,
            # Reduced costs must all be smaller than OptimalityTol in the improving direction in order for a model to
            # be declared optimal
            "MIPGap": 1e-2,
            # Relative Tolerance between the best integer objective and the objective of the best node remaining
            "MIPFocus": 2
            # 1 feasible solution quickly. 2 proving optimality. 3 if the best objective bound is moving very
            # slowly/focus on the bound "Cutoff": #Indicates that you aren't interested in solutions whose objective
            # values are worse than the specified value., could be dynamically be used in moo
        }
        # add the command line options of the solver here, For example to use CBC add a new item to the dictionary
        # "cbc": {"tee": False}
    }

    # create an energy network and set the network parameters from an excel file
    network = EnergyNetwork(timePeriod, temperatureLevels=True)
    network.setFromExcel(os.path.join(inputFilePath, inputfileName), numberOfBuildings, opt=optimizationType,
                         mergeLinkBuses=mergeLinkBuses, mergeBuses=mergeBuses, dispatchMode=dispatchMode)

    # optimize the energy network
    limit, capacitiesTransformers, capacitiesStorages = network.optimize(solver='gurobi',
                                                                         numberOfBuildings=numberOfBuildings,
                                                                         options=optimizationOptions,
                                                                         mergeLinkBuses=mergeLinkBuses)

    # print optimization outputs i.e. costs, environmental impact and capacities selected for different components (
    # with investment optimization)
    network.printInvestedCapacities(capacitiesTransformers, capacitiesStorages)
    network.printCosts()
    network.printEnvImpacts()
    network.printMetaresults()

    # save results
    if not os.path.exists(resultFilePath):
        os.makedirs(resultFilePath)
    network.exportToExcel(os.path.join(resultFilePath, resultFileName), mergeLinkBuses=mergeLinkBuses)
