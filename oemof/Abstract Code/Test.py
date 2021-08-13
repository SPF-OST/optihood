import pandas as pd
from oemof.tools import logger
import logging
import os
from ttictoc import tic,toc
try:
    import matplotlib.pyplot as plt
except ImportError:
    plt = None
from groups import EnergyNetwork

if __name__ == '__main__':
    tic()
    network = EnergyNetwork(pd.date_range("2018-01-01 01:00:00", "2019-01-01 00:00:00", freq="60min"), tSH=35, tDHW=55)
    network.setFromExcel(os.path.join(os.getcwd(), "scenario.xls"))
    network.printNodes()
    network.optimize(solver='gurobi')
    print("Calculation time:")
    print(toc())
    network.printStateofCharge("electricalStorage", "Building1")
    network.printStateofCharge("dhwStorage", "Building1")
    network.printStateofCharge("shStorage", "Building1")
    network.printStateofCharge("electricalStorage", "Building2")
    network.printStateofCharge("dhwStorage", "Building2")
    network.printStateofCharge("shStorage", "Building2")
    network.printInvestedCapacities("Building1")
    network.printInvestedCapacities("Building2")
    network.printMetaresults()
    network.printCosts()
    network.printEnvImpacts()
    network.exportToExcel('results.xlsx')
