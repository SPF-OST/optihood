import pandas as pd
import os
try:
    import matplotlib.pyplot as plt
except ImportError:
    plt = None

# import plotting methods for Sankey and detailed plots

import optihood.plot_sankey as snk
import optihood.plot_functions as fnc

if __name__ == '__main__':

    # set a time period for the optimization problem
    timePeriod = pd.date_range("2018-01-01 00:00:00", "2018-12-31 23:00:00", freq="60min")

    # define paths for the results excel file and figures
    resultFilePath =r"..\results"
    resultFileName ="results.xlsx"

    figureFilePath = r"..\figures"
    sankeyFileName = f"SankeyPlot.html"

    # initialize parameter
    numberOfBuildings = 4
    UseLabelDict = True     # a dictionary defining the labels to be used for different flows
                            # any new flow should be added into this dictionary if UseLabelDict = True
                            # The dictionary can be found in /.../optihood/labelDict.py

    # plot sankey diagram
    snk.plot(os.path.join(resultFilePath, resultFileName), os.path.join(figureFilePath, sankeyFileName),
                   numberOfBuildings, UseLabelDict)

    # plot detailed energy flow
    plotLevel = "allMonths"  # permissible values (for energy balance plot): "allMonths" {for all months}
    # or specific month {"Jan", "Feb", "Mar", etc. three letter abbreviation of the month name}
    # or specific date {format: YYYY-MM-DD}
    plotType = "bokeh"  # permissible values: "energy balance", "bokeh"
    flowType = "electricity"  # permissible values: "all", "electricity", "space heat", "domestic hot water"

    fnc.plot(os.path.join(resultFilePath, resultFileName), figureFilePath, plotLevel, plotType, flowType)

