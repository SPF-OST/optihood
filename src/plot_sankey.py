import sys
from random import random

import plotly.graph_objects as go
import pandas as pd
from plot_functions import getData
import numpy as np
from labelDict import labelDict
from labelDict import labelPositionDict
from labelDict import fullPositionDict
from matplotlib import colors



def addCapacities(nodes, dataDict, buildings, UseLabelDict):
    capacities = ["sufficient"] * len(nodes)
    for i in buildings:
        capTransformers=dataDict["capTransformers__Building"+str(i)]
        capStorages=dataDict["capStorages__Building"+str(i)]
        for j, k in capStorages.iterrows():
            if k[0]==0:
                continue
            if UseLabelDict:
                index=nodes.index(labelDict[j])
            else:
                index = nodes.index(j)
            #nodes[index]=nodes[index]+" "+str(round(k[0],2))+" kWh"
            if "Bat" in labelDict[j]:
                capacities[index]=str(round(k[0],1))+" kWh"
            else:
                capacities[index] = str(round(k[0], 1)) + " L"
        for j, k in capTransformers.iterrows():
            if k[0]==0:
                continue
            jComponents=j.split("'")
            if 'Bus' in jComponents[1]:
                j =jComponents[3]
            else:
                j=jComponents[1]

            if UseLabelDict == True:
                index=nodes.index(labelDict[j])
            else:
                index = nodes.index(j)
            #nodes[index]=nodes[index]+" "+str(k[0])+" kW"
            capacities[index]=str(round(k[0],1))+" kW"
    return capacities


def readResults(fileName, buildings, ColorDict, UseLabelDict):
    dataDict = getData(fileName)
    keys=dataDict.keys()
    nodes, sources, targets, values,x,y = createSankeyData(dataDict, keys, UseLabelDict, buildings)
    capacities = addCapacities(nodes, dataDict, buildings, UseLabelDict)
    nodesColors=pd.Series(createColorList(nodes, ColorDict))
    linksColors = nodesColors[sources]
    dhwIndex = [a and b for a, b in zip((nodesColors[targets] == ColorDict["dhw"]), (nodesColors[sources] == ColorDict["sh"]))]
    linksColors = np.where(dhwIndex, ColorDict["dhw"], linksColors)
    shIndex = [a and b for a, b in zip((nodesColors[targets] == ColorDict["sh"]), (nodesColors[sources] == ColorDict["dhw"]))]
    linksColors = np.where(shIndex, ColorDict["sh"], linksColors)
    linksColors = np.where(nodesColors[targets] == ColorDict["elec"], ColorDict["elec"], linksColors)

    data = [go.Sankey(
        arrangement="snap",
        valuesuffix="kWh",
        node={
            "pad":25,
            "thickness":15,
            "line":dict(color="black", width=0.5),
            "label":nodes,#+str(values),
            "color":nodesColors.tolist(),
            #"groups":[linkGroup],
            "customdata": capacities,
            "hovertemplate":  '%{label} has %{customdata} capacity installed',
            "x":x,
            "y":y,
            },
        link={
            "source":sources,
            "target":targets,
            "value":values,
            "color":linksColors.tolist(),
            },
        )]
    return data


def createSankeyData(dataDict, keys, UseLabelDict, buildings=[]):
    sources = [] #contains index of node
    targets = [] #contains index of node
    values = []
    nodes = []
    # (x,y) is the position of the node
    x=[] #equivalent in dimension to nodes
    y=[] #equivalent in dimension to nodes
    linkGroup=[]
    if UseLabelDict:
        PositionDict = labelPositionDict
    else:
        PositionDict = fullPositionDict
    for key in keys:
        df = dataDict[key]
        dfKeys = df.keys()
        if "dhwStorageBus" in key:
            continue
        if all([str(i) not in key for i in buildings]):
            continue
        for dfKey in dfKeys:
            if isinstance(dfKey, int) or "storage_content" in dfKey:
                continue

            dfKeySplit = dfKey.split("'")
            sourceNodeName=dfKeySplit[1]
            targetNodeName =dfKeySplit[3]

            if UseLabelDict:
                sourceNodeName = labelDict[sourceNodeName]
                targetNodeName = labelDict[targetNodeName]
                if sourceNodeName == targetNodeName:
                    continue
                if "exSolar" in targetNodeName:
                    continue

            if "Resource" not in sourceNodeName:
                dfKeyValues = df[dfKey].values
                value = sum(dfKeyValues)
                if value < 0.001:
                    continue
                values.append(value)
                if sourceNodeName not in nodes:
                    nodes.append(sourceNodeName)
                    for posKey in PositionDict.keys():
                        if posKey in sourceNodeName and posKey[0:2] == sourceNodeName[0:2]: #second part of the term added for CHP and HP
                            x.append(PositionDict[posKey][0])
                            if "electricityLink" in sourceNodeName or "elLink"in sourceNodeName:
                                y.append((0.5-(PositionDict[posKey][1]))/len(buildings))
                            elif "shLink" in sourceNodeName:
                                y.append((0.5 - (PositionDict[posKey][1])) / len(buildings))
                            else:
                                buildingNumber=buildings.index(int(sourceNodeName[-1]))
                                temp = (PositionDict[posKey][1]) / len(buildings) + buildingNumber / len(buildings)
                                y.append(temp)
                sources.append(nodes.index(sourceNodeName))

                if targetNodeName not in nodes:
                    nodes.append(targetNodeName)
                    for posKey in PositionDict.keys():
                        if posKey in targetNodeName and posKey[0:2] == targetNodeName[0:2]:
                            x.append(PositionDict[posKey][0])
                            if "electricityLink" in targetNodeName or "elLink"in targetNodeName:
                                y.append((0.5-(PositionDict[posKey][1]))/len(buildings))
                            elif "shLink" in targetNodeName:
                                y.append((0.5 - (PositionDict[posKey][1])) / len(buildings))
                            else:
                                buildingNumber=buildings.index(int(targetNodeName[-1]))
                                temp = (PositionDict[posKey][1]) / len(buildings) + (buildingNumber) / len(buildings)
                                y.append(temp)
                targets.append(nodes.index(targetNodeName))
    return nodes, sources, targets, values, x, y


def createColorList(inputList, ColorDict):
    colorsList=[]
    for n in inputList:
        if "el" in n or "El" in n or "pv" in n or "grid" in n or "Bat" in n:
            color = ColorDict["elec"]
        elif "Gas" in n:
            color = ColorDict["gas"]
        elif "sh" in n or "SH" in n or "spaceHeating" in n:
            color = ColorDict["sh"]
        elif "dhw" in n or "DHW" in n or "domestic" in n or "solar" or "sc" in n:
            color = ColorDict["dhw"]
        else:
            color = ColorDict["other"]
        colorsList.append(color)
    return colorsList


def displaySankey(fileName, UseLabelDict, buildings):
    OPACITY = 0.6
    ColorDict = {"elec": 'rgba' + str(colors.to_rgba("skyblue", OPACITY)),
                 "gas": 'rgba' + str(colors.to_rgba("darkgray", OPACITY)),
                 "dhw": 'rgba' + str(colors.to_rgba("red", OPACITY)),
                 "sh": 'rgba' + str(colors.to_rgba("magenta", OPACITY)),
                 "other": 'rgba' + str(colors.to_rgba("lime", OPACITY))
                 }
    data = readResults(fileName, buildings, ColorDict, UseLabelDict)

    node = data[0]['node']
    link = data[0]['link']
    fig = go.Figure(go.Sankey(arrangement = "perpendicular",
                              link=link,
                              node=node
                              )) #snap, perpendicular,freeform, fixed
    fig.update_layout(
        title=fileName +" for buildings " + str(buildings),
        font=dict(size=10, color='black'),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
    )
    fig.add_hline(y=0, line_color='rgba(0,0,0,0)')
    if len(buildings)%2==0:
        fig.add_hline(y=0.5, line_dash="dash")
    if len(buildings)%3==0:
        fig.add_hline(y=0.33, line_dash="dash")
        fig.add_hline(y=0.66, line_dash="dash")
    if len(buildings)%4==0:
        fig.add_hline(y=0.25, line_dash="dash")
        fig.add_hline(y=0.75, line_dash="dash")
    fig.add_hline(y=1.0, line_color='rgba(0,0,0,0)')
    fig.update_xaxes(visible=False)
    fig.update_yaxes(visible=False)
    return fig


def main(numberOfBuildings, plotOptim, optMode, UseLabelDict):
    BUILDINGSLIST = list(range(1, numberOfBuildings + 1))
    RESULTSFILE = f"..\data\Results\\results{numberOfBuildings}_{plotOptim}_{optMode}.xlsx"
    fig = displaySankey(RESULTSFILE, UseLabelDict, BUILDINGSLIST)
    fig.show()
    fig.write_html(f"..\Figures\Sankey_{plotOptim}.html")
    sys.exit()


if __name__ == "__main__":
    optMode = "group"  # parameter defining whether the results file corresponds to "indiv" or "group" optimization
    numberOfBuildings = 1
    plotOptim = 3  # defines the number of the optimization to plot
    UseLabelDict = True
    main(numberOfBuildings, plotOptim, optMode, UseLabelDict)
