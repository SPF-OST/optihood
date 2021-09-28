import pandas as pd
import os
try:
    import matplotlib.pyplot as plt
except ImportError:
    plt = None
from groups_indiv import EnergyNetwork

if __name__ == '__main__':
    # -----------------------------------------------------------------------------#
    ## First optimization ##
    # -----------------------------------------------------------------------------#
    print("******************")
    print("OPTIMIZATION 1")
    print("******************")
    network = EnergyNetwork(pd.date_range("2018-01-01 01:00:00", "2019-01-01 00:00:00", freq="60min"), tSH=35, tDHW=55)
    network.setFromExcel(os.path.join(os.getcwd(), "scenario4.xls"), opt="costs")
    network.printNodes()
    envImpact, capacitiesTransformers, capacitiesStorages = network.optimize(solver='gurobi', envImpactlimit=1000000)
    network.printInvestedCapacities(capacitiesTransformers, capacitiesStorages)
    meta = network.printMetaresults()
    network.printCosts()
    network.printEnvImpacts()
    maxEnvImpact = envImpact
    print(envImpact)
    network.exportToExcel('results4_1_indiv.xlsx', capacitiesTransformers, capacitiesStorages)

    costsList = [meta['objective']]
    envList = [envImpact]
    # -----------------------------------------------------------------------------#
    ## Second optimization ##
    # -----------------------------------------------------------------------------#
    print("******************")
    print("OPTIMIZATION 2")
    print("******************")
    network = EnergyNetwork(pd.date_range("2018-01-01 01:00:00", "2019-01-01 00:00:00", freq="60min"), tSH=35, tDHW=55)
    network.setFromExcel(os.path.join(os.getcwd(), "scenario4.xls"), opt="env")
    #network.printNodes()
    envImpact, capacitiesTransformers, capacitiesStorages = network.optimize(solver='gurobi', envImpactlimit=1000000)
    network.printInvestedCapacities(capacitiesTransformers, capacitiesStorages)
    network.printCosts()
    network.printEnvImpacts()
    minEnvImpact = envImpact
    print(envImpact)
    network.exportToExcel('results4_2_indiv.xlsx', capacitiesTransformers, capacitiesStorages)
    print('Each iteration will keep femissions lower than some values between femissions_min and femissions_max, so [' + str(min_env) + ', ' + str(max_env) + ']')

    # -----------------------------------------------------------------------------#
    ## Multi optimization ##
    # -----------------------------------------------------------------------------#
    network = EnergyNetwork(pd.date_range("2018-01-01 01:00:00", "2019-01-01 00:00:00", freq="60min"), tSH=35, tDHW=55)
    network.setFromExcel(os.path.join(os.getcwd(), "scenario4.xls"), opt="costs")

    n = 5
    step = int((maxEnvImpact - minEnvImpact) / n)
    steps = list(range(int(minEnvImpact), int(maxEnvImpact), step))

    j = 3
    for i in steps[::-1]:
        print("******************")
        print("OPTIMIZATION "+str(j))
        print("******************")
        print(i)
        #network.printNodes()
        envImpact, capacitiesTransformers, capacitiesStorages = network.optimize(solver='gurobi', envImpactlimit=i+1)
        network.exportToExcel('results4_'+str(j)+'_indiv.xlsx', capacitiesTransformers, capacitiesStorages)
        network.printInvestedCapacities(capacitiesTransformers, capacitiesStorages)
        meta = network.printMetaresults()
        network.printCosts()
        network.printEnvImpacts()
        print(envImpact)
        costsList.append(meta['objective'])
        envList.append(envImpact)
        j += 1

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


