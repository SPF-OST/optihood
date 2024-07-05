import os as _os
import pathlib as _pl

import pandas as _pd

import optihood as _oh
import optihood.energy_network as _en
from tests.xls_helpers import check_assertion

cwd = _os.getcwd()
packageDir = _pl.Path(_oh.__file__).resolve().parent
_input_data_dir = packageDir / ".." / "data" / "excels" / "basic_example"
_examples_dir = packageDir / ".." / "data" / "examples"


class TestEnergyNetwork:
    def test_set_from_excel(self):
        """ File System touching test to check see whether network is populated correctly using a scenario. """

        # Given
        _input_data_path = str(_input_data_dir / "scenario.xls")

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
        check_assertion(errors, len(network.groups), 147)

        check_assertion(errors, len(network.nodes), 140)

        check_assertion(errors, network.results, None)

        check_assertion(errors, len(network.signals), 1)

        check_assertion(errors, network.temporal, None)

        check_assertion(errors, len(network.timeincrement), 744)

        check_assertion(errors, network.timeincrement.unique(), 1.)

        check_assertion(errors, len(network.timeindex), 745)

        if errors:
            raise ExceptionGroup(f"found {len(errors)} errors", errors)


