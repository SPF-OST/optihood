import sys
from random import random
import os
import plotly.graph_objects as go
import pandas as pd
from optihood.plot_functions import getData
import numpy as np
from optihood.labelDict import labelDictGenerator, positionDictGenerator
from matplotlib import colors

def addCapacities(nodes, dataDict, buildings, UseLabelDict, labelDict, mergedLinks):
    capacities = ["sufficient"] * len(nodes)
    for i in buildings:
        capTransformers=dataDict["capTransformers__Building"+str(i)]
        capStorages=dataDict["capStorages__Building"+str(i)]
        for j, k in capStorages.iterrows():
            if k[0] < 0.1: # if the installed capacity is 0 then skip (sometimes as an error very low capacites are selected. To handle this k<0.01kW is set as the condition for comparison)
                continue
            index=nodes.index(labelDict[j])
            #nodes[index]=nodes[index]+" "+str(round(k[0],2))+" kWh"
            if "Bat" in labelDict[j]:
                capacities[index] = str(round(k[0], 1)) + " kWh"
            else:
                capacities[index] = str(round(k[0], 1)) + " L"
        for j, k in capTransformers.iterrows():
            if k[0] < 0.001:     # if the installed capacity is 0 then skip (sometimes as an error very low capacites are selected. To handle this k<0.001kW is set as the condition for comparison
                continue
            jComponents=j.split("'")
            if 'Bus' in jComponents[1]:
                j =jComponents[3]
            else:
                j=jComponents[1]

            index=nodes.index(labelDict[j])

            #nodes[index]=nodes[index]+" "+str(k[0])+" kW"
            if round(k[0],1) == 0:
                capacities[index] = str(round(k[0], 2)) + " kW"
            else:
                capacities[index] = str(round(k[0], 1)) + " kW"
    return capacities


def readResults(fileName, buildings, ColorDict, UseLabelDict, labelDict, positionDict, labels, mergedLinks):
    dataDict = getData(fileName)
    keys=dataDict.keys()
    nodes, sources, targets, values,x,y = createSankeyData(dataDict, keys, UseLabelDict, labelDict, positionDict, buildings, mergedLinks)
    capacities = addCapacities(nodes, dataDict, buildings, UseLabelDict, labelDict, mergedLinks)
    nodesColors = pd.Series(createColorList(nodes, ColorDict, labels))
    linksColors = nodesColors[sources]
    linksColors = np.where(nodesColors[targets] == ColorDict["dhw"], ColorDict["dhw"], linksColors)
    linksColors = np.where(nodesColors[targets] == ColorDict["sh"], ColorDict["sh"], linksColors)
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


def createSankeyData(dataDict, keys, UseLabelDict, labelDict, PositionDict, buildings=[], mergedLinks=False):
    sources = [] #contains index of node
    targets = [] #contains index of node
    values = []
    nodes = []
    # (x,y) is the position of the node
    x=[] #equivalent in dimension to nodes
    y=[] #equivalent in dimension to nodes
    linkGroup=[]
    mergedComponents = ["electricityBus", "electricityInBus", "domesticHotWaterBus", "dhwDemandBus", "spaceHeatingBus", "shDemandBus", "excesselectricityBus", "producedElectricity", "spaceHeating", "domesticHotWater"]

    for key in keys:
        df = dataDict[key]
        dfKeys = df.keys()
        if "dhwStorageBus" in key and not mergedComponents:
            continue
        if all([str(i) not in key for i in buildings]) and key not in mergedComponents:
            continue
        for dfKey in dfKeys:
            if isinstance(dfKey, int) or "storage_content" in dfKey:
                continue

            dfKeySplit = dfKey.split("'")
            sourceNodeName=dfKeySplit[1]
            targetNodeName =dfKeySplit[3]

            if mergedLinks:
                # for the sake for representation the merged buses (if present) are added to Building 1
                if sourceNodeName in mergedComponents:
                    sourceNodeName = sourceNodeName + '__Building1'
                if targetNodeName in mergedComponents:
                    targetNodeName = targetNodeName + '__Building1'


            if sourceNodeName in labelDict:
                sourceNodeName = labelDict[sourceNodeName]
            if targetNodeName in labelDict:
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
                            if labelDict["electricityLink"] in sourceNodeName:
                                y.append((0.5-(PositionDict[posKey][1]))/len(buildings))
                            elif labelDict["shLink"] in sourceNodeName:
                                y.append((0.5 - (PositionDict[posKey][1])) / len(buildings))
                            elif labelDict["dhwLink"] in sourceNodeName:
                                y.append((0.5 - (PositionDict[posKey][1])) / len(buildings))
                            elif ("grid" in sourceNodeName or "Grid" in sourceNodeName) and mergedLinks:
                                buildingNumber = 1
                                temp = (PositionDict[posKey][1]) / len(buildings) + buildingNumber / len(buildings)
                                y.append(temp)
                            else:
                                buildingNumber=buildings.index(int(sourceNodeName.split('_')[-1][1:]))
                                temp = (PositionDict[posKey][1]) / len(buildings) + buildingNumber / len(buildings)
                                y.append(temp)
                sources.append(nodes.index(sourceNodeName))

                if targetNodeName not in nodes:
                    nodes.append(targetNodeName)
                    for posKey in PositionDict.keys():
                        if posKey in targetNodeName and posKey[0:2] == targetNodeName[0:2]:
                            x.append(PositionDict[posKey][0])
                            if labelDict["electricityLink"] in targetNodeName:
                                y.append((0.5-(PositionDict[posKey][1]))/len(buildings))
                            elif labelDict["shLink"] in targetNodeName:
                                y.append((0.5 - (PositionDict[posKey][1])) / len(buildings))
                            elif labelDict["dhwLink"] in targetNodeName:
                                y.append((0.5 - (PositionDict[posKey][1])) / len(buildings))
                            elif ("grid" in sourceNodeName or "Grid" in sourceNodeName) and mergedLinks:
                                buildingNumber = 1
                                temp = (PositionDict[posKey][1]) / len(buildings) + buildingNumber / len(buildings)
                                y.append(temp)
                            else:
                                buildingNumber=buildings.index(int(targetNodeName.split('_')[-1][1:]))
                                temp = (PositionDict[posKey][1]) / len(buildings) + (buildingNumber) / len(buildings)
                                y.append(temp)
                targets.append(nodes.index(targetNodeName))
    return nodes, sources, targets, values, x, y


def createColorList(inputList, ColorDict, labels):
    colorsList=[]
    for n in inputList:
        if (labels!='default' and labels["naturalGas"] in n) or (labels=='default' and "natGas" in n):           # Check for whether labels of a specific type are defined or not should be added here
            color = ColorDict["gas"]
        elif (labels!='default' and labels["qSource"] in n) or (labels=='default' and "qSource" in n):
            color = ColorDict["qs"]
        elif (labels!='default' and (labels["excessSh"] in n or labels["prodSH"] in n or labels["shBus"] in n or labels["StorageSh"] in n or labels["DemandSh"] in n)) or (labels=='default' and any(v in n for v in ["shLink", "prodSH", "shBus", "shStor", "Q_sh", "exSh", "usedSH"])):
            color = ColorDict["sh"]
        elif (labels!='default' and (labels["solarCollector"] in n or labels["excessSolarCollector"] in n or labels["StorageDhw"] in n or labels["dhwBus"] in n or labels["DemandDhw"] in n)) or (labels=='default' and any(v in n for v in ["dhwLink", "solar", "exSolar", "dhwStor", "dhwBus", "Q_dhw", "prodDHW"])):
            color = ColorDict["dhw"]
        elif (labels!='default' and (labels["elBus"] in n or labels["grid"] in n or labels["pv"] in n or labels["prodEl"] in n or labels["localEl"] in n or labels["StorageEl"] in n or labels["excessEl"] in n or labels["DemandEl"] in n or labels["DemandMob"] in n))  or (labels=='default' and any(v in n for v in ["excesselectricityProdBus", "eMobilityDemand", "elLink", "grid", "pv", "prodEl", "localEl", "Bat", "exEl", "usedEl", "Q_el", "Q_mob"])):
            color = ColorDict["elec"]
        elif (labels!='default' and labels["hSB"] in n) or (labels=='default' and "hSB" in n):
            color = ColorDict["hs"]
        else:
            color = ColorDict["other"]
        colorsList.append(color)
    return colorsList


def displaySankey(fileName, UseLabelDict, labelDict, positionDict, labels, buildings, mergedLinks, hideBuildingNumber):
    OPACITY = 0.6
    ColorDict = {"elec": 'rgba' + str(colors.to_rgba("skyblue", OPACITY)),
                 "gas": 'rgba' + str(colors.to_rgba("darkgray", OPACITY)),
                 "dhw": 'rgba' + str(colors.to_rgba("red", OPACITY)),
                 "sh": 'rgba' + str(colors.to_rgba("magenta", OPACITY)),
                 "other": 'rgba' + str(colors.to_rgba("black", OPACITY)),
                 "hs": 'rgba' + str(colors.to_rgba("yellow", OPACITY)),
                 "qs": 'rgba' + str(colors.to_rgba("green", OPACITY))
                 }
    data = readResults(fileName, buildings, ColorDict, UseLabelDict, labelDict, positionDict, labels, mergedLinks)

    node = data[0]['node']
    link = data[0]['link']
    if hideBuildingNumber == True:
        node['label'] = tuple(s if not "_B" in s else s.split("_")[0] for s in node['label'])
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


def plot(excelFileName, outputFileName, numberOfBuildings, UseLabelDict, labels, optimType, mergedLinks=False, hideBuildingNumber=False):
    BUILDINGSLIST = list(range(1, numberOfBuildings + 1))
    labelDict = labelDictGenerator(numberOfBuildings, labels, optimType, mergedLinks)
    positionDict = positionDictGenerator(labels, optimType, mergedLinks)
    fig = displaySankey(excelFileName, UseLabelDict, labelDict, positionDict, labels, BUILDINGSLIST, mergedLinks, hideBuildingNumber)
    fig.show()
    fig.write_html(outputFileName)


if __name__ == "__main__":
    optMode = "group"  # parameter defining whether the results file corresponds to "indiv" or "group" optimization
    numberOfBuildings = 4
    plotOptim = 3  # defines the number of the optimization to plot
    UseLabelDict = True
    excelFileName = os.path.join(r"..\data\Results", f"results{numberOfBuildings}_{plotOptim}_{optMode}.xlsx")
    outputFileName = os.path.join(r"..\data\figures", f"Sankey_{plotOptim}.html")
    plot(excelFileName, outputFileName, numberOfBuildings, UseLabelDict, labels='default', optimType=optMode)
