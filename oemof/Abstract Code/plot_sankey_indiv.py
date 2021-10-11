from random import random

import plotly.graph_objects as go
import pandas as pd
import plot_functions_indiv


def readResults():
    dataDict = plot_functions_indiv.get_data("results4_1_indiv.xlsx")
    keys=dataDict.keys()
    sources=[]
    targets=[]
    nodes=[]
    values=[]
    for key in keys:
        df = dataDict[key]
        dfKeys=df.keys()
        for dfKey in dfKeys:
            if isinstance(dfKey,int):
                continue
            dfKeySplit=dfKey.split("'")
            if "1"in dfKeySplit[1] and"1"in dfKeySplit[3]:
                if dfKeySplit[1] not in nodes:
                    nodes.append(dfKeySplit[1])
                sources.append(nodes.index(dfKeySplit[1]))
                if dfKeySplit[3] not in nodes:
                    nodes.append(dfKeySplit[3])
                targets.append(nodes.index(dfKeySplit[3]))
                dfKeyValues=df[dfKey].values
                value = sum(dfKeyValues)
                values.append(value)
    opacity = 0.8
    data = [go.Sankey(
        valuesuffix="kWh",
        node=dict(
            pad=15,
            thickness=15,
            line=dict(color="black", width=0.5),
            label=nodes,
            # hovertemplate='Node %{customdata} has total value %{value}<extra></extra>',
            color="blue"
        ),
        link=dict(
            source=sources,
            target=targets,
            value=values,
            # hovertemplate='Link from node %{source.customdata}<br />' +
            #               'to node%{target.customdata}<br />has value %{value}' +
            #               '<br />and data %{customdata}<extra></extra>',
        ))]
    return data

def displaySankey():
    opacity = str(0.8)

    data = readResults()
    # override gray link colors with 'source' colors
    node = data[0]['node']
    link = data[0]['link']
    fig = go.Figure(go.Sankey(link=link, node=node))
    return fig
