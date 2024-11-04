import os as _os
import pathlib as _pl
import unittest as _ut

import pandas as _pd

import optihood as _oh
import optihood.energy_network as _en
from tests.xls_helpers import check_assertion, check_dataframe_assertion

cwd = _os.getcwd()
packageDir = _pl.Path(_oh.__file__).resolve().parent
_input_data_dir = packageDir / ".." / "data" / "excels" / "basic_example"
_examples_dir = packageDir / ".." / "data" / "examples"
_input_data_path = _input_data_dir / "scenario.xls"
_input_csv_dir = packageDir / ".." / "data" / "CSVs" / "basic_example_CSVs"


class TestEnergyNetwork(_ut.TestCase):
    def setUp(self):
        self.maxDiff = None

    def test_set_from_excel(self):
        """File System touching test to check see whether network is populated correctly using a scenario."""

        # Given

        time_period = _pd.date_range("2018-01-01 00:00:00", "2018-01-31 23:00:00", freq="60min")
        nr_of_buildings = 4
        optimization_type = "costs"  # set as "env" for environmental optimization and "costs" for cost optimization

        # When
        _os.chdir(_examples_dir)
        network = _en.EnergyNetworkClass(time_period)
        network.setFromExcel(str(_input_data_path), nr_of_buildings, opt=optimization_type)
        _os.chdir(cwd)

        # Then
        errors = []
        check_assertion(self, errors, len(network.groups), 147)

        check_assertion(self, errors, len(network.nodes), 140)

        check_assertion(self, errors, network.results, None)

        check_assertion(self, errors, len(network.signals), 1)

        check_assertion(self, errors, network.temporal, None)

        check_assertion(self, errors, len(network.timeincrement), 744)

        check_assertion(self, errors, network.timeincrement.unique(), 1.0)

        check_assertion(self, errors, len(network.timeindex), 745)

        if errors:
            raise ExceptionGroup(f"found {len(errors)} errors", errors)

    def test_get_nodal_data_from_Excel(self):
        """File System touching test to get an initial grip on what the nodal data should be after reading the
        scenario."""
        network = _en.EnergyNetworkClass(None)

        data = _pd.ExcelFile(str(_input_data_path))
        initial_nodal_data = network.get_nodal_data_from_Excel(data)
        data.close()

        errors = []

        check_assertion(self, errors, len(initial_nodal_data), 10)
        check_assertion(
            self,
            errors,
            list(initial_nodal_data.keys()),
            [
                "buses",
                "grid_connection",
                "commodity_sources",
                "solar",
                "transformers",
                "demand",
                "storages",
                "stratified_storage",
                "profiles",
                "links"
            ],
        )

        check_assertion(self, errors, initial_nodal_data["buses"].shape, (48, 5))
        check_assertion(self, errors, initial_nodal_data["grid_connection"].shape, (24, 5))
        check_assertion(self, errors, initial_nodal_data["commodity_sources"].shape, (8, 6))
        check_assertion(self, errors, initial_nodal_data["solar"].shape, (8, 31))
        check_assertion(self, errors, initial_nodal_data["transformers"].shape, (16, 19))
        check_assertion(self, errors, initial_nodal_data["demand"].shape, (12, 7))
        check_assertion(self, errors, initial_nodal_data["storages"].shape, (12, 20))
        check_assertion(self, errors, initial_nodal_data["stratified_storage"].shape, (2, 11))
        check_assertion(self, errors, initial_nodal_data["profiles"].shape, (2, 3))
        check_assertion(self, errors, initial_nodal_data["links"].shape, (3, 6))

        if errors:
            raise ExceptionGroup(f"found {len(errors)} errors", errors)

    def test_set_from_csvs(self):
        """File system touching test.
        Compare network state of the csv variety with that of the Excel variety.
        """
        time_period = _pd.date_range("2018-01-01 00:00:00", "2018-01-31 23:00:00", freq="60min")
        nr_of_buildings = 4
        optimization_type = "costs"  # set as "env" for environmental optimization and "costs" for cost optimization

        # When
        _os.chdir(_examples_dir)
        network_csv = _en.EnergyNetworkClass(time_period)
        network_csv.set_from_csv(_input_csv_dir, nr_of_buildings, opt=optimization_type)

        network_excel = _en.EnergyNetworkClass(time_period)
        network_excel.setFromExcel(_input_data_path, nr_of_buildings, opt=optimization_type)
        _os.chdir(cwd)

        # Then
        sorted_csv_nodes = sorted(list(network_csv.nodes))
        sorted_excel_nodes = sorted(list(network_excel.nodes))
        for i in range(len(sorted_csv_nodes)):
            sorted_csv_nodes[i] = str(sorted_csv_nodes[i])
            sorted_excel_nodes[i] = str(sorted_excel_nodes[i])
        self.assertListEqual(sorted_csv_nodes, sorted_excel_nodes)
        assert network_csv.results == network_excel.results
        # signals
        check_dataframe_assertion([], network_csv.timeincrement, network_excel.timeincrement)
        assert (network_csv.timeindex == network_excel.timeindex).all()
