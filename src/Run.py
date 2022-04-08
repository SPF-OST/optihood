import pandas as pd
import os
import loadProfilesResidential as Resi
import shoppingmall as Shop
try:
    import matplotlib.pyplot as plt
except ImportError:
    plt = None


def createProfiles(profilesCreation, inputFilePath, inputfileName):
    if profilesCreation:
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


def optimizeNetwork(network, instance, envImpactlimit, clusterSize, optimizationOptions, resultFilePath, numberOfBuildings, optMode):
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


def optimization(numberOfBuildings, numberOfOptimizations, optMode, cluster):
    inputFilePath = "..\data\excels\\"
    resultFilePath = "..\data\Results"
    inputfileName = "scenario" + str(numberOfBuildings) + ".xls"
    if optMode == "indiv":
        from energy_network import EnergyNetworkIndiv as EnergyNetwork
    elif optMode == "group":
        from energy_network import EnergyNetworkGroup as EnergyNetwork
    if cluster:
        clusterSize = {"2018-07-30": 26,
                       "2018-02-03": 44,
                       "2018-07-23": 32,
                       "2018-09-18": 28,
                       "2018-04-15": 22,
                       "2018-10-01": 32,
                       "2018-11-04": 32,
                       "2018-10-11": 37,
                       "2018-01-24": 15,
                       "2018-08-18": 26,
                       "2018-05-28": 23,
                       "2018-02-06": 48}
        timePeriod = ["2018-01-01 00:00:00",
                      "2018-01-12 23:00:00"]  # 1 Jan is a specific case (for elec_impact), so we start from 2
    else:
        clusterSize = {}
        timePeriod = ["2018-01-01 00:00:00",
                      "2018-12-31 23:00:00"]
    optimizationOptions = {
        "gurobi": {
            "BarConvTol": 0.5,
            # The barrier solver terminates when the relative difference between the primal and dual objective values is less than the specified tolerance (with a GRB_OPTIMAL status)
            # "NonConvex":2, # when 0 error is being sent when non-convex, 1 when non-convex funktion could not be linearized, 2 bilinear form and spacial branching for non-convex
            "OptimalityTol": 1e-4,
            # Reduced costs must all be smaller than OptimalityTol in the improving direction in order for a model to be declared optimal
            # "PoolGap":1  #Determines how large a (relative) gap to tolerate in stored solutions. When this parameter is set to a non-default value, solutions whose objective values exceed that of the best known solution by more than the specified (relative) gap are discarded.
            "MIPGap": 0.01,
            # Relative Tolerance between the best integer objective and de objective of the best node remaining
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
            'MIPGap'] = 1e-4  # If clusterSize is set, reduce the MIP Gap parameter in optimizationOptions to 1e-4 (else 100 is acceptable)
    optimizationInstanceNumber = 1
    costsList = []
    envList = []
    # -----------------------------------------------------------------------------#
    ## First optimization ##
    # -----------------------------------------------------------------------------#
    print("******************\nOPTIMIZATION " + str(optimizationInstanceNumber) + "\n******************")
    network = EnergyNetwork(pd.date_range(timePeriod[0], timePeriod[1], freq="60min"), tSH=35, tDHW=55)
    network.setFromExcel(os.path.join(inputFilePath, inputfileName), numberOfBuildings, clusterSize, opt="costs")
    (max_env, costs, meta) = optimizeNetwork(network, optimizationInstanceNumber, 1000000, clusterSize, optimizationOptions, resultFilePath, numberOfBuildings, optMode)
    optimizationInstanceNumber += 1
    costsListLast = meta['objective']
    envListLast = max_env
    # -----------------------------------------------------------------------------#
    ## Second optimization ##
    # -----------------------------------------------------------------------------#
    if numberOfOptimizations > 1:
        print("******************\nOPTIMIZATION " + str(optimizationInstanceNumber) + "\n******************")
        network = EnergyNetwork(pd.date_range(timePeriod[0], timePeriod[1], freq="60min"), tSH=35, tDHW=55)
        network.setFromExcel(os.path.join(inputFilePath, inputfileName), numberOfBuildings, clusterSize, opt="env")
        (min_env, costs, meta) = optimizeNetwork(network, optimizationInstanceNumber, 1000000, clusterSize, optimizationOptions, resultFilePath, numberOfBuildings, optMode)
        optimizationInstanceNumber += 1
        costsList.append(costs)
        envList.append(min_env)
        print(
            'Each iteration will keep emissions lower than some values between femissions_min and femissions_max, so ['
            + str(min_env) + ', ' + str(max_env) + ']')

        # -----------------------------------------------------------------------------#
        ## MOO steps between Cost-Optimized and Env-Optimized ##
        # -----------------------------------------------------------------------------#
        steps = list(range(int(min_env), int(max_env), int((max_env - min_env) / (numberOfOptimizations - 1))))
        for envCost in steps[1:numberOfOptimizations - 1]:
            print("******************\nOPTIMIZATION " + str(optimizationInstanceNumber) + "\n******************")
            network = EnergyNetwork(pd.date_range(timePeriod[0], timePeriod[1], freq="60min"), tSH=35,
                                    tDHW=55)
            network.setFromExcel(os.path.join(inputFilePath, inputfileName), numberOfBuildings, clusterSize,
                                 opt="costs")
            (limit, costs, meta) = optimizeNetwork(network, optimizationInstanceNumber, envCost + 1, clusterSize, optimizationOptions, resultFilePath, numberOfBuildings, optMode)
            costsList.append(meta['objective'])
            envList.append(limit)
            optimizationInstanceNumber += 1
    costsList.append(costsListLast)
    envList.append(envListLast)
    return costsList, envList
