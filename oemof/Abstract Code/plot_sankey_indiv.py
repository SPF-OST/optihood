from random import random

import plotly.graph_objects as go
import pandas as pd
import plot_functions_indiv


def readResults(fileName, buildings):
    dataDict = plot_functions_indiv.get_data(fileName)
    keys=dataDict.keys()
    nodes, sources, targets, values = createSankeyData(dataDict, keys, buildings)

    nodesColors=pd.Series(createColorList(nodes))
    linksColors = nodesColors[sources]

    data = [go.Sankey(
        valuesuffix="kWh",
        node=dict(
            pad=15,
            thickness=15,
            line=dict(color="black", width=0.5),
            label=nodes,
            color=nodesColors
        ),
        link=dict(
            source=sources,
            target=targets,
            value=values,
            color=linksColors,
        ))]
    return data


def createSankeyData(dataDict, keys, buildings):
    sources = []
    targets = []
    nodes = []
    values = []
    for key in keys:
        df = dataDict[key]
        dfKeys = df.keys()
        if "dhwStorageBus" in key:
            continue
        if all([str(i) not in key for i in buildings]):
            continue
        for dfKey in dfKeys:
            if isinstance(dfKey, int):
                continue
            dfKeySplit = dfKey.split("'")
            # if "domesticHotWaterDemand" in dfKeySplit[3]:
            #     continue
            if "Resource" in dfKeySplit[1]:
                continue
            if dfKeySplit[1] not in nodes:
                nodes.append(dfKeySplit[1])
            sources.append(nodes.index(dfKeySplit[1]))
            if dfKeySplit[3] not in nodes:
                nodes.append(dfKeySplit[3])
            targets.append(nodes.index(dfKeySplit[3]))
            dfKeyValues = df[dfKey].values
            value = sum(dfKeyValues)
            if value < 1:
                value = 0
            values.append(value)
    return nodes, sources, targets, values


def createColorList(inputList):
    colors=[]
    for n in inputList:
        if "elec" in n or "Elec" in n or "pv" in n or "grid" in n:
            color = "skyblue"
        elif "sh" in n or "SH" in n or "spaceHeating" in n:
            color = "darkorange"
        elif "dhw" in n or "DHW" in n or "domestic" in n or "solarCollector" in n:
            color = "red"
        elif "Gas" in n:
            color = "darkgray"
        else:
            color = "lime"
        colors.append(color)
    return colors


def displaySankey(fileName, buildings):
    data = readResults(fileName, buildings)
    node = data[0]['node']
    link = data[0]['link']
    fig = go.Figure(go.Sankey(link=link, node=node))
    return fig
