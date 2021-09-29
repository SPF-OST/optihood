import pandas as pd
import os
try:
    import matplotlib.pyplot as plt
except ImportError:
    plt = None
from groups_indiv import EnergyNetwork
import time

numberOfBuildings = 4
numberOfOptimizations = 7
inputfileName = "scenario" + str(numberOfBuildings) + ".xls"

def optimizeNetwork(network, buildingList, instance, aspectBalace):
    print("start of opt"+str(time.time()))
    limit, capas_c, capas_s = network.optimize(solver='gurobi', e=aspectBalace)
    print("end of opt"+str(time.time()))
    for buildingName in buildingList:
        network.printInvestedCapacities(capas_c, capas_s, buildingName)
    network.printCosts()
    network.printEnvImpacts()
    network.exportToExcel('results' + str(numberOfBuildings) + '_' + str(instance) + '_indiv.xlsx', capas_c, capas_s)
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
    print("start of moo "+str(time.time()))
    buildingList = ["Building1", "Building2", "Building3", "Building4"]
    optimizationInstanceNumber = 1
    # -----------------------------------------------------------------------------#
    ## First optimization ##
    # -----------------------------------------------------------------------------#
    print("******************\nOPTIMIZATION " + str(optimizationInstanceNumber) + "\n******************")
    network = EnergyNetwork(pd.date_range("2018-01-01 01:00:00", "2019-01-01 00:00:00", freq="60min"), tSH=35, tDHW=55)
    network.setFromExcel(os.path.join(os.getcwd(), inputfileName), opt="costs")
    # network.printNodes()
    (max_env, meta) = optimizeNetwork(network, buildingList[::numberOfBuildings], optimizationInstanceNumber, 1000000)
    optimizationInstanceNumber += 1
    costsList = [meta['objective']]
    envList = [max_env]
    print("end of optimization " + str(1) + " in " + str(time.time()))
    # -----------------------------------------------------------------------------#
    ## Second optimization ##
    # -----------------------------------------------------------------------------#
    if numberOfOptimizations > 1:
        print("******************\nOPTIMIZATION " + str(optimizationInstanceNumber) + "\n******************")
        network = EnergyNetwork(pd.date_range("2018-01-01 01:00:00", "2019-01-01 00:00:00", freq="60min"), tSH=35, tDHW=55)
        network.setFromExcel(os.path.join(os.getcwd(), inputfileName), opt="env")
        #network.printNodes()
        (min_env, meta) = optimizeNetwork(network, buildingList, optimizationInstanceNumber, 1000000)
        optimizationInstanceNumber += 1
        print('Each iteration will keep femissions lower than some values between femissions_min and femissions_max, so [' + str(min_env) + ', ' + str(max_env) + ']')


        network = EnergyNetwork(pd.date_range("2018-01-01 01:00:00", "2019-01-01 00:00:00", freq="60min"), tSH=35, tDHW=55)
        network.setFromExcel(os.path.join(os.getcwd(), inputfileName), opt="costs")
        print("end of optimization " + str(2) + " in " + str(time.time()))
        steps = list(range(int(min_env), int(max_env), int((max_env - min_env) / (numberOfOptimizations-2))))
        for envCost in steps[::-1]:
            print("******************\nOPTIMIZATION " + str(optimizationInstanceNumber) + "\n******************")
            print(envCost)
            #network.printNodes()
            (limit, meta) = optimizeNetwork(network, buildingList, optimizationInstanceNumber, envCost + 1)
            costsList.append(meta['objective'])
            envList.append(limit)
            print("end of optimization "+str(optimizationInstanceNumber+2)+" in "+str(time.time()))
            optimizationInstanceNumber += 1

        # -----------------------------------------------------------------------------#
        ## Plot Paretofront ##
        # -----------------------------------------------------------------------------#
    plotParetoFront(costsList, envList)


