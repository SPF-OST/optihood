import pandas as pd
import pathlib as _pl
import os
try:
    import matplotlib.pyplot as plt
except ImportError:
    plt = None

# import EnergyNetworkGroup class
from optihood.energy_network import EnergyNetworkGroup as EnergyNetwork
from optihood.IO.map_interface import StaticMapOptihoodNetwork

def plot_network(network, title):
    static_map = StaticMapOptihoodNetwork(network)
    static_map.draw()
    plt.title(title)
    plt.scatter(network.graph_data["consumers"]['longitude'], network.graph_data["consumers"]['latitude'],
                color='tab:green', label='consumers', zorder=2.5, s=50)
    plt.scatter(network.graph_data["producers"]['longitude'], network.graph_data["producers"]['latitude'],
                color='tab:red', label='producers', zorder=2.5, s=50)
    plt.scatter(network.graph_data["forks"]['longitude'], network.graph_data["forks"]['latitude'],
                color='tab:grey', label='forks', zorder=2.5, s=50)
    plt.text(-2, 32, 'P0', fontsize=14)
    plt.text(82, 0, 'P1', fontsize=14)
    plt.legend()
    plt.show()


if __name__ == '__main__':
    # set a time period for the optimization problem
    timePeriod = pd.date_range("2018-01-01 00:00:00", "2018-01-31 23:00:00", freq="60min")

    # define paths for input and result files
    curDir = _pl.Path(__file__).resolve().parent
    inputFilePath = curDir / ".." / "excels" / "dhn_pipes_optimization"
    inputfileName = "scenario.xls"

    resultFilePath = curDir / ".." / "results"
    resultFileName ="results_dhn_pipes.xlsx"

    # initialize parameters
    numberOfBuildings = 10      # one building per producer/consumer (1,2 --> producers, 3-10 --> consumers)
    optimizationType = "costs"  # set as "env" for environmental optimization

    # create an energy network and set the network parameters from an excel file
    network = EnergyNetwork(timePeriod)
    network.setFromExcel(os.path.join(inputFilePath, inputfileName), numberOfBuildings, opt=optimizationType)

    plot_network(network=network, title="District Heating Network (Given)")

    # optimize the energy network
    limit, capacitiesTransformers, capacitiesStorages, capacitiesPipes = network.optimize(solver='gurobi', numberOfBuildings=numberOfBuildings)

    network.printInvestedCapacities(capacitiesTransformers, capacitiesStorages, capacitiesPipes)
    network.printCosts()
    network.printEnvImpacts()
    network.printMetaresults()

    # save results
    if not os.path.exists(resultFilePath):
        os.makedirs(resultFilePath)
    network.saveUnprocessedResults(os.path.join(resultFilePath, resultFileName))

    # Print the graph of results (pipes, forks, producers and consumers)
    plot_network(network=network, title="Optimized District Heating Network")
