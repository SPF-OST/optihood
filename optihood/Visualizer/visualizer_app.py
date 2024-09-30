import json
from textwrap import dedent as d
import typing as _tp

import dash
import plotly.express as px
from dash import html, dcc, Input, Output, State, callback
import dash_cytoscape as cyto
import matplotlib.pyplot as plt

app = dash.Dash('Optihood input Visualizer')


def setup_cytoscape_app(nodes: _tp.Dict[str, _tp.Dict[str, _tp.Union[str, float]]] , edges) -> dash.Dash:
    """
    This example comes directly from the Plotly homepage.
    http://dash.plotly.com/cytoscape/events
    """
    styles = {
        'pre': {
            'border': 'thin lightgrey solid',
            'overflowX': 'scroll'
        }
    }

    default_stylesheet = [
        {
            'selector': 'node',
            'style': {
                'label': 'data(label)'
            }
        },
    ]

    app.layout = html.Div([
        cyto.Cytoscape(
            id='cytoscape-event-callbacks-3',
            layout={'name': 'preset'},
            elements=edges + nodes,
            stylesheet=default_stylesheet,
            style={'width': '100%', 'height': '450px'}
        ),
        html.Button('Add Node', id='btn-add-node-example', n_clicks_timestamp=0),
        html.Button('Remove Node', id='btn-remove-node-example', n_clicks_timestamp=0),
        dcc.Markdown(id='cytoscape-selectedNodeData-markdown')
    ])

    @callback(Output('cytoscape-selectedNodeData-markdown', 'children'),
          Input('cytoscape-event-callbacks-3', 'selectedNodeData'))
    def displaySelectedNodeData(data_list):
        if data_list is None:
            return "No nodes selected."

        selected_nodes_list = [f"{data['label']}, {data['lat']}, {data['long']}" for data in data_list]
        return "You selected the nodes: " + "\n* ".join(selected_nodes_list)

    return app


def setup_plotly_app(figure_handle: plt.Figure) -> dash.Dash:
    """
    This example comes directly from the Plotly homepage.
    https://community.plotly.com/t/use-hover-trace-as-input-for-callback/34390
    """

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


def run_cytoscape_visualizer(nodes, edges) -> None:
    app = setup_cytoscape_app(nodes, edges)
    app.run_server(debug=True)


if __name__ == '__main__':
    version = "plotly"
    if version == "plotly":
        df = px.data.iris()
        fig = px.scatter_matrix(df[['sepal_length', 'sepal_width']])
        run_fig_visualizer(fig)
    elif version == "cytoscape":
        nodes_dict = [
            {
                'data': {'id': short, 'label': label, "lat": lat, "long": long},
                'position': {'x': 20 * lat, 'y': -20 * long}
            }
            for short, label, long, lat in (
                ('la', 'Los Angeles', 34.03, -118.25),
                ('nyc', 'New York', 40.71, -74),
                ('to', 'Toronto', 43.65, -79.38),
                ('mtl', 'Montreal', 45.50, -73.57),
                ('van', 'Vancouver', 49.28, -123.12),
                ('chi', 'Chicago', 41.88, -87.63),
                ('bos', 'Boston', 42.36, -71.06),
                ('hou', 'Houston', 29.76, -95.37)
            )
        ]

        edges_dict = [
            {'data': {'source': source, 'target': target}}
            for source, target in (
                ('van', 'la'),
                ('la', 'chi'),
                ('hou', 'chi'),
                ('to', 'mtl'),
                ('mtl', 'bos'),
                ('nyc', 'bos'),
                ('to', 'hou'),
                ('to', 'nyc'),
                ('la', 'nyc'),
                ('nyc', 'bos')
            )
        ]
        run_cytoscape_visualizer(nodes_dict, edges_dict)
