import json
import os
from textwrap import dedent as d
import typing as _tp
import pathlib as _pl
import json as _json

import dash
from datetime import datetime
import plotly.express as px
from dash import html, dcc, Input, Output, State, callback, ctx, callback_context
from dash.exceptions import PreventUpdate
import dash_cytoscape as cyto
import matplotlib.pyplot as plt

import optihood.Visualizer.scenario_to_visualizer as stv
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
                        edges: _tp.Optional[_tp.Dict[str, _tp.Dict[str, _tp.Union[str, float]]]] = None,
                        node_layout_file: str = 'saved_layout.json',
                        layout_mode: str ='breadthfirst') -> dash.Dash:
    """
    This example comes directly from the Plotly homepage.
    http://dash.plotly.com/cytoscape/events
    """
    if not graphData and not nodes and not edges:
        raise TypeError('Though all inputs are optional, either graphData or both Nodes and Edges need to be defined.')

    if graphData:
        nodes = graphData.nodes
        edges = graphData.edges

    # enable svg export
    cyto.load_extra_layouts()
    app = dash.Dash('Optihood input Visualizer')
    styles = {
        'output': {
            'overflow-y': 'scroll',
            'overflow-wrap': 'break-word',
            'height': 'calc(100% - 25px)',
            'border': 'thin lightgrey solid'
        },
        'tab': {'height': 'calc(98vh - 115px)'}
    }

    default_stylesheet = [
        # selection colors
        {
            'selector': 'node',
            'style': {
                'label': 'data(label)',
                'background-color': 'data(color)',
                'font-size': '20px',
                'font-weight': 'bold'
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
                'line-color': 'forestgreen',
            }
        },
        {
            'selector': f'.{stv.EnergyTypes.domestic_hot_water.value}',
            'style': {
                'line-color': 'tomato',
            }
        },
        {
            'selector': f'.{stv.EnergyTypes.space_heating.value}',
            'style': {
                'line-color': 'goldenrod',
            }
        },
        {
            'selector': f'.{stv.EnergyTypes.gas.value}',
            'style': {
                'curve-style': 'segments',
                'line-color': 'mediumpurple',
            }
        },
        {
            'selector': f'.{stv.EnergyTypes.unknown.value}',
            'style': {
                "line-style": 'dashed',
                'line-color': 'grey',
            }
        },
        {
            'selector': f'.{stv.EnergyTypes.low_temp_grid.value}',
            'style': {
                'line-color': 'dodgerblue',
            }
        },
        {
            'selector': f'.{stv.EnergyTypes.sh_temp_grid.value}',
            'style': {
                'line-color': 'goldenrod',
            }
        },
        {
            'selector': f'.{stv.EnergyTypes.med_temp_grid.value}',
            'style': {
                'line-color': 'orangered',
            }
        },
        {
            'selector': f'.{stv.EnergyTypes.dhw_temp_grid.value}',
            'style': {
                'line-color': 'tomato',
            }
        },
        {
            'selector': f'.{stv.EnergyTypes.biomass.value}',
            'style': {
                'line-color': 'yellowgreen',
            }
        },
        {
            'selector': f'.{stv.EnergyTypes.oil.value}',
            'style': {
                'line-color': 'royalblue',
            }
        },
        {
            'selector': f'.{stv.EnergyTypes.district.value}',
            'style': {
                'line-color': 'crimson',
            }
        },
        {
            'selector': f'.{stv.EnergyTypes.cooling.value}',
            'style': {
                'line-color': 'dodgerblue',
            }
        },

    ]

    app.layout = html.Div([
        cyto.Cytoscape(
            id='cytoscape-event-callbacks-3',
            layout={'name': layout_mode},  # 'cose', 'breadthfirst'
            elements=edges + nodes,
            stylesheet=default_stylesheet,
            style={'width': '100%', 'height': '640px'}
        ),
        html.Button("💾 Save Layout", id="save-button", n_clicks=0),
        html.Div(id="save-status", style={"marginTop": "10px", "color": "green"}),
        dcc.Markdown(id='cytoscape-selectedNodeData-markdown'),
    ])

    @callback(Output('cytoscape-selectedNodeData-markdown', 'children'),
              Input('cytoscape-event-callbacks-3', 'selectedNodeData'))
    def displaySelectedNodeData(data_list):
        if data_list is None:
            return "No nodes selected."

        NodalData = stv.scenario_data_factory(stv.ScenarioDataTypes.example)
        selected_nodes_list = [NodalData.read_nodal_infos(data) for data in data_list]
        return "You selected the nodes: " + "\n* ".join(selected_nodes_list)

    @callback(
        Output("save-status", "children"),
        Input("save-button", "n_clicks"),
        State("cytoscape-event-callbacks-3", "elements"),
        prevent_initial_call=True
    )
    def save_layout(_, elements):
        if not callback_context.triggered:
            raise PreventUpdate

        if elements:
            positions = {
                el['data']['id']: el['position']
                for el in elements if 'position' in el
            }
            with open(node_layout_file, "w") as f:
                json.dump(positions, f, indent=2)
            timestamp = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
            return f"Layout saved successfully at {timestamp}. Location: {os.path.abspath(node_layout_file)}"

        return "No elements to save."

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


def run_cytoscape_visualizer(
        graphData: _tp.Optional[_cv.EnergyNetworkGraphData] = None,
        nodes: _tp.Optional[_tp.Dict[str, _tp.Dict[str, _tp.Union[str, float]]]] = None,
        edges: _tp.Optional[_tp.Dict[str, _tp.Dict[str, _tp.Union[str, float]]]] = None,
        node_layout_file: str = 'saved_layout.json',
        layout_mode: _tp.Literal["breadthfirst", "circle", "cose", "grid", "random"] = 'breadthfirst'
        ) -> None:
    """
    Method to visualize an energy network.
    Takes either a EnergyNetworkGraphData object, or the combination of both nodes and edges dictionaries.
    
    This visualizer runs in a web browser.
    There you can move the nodes to a better position and save the positions to the "node_layout_file".

    Parameters
    ----------
    graphData:
        optional EnergyNetworkGraphData object with nodes and edges.

    nodes:
        optional dictionary of "nodes" in the network. These correspond to the components, links, buses, etc.

    edges:
        optional dictionary of "edges" in the network. These correspond to flows between nodes and connect them.

    node_layout_file:
        file where the node positions should be stored.

    layout_mode:
        When no node_layout_file is available yet, the nodes will be distributed automatically using this algorithm.
        Options are: "breadthfirst", "circle", "cose", "grid" and "random".
    """
    if node_layout_file:
        node_layout_path = _pl.Path(node_layout_file)
        if node_layout_path.exists():
            with node_layout_path.open("r") as f:
                saved_positions = _json.load(f)

            for node in graphData.nodes:
                node_id = node['data']['id']
                if node_id in saved_positions:
                    node['position'] = saved_positions[node_id]

            layout_mode = 'preset'
    app = setup_cytoscape_app(graphData, nodes, edges, node_layout_file, layout_mode)
    app.run(debug=True)


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
