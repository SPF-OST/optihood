import json
import os as _os
import pathlib as _pl
import unittest as _ut

import pandas as _pd
import pytest as _pt

import optihood as _oh
import optihood.IO.readers as _re
import optihood.Visualizer.convert_scenario as _cs
import optihood.Visualizer.visualizer_app as _va
import optihood.energy_network as _en

cwd = _os.getcwd()
packageDir = _pl.Path(_oh.__file__).resolve().parent
_input_data_dir = packageDir / ".." / "data" / "excels" / "basic_example"
_examples_dir = packageDir / ".." / "data" / "examples"
_input_data_path = _input_data_dir / "scenario.xls"
filter_results = False   #False
include_links = True
building_no = 1

manual = True          #True

# Helper functions
def get_building_no(node):
    """Extract building number from node or return 0 if not present."""
    return int(node.split("_B")[-1]) if "_B" in node else 0

def is_link(node):
    """Check if the node ends with 'link' (case-insensitive)."""
    return "link" in node.lower()


@_pt.mark.skipif(manual, reason="Manual test of visualizer")
class TestVisualizeEnergyNetwork(_ut.TestCase):
    def setUp(self):
        self.maxDiff = None

    def test_visualize_from_energy_network(self):
        # Given
        time_period = _pd.date_range("2018-01-01 00:00:00", "2018-01-31 23:00:00", freq="60min")

        _os.chdir(_examples_dir)
        network = _en.EnergyNetworkClass(time_period)
        data = _pd.ExcelFile(str(_input_data_path))
        initial_nodal_data = network.get_nodal_data_from_Excel(data)
        data.close()
        _os.chdir(cwd)

        # When
        converters = _cs.get_converters(initial_nodal_data, nr_of_buildings=4)
        graphData = _cs.get_graph_data(converters)
        if filter_results:
            graphData.nodes = [n for n in graphData.nodes if
                               ('building' in n['data'] and n['data']['building'] == building_no)
                               or (include_links and n['classes'] == "link")]
            graphData.edges = [e for e in graphData.edges if
                               (get_building_no(e['data']['source']) == get_building_no(e['data']['target']) == building_no)
                               or (include_links and (is_link(e['data']['source']) or is_link(e['data']['target'])) and
                                   (
                                           get_building_no(e['data']['target']) == building_no or
                                           get_building_no(e['data']['source']) == building_no
                                   ))]
        _va.run_cytoscape_visualizer(graphData=graphData)

        self.assertEqual(True, False)  # add assertion here


@_pt.mark.skipif(manual, reason="Manual test of visualizer")
class TestVisualizeEnergyNetwork_from_csv(_ut.TestCase):
    def setUp(self):
        self.maxDiff = None

    def test_visualize_from_energy_network(self):
        # Given


        _os.chdir(_examples_dir)
        csvReader = _re.CsvScenarioReader(input_data_dir)
        initial_nodal_data = csvReader.read_scenario()
        _os.chdir(cwd)

        # When
        converters = _cs.get_converters(initial_nodal_data, nr_of_buildings=4)
        graphData = _cs.get_graph_data(converters)
        if filter_results:
            graphData.nodes = [n for n in graphData.nodes if
                               ('building' in n['data'] and n['data']['building'] == building_no)
                               or (include_links and n['classes'] == "link")]
            graphData.edges = [e for e in graphData.edges if
                               (get_building_no(e['data']['source']) == get_building_no(e['data']['target']) == building_no)
                               or (include_links and (is_link(e['data']['source']) or is_link(e['data']['target'])) and
                                   (
                                           get_building_no(e['data']['target']) == building_no or
                                           get_building_no(e['data']['source']) == building_no
                                   ))]
        _va.run_cytoscape_visualizer(graphData=graphData)

        self.assertEqual(True, False)  # add assertion here

class TestScenarioTillGraphData(_ut.TestCase):
    def setUp(self):
        self.maxDiff = None

    def test_example_scenario(self):
        input_data_path = _input_data_dir / "scenario.xls"

         # Given
        time_period = _pd.date_range("2018-01-01 00:00:00", "2018-01-31 23:00:00", freq="60min")

        _os.chdir(_examples_dir)
        network = _en.EnergyNetworkClass(time_period)
        data = _pd.ExcelFile(str(input_data_path))
        initial_nodal_data = network.get_nodal_data_from_Excel(data)
        data.close()
        _os.chdir(cwd)

        # When
        converters = _cs.get_converters(initial_nodal_data, nr_of_buildings=4)
        graphData = _cs.get_graph_data(converters)

        with open(_pl.Path(__file__).parent / 'expected_files' / 'test_example_scenario_nodes.json') as f:
            nodes_expected = json.load(f)

        assert len(graphData.nodes) == len(nodes_expected)
        self.assertListEqual(graphData.nodes, nodes_expected)

        with open(_pl.Path(__file__).parent / 'expected_files' / 'test_example_scenario_edges.json') as f:
            edges_expected = json.load(f)
        assert len(graphData.edges) == len(edges_expected)
        self.assertListEqual(graphData.edges, edges_expected)


if __name__ == '__main__':
    _ut.main()
