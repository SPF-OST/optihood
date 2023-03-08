
from KPI_functions import *

pd.set_option('display.max_columns', 20)

labelDict['CHPHeatImpactTotal'] = 'CHPh'
labelDict['GWHPImpactTotal'] = 'GWHP'
labelDict['HPImpactTotal'] = 'HP'
labelDict['ElectricRodImpactTotal'] = 'ElectricRod'
labelDict['GasBoilerImpactTotal'] = 'GasBoiler'
labelDict['SolarCollectorImpactTotal'] = 'SolarCollector'

labelDict['CHPImpactTotal'] = 'CHP'
labelDict['CHPElecImpactTotal'] = 'CHPe'
labelDict['PVImpactTotal'] = 'PV'
labelDict['GridImpactTotal'] = 'Grid'

labelDict['CHPshTotal'] = 'CHPh'
labelDict['GWHPshTotal'] = 'GWHP'
labelDict['GasBoilershTotal'] = 'GasBoiler'
labelDict['HPshTotal'] = 'HP'
labelDict['ElectricRodshTotal'] = 'ElectricRod'

labelDict['CHPdhwTotal'] = 'CHPh'
labelDict['GWHPdhwTotal'] = 'GWHP'
labelDict['GasBoilerdhwTotal'] = 'GasBoiler'
labelDict['HPdhwTotal'] = 'HP'
labelDict['ElectricRoddhwTotal'] = 'ElectricRod'

labelDict['CHPTotal'] = 'CHPh'
labelDict['GWHPTotal'] = 'GWHP'
labelDict['GasBoilerTotal'] = 'GasBoiler'
labelDict['HPTotal'] = 'HP'
labelDict['ElectricRodTotal'] = 'ElectricRod'
labelDict['PVTotal'] = 'PV'
labelDict['gridTotal'] = 'Grid'
labelDict['excessTotal'] = 'Excess'

for b in range(6):
    for h in ["shSourceBus", "dhwStorageBus"]:
        labelDict["(('CHP__Building" + str(b+1) + "', '" + str(h) + "__Building" + str(b+1) + "'), 'flow')"] = "CHP" + str(h) + "_B" + str(b+1)
        labelDict["(('GWHP__Building" + str(b+1) + "', '" + str(h) + "__Building" + str(b+1) + "'), 'flow')"] = "GWHP" + str(h) + "_B" + str(b+1)
        labelDict["(('GasBoiler__Building" + str(b+1) + "', '" + str(h) + "__Building" + str(b+1) + "'), 'flow')"] = "GasBoiler" + str(h) + "_B" + str(b+1)
        labelDict["(('HP__Building" + str(b+1) + "', '" + str(h) + "__Building" + str(b+1) + "'), 'flow')"] = "HP" + str(h) + "_B" + str(b+1)
        labelDict["(('ElectricRod__Building" + str(b+1) + "', '" + str(h) + "__Building" + str(b+1) + "'), 'flow')"] = "ElectricRod" + str(h) + "_B" + str(b+1)

    labelDict["(('electricityBus__Building" + str(b+1) + "', 'excesselectricityBus__Building" + str(b+1) + "'), 'flow')"] = "excessElec_B" + str(b+1)
    labelDict["(('solarCollector__Building" + str(b+1) + "', 'dhwStorageBus__Building" + str(b+1) + "'), 'flow')"] = "solarCollectordhw_B" + str(b+1)

    labelDict["('heat_solarCollector__Building" + str(b+1) + "', 'solarConnectBus__Building" + str(b+1) + "')"] = "solarConnectBus"
    labelDict["('pv__Building" + str(b+1) + "', 'electricityProdBus__Building" + str(b+1) + "')"] = "PV"
    labelDict["('CHP__Building" + str(b+1) + "', 'shSourceBus__Building" + str(b+1) + "')"] = 'CHP'
    labelDict["('GasBoiler__Building" + str(b+1) + "', 'shSourceBus__Building" + str(b+1) + "')"] = "GasBoiler"
    labelDict["('GWHP__Building" + str(b+1) + "', 'shSourceBus__Building" + str(b+1) + "')"] = 'GWHP'
    labelDict["('HP__Building" + str(b+1) + "', 'shSourceBus__Building" + str(b+1) + "')"] = 'HP'
    labelDict["('ElectricRod__Building" + str(b+1) + "', 'shSourceBus__Building" + str(b+1) + "')"] = 'ElectricRod'




def run_kpi(dataDict, inputFileName, buildings, selected_days,
            elecEmission, elecCost, gasEmission, gasCost, rangeToConsider,
            outputFileName, iter, iterRange, optMode, results):

    # use the functions you need to plot
    selfsuffisant(dataDict, buildings, outputFileName, selected_days, 'month', iter, iterRange, results)
    selfsuffisant(dataDict, buildings, outputFileName, selected_days, 'hour', iter, iterRange, results)
    full_load_hour(dataDict, buildings, iter, outputFileName)
    heat_distr(dataDict, buildings, iter, outputFileName, 'year')
    heat_distr(dataDict, buildings, iter, outputFileName, 'month')
    installed_capacity(dataDict, buildings, outputFileName, iter, iterRange, results, 'building')
    results = iter_heat(dataDict, buildings, outputFileName, iter, iterRange, results)
    results = selfsuffisant(dataDict, buildings, outputFileName, selected_days, 'year', iter, iterRange, results)
    results = installed_capacity(dataDict, buildings, outputFileName, iter, iterRange, results, 'grouped')
    stacked_full_load(dataDict, buildings, iter, outputFileName)
    flexibilityBarChart(dataDict, inputFileName, buildings, gasCost, elecCost, gasEmission, elecEmission,
                        optMode, outputFileName, selected_days, iter, iterRange, rangeToConsider, results)

    return results

if __name__ == "__main__":
    optMode = "group"  # parameter defining whether the results file corresponds to "indiv" or "group" optimization
    numberOfBuildings = 4 # number of buildings in the scenario
    iterOptim = 5 # number of iterations to plot
    iterRange = [1] + list(range(iterOptim, 1, -1)) # create list to define the order of to plot the iterations

    UseLabelDict = True

    rangeToConsider = pd.date_range('2021-01-01 00:00:00', '2021-12-31 23:00:00', freq='H')

    # link to the folder
    folder = "group_sm_8ct/"

    inputFileName = folder + "scenario"  # link to the scenario file
    outputFileName = folder + "Results/KPI/"

    # link to csv or constant value
    elecEmission = "excels/electricity_impact.csv"
    elecCost = "group_sm_8ct/excels/electricity_cost.csv"
    gasEmission = 0.228
    gasCost = 0.087

    if not os.path.exists(outputFileName):
        os.mkdir(outputFileName)

    # selfsuffisant KPI can also be displayed by single days
    selected_days = [] # pd.to_datetime({'year': [2021, 2021, 2021],
                       #             'month': [2, 8, 11],
                       #             'day': [4, 15, 25]})

    results = {}
    for iter in iterRange:
        excelFileName = os.path.join(folder + "Results/", f"results{numberOfBuildings}_{iter}_{optMode}.xlsx")
        dataDict = read_results(excelFileName)
        path = outputFileName + '/Optimization{}'.format(iter)
        if not os.path.exists(path):
            os.mkdir(path)

        print(excelFileName)
        results = run_kpi(dataDict, inputFileName, numberOfBuildings, selected_days,
                          elecEmission, elecCost, gasEmission, gasCost, rangeToConsider,
                          outputFileName, iter, iterRange, optMode, results)
