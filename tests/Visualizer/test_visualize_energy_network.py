import os as _os
import pathlib as _pl
import unittest as _ut
import pytest as _pt

import pandas as _pd

import optihood as _oh
import optihood.energy_network as _en
import optihood.Visualizer.visualizer_app as _va
import optihood.Visualizer.convert_scenario as _cs

cwd = _os.getcwd()
packageDir = _pl.Path(_oh.__file__).resolve().parent
_input_data_dir = packageDir / ".." / "data" / "excels" / "basic_example"
_examples_dir = packageDir / ".." / "data" / "examples"
_input_data_path = _input_data_dir / "scenario.xls"

manual = True


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
        converters = _cs.get_converters(initial_nodal_data)
        graphData = _cs.get_graph_data(converters)
        _va.run_cytoscape_visualizer(graphData=graphData)


        self.assertEqual(True, False)  # add assertion here


if __name__ == '__main__':
    _ut.main()
