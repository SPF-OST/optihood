import pandas as pd
import os
import pathlib as _pl

from optihood.IO.writers import ScenarioFileWriterExcel
from optihood.energy_network import EnergyNetworkGroup as EnergyNetwork

if __name__ == '__main__':    

    optimization_type = "cost"
    scenario = "HP_GS_PV"
    # set a time period for the optimization problem
    timePeriod = pd.date_range("2018-01-01 00:00:00", "2018-01-31 23:00:00", freq="60min")

    # define paths for input and result files
    curDir = _pl.Path(__file__).resolve().parent
    inputFilePath = curDir / ".." / "configs" / "basic_example_config"
    configFileName = f"scenario_{scenario}_group.ini"
    inputfileName = f"scenario_{scenario}.xls"  # excel file which would be created by createScenarioFile()

    resultFilePath = curDir / ".." / "results"
    resultFileName = "results_example_config.xlsx"

    print("Scenario config file path: " + os.path.join(inputFilePath, configFileName))
    print("Scenario excel file path: " + os.path.join(inputFilePath, inputfileName))
    print("Result file path: " + os.path.join(resultFilePath, resultFileName))

    # initialize parameters
    numberOfBuildings = 4
    optimizationType = "costs"  # set as "env" for environmental optimization and "costs" for cost optimization
    mergeLinkBuses = True
    merge_buses = ["electricity", "space_heat", "domestic_hot_water"]

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

    # create scenario file from config file
    scenarioFileWriter = ScenarioFileWriterExcel(inputFilePath / configFileName, version='grouped',
                                                 nr_of_buildings=numberOfBuildings)
    scenarioFileWriter.write(inputFilePath / inputfileName)

    # create an energy network and set the network parameters from an excel file
    network = EnergyNetwork(timePeriod)
    network.setFromExcel(os.path.join(inputFilePath, inputfileName), numberOfBuildings, opt=optimizationType,
                         mergeLinkBuses=mergeLinkBuses, mergeBuses=merge_buses)

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
