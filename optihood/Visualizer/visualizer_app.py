import json
from textwrap import dedent as d
import typing as _tp

import dash
import plotly.express as px
from dash import html, dcc, Input, Output, State, callback
import dash_cytoscape as cyto
import matplotlib.pyplot as plt
import matplotlib as _mpl
import numpy as _np

from optihood.Visualizer import scenario_to_visualizer as stv
import optihood.Visualizer.convert_scenario as _cv

"""
    The dash technology restricts the passing of information to a list of dicts with limited elements (str, int, float).
    Thus, polymorphism is now working around the dictionary as follows:
    - Prepare dicts to be given to dash from polymorphic classes
    - Use same classes to read the dict again and produce the string needed for the UI.
    - These classes should be usable in different technology, which is likely required to move forward to a GUI.
"""


# TODO: better to overload input.

# TODO: extract style sheets and make methods to create them.
#       nodal_shapes = {'bus': 'rectangle'}
#       styles = get_styles(nodal_shapes)


def setup_cytoscape_app(graphData: _tp.Optional[_cv.EnergyNetworkGraphData] = None,
                        nodes: _tp.Optional[_tp.Dict[str, _tp.Dict[str, _tp.Union[str, float]]]] = None,
                        edges: _tp.Optional[_tp.Dict[str, _tp.Dict[str, _tp.Union[str, float]]]] = None) -> dash.Dash:
    """
    This example comes directly from the Plotly homepage.
    http://dash.plotly.com/cytoscape/events
    """
    if not graphData and not nodes and not edges:
        raise TypeError('Though all inputs are optional, either graphData or both Nodes and Edges need to be defined.')

    if graphData:
        nodes = graphData.nodes
        edges = graphData.edges

    app = dash.Dash('Optihood input Visualizer')
    styles = {
        'pre': {
            'border': 'thin lightgrey solid',
            'overflowX': 'scroll'
        }
    }

    default_stylesheet = [
        # selection colors
        {
            'selector': 'node',
            'style': {
                'label': 'data(label)',
                'background-color': 'data(color)',
            }
        },

        ## node shapes ##
        # ellipse
        # triangle
        # round-triangle
        # rectangle
        # round-rectangle
        # bottom-round-rectangle
        # cut-rectangle
        # barrel
        # rhomboid
        # right-rhomboid
        # diamond
        # round-diamond
        # pentagon
        # round-pentagon
        # hexagon
        # round-hexagon
        # concave-hexagon
        # heptagon
        # round-heptagon
        # octagon
        # round-octagon
        # star
        # tag
        # round-tag
        # vee
        {
            'selector': '.bus',
            'style': {
                "shape": 'rectangle',
            }
        },
        {
            'selector': '.demand',
            'style': {
                "shape": 'triangle',
            }
        },
        {
            'selector': '.transformer',
            'style': {
                "shape": 'right-rhomboid',
            }
        },
        {
            'selector': '.source',
            'style': {
                "shape": 'diamond',
            }
        },
        {
            'selector': '.grid_connection',
            'style': {
                "shape": 'hexagon',
            }
        },
        {
            'selector': '.storage',
            'style': {
                "shape": 'star',
            }
        },
        {
            'selector': '.solar',
            'style': {
                "shape": 'vee',
            }
        },
        {
            'selector': '.link',
            'style': {
                "shape": 'round-rectangle',
            }
        },

        # line styles
        {
            'selector': f'.{stv.EnergyTypes.electricity.value}',
            'style': {
                "line-style": 'dashed',
                'line-color': 'blue',
                # 'label': 'data(label)'
            }
        },
        {
            'selector': f'.{stv.EnergyTypes.domestic_hot_water.value}',
            'style': {
                # "line-style": 'dashed',
                # 'line-dash-pattern': [6, 3],
                'line-color': 'red',
                # 'label': 'data(label)'
            }
        },
        {
            'selector': f'.{stv.EnergyTypes.space_heating.value}',
            'style': {
                # 'curve-style': 'segments',
                'line-color': 'black',
                # 'label': 'data(label)'
            }
        },
        {
            'selector': f'.{stv.EnergyTypes.gas.value}',
            'style': {
                'curve-style': 'segments',
                'line-color': 'purple',
                # 'label': 'data(label)'
            }
        },
        {
            'selector': f'.{stv.EnergyTypes.unknown.value}',
            'style': {
                # 'curve-style': 'segments',
                'line-color': 'grey',
                'width': 10
                # 'label': 'data(label)'
            }
        },

    ]

    app.layout = html.Div([
        cyto.Cytoscape(
            id='cytoscape-event-callbacks-3',
            layout={'name': 'breadthfirst'},  # 'cose', 'breadthfirst'
            elements=edges + nodes,
            stylesheet=default_stylesheet,
            style={'width': '100%', 'height': '640px'}
        ),
        # html.Button('Add Node', id='btn-add-node-example', n_clicks_timestamp=0),
        # html.Button('Remove Node', id='btn-remove-node-example', n_clicks_timestamp=0),
        dcc.Markdown(id='cytoscape-selectedNodeData-markdown')
    ])

    @callback(Output('cytoscape-selectedNodeData-markdown', 'children'),
              Input('cytoscape-event-callbacks-3', 'selectedNodeData'))
    def displaySelectedNodeData(data_list):
        if data_list is None:
            return "No nodes selected."

        NodalData = stv.scenario_data_factory(stv.ScenarioDataTypes.example)
        selected_nodes_list = [NodalData.read_nodal_infos(data) for data in data_list]
        return "You selected the nodes: " + "\n* ".join(selected_nodes_list)

    # @callback(Output('cytoscape-event-callbacks-3', 'elements'),
    #           Input('btn-add-node-example', 'n_clicks_timestamp'),
    #           Input('btn-remove-node-example', 'n_clicks_timestamp'),
    #           State('cytoscape-event-callbacks-3', 'elements'))
    # def update_elements(btn_add, btn_remove, elements):
    #     current_nodes, deleted_nodes = get_current_and_deleted_nodes(elements)
    #     # If the add button was clicked most recently and there are nodes to add
    #     if int(btn_add) > int(btn_remove) and len(deleted_nodes):
    #
    #         # We pop one node from deleted nodes and append it to nodes list.
    #         current_nodes.append(deleted_nodes.pop())
    #         # Get valid edges -- both source and target nodes are in the current graph
    #         cy_edges = get_current_valid_edges(current_nodes, edges)
    #         return cy_edges + current_nodes
    #
    #     # If the remove button was clicked most recently and there are nodes to remove
    #     elif int(btn_remove) > int(btn_add) and len(current_nodes):
    #         current_nodes.pop()
    #         cy_edges = get_current_valid_edges(current_nodes, edges)
    #         return cy_edges + current_nodes
    #
    #     # Neither have been clicked yet (or fallback condition)
    #     return elements
    #
    # def get_current_valid_edges(current_nodes, all_edges):
    #     """Returns edges that are present in Cytoscape:
    #     its source and target nodes are still present in the graph.
    #     """
    #     valid_edges = []
    #     node_ids = {n['data']['id'] for n in current_nodes}
    #
    #     for e in all_edges:
    #         if e['data']['source'] in node_ids and e['data']['target'] in node_ids:
    #             valid_edges.append(e)
    #     return valid_edges
    #
    # def get_current_and_deleted_nodes(elements):
    #     """Returns nodes that are present in Cytoscape and the deleted nodes
    #     """
    #     current_nodes = []
    #     deleted_nodes = []
    #
    #     # get current graph nodes
    #     for ele in elements:
    #         # if the element is a node
    #         if 'source' not in ele['data']:
    #             current_nodes.append(ele)
    #
    #     # get deleted nodes
    #     node_ids = {n['data']['id'] for n in current_nodes}
    #     for n in nodes:
    #         if n['data']['id'] not in node_ids:
    #             deleted_nodes.append(n)
    #
    #     return current_nodes, deleted_nodes

    return app


def setup_plotly_app(figure_handle: plt.Figure) -> dash.Dash:
    """
    This example comes directly from the Plotly homepage.
    https://community.plotly.com/t/use-hover-trace-as-input-for-callback/34390
    """
    app = dash.Dash('Optihood input Visualizer')
    styles = {
        'pre': {
            'border': 'thin lightgrey solid',
            'overflowX': 'scroll'
        }
    }

    app.layout = html.Div([
        dcc.Graph(
            id='basic-interactions',
            figure=figure_handle,
        ),

        html.Div(className='row', children=[
            html.Div([
                dcc.Markdown(d("""
                    **Hover Data**

                    Mouse over values in the graph.
                """)),
                html.Pre(id='hover-data', style=styles['pre'])
            ], className='three columns'),

            html.Div([
                dcc.Markdown(d("""
                    **Click Data**

                    Click on points in the graph.
                """)),
                html.Pre(id='click-data', style=styles['pre']),
            ], className='three columns'),

            html.Div([
                dcc.Markdown(d("""
                    **Selection Data**

                    Choose the lasso or rectangle tool in the graph's menu
                    bar and then select points in the graph.

                    Note that if `layout.clickmode = 'event+select'`, selection data also
                    accumulates (or un-accumulates) selected data if you hold down the shift
                    button while clicking.
                """)),
                html.Pre(id='selected-data', style=styles['pre']),
            ], className='three columns'),

            html.Div([
                dcc.Markdown(d("""
                    **Zoom and Relayout Data**

                    Click and drag on the graph to zoom or click on the zoom
                    buttons in the graph's menu bar.
                    Clicking on legend items will also fire
                    this event.
                """)),
                html.Pre(id='relayout-data', style=styles['pre']),
            ], className='three columns')
        ])
    ])

    @app.callback(
        Output('hover-data', 'children'),
        [Input('basic-interactions', 'hoverData')])
    def display_hover_data(hoverData):
        return json.dumps(hoverData, indent=2)

    @app.callback(
        Output('click-data', 'children'),
        [Input('basic-interactions', 'clickData')])
    def display_click_data(clickData):
        return json.dumps(clickData, indent=2)

    @app.callback(
        Output('selected-data', 'children'),
        [Input('basic-interactions', 'selectedData')])
    def display_selected_data(selectedData):
        return json.dumps(selectedData, indent=2)

    @app.callback(
        Output('relayout-data', 'children'),
        [Input('basic-interactions', 'relayoutData')])
    def display_relayout_data(relayoutData):
        return json.dumps(relayoutData, indent=2)

    return app


def run_fig_visualizer(figure_handle: plt.Figure) -> None:
    app = setup_plotly_app(figure_handle)
    app.run_server(debug=True)


def run_cytoscape_visualizer(graphData: _tp.Optional[_cv.EnergyNetworkGraphData] = None,
                             nodes: _tp.Optional[_tp.Dict[str, _tp.Dict[str, _tp.Union[str, float]]]] = None,
                             edges: _tp.Optional[_tp.Dict[str, _tp.Dict[str, _tp.Union[str, float]]]] = None) -> None:
    app = setup_cytoscape_app(graphData, nodes, edges)
    app.run_server(debug=True)


if __name__ == '__main__':

    version = "cytoscape"
    if version == "plotly":
        df = px.data.iris()
        fig = px.scatter_matrix(df[['sepal_length', 'sepal_width']])
        run_fig_visualizer(fig)
    elif version == "cytoscape":
        NodalData = stv.scenario_data_factory(stv.ScenarioDataTypes.example)
        energy_type = stv.EnergyTypes.electricity
        nodal_data_list = [
            NodalData('la', 'Los_Angeles', 'van', 'chi', energy_type, True, 34.03, -118.25),
            NodalData('nyc', 'New_York', 'to', 'bos', energy_type, True, 40.71, -74),
            NodalData('to', 'Toronto', 'hou', ['hou', 'nyc', 'mtl'], energy_type, True, 43.65, -79.38),
            NodalData('mtl', 'Montreal', 'to', 'bos', energy_type, True, 45.50, -73.57),
            NodalData('van', 'Vancouver', None, 'la', energy_type, True, 49.28, -123.12),
            NodalData('chi', 'Chicago', 'la', 'hou', energy_type, True, 41.88, -87.63),
            NodalData('bos', 'Boston', "nyc", None, energy_type, True, 42.36, -71.06),
            NodalData('hou', 'Houston', "chi", 'chi', energy_type, True, 29.76, -95.37)
        ]
        nodes_dict = []
        edges_dict = []
        for i, nodalData in enumerate(nodal_data_list):
            nodes_dict.append(nodalData.get_nodal_infos())
            edges_dict += nodalData.get_edge_infos()

        run_cytoscape_visualizer(nodes_dict, edges_dict)
