import pandas as pd
import os
try:
    import matplotlib.pyplot as plt
except ImportError:
    plt = None
from groups_indiv import EnergyNetwork
from groups_group import EnergyNetwork
import time

numberOfBuildings = 4
numberOfOptimizations = 7
inputfileName = "scenario" + str(numberOfBuildings) + ".xls"
optimizationOptions ={
                    "BarConvTol":1.0,
                    "NonConvex":2,
                    "OptimalityTol":1e-4,
                    "MIPGap":1000
                    }

def optimizeNetwork(network, instance, envImpactlimit):
    limit, capas_c, capas_s = network.optimize(solver='gurobi', envImpactlimit=envImpactlimit, options=optimizationOptions)
    network.printInvestedCapacities(capas_c, capas_s)
    network.printCosts()
    network.printEnvImpacts()
    network.exportToExcel('results' + str(numberOfBuildings) + '_' + str(instance) + '_indiv.xlsx')
    meta = network.printMetaresults()
    print(limit)
    return(limit, meta)


def plotParetoFront(costsList, envList):
    plt.figure()
    plt.plot(costsList, envList, 'o-.')
    plt.xlabel('Costs (CHF)')
    plt.ylabel('Emissions (kgCO2eq)')
    plt.title('Pareto-front')
    plt.grid(True)
    plt.savefig("ParetoFront.png")
    print("Costs : (CHF)")
    print(costsList)
    print("Emissions : (kgCO2)")
    print(envList)


if __name__ == '__main__':
    optimizationInstanceNumber = 1
    # -----------------------------------------------------------------------------#
    ## First optimization ##
    # -----------------------------------------------------------------------------#
    print("******************\nOPTIMIZATION " + str(optimizationInstanceNumber) + "\n******************")
    network = EnergyNetwork(pd.date_range("2018-01-01 01:00:00", "2019-01-01 00:00:00", freq="60min"), tSH=35, tDHW=55)
    network.setFromExcel(os.path.join(os.getcwd(), inputfileName), opt="costs")
    (max_env, meta) = optimizeNetwork(network, optimizationInstanceNumber, 1000000)
    optimizationInstanceNumber += 1
    costsList = [meta['objective']]
    envList = [max_env]
    # -----------------------------------------------------------------------------#
    ## Second optimization ##
    # -----------------------------------------------------------------------------#
    if numberOfOptimizations > 1:
        print("******************\nOPTIMIZATION " + str(optimizationInstanceNumber) + "\n******************")
        network = EnergyNetwork(pd.date_range("2018-01-01 01:00:00", "2019-01-01 00:00:00", freq="60min"), tSH=35, tDHW=55)
        network.setFromExcel(os.path.join(os.getcwd(), inputfileName), opt="env")
        (min_env, meta) = optimizeNetwork(network, optimizationInstanceNumber, 1000000)
        optimizationInstanceNumber += 1
        print('Each iteration will keep femissions lower than some values between femissions_min and femissions_max, so [' + str(min_env) + ', ' + str(max_env) + ']')

        # -----------------------------------------------------------------------------#
        ## MOO steps between Cost-Optimized and Env-Optimized ##
        # -----------------------------------------------------------------------------#
        network = EnergyNetwork(pd.date_range("2018-01-01 01:00:00", "2019-01-01 00:00:00", freq="60min"), tSH=35, tDHW=55)
        network.setFromExcel(os.path.join(os.getcwd(), inputfileName), opt="costs")
        steps = list(range(int(min_env), int(max_env), int((max_env - min_env) / (numberOfOptimizations-2))))
        for envCost in steps[::-1]:
            print("******************\nOPTIMIZATION " + str(optimizationInstanceNumber) + "\n******************")
            (limit, meta) = optimizeNetwork(network, optimizationInstanceNumber, envCost + 1)
            costsList.append(meta['objective'])
            envList.append(limit)
            optimizationInstanceNumber += 1

        # -----------------------------------------------------------------------------#
        ## Plot Paretofront ##
        # -----------------------------------------------------------------------------#
    plotParetoFront(costsList, envList)


