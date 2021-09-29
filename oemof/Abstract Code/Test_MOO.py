import pandas as pd
import os
try:
    import matplotlib.pyplot as plt
except ImportError:
    plt = None
from groups_indiv import EnergyNetwork

def optimizeNetwork(network, buildingList, instance, aspectBalace):
    limit, capas_c, capas_s = network.optimize(solver='gurobi', e=aspectBalace)
    for buildingName in buildingList:
        network.printInvestedCapacities(capas_c, capas_s, buildingName)
    network.printCosts()
    network.printEnvImpacts()
    network.exportToExcel('results4_'+str(instance)+'_indiv.xlsx', capas_c, capas_s)
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
    buildingList = ["Building1", "Building2", "Building3", "Building4"]
    optimizationInstanceNumber = 1
    # -----------------------------------------------------------------------------#
    ## First optimization ##
    # -----------------------------------------------------------------------------#
    print("******************\nOPTIMIZATION " + str(optimizationInstanceNumber) + "\n******************")
    network = EnergyNetwork(pd.date_range("2018-01-01 01:00:00", "2019-01-01 00:00:00", freq="60min"), tSH=35, tDHW=55)
    network.setFromExcel(os.path.join(os.getcwd(), "scenario4.xls"), opt="costs")

    # network.printNodes()
    (max_env, meta) = optimizeNetwork(network, buildingList, optimizationInstanceNumber, 1000000)
    optimizationInstanceNumber += 1
    costsList = [meta['objective']]
    envList = [max_env]

    # -----------------------------------------------------------------------------#
    ## Second optimization ##
    # -----------------------------------------------------------------------------#
    print("******************\nOPTIMIZATION " + str(optimizationInstanceNumber) + "\n******************")
    network = EnergyNetwork(pd.date_range("2018-01-01 01:00:00", "2019-01-01 00:00:00", freq="60min"), tSH=35, tDHW=55)
    network.setFromExcel(os.path.join(os.getcwd(), "scenario4.xls"), opt="env")
    #network.printNodes()
    (min_env, meta) = optimizeNetwork(network, buildingList, optimizationInstanceNumber, 1000000)
    optimizationInstanceNumber += 1
    print('Each iteration will keep femissions lower than some values between femissions_min and femissions_max, so [' + str(min_env) + ', ' + str(max_env) + ']')


    network = EnergyNetwork(pd.date_range("2018-01-01 01:00:00", "2019-01-01 00:00:00", freq="60min"), tSH=35, tDHW=55)
    network.setFromExcel(os.path.join(os.getcwd(), "scenario4.xls"), opt="costs")

    n = 5
    steps = list(range(int(min_env), int(max_env), int((max_env - min_env) / n)))
    for envCost in steps[::-1]:
        print("******************\nOPTIMIZATION " + str(optimizationInstanceNumber) + "\n******************")
        print(envCost)
        #network.printNodes()
        (limit, meta) = optimizeNetwork(network, buildingList, optimizationInstanceNumber, envCost + 1)
        costsList.append(meta['objective'])
        envList.append(limit)
        optimizationInstanceNumber += 1

    # -----------------------------------------------------------------------------#
    ## Plot Paretofront ##
    # -----------------------------------------------------------------------------#
    plotParetoFront(costsList, envList)


