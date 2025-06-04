import pathlib as _pl
import unittest as _ut
import pytest as _pt

import logging as _log
import numpy as _np
import pandas as _pd

import optihood.IO.readers as ior
import optihood.IO.writers as wr
import optihood.energy_network as en
import optihood.entities as ent
import tests.xls_helpers as xlsh

_CSV_DIR_PATH = xlsh.ROOT_DATA_DIR / "CSVs" / "basic_example_CSVs"
_input_data_dir = xlsh.ROOT_DATA_DIR / "excels" / "basic_example"
_input_data_path = _input_data_dir / "scenario.xls"


def join_if_multiple(x):
    """Needed to overcome changes when using subsequent IO for tests."""
    if isinstance(x, str):
        x = eval(x)

    if len(x) > 1:
        return ', '.join(x)

    return x[0]


def write_expected_file(nodal_data_with_unique_labels, expected_files_path: _pl.Path) -> None:
    """Helper function to update the expected files."""
    writer = wr.ScenarioFileWriterCSV(_pl.Path("irrelevant"), "individual")
    writer.data = nodal_data_with_unique_labels
    writer._write_scenario_to_file(expected_files_path)


class TestCsvScenarioReader(_ut.TestCase):
    def setUp(self):
        self.maxDiff = None

        network = en.EnergyNetworkClass(None)
        data = _pd.ExcelFile(str(_input_data_path))
        self.expected_nodal_data = network.get_nodal_data_from_Excel(data)
        data.close()

    def test_read(self):
        """Test to ensure new reader produces 'identical' inputs to optihood."""
        csvReader = ior.CsvScenarioReader(_CSV_DIR_PATH, "current")
        nodal_data = csvReader.read_scenario()

        errors = []

        xlsh.check_assertion(self, errors, nodal_data.keys(), self.expected_nodal_data.keys())

        for key, df_current in nodal_data.items():
            # check_dtype=False to simplify comparison between Excel and CSV files.
            xlsh.check_dataframe_assertion(errors, df_current, self.expected_nodal_data[key], check_dtype=False)

        if errors:
            raise ExceptionGroup(f"found {len(errors)} errors", errors)

    def test_read_without_future_warning(self):
        """Test to ensure new reader produces 'identical' inputs to optihood."""
        csvReader = ior.CsvScenarioReader(_CSV_DIR_PATH)
        nodal_data = csvReader.read_scenario()

        errors = []

        xlsh.check_assertion(self, errors, nodal_data.keys(), self.expected_nodal_data.keys())

        for key, df_current in nodal_data.items():
            # check_dtype=False to simplify comparison between Excel and CSV files.
            xlsh.check_dataframe_assertion(errors, df_current, self.expected_nodal_data[key], check_dtype=False)

        if errors:
            raise ExceptionGroup(f"found {len(errors)} errors", errors)

    def test_get_unique_labels(self):
        """unit test"""
        df = _pd.DataFrame({ent.CommonLabels.label: ["a", "a", "b", "c"],
                            ent.CommonLabels.building: ["1", "2", "1", "1"],
                            })
        results = ior.get_unique_labels(df)
        self.assertListEqual(results, ['a__B001', 'a__B002', 'b__B001', 'c__B001'])

    def test_get_unique_buses(self):
        """unit test"""
        df = _pd.DataFrame({ent.CommonLabels.to: ["a", "a,b", "b,d,e", "c"],
                            ent.CommonLabels.building: ["1", "2", "1", "1"],
                            })
        results = ior.get_unique_buses(df, ent.CommonLabels.to)
        self.assertListEqual(results, [['a__B001'],
                                       ['a__B002', 'b__B002'],
                                       ['b__B001', 'd__B001', 'e__B001'],
                                       ['c__B001']])

    def test_add_unique_label_columns(self):
        """end2end test
        Unfortunately, the reader adds quotes to the entries.
        This leads to very strange behavior in assert_frame_equal:
        At positional index 0, first diff: ['electricityProdBus__B001'] != ['electricityProdBus__B001']
        Thus, this test undoes the work of putting strings in lists, to put them back to a single string again.
        """
        csvReader = ior.CsvScenarioReader(_CSV_DIR_PATH)
        nodal_data = csvReader.read_scenario()

        nodal_data_with_unique_labels = ior.add_unique_label_columns(nodal_data)

        expected_files_path = _pl.Path(__file__).parent / "expected_files" / "without_building_csvs"
        # =================================
        # TODO: Use this to update the expected files.  # pylint: disable=fixme
        # write_expected_file(nodal_data_with_unique_labels, expected_files_path)
        # =================================

        csvReader = ior.CsvScenarioReader(expected_files_path)
        expected_data = csvReader.read_scenario()

        errors = []

        xlsh.check_assertion(self, errors, nodal_data_with_unique_labels.keys(), expected_data.keys())

        for key, df_current in nodal_data_with_unique_labels.items():
            # check_dtype=False to simplify comparison between Excel and CSV files.
            df_expected = expected_data[key]
            from_unique = ent.CommonLabels.from_unique
            if from_unique in df_current.columns:
                df_expected[from_unique] = df_expected[from_unique].apply(join_if_multiple)
                df_current[from_unique] = df_current[from_unique].apply(join_if_multiple)

            to_unique = ent.CommonLabels.to_unique
            if to_unique in df_current.columns:
                df_expected[to_unique] = df_expected[to_unique].apply(join_if_multiple)
                df_current[to_unique] = df_current[to_unique].apply(join_if_multiple)

            connect_unique = ent.CommonLabels.connect_unique
            if connect_unique in df_current.columns:
                df_expected[connect_unique] = df_expected[connect_unique].apply(join_if_multiple)
                df_current[connect_unique] = df_current[connect_unique].apply(join_if_multiple)

            xlsh.check_dataframe_assertion(errors, df_current, df_expected, check_dtype=False)

        if errors:
            raise ExceptionGroup(f"found {len(errors)} errors", errors)

    def test_get_unique_buildings_with_circuits(self):
        """unit test"""
        df = _pd.DataFrame({ent.BuildingModelParameters.Building_Number: [1, 1, 2, 3],
                            ent.BuildingModelParameters.Circuit: [1, 2, 1, 1],
                            })
        results = ior.get_unique_buildings(df)
        self.assertListEqual(results, ['Building_model__B001_C001', 'Building_model__B001_C002',
                                       'Building_model__B002_C001', 'Building_model__B003_C001'])

    def test_get_unique_buildings_without_circuits(self):
        """unit test"""
        df = _pd.DataFrame({ent.BuildingModelParameters.Building_Number: [1, 1, 2, 3],
                            })
        results = ior.get_unique_buildings(df)
        self.assertListEqual(results, ['Building_model__B001', 'Building_model__B001', 'Building_model__B002',
                                       'Building_model__B003'])

    def test_add_unique_label_columns_including_buildings(self):
        """End2end test"""
        csvReader = ior.CsvScenarioReader(_CSV_DIR_PATH)
        nodal_data = csvReader.read_scenario()
        building_df = _pd.DataFrame({ent.BuildingModelParameters.Building_Number: [1, 1, 2, 3],
                                     ent.BuildingModelParameters.Circuit: [1, 2, 1, 1],
                                     })
        nodal_data[ent.NodeKeysOptional.building_model_parameters] = building_df

        nodal_data_with_unique_labels = ior.add_unique_label_columns(nodal_data)

        expected_files_path = _pl.Path(__file__).parent / "expected_files" / "without_building_csvs"

        # =================================
        # TODO: Use this to update the expected files.  # pylint: disable=fixme
        # write_expected_file(nodal_data_with_unique_labels, expected_files_path)
        # =================================

        csvReader = ior.CsvScenarioReader(expected_files_path)
        expected_data = csvReader.read_scenario()

        building_df_expected = building_df.copy()
        building_df_expected[ent.BuildingModelParameters.building_unique] = ['Building_model__B001_C001',
                                                                             'Building_model__B001_C002',
                                                                             'Building_model__B002_C001',
                                                                             'Building_model__B003_C001',
                                                                             ]
        expected_data[ent.NodeKeysOptional.building_model_parameters] = building_df_expected

        errors = []

        xlsh.check_assertion(self, errors, nodal_data_with_unique_labels.keys(), expected_data.keys())

        for key, df_current in nodal_data_with_unique_labels.items():
            # check_dtype=False to simplify comparison between Excel and CSV files.
            df_expected = expected_data[key]
            from_unique = ent.CommonLabels.from_unique
            if from_unique in df_current.columns:
                df_expected[from_unique] = df_expected[from_unique].apply(join_if_multiple)
                df_current[from_unique] = df_current[from_unique].apply(join_if_multiple)

            to_unique = ent.CommonLabels.to_unique
            if to_unique in df_current.columns:
                df_expected[to_unique] = df_expected[to_unique].apply(join_if_multiple)
                df_current[to_unique] = df_current[to_unique].apply(join_if_multiple)

            connect_unique = ent.CommonLabels.connect_unique
            if connect_unique in df_current.columns:
                df_expected[connect_unique] = df_expected[connect_unique].apply(join_if_multiple)
                df_current[connect_unique] = df_current[connect_unique].apply(join_if_multiple)

            xlsh.check_dataframe_assertion(errors, df_current, df_expected, check_dtype=False)

        if errors:
            raise ExceptionGroup(f"found {len(errors)} errors", errors)


class TestProfileAndOtherDataReader:
    def setUp(self):
        self.maxDiff = None

    def test_get_values_from_dataframe(self):
        df = _pd.DataFrame({"label": ["thing", "stuff"],
                            "desired_value": [1, 2],
                            })
        results = ior.ProfileAndOtherDataReader().get_values_from_dataframe(df, "stuff", "label",
                                                                            "desired_value", message="Test issue")
        assert results == 2

    def test_get_values_from_dataframe_nan(self, caplog):
        df = _pd.DataFrame({"label": ["thing", "stuff"],
                            "desired_value": [1, _np.nan],
                            })
        with caplog.at_level(_log.ERROR):
            with _pt.raises(ValueError):
                ior.ProfileAndOtherDataReader().get_values_from_dataframe(df, "stuff", "label",
                                                                          "desired_value", message="Test issue")
            assert "Value empty in:" in caplog.text

    def test_get_values_from_dataframe_nan_allowed(self):
        df = _pd.DataFrame({"label": ["thing", "stuff"],
                            "desired_value": [1, _np.nan],
                            })
        results = ior.ProfileAndOtherDataReader().get_values_from_dataframe(df, "stuff", "label",
                                                                            "desired_value", message="Test issue",
                                                                            nan_allowed=True)
        assert _np.isnan(results)

    def test_get_values_from_dataframe_path(self):
        df = _pd.DataFrame({"label": ["thing", "stuff"],
                            "desired_value": [1, "path_to_profile.csv"],
                            })
        results = ior.ProfileAndOtherDataReader().get_values_from_dataframe(df, "stuff", "label",
                                                                            "desired_value", message="Test issue")
        assert results == "path_to_profile.csv"

    def test_get_values_from_dataframe_change_types(self, caplog):
        df = _pd.DataFrame({"label": ["thing", "stuff"],
                            "desired_value": [1, True],
                            })

        with caplog.at_level(_log.ERROR):
            with _pt.raises(ValueError):
                ior.ProfileAndOtherDataReader().get_values_from_dataframe(df, "stuff", "label",
                                                                          "desired_value", message="Test issue",
                                                                          desired_instances=(float))
            assert "Corrupt value in:" in caplog.text

    @_pt.mark.manual
    def test_add_weather_profiles(self):
        ior.ProfileAndOtherDataReader().add_weather_profiles()
        assert False

    @_pt.mark.manual
    def test_add_electricity_cost(self):
        ior.ProfileAndOtherDataReader().add_electricity_cost()
        assert False

    @_pt.mark.manual
    def test_add_electricity_impact(self):
        ior.ProfileAndOtherDataReader().add_electricity_impact()
        assert False

    @_pt.mark.manual
    def test_cluster_desired_column(self):
        ior.ProfileAndOtherDataReader().cluster_desired_column()
        assert False

    @_pt.mark.manual
    def test_cluster_and_multiply_desired_column(self):
        ior.ProfileAndOtherDataReader().cluster_and_multiply_desired_column()
        assert False

    @_pt.mark.manual
    def test_add_demand_profiles(self):
        ior.ProfileAndOtherDataReader().add_demand_profiles()
        assert False

    @_pt.mark.manual
    def test_maybe_add_natural_gas(self):
        ior.ProfileAndOtherDataReader().maybe_add_natural_gas()
        assert False

    @_pt.mark.manual
    def test_maybe_add_building_model_with_internal_gains(self):
        ior.ProfileAndOtherDataReader().maybe_add_building_model_with_internal_gains()
        assert False

    @_pt.mark.manual
    def test_clip_to_time_index(self):
        ior.ProfileAndOtherDataReader().clip_to_time_index()
        assert False
