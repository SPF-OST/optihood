import pandas as pd
import numpy as np
import os
import loadProfilesResidential as Resi
import shoppingmall as Shop
from multiprocessing import Process, Queue
import concurrent.futures
import sys
try:
    import matplotlib.pyplot as plt
except ImportError:
    plt = None

# Parameters
optMode = "group"
createProfiles = False
cluster = False
numberOfBuildings = 1
numberOfOptimizations = 10


inputFilePath = "..\data\excels\\"
resultFilePath = "..\data\Results"
inputfileName = "scenario" + str(numberOfBuildings) + ".xls"

if optMode == "indiv":
    from energy_network import EnergyNetworkIndiv as EnergyNetwork
elif optMode == "group":
    from energy_network import EnergyNetworkGroup as EnergyNetwork


if createProfiles:
    residentialBuildings = pd.read_excel(os.path.join(inputFilePath, inputfileName), sheet_name="residential")
    for i in range(len(residentialBuildings)):
        res = residentialBuildings.iloc[i]
        building = Resi.Residential(res)
        building.create_profile()
    shoppingMalls = pd.read_excel(os.path.join(inputFilePath, inputfileName), sheet_name="mall")
    for i in range(len(shoppingMalls)):
        mall = shoppingMalls.iloc[i]
        building = Shop.Shopping(mall)
        building.create_profile()

if cluster:  # at the moment, we have 12 clusters (12 days in the analysis)
    clusterSize = {"2021-07-30": 26,
                   "2021-02-03": 44,
                   "2021-07-23": 32,
                   "2021-09-18": 28,
                   "2021-04-15": 22,
                   "2021-10-01": 32,
                   "2021-11-04": 32,
                   "2021-10-11": 37,
                   "2021-01-24": 15,
                   "2021-08-18": 26,
                   "2021-05-28": 23,
                   "2021-02-06": 48}
    timePeriod = ["2021-01-01 00:00:00",
                  "2021-01-12 23:00:00"]  # 1 Jan is a specific case (for elec_impact), so we start from 2
else:
    clusterSize = {}
    timePeriod = ["2021-01-01 00:00:00", "2021-12-31 23:00:00"]

optimizationOptions = {
    "gurobi": {
        "BarConvTol": 0.5,
        # The barrier solver terminates when the relative difference between the primal and dual objective values is less than the specified tolerance (with a GRB_OPTIMAL status)
        #"NonConvex":2, # when 0 error is being sent when non-convex, 1 when non-convex funktion could not be linearized, 2 bilinear form and spacial branching for non-convex
        "OptimalityTol": 1e-4,
        # Reduced costs must all be smaller than OptimalityTol in the improving direction in order for a model to be declared optimal
        # "PoolGap":1  #Determines how large a (relative) gap to tolerate in stored solutions. When this parameter is set to a non-default value, solutions whose objective values exceed that of the best known solution by more than the specified (relative) gap are discarded.
        "MIPGap": 1e-2,
        # Relative Tolerance between the best integer objective and the objective of the best node remaining
        "MIPFocus": 2
        # 1 feasible solution quickly. 2 proving optimality. 3 if the best objective bound is moving very slowly/focus on the bound
        # "Cutoff": #Indicates that you aren't interested in solutions whose objective values are worse than the specified value., could be dynamically be used in moo
    },
    "CBC ": {

    },
    "GLPK": {

    }}

if clusterSize:
    optimizationOptions['gurobi'][
        'MIPGap'] = 1e-4  # If clusterSize is set, reduce the MIP Gap parameter in optimizationOptions to 1e-4 (else 1% is acceptable)


def optimizeNetwork(network, instance, envImpactlimit):
    limit, capacitiesTransformers, capacitiesStorages = network.optimize(solver='gurobi', envImpactlimit=envImpactlimit,
                                                                         clusterSize=clusterSize,
                                                                         options=optimizationOptions)
    network.printInvestedCapacities(capacitiesTransformers, capacitiesStorages)
    network.printCosts()
    network.printEnvImpacts()
    if not os.path.exists(resultFilePath):
        os.makedirs(resultFilePath)
    network.exportToExcel(
        resultFilePath + "\\results" + str(numberOfBuildings) + '_' + str(instance) + '_' + optMode + '.xlsx')
    costs = network.getTotalCosts()
    meta = network.printMetaresults()
    print(limit)
    return (limit, costs, meta)


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


def f1(q):
    old_stdout = sys.stdout
    log_file = open("optimization1.log","w")
    sys.stdout = log_file
    print("******************\nOPTIMIZATION " + str(1) + "\n******************")
    network = EnergyNetwork(pd.date_range(timePeriod[0], timePeriod[1], freq="60min"))
    network.setFromExcel(os.path.join(inputFilePath, inputfileName), numberOfBuildings, clusterSize, opt="costs")
    (max_env, costs, meta) = optimizeNetwork(network, 1, 1000000)
    #costsListLast = meta['objective']
    sys.stdout = old_stdout
    log_file.close()
    q.put((max_env, meta['objective']))

def f2(q):
    old_stdout = sys.stdout
    log_file = open("optimization2.log", "w")
    sys.stdout = log_file
    print("******************\nOPTIMIZATION " + str(2) + "\n******************")
    network = EnergyNetwork(pd.date_range(timePeriod[0], timePeriod[1], freq="60min"))
    network.setFromExcel(os.path.join(inputFilePath, inputfileName), numberOfBuildings, clusterSize, opt="env")
    (min_env, costs, meta) = optimizeNetwork(network, 2, 1000000)
    # costsList.append(costs)
    # envList.append(min_env)
    sys.stdout = old_stdout
    log_file.close()
    q.put(min_env)

def fi(instance, envCost, q):
    old_stdout = sys.stdout
    log_file = open(f"optimization{instance}.log", "w")
    sys.stdout = log_file
    print("******************\nOPTIMIZATION " + str(instance) + "\n******************")
    network = EnergyNetwork(pd.date_range(timePeriod[0], timePeriod[1], freq="60min"))
    network.setFromExcel(os.path.join(inputFilePath, inputfileName), numberOfBuildings, clusterSize, opt="costs")
    (limit, costs, meta) = optimizeNetwork(network, instance, envCost + 1)
    #costsList.append(meta['objective'])
    #envList.append(limit)
    sys.stdout = old_stdout
    log_file.close()
    q.put((instance, meta['objective'], limit))


if __name__ == '__main__':
    costsList = (numberOfOptimizations-2)*[0]
    envList = (numberOfOptimizations-2)*[0]

    q1 = Queue()
    q2 = Queue()
    p1 = Process(target=f1, args=(q1,))
    p2 = Process(target=f2, args=(q2,))
    p1.start()
    p2.start()
    p1.join()
    p2.join()
    (max_env, costsListLast) = q1.get()
    min_env = q2.get()


    print(
        'Each iteration will keep emissions lower than some values between femissions_min and femissions_max, so [' + str(
            min_env) + ', ' + str(max_env) + ']')
    #steps = list(range(int(min_env), int(max_env), int((max_env - min_env) / (numberOfOptimizations - 1))))
    steps = list(np.geomspace(int(min_env), int(max_env), numberOfOptimizations-2, endpoint=False))
    print(steps)

    qi = Queue()
    processes = []
    for i in range(numberOfOptimizations - 2):
        instance = i + 3
        limit = steps[i]
        p = Process(target=fi, args=(instance, limit, qi,))
        processes.append(p)
        p.start()

    for p in processes:
        p.join()

    while not qi.empty():
        (instance, cost, env) = qi.get()
        costsList[instance - 3] = cost
        envList[instance - 3] = env

        # -----------------------------------------------------------------------------#
        ## Plot Paretofront ##
        # -----------------------------------------------------------------------------#

    costsList.append(costsListLast)
    envList.append(max_env)
    plotParetoFront(costsList, envList)
