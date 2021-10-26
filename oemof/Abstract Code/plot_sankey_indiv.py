from random import random

import plotly.graph_objects as go
import pandas as pd
import plot_functions_indiv
import numpy as np
from labelDict import labelDict
from labelDict import labelPositionDict
from matplotlib import colors

useLabelDict=True
opacity=0.6
colorDict={"elec":'rgba'+str(colors.to_rgba("skyblue",opacity)),
           "gas":'rgba'+str(colors.to_rgba("darkgray",opacity)),
           "dhw":'rgba'+str(colors.to_rgba("red",opacity)),
           "sh":'rgba'+str(colors.to_rgba("magenta",opacity)),
           "other":'rgba'+str(colors.to_rgba("lime",opacity))
           }

PositionDict={
    "naturalGas":	[0.001, 0.75],
    "gridBus":	[0.001, 0.05],
    "pv":   [0.001, 0.2],
    "gridElect":	[0.1, 0.05],
    "CHP_SH":	[0.1, 0.6],
    "CHP_DHW":	[0.1, 0.99],
    "electricityBus":	[0.2, 0.2],
    "producedElectricity":	[0.3, 0.25],
    "electricityLink":	[0.3, 0.35],
	"electricalStorage":	[0.3, 0.25],
    "excesselect":	[0.5, 0.05],
    "electricityInBus":	[0.5, 0.2],
    "HP_SH":	[0.6, 0.3],
    "HP_DHW":	[0.6, 0.9],
    "solarCollector":	[0.6, 0.85],
    "spaceHeatingBus":	[0.7, 0.58],
    "spaceHeating_":	[0.8, 0.6],
    "shStorage":	[0.8, 0.37],
    "spaceHeatingDemandBus":	[0.9, 0.6],
    "dhwStorageBus":	[0.7, 0.9],
    "dhwStorage_":	[0.8, 0.9],
	"domesticHotWaterBus":	[0.9, 0.9],
    "electricityDemand":	[0.999, 0.1],
    "spaceHeatingDemand_":	[0.999, 0.6],
    "domesticHotWaterDemand":	[0.999, 0.9]
	}

def readResults(fileName, buildings):
    dataDict = plot_functions_indiv.get_data(fileName)
    keys=dataDict.keys()
    nodes, sources, targets, values,x,y, linkGroup = createSankeyData(dataDict, keys, buildings)

    nodesColors=pd.Series(createColorList(nodes))
    linksColors = nodesColors[sources]
    dhwIndex = [a and b for a, b in zip((nodesColors[targets] == colorDict["dhw"]), (nodesColors[sources] != colorDict["gas"]))]
    linksColors = np.where(dhwIndex, colorDict["dhw"], linksColors)
    linksColors = np.where(nodesColors[targets]==colorDict["elec"], colorDict["elec"], linksColors)
    #linksColors = np.where(nodesColors[sources]==colorDict["elec"], colorDict["elec"], linksColors)

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
            "x":x,
            "y":y,
            },
        link= {
            "source":sources,
            "target":targets,
            "value":values,
            "color":linksColors.tolist(),
            }
        )]
    return data


def createSankeyData(dataDict, keys, buildings=[]):
    sources = []
    targets = []
    nodes = []
    values = []
    x=[]
    y=[]
    linkGroup=[]
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
            sourceNodeName=dfKeySplit[1]
            targetNodeName =dfKeySplit[3]

            if useLabelDict == True:
                sourceNodeName=labelDict[sourceNodeName]
                targetNodeName=labelDict[targetNodeName]
                PositionDict=labelPositionDict
                if sourceNodeName==targetNodeName:
                    continue

            if "Resource" not in sourceNodeName:
                dfKeyValues = df[dfKey].values
                value = sum(dfKeyValues)
                if value < 1:
                    continue
                values.append(value)
                if sourceNodeName not in nodes:
                    nodes.append(sourceNodeName)
                    if "electricityLink" in sourceNodeName or "elLink"in sourceNodeName:
                        linkGroup.append(nodes.index(sourceNodeName))
                    for posKey in PositionDict.keys():
                        if posKey in sourceNodeName and posKey[0:2] == sourceNodeName[0:2]: #second part of the term added for CHP and HP
                            x.append(PositionDict[posKey][0])
                            if "electricityLink" in sourceNodeName or "elLink"in sourceNodeName:
                                y.append((0.5-(PositionDict[posKey][1]))/len(buildings))
                            else:
                                buildingNumber=buildings.index(int(sourceNodeName[-1]))
                                temp = (PositionDict[posKey][1]) / len(buildings) + (buildingNumber) / len(buildings)
                                y.append(temp)
                sources.append(nodes.index(sourceNodeName))

                if targetNodeName not in nodes:
                    nodes.append(targetNodeName)
                    if "electricityLink" in targetNodeName or "elLink"in targetNodeName:
                        linkGroup.append(nodes.index(targetNodeName))
                    for posKey in PositionDict.keys():
                        if posKey in targetNodeName and posKey[0:2] == targetNodeName[0:2]:
                            x.append(PositionDict[posKey][0])
                            if "electricityLink" in targetNodeName or "elLink"in targetNodeName:
                                y.append((0.5-(PositionDict[posKey][1]))/len(buildings))
                            else:
                                buildingNumber=buildings.index(int(targetNodeName[-1]))
                                temp = (PositionDict[posKey][1]) / len(buildings) + (buildingNumber) / len(buildings)
                                y.append(temp)
                targets.append(nodes.index(targetNodeName))
    return nodes, sources, targets, values, x, y, linkGroup


def createColorList(inputList):
    colorsList=[]
    for n in inputList:
        if "el" in n or "El" in n or "pv" in n or "grid" in n:
            color = colorDict["elec"]
        elif "Gas" in n:
            color = colorDict["gas"]
        elif "sh" in n or "SH" in n or "spaceHeating" in n:
            color = colorDict["sh"]
        elif "dhw" in n or "DHW" in n or "domestic" in n or "solar" or "sc" in n:
            color = colorDict["dhw"]
        else:
            color = colorDict["other"]
        colorsList.append(color)
    return colorsList


def displaySankey(fileName, buildings):
    data = readResults(fileName, buildings)

    node = data[0]['node']
    link = data[0]['link']
    fig = go.Figure(go.Sankey(arrangement = "perpendicular",
                              link=link,
                              node=node)) #snap, perpendicular,freeform, fixed
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
