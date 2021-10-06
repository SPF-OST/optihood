import pandas as pd
import os
try:
    import matplotlib.pyplot as plt
except ImportError:
    plt = None
from groups_indiv import EnergyNetwork

if __name__ == '__main__':

    network = EnergyNetwork(pd.date_range("2018-01-01 01:00:00", "2019-01-01 00:00:00", freq="60min"), tSH=35, tDHW=55)
    network.setFromExcel(os.path.join(os.getcwd(), "scenario4.xls"), opt="costs")   # opt= "costs" for cost optimization and "env for environmental optimization
    network.printNodes()
    envImpact, capacitiesTransformers, capacitiesStorages = network.optimize(solver='gurobi', envImpactlimit=1000000)
    network.printInvestedCapacities(capacitiesTransformers, capacitiesStorages)
    meta = network.printMetaresults()
    network.printCosts()
    network.printEnvImpacts()
    network.exportToExcel('results_indiv.xlsx')