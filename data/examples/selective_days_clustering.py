import pandas as pd
import os
try:
    import matplotlib.pyplot as plt
except ImportError:
    plt = None

from optihood.energy_network import EnergyNetworkIndiv as EnergyNetwork
import optihood.plot_sankey as snk
import optihood.plot_functions as fnc

if __name__ == '__main__':

    # In this example we consider 12 clusters
    # 12 representative days for the whole year
    # The number of days belonging to each cluster is defined in the dictionary 'cluster'
    cluster = {"2018-07-30": 26,
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

    # set a time period for the optimization problem according to the size of clusers
    timePeriod = pd.date_range("2018-01-01 00:00:00", "2018-01-12 23:00:00", freq="60min")

    # define paths for input and result files
    inputFilePath = r"..\excels"
    inputfileName = "scenario.xls"

    resultFilePath =r"..\results"
    resultFileName ="results.xlsx"

    # initialize parameters
    numberOfBuildings = 4
    temperatureSH = 35
    temperatureDHW = 55
    optimizationType = "costs"  # set as "env" for environmental optimization

    # create an energy network and set the network parameters from an excel file
    network = EnergyNetwork(timePeriod, temperatureSH, temperatureDHW)
    network.setFromExcel(os.path.join(inputFilePath, inputfileName), numberOfBuildings, clusterSize=cluster, opt=optimizationType)

    # optimize the energy network
    limit, capacitiesTransformers, capacitiesStorages = network.optimize(solver='gurobi', clusterSize=cluster)

    # print optimization outputs i.e. costs, environmental impact and capacities selected for different components (with investment optimization)
    network.printInvestedCapacities(capacitiesTransformers, capacitiesStorages)
    network.printCosts()
    network.printEnvImpacts()

    # save results
    if not os.path.exists(resultFilePath):
        os.makedirs(resultFilePath)
    network.exportToExcel(os.path.join(resultFilePath, resultFileName))

    # plot sankey diagram
    UseLabelDict = True     # a dictionary defining the labels to be used for different flows
    figureFilePath = r"..\figures"
    sankeyFileName = f"Sankey_{numberOfBuildings}_{optimizationType}.html"

    snk.plot(os.path.join(resultFilePath, resultFileName), os.path.join(figureFilePath, sankeyFileName),
                   numberOfBuildings, UseLabelDict)

    # plot detailed energy flow
    plotLevel = "allMonths"  # permissible values (for energy balance plot): "allMonths" {for all months}
    # or specific month {"Jan", "Feb", "Mar", etc. three letter abbreviation of the month name}
    # or specific date {format: YYYY-MM-DD}
    plotType = "bokeh"  # permissible values: "energy balance", "bokeh"
    flowType = "electricity"  # permissible values: "all", "electricity", "space heat", "domestic hot water"

    fnc.plot(os.path.join(resultFilePath, resultFileName), figureFilePath, plotLevel, plotType, flowType)