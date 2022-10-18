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


def plotParetoFront(filePath, costsList, envList):
    plt.figure()
    plt.plot(costsList, envList, 'o-.')
    plt.xlabel('Costs (CHF)')
    plt.ylabel('Emissions (kgCO2eq)')
    plt.title('Pareto-front')
    plt.grid(True)
    plt.savefig(filePath)
    print("Costs : (CHF)")
    print(costsList)
    print("Emissions : (kgCO2)")
    print(envList)

if __name__ == '__main__':

    # set a time period for the optimization problem
    timePeriod = pd.date_range("2018-01-01 00:00:00", "2018-12-31 23:00:00", freq="60min")

    # define paths for input and result files
    inputFilePath = r"..\excels"
    inputfileName = "scenario.xls"

    resultFilePath =r"..\results"

    # initialize parameters
    numberOfOptimizations = 5       # number of optimizations in multi objective optimization pareto front
    numberOfBuildings = 4

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

    # lists of costs and environmental impacts for different optimizations
    costsList = []
    envList = []

    for opt in range(1, numberOfOptimizations+1):

        # First optimization is by Cost alone
        # Second optimization is by Environmental impact alone
        # Third optimization onwards are the steps in between Cost-Optimized and Env-Optimized (by epsilon constraint method)

        if opt == 2:        # Environmental optimization
            optimizationType = "env"
            envImpactlimit = 1000000
        else:
            optimizationType = "costs"
            if opt == 1:    # Cost optimization
                envImpactlimit = 1000000
            else:           # Constrained optimization for multi-objective analysis (steps between Cost-Optimized and Env-Optimized)
                envImpactlimit = steps[opt - 3]

        print("******************\nOPTIMIZATION " + str(opt) + "\n******************")

        # create an energy network and set the network parameters from an excel file
        network = EnergyNetwork(timePeriod)
        network.setFromExcel(os.path.join(inputFilePath, inputfileName), numberOfBuildings, opt=optimizationType)

        # optimize the energy network
        env, capacitiesTransformers, capacitiesStorages = network.optimize(solver='gurobi',
                                                                           envImpactlimit=envImpactlimit,
                                                                           numberOfBuildings=numberOfBuildings,
                                                                           options=optimizationOptions)

        # print optimization outputs i.e. costs, environmental impact and capacities selected for different components (with investment optimization)
        network.printInvestedCapacities(capacitiesTransformers, capacitiesStorages)
        network.printCosts()
        network.printEnvImpacts()

        # save results
        resultFileName = "results" + str(numberOfBuildings) + '_' + str(opt) + '.xlsx'    # result filename for each optimization

        if not os.path.exists(resultFilePath):
            os.makedirs(resultFilePath)

        network.exportToExcel(os.path.join(resultFilePath, resultFileName))

        costs = network.getTotalCosts()
        meta = network.printMetaresults()

        if opt == 1:  # Cost optimization
            costsListLast = meta['objective']
            envListLast = env
            max_env = env
        else:
            if opt == 2:  # Environmental optimization
                min_env = env
                costsList.append(costs)
                # Define steps for multi-objective optimization
                steps = list(range(int(min_env), int(max_env), int((max_env - min_env) / (numberOfOptimizations - 1))))[1:]
            else:  # Constrained optimization for multi-objective analysis (steps between Cost-Optimized and Env-Optimized)
                costsList.append(meta['objective'])
            envList.append(env)

    costsList.append(costsListLast)
    envList.append(envListLast)

    # plot pareto front to visualize multi objective optimization results
    figureFilePath = r"..\figures"
    figureFileName = f"Pareto.png"

    plotParetoFront(os.path.join(figureFilePath, figureFileName), costsList, envList)


