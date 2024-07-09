import os as _os
import pathlib as _pl
import unittest as _ut

import pandas as _pd

import optihood as _oh
import optihood.energy_network as _en
from tests.xls_helpers import check_assertion

cwd = _os.getcwd()
packageDir = _pl.Path(_oh.__file__).resolve().parent
_input_data_dir = packageDir / ".." / "data" / "excels" / "basic_example"
_examples_dir = packageDir / ".." / "data" / "examples"
_input_data_path = str(_input_data_dir / "scenario.xls")


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
        network.setFromExcel(_input_data_path, nr_of_buildings, opt=optimization_type)
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
        network = _en.EnergyNetworkClass(None)

        data = _pd.ExcelFile(_input_data_path)
        initial_nodal_data = network.get_nodal_data_from_Excel(data)
        data.close()

        errors = []

        check_assertion(self, errors, len(initial_nodal_data), 9)
        check_assertion(self, errors, list(initial_nodal_data.keys()), [
            "buses",
            "grid_connection",
            "commodity_sources",
            "solar",
            "transformers",
            "demand",
            "storages",
            "stratified_storage",
            "profiles",
        ])

        check_assertion(self, errors, initial_nodal_data["buses"].shape, (48, 5))
        check_assertion(self, errors, initial_nodal_data["grid_connection"].shape, (24, 5))
        check_assertion(self, errors, initial_nodal_data["commodity_sources"].shape, (8, 6))
        check_assertion(self, errors, initial_nodal_data["solar"].shape, (8, 31))
        check_assertion(self, errors, initial_nodal_data["transformers"].shape, (16, 19))
        check_assertion(self, errors, initial_nodal_data["demand"].shape, (12, 7))
        check_assertion(self, errors, initial_nodal_data["storages"].shape, (12, 20))
        check_assertion(self, errors, initial_nodal_data["stratified_storage"].shape, (2, 11))
        check_assertion(self, errors, initial_nodal_data["profiles"].shape, (2, 3))

        if errors:
            raise ExceptionGroup(f"found {len(errors)} errors", errors)
