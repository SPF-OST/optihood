import numpy as np
import pandas as pd
import plotly.graph_objects as go
from matplotlib import colors
import plot_functions_indiv

intervalSizeHours = 1095 #24

opacity=0.8
colorDict={"elec":'rgba'+str(colors.to_rgba("skyblue",opacity)),
           "gas":'rgba'+str(colors.to_rgba("darkgray",opacity)),
           "dhw":'rgba'+str(colors.to_rgba("red",opacity)),
           "sh":'rgba'+str(colors.to_rgba("magenta",opacity)),
           "other":'rgba'+str(colors.to_rgba("lime",opacity))
           }

PositionDict={
    "naturalGas":	[0.001, 0.65],
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
    return createSankeyData(dataDict, keys, buildings)


def createSankeyData(dataDict, keys, buildings=None):
    if buildings is None:
        buildings = []
    nodesList=[]
    sourcesList=[]
    targetsList=[]
    valuesList=[]
    xList=[]
    yList=[]
    linkGroupList=[]
    nodesColorsList = []
    linksColorsList = []
    numberOfMeasurements=len(next(iter(dataDict.values())))
    for iteration in range(0, int(numberOfMeasurements/intervalSizeHours)):
        sources = []
        targets = []
        nodes = []
        values = []
        x = []
        y = []
        linkGroup = []
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
                sourceNodeName=dfKeySplit[1]
                targetNodeName =dfKeySplit[3]
                if "Resource" not in dfKeySplit[1]:
                    dfKeyValues = df[dfKey].values
                    value = sum(list(dfKeyValues)[iteration*intervalSizeHours:(iteration*intervalSizeHours+intervalSizeHours)])
                    if value < intervalSizeHours/100:
                        continue
                    values.append(value)

                    if sourceNodeName not in nodes:
                        nodes.append(sourceNodeName)
                        if "electricityLink" in sourceNodeName:
                            linkGroup.append(nodes.index(sourceNodeName))
                        for posKey in PositionDict.keys():
                            if posKey in sourceNodeName and posKey[0:2] == sourceNodeName[0:2]: #second part of the term added for CHP and HP
                                x.append(PositionDict[posKey][0])
                                if "electricityLink" in sourceNodeName:
                                    y.append((0.5-PositionDict[posKey][1])/ len(buildings))
                                else:
                                    buildingNumber=buildings.index(int(sourceNodeName[-1]))
                                    y.append(PositionDict[posKey][1]/len(buildings)+(buildingNumber)/len(buildings))
                    sources.append(nodes.index(sourceNodeName))

                    if targetNodeName not in nodes:
                        nodes.append(targetNodeName)
                        if "electricityLink" in targetNodeName:
                            linkGroup.append(nodes.index(targetNodeName))
                        for posKey in PositionDict.keys():
                            if posKey in targetNodeName and posKey[0:2] == targetNodeName[0:2]:
                                x.append(PositionDict[posKey][0])
                                if "electricityLink" in targetNodeName:
                                    y.append((0.5-PositionDict[posKey][1])/len(buildings))
                                else:
                                    buildingNumber=buildings.index(int(targetNodeName[-1]))
                                    y.append(PositionDict[posKey][1]/len(buildings)+(buildingNumber)/len(buildings))
                    targets.append(nodes.index(targetNodeName))


                nodesColors = pd.Series(createColorList(nodes))
                linksColors = nodesColors[sources]
                linksColors = np.where(nodesColors[targets] == colorDict["elec"], colorDict["elec"], linksColors)
        nodesList.append(nodes)
        sourcesList.append(sources)
        targetsList.append(targets)
        valuesList.append(values)
        xList.append(x)
        yList.append(y)
        linkGroupList.append(linkGroup)
        nodesColorsList.append(nodesColors.tolist())
        linksColorsList.append(linksColors.tolist())
    return nodesList, sourcesList, targetsList, valuesList, xList, yList, nodesColorsList, linksColorsList


def createColorList(inputList):
    colors=[]
    for n in inputList:
        if "elec" in n or "Elec" in n or "pv" in n or "grid" in n:
            color = colorDict["elec"]
        elif "sh" in n or "SH" in n or "spaceHeating" in n:
            color = colorDict["sh"]
        elif "dhw" in n or "DHW" in n or "domestic" in n or "solarCollector" in n:
            color = colorDict["dhw"]
        elif "Gas" in n:
            color = colorDict["gas"]
        else:
            color = colorDict["other"]
        colors.append(color)
    return colors


def displaySankey(fileName, buildings):
    nodes, sources, targets, values, x, y, nodesColors, linksColors = readResults(fileName, buildings)

    fig = go.Figure(data=[go.Sankey(
                        arrangement="perpendicular",
                        node=dict(
                            pad=20,
                            thickness=15,
                            line=dict(color="black", width=0.5),
                            label=nodes[0],
                            color=nodesColors[0],
                            x=x[0],
                            y=y[0],
                        ),
                        link=dict(
                            source=sources[0],
                            target=targets[0],
                            value=values[0],
                            color=linksColors[0],
                        ),
            )],
                    layout=go.Layout(
                        updatemenus=[dict(type="buttons",
                                          buttons=[dict(label="Play",
                                                        method="animate",
                                                        args=[None])])]),
                    frames=[go.Frame(
                        data=[go.Sankey(
                            arrangement="perpendicular",
                            node=dict(
                                pad=20,
                                thickness=15,
                                line=dict(color="black", width=0.5),
                                label=nodes[i],
                                color=nodesColors[i],
                                x=x[i],
                                y=y[i],
                            ),
                            link=dict(
                                source=sources[i],
                                target=targets[i],
                                value=values[i],
                                color=linksColors[i],
                            ),
                            )])
                        for i in range(0, len(values))]
                    )
    fig.update_layout(
        title=fileName +" for buildings " + str(buildings),
        font=dict(size=10, color='black'),
    )


    steps = []
    for i in range(0, len(fig.frames)):
        step = dict(
            method = 'restyle',
            args = ['visible', [True]],
            label="Timestep "+str(i)
        )
        steps.append(step)


    sliders = [dict(
        active=10,
        currentvalue={"prefix": "Date: "},
        pad={"t": 50},
        steps=steps
    )]

    fig.update_layout(
        sliders=sliders
    )

    return fig
