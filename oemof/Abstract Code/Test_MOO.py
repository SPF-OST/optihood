import pandas as pd
from oemof.tools import logger
import logging
import os
from ttictoc import tic,toc
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
    # network.printNodes()
    limit, capas_c, capas_s = network.optimize(solver='gurobi', e=1000000)
    network.printInvestedCapacities(capas_c, capas_s, "Building1")
    network.printInvestedCapacities(capas_c, capas_s, "Building2")
    network.printInvestedCapacities(capas_c, capas_s, "Building3")
    network.printInvestedCapacities(capas_c, capas_s, "Building4")
    meta = network.printMetaresults()
    network.printCosts()
    network.printEnvImpacts()
    max_env = limit
    print(limit)
    network.exportToExcel('results4_1_indiv.xlsx', capas_c, capas_s)

    costsList = [meta['objective']]
    envList = [limit]
    # -----------------------------------------------------------------------------#
    ## Second optimization ##
    # -----------------------------------------------------------------------------#
    print("******************")
    print("OPTIMIZATION 2")
    print("******************")
    network = EnergyNetwork(pd.date_range("2018-01-01 01:00:00", "2019-01-01 00:00:00", freq="60min"), tSH=35, tDHW=55)
    network.setFromExcel(os.path.join(os.getcwd(), "scenario4.xls"), opt="env")
    #network.printNodes()
    limit, capas_c, capas_s = network.optimize(solver='gurobi', e=1000000)
    network.printInvestedCapacities(capas_c, capas_s, "Building1")
    network.printInvestedCapacities(capas_c, capas_s, "Building2")
    network.printInvestedCapacities(capas_c, capas_s, "Building3")
    network.printInvestedCapacities(capas_c, capas_s, "Building4")
    network.printCosts()
    network.printEnvImpacts()
    min_env = limit
    print(limit)
    network.exportToExcel('results4_2_indiv.xlsx', capas_c, capas_s)
    print('Each iteration will keep femissions lower than some values between femissions_min and femissions_max, so [' + str(min_env) + ', ' + str(max_env) + ']')

    # -----------------------------------------------------------------------------#
    ## Multi optimization ##
    # -----------------------------------------------------------------------------#
    network = EnergyNetwork(pd.date_range("2018-01-01 01:00:00", "2019-01-01 00:00:00", freq="60min"), tSH=35, tDHW=55)
    network.setFromExcel(os.path.join(os.getcwd(), "scenario4.xls"), opt="costs")

    n = 5
    step = int((max_env - min_env) / n)
    steps = list(range(int(min_env), int(max_env), step))

    j = 3
    for i in steps[::-1]:
        print("******************")
        print("OPTIMIZATION "+str(j))
        print("******************")
        print(i)
        #network.printNodes()
        limit, capas_c, capas_s = network.optimize(solver='gurobi', e=i+1)
        network.exportToExcel('results4_'+str(j)+'_indiv.xlsx', capas_c, capas_s)
        network.printInvestedCapacities(capas_c, capas_s, "Building1")
        network.printInvestedCapacities(capas_c, capas_s, "Building2")
        network.printInvestedCapacities(capas_c, capas_s, "Building3")
        network.printInvestedCapacities(capas_c, capas_s, "Building4")
        meta = network.printMetaresults()
        network.printCosts()
        network.printEnvImpacts()
        print(limit)
        costsList.append(meta['objective'])
        envList.append(limit)
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


