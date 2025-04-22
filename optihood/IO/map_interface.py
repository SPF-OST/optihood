import numpy as np
import matplotlib.collections as collections
import matplotlib.pyplot as plt
import networkx as nx
import pandas as pd

def energy_network_to_nx_graph(energy_network_data, type_of_graph=None):
    r"""
    This function is adapted from dhnx.graph.thermal_network_to_nx_graph function
    """
    if type_of_graph is None:
        type_of_graph = nx.Graph()

    nx_graph = type_of_graph
    edges = energy_network_data['pipes'].copy()
    edge_attr = list(edges.columns)
    edge_attr.remove('from')
    edge_attr.remove('to')
    nx_graph = nx.from_pandas_edgelist(
        edges,
        'from',
        'to',
        edge_attr=edge_attr,
        create_using=nx_graph
    )

    nodes = {
        list_name: energy_network_data[list_name].copy() for list_name in [
            'forks',
            'producers',
            'consumers'
        ]
    }

    nodes = pd.concat(nodes.values(), sort=True)
    node_attrs = {node_id: dict(data) for node_id, data in nodes.iterrows()}
    nx.set_node_attributes(nx_graph, node_attrs)

    return nx_graph


class StaticMapOptihoodNetwork:
    r"""
        A static map of optihood.energy_network.EnergyNetworkGroup instance
        with district heating pipes and forks.

        This class has been adapted from dhnx.plotting.StaticMap class.
    """
    def __init__(self, energy_network, fig_size=(5, 5), node_size=3,
                 edge_width=3, node_color='r', edge_color='g'):
        self.graph = energy_network.to_network_graph()
        self.fig_size = fig_size
        self.node_size = node_size
        self.edge_width = edge_width
        self.node_color = node_color
        self.edge_color = edge_color
        self.positions = {node_id: np.array([data['longitude'], data['latitude']])
                          for node_id, data in self.graph.nodes(data=True)}
        self.extent = self._get_extent()

    def _get_extent(self):
        lon = [pos[0] for pos in self.positions.values()]
        lat = [pos[1] for pos in self.positions.values()]
        extent = np.array([np.min(lon), np.max(lon), np.min(lat), np.max(lat)])
        delta = [extent[1] - extent[0], extent[3] - extent[2]]
        extent = extent.astype(float)
        extent += 0.1 * np.array([-delta[0], delta[0], -delta[1], delta[1]])
        return extent

    def draw(self, bgcolor='w', no_axis=False, background_map=False,
             use_geom=False, edge_color='b', edge_linewidth=2,
             edge_alpha=1, node_size=40, node_color='r', node_alpha=1,
             edgecolor='r', node_zorder=1):
        """
        This function has been adapted from osmnx plots.plot_graph() function.
        background_map is False currently
        """

        fig, ax = plt.subplots(figsize=self.fig_size, facecolor=bgcolor)

        lines = []
        for u, v, data in self.graph.edges(data=True):
            if 'geometry' in data and use_geom:
                # if it has a geometry attribute (a list of line segments), add them
                # to the list of lines to plot
                xs, ys = data['geometry'].xy
                lines.append(list(zip(xs, ys)))
            else:
                # if it doesn't have a geometry attribute, the edge is a straight
                # line from node to node
                x1 = self.graph.nodes[u]['longitude']
                y1 = self.graph.nodes[u]['latitude']
                x2 = self.graph.nodes[v]['longitude']
                y2 = self.graph.nodes[v]['latitude']
                line = [(x1, y1), (x2, y2)]
                lines.append(line)

        # add the lines to the axis as a linecollection
        lc = collections.LineCollection(lines,
                                        colors=edge_color,
                                        linewidths=edge_linewidth,
                                        alpha=edge_alpha,
                                        zorder=2)
        ax.add_collection(lc)

        node_Xs = [float(x) for _, x in self.graph.nodes(data='longitude')]
        node_Ys = [float(y) for _, y in self.graph.nodes(data='latitude')]

        ax.scatter(node_Xs,
                   node_Ys,
                   s=node_size,
                   c=node_color,
                   alpha=node_alpha,
                   edgecolor=edgecolor,
                   zorder=node_zorder)

        if no_axis:
            ax = plt.gca()
            ax.set_axis_off()

        return fig, ax