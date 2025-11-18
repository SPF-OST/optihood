import os as _os
import pathlib as _pl
import unittest as _ut

import pandas as _pd
import pytest as _pt

import optihood.MPC.interface as mpci
import optihood.energy_network as en
import optihood.entities as ent
import tests.xls_helpers as xlsh


class TestPrepMpcInputs(_ut.TestCase):
    def setUp(self):
        self.maxDiff = None

    def test_maybe_get_entries_or_defaults_sh_storage_nothing(self):
        """Ensures nothing is returned, when nothing found."""
        nodal_data = {ent.NodeKeys.storages: _pd.DataFrame(0, index=[0, 1], columns=[ent.StorageLabels.label.value])}
        result = mpci.StoragesMPC().maybe_get_entries_or_defaults(nodal_data)
        self.assertDictEqual(result, {})

    def test_maybe_get_entries_or_defaults_sh_storage_no_init(self):
        """Checks whether the default is used correctly."""
        nodal_data = {ent.NodeKeys.storages: _pd.DataFrame(
            {ent.CommonLabels.label.value: [ent.StorageTypes.shStorage, 0, 0],
             ent.CommonLabels.label_unique.value: ["shStorage__B001", 0, 0],
             }
        )}
        result = mpci.StoragesMPC().maybe_get_entries_or_defaults(nodal_data)
        self.assertDictEqual(result, {"shStorage__B001": {ent.StorageLabels.initial_capacity.value: 0.0}})

    def test_maybe_get_entries_or_defaults_sh_storage_with_init(self):
        """Checks whether the initial capacity is used correctly."""
        nodal_data = {ent.NodeKeys.storages: _pd.DataFrame(
            {ent.CommonLabels.label.value: [ent.StorageTypes.shStorage, 0, 0],
             ent.CommonLabels.label_unique.value: ["shStorage__B001", 0, 0],
             ent.StorageLabels.initial_capacity.value: [0.5, 0, 0],
             }
        )}
        result = mpci.StoragesMPC().maybe_get_entries_or_defaults(nodal_data)
        self.assertDictEqual(result, {"shStorage__B001": {ent.StorageLabels.initial_capacity.value: 0.5}})

    def test_maybe_get_entries_or_defaults_all_similar_storages_with_init(self):
        """Check whether all cases work together."""
        nodal_data = {ent.NodeKeys.storages: _pd.DataFrame(
            {ent.CommonLabels.label.value: [ent.StorageTypes.shStorage, ent.StorageTypes.dhwStorage,
                                            ent.StorageTypes.electricalStorage, 0, 0],
             ent.CommonLabels.label_unique.value: ["shStorage__B001", "dhwStorage__B003", "electricalStorage", 0, 0],
             ent.StorageLabels.initial_capacity.value: [0.5, 0.3, 0.75, 0, 0],
             }
        )}
        result = mpci.StoragesMPC().maybe_get_entries_or_defaults(nodal_data)
        self.assertDictEqual(result, {'dhwStorage__B003': {'initial capacity': 0.3},
                                      'electricalStorage': {'initial capacity': 0.75},
                                      'shStorage__B001': {'initial capacity': 0.5}}
                             )

    def test_maybe_get_entries_or_defaults_ice_storage_nothing(self):
        """Checks whether this is ignored correctly."""
        nodal_data = {ent.NodeKeys.storages: _pd.DataFrame(0, index=[0, 1], columns=[ent.StorageLabels.label.value])}
        result = mpci.IceStorageMPC().maybe_get_entries_or_defaults(nodal_data)
        self.assertDictEqual(result, {})

    def test_maybe_get_entries_or_defaults_ice_storage_no_init(self):
        """Checks whether the default is used correctly."""
        nodal_data = {ent.NodeKeys.storages: _pd.DataFrame(
            {ent.CommonLabels.label.value: [ent.IceStorageTypes.iceStorage, 0, 0],
             ent.CommonLabels.label_unique.value: ["iceStorage__B001", 0, 0],
             }
        )}
        result = mpci.IceStorageMPC().maybe_get_entries_or_defaults(nodal_data)
        self.assertDictEqual(result, {"iceStorage__B001": {ent.StorageLabels.initial_capacity.value: 0.0,
                                                           ent.StorageLabels.initial_temp.value: 2.0}})

    def test_maybe_get_entries_or_defaults_ice_storage_with_init(self):
        """Checks whether the initial values are used correctly."""
        nodal_data = {ent.NodeKeys.storages: _pd.DataFrame(
            {ent.CommonLabels.label.value: [ent.IceStorageTypes.iceStorage, 0, 0],
             ent.CommonLabels.label_unique.value: ["iceStorage__B001", 0, 0],
             ent.StorageLabels.initial_capacity.value: [0.5, 0, 0],
             ent.StorageLabels.initial_temp.value: [0.5, 0, 0],
             }
        )}
        result = mpci.IceStorageMPC().maybe_get_entries_or_defaults(nodal_data)
        self.assertDictEqual(result, {"iceStorage__B001": {ent.StorageLabels.initial_capacity.value: 0.5,
                                                           ent.StorageLabels.initial_temp.value: 0.5}})

    def test_maybe_get_entries_or_defaults_building_nothing(self):
        """Users should get proper feedback when no data is in the csv."""
        building_model_params = _pd.DataFrame(columns=[ent.BuildingModelParameters.tWallInit])
        nodal_data = {ent.NodeKeysOptional.building_model_parameters: building_model_params}
        with _pt.raises(ValueError):
            mpci.BuildingMPC().maybe_get_entries_or_defaults(nodal_data)

    def test_maybe_get_entries_or_defaults_building_no_init(self):
        """Checks whether the default is used correctly."""
        building_model_params = _pd.DataFrame(
            {ent.BuildingModelParameters.building_unique.value: ["Building_model__B001_0", "Building_model__B001_1",
                                                                 "Building_model__B002_0"],
             }
        )
        nodal_data = {ent.NodeKeysOptional.building_model_parameters: building_model_params}
        result = mpci.BuildingMPC().maybe_get_entries_or_defaults(nodal_data)
        self.assertDictEqual(result, {
            'Building_model__B001_0': {'tDistributionInit': 15.0, 'tIndoorInit': 20.0, 'tWallInit': 25.0},
            'Building_model__B001_1': {'tDistributionInit': 15.0, 'tIndoorInit': 20.0, 'tWallInit': 25.0},
            'Building_model__B002_0': {'tDistributionInit': 15.0, 'tIndoorInit': 20.0, 'tWallInit': 25.0}})

    def test_maybe_get_entries_or_defaults_building_with_init(self):
        """Checks whether the default is used correctly."""
        building_model_params = _pd.DataFrame(
            {ent.BuildingModelParameters.building_unique.value: ["Building_model__B001_0", "Building_model__B001_1",
                                                                 "Building_model__B002_0"],
             ent.BuildingModelParameters.tWallInit: [10., 12., 13.],
             ent.BuildingModelParameters.tIndoorInit: [22., 21., 20.3],
             ent.BuildingModelParameters.tDistributionInit: [30., 26., 29.],
             }
        )
        nodal_data = {ent.NodeKeysOptional.building_model_parameters: building_model_params}
        result = mpci.BuildingMPC().maybe_get_entries_or_defaults(nodal_data)
        self.assertDictEqual(result, {
            'Building_model__B001_0': {'tDistributionInit': 30.0, 'tIndoorInit': 22.0, 'tWallInit': 10.0},
            'Building_model__B001_1': {'tDistributionInit': 26.0, 'tIndoorInit': 21.0, 'tWallInit': 12.0},
            'Building_model__B002_0': {'tDistributionInit': 29.0, 'tIndoorInit': 20.3, 'tWallInit': 13.0}})

    def test_prep_mpc_inputs(self):
        nodal_data = {ent.NodeKeys.storages: _pd.DataFrame(
            {ent.CommonLabels.label.value: [ent.IceStorageTypes.iceStorage, ent.StorageTypes.shStorage,
                                            ent.StorageTypes.dhwStorage,
                                            ent.StorageTypes.electricalStorage, 0, 0],
             ent.CommonLabels.label_unique.value: ["iceStorage__B001", "shStorage__B001", "dhwStorage__B003",
                                                   "electricalStorage", 0, 0],
             ent.StorageLabels.initial_capacity.value: [0.25, 0.5, 0.3, 0.75, 0, 0],
             ent.StorageLabels.initial_temp.value: [1.5, "x", "x", "x", "x", "x"],
             }
        )}
        result, label_to_sheet = mpci.prep_mpc_inputs(nodal_data)

        errors = []
        try:
            self.assertDictEqual(result, {'dhwStorage__B003': {'initial capacity': 0.3},
                                          'electricalStorage': {'initial capacity': 0.75},
                                          'shStorage__B001': {'initial capacity': 0.5},
                                          'iceStorage__B001': {'initial capacity': 0.25, 'initial_temp': 1.5},
                                          }
                                 )
        except AssertionError as e:
            errors.append(e)

        try:
            self.assertDictEqual(label_to_sheet,
                                 {'dhwStorage__B003': ent.NodeKeys.storages,
                                  'electricalStorage': ent.NodeKeys.storages,
                                  'iceStorage__B001': ent.NodeKeys.storages,
                                  'shStorage__B001': ent.NodeKeys.storages
                                  })
        except AssertionError as e:
            errors.append(e)

        if errors:
            raise ExceptionGroup(f"Found {len(errors)} issues", errors)

    def test_prep_mpc_inputs_with_building(self):
        nodal_data = {ent.NodeKeys.storages: _pd.DataFrame(
            {ent.CommonLabels.label.value: [ent.IceStorageTypes.iceStorage, ent.StorageTypes.shStorage,
                                            ent.StorageTypes.dhwStorage,
                                            ent.StorageTypes.electricalStorage, 0, 0],
             ent.CommonLabels.label_unique.value: ["iceStorage__B001", "shStorage__B001", "dhwStorage__B003",
                                                   "electricalStorage", 0, 0],
             ent.StorageLabels.initial_capacity.value: [0.25, 0.5, 0.3, 0.75, 0, 0],
             ent.StorageLabels.initial_temp.value: [1.5, "x", "x", "x", "x", "x"],
             }
        )}
        building_model_params = _pd.DataFrame(
            {ent.BuildingModelParameters.building_unique.value: ["Building_model__B001", "Building_model__B002"],
             ent.BuildingModelParameters.tWallInit: [10., 13.],
             ent.BuildingModelParameters.tIndoorInit: [22., 20.3],
             ent.BuildingModelParameters.tDistributionInit: [30., 29.],
             }
        )
        result, label_to_sheet = mpci.prep_mpc_inputs(nodal_data, building_model_params)

        errors = []
        try:
            self.assertDictEqual(result, {'dhwStorage__B003': {'initial capacity': 0.3},
                                          'electricalStorage': {'initial capacity': 0.75},
                                          'shStorage__B001': {'initial capacity': 0.5},
                                          'iceStorage__B001': {'initial capacity': 0.25, 'initial_temp': 1.5},
                                          'Building_model__B001': {'tDistributionInit': 30.0, 'tIndoorInit': 22.0,
                                                                   'tWallInit': 10.0},
                                          'Building_model__B002': {'tDistributionInit': 29.0, 'tIndoorInit': 20.3,
                                                                   'tWallInit': 13.0},
                                          }
                                 )
        except AssertionError as e:
            errors.append(e)

        try:
            self.assertDictEqual(label_to_sheet,
                                 {'Building_model__B001': ent.NodeKeysOptional.building_model_parameters,
                                  'Building_model__B002': ent.NodeKeysOptional.building_model_parameters,
                                  'dhwStorage__B003': ent.NodeKeys.storages,
                                  'electricalStorage': ent.NodeKeys.storages,
                                  'iceStorage__B001': ent.NodeKeys.storages,
                                  'shStorage__B001': ent.NodeKeys.storages
                                  })
        except AssertionError as e:
            errors.append(e)

        if errors:
            raise ExceptionGroup(f"Found {len(errors)} issues", errors)


STORAGES_SHEET_NAME = ent.NodeKeys.storages
BUILDING_MODEL_SHEET_NAME = ent.NodeKeysOptional.building_model_parameters


class TestMpcHandler(_ut.TestCase):
    def setUp(self):
        self.maxDiff = None

    def test_get_mpc_scenario_from_csv(self):
        """End2end test for this method.
        Includes assert of part of nodal_data state relevant for MPC.

        Maybe Flaky
        Seems to introduce the "building_model_parameter when run in the terminal
        """

        # Profile data is located relative to example scripts.
        # Therefore, we need to change directories.
        cur_dir = _os.getcwd()
        _os.chdir(xlsh.EXAMPLE_SCRIPT_DIR)
        input_folder_path = xlsh.ROOT_DATA_DIR / "CSVs" / "MPC_example_CSVs"
        mpc = mpci.MpcHandler(prediction_window_in_hours=24, time_step_in_minutes=60,
                              nr_of_buildings=1)
        mpc.set_full_time_period(2018, 1, 1, 2018, 1, 31)

        mpc.optimization_settings = en.OptimizationProperties(
            optimization_type="costs",
            merge_link_buses=False,
            merge_buses=None,
            merge_heat_source_sink=False,
            temperature_levels=False,
            cluster_size=None,
            dispatch_mode=True,
            include_carbon_benefits=False,
        )

        system_state = mpc.get_mpc_scenario_from_csv(input_folder_path)

        _os.chdir(cur_dir)

        errors = []
        try:
            self.assertDictEqual(system_state, {'electricalStorage__B001': {'initial capacity': 0},
                                                'shStorage__B001': {'initial capacity': 0}})
        except AssertionError as e:
            errors.append(e)

        try:
            assert mpc.nr_of_buildings == 1
        except AssertionError as e:
            errors.append(e)

        try:
            assert mpc.prediction_window_in_hours == 24
        except AssertionError as e:
            errors.append(e)

        try:
            assert mpc.time_step_in_minutes == 60
        except AssertionError as e:
            errors.append(e)

        try:
            assert all(mpc.nodal_data[ent.NodeKeys.storages][ent.StorageLabels.initial_capacity]) == 0
        except AssertionError as e:
            errors.append(e)

        if errors:
            raise ExceptionGroup(f"Found {len(errors)} issues", errors)

    def test_get_current_time_period(self):
        """Unit test"""
        current_time_period_start = _pd.DatetimeIndex(["2018-01-01"])[0]
        mpc = mpci.MpcHandler(prediction_window_in_hours=2, time_step_in_minutes=60,
                              nr_of_buildings=1)
        current_time_period = mpc.get_current_time_period(current_time_period_start)
        expected = _pd.DatetimeIndex(["2018-01-01 00:00:00", "2018-01-01 01:00:00", "2018-01-01 02:00:00"])
        _pd.testing.assert_index_equal(current_time_period, expected)

    def test_update_nodal_data(self):
        """Unit test"""
        current_system_state = {'electricalStorage__B001': {'initial capacity': 0.42},
                                'shStorage__B001': {'initial capacity': 0.66}}
        mpc = mpci.MpcHandler(prediction_window_in_hours=2, time_step_in_minutes=60,
                              nr_of_buildings=1)
        mpc.nodal_data = {STORAGES_SHEET_NAME: _pd.DataFrame([
            {ent.CommonLabels.label_unique: 'electricalStorage__B001', 'initial capacity': 0.},
            {ent.CommonLabels.label_unique: 'shStorage__B001', 'initial capacity': 0.},
        ])
        }
        mpc.label_to_sheet = {'electricalStorage__B001': STORAGES_SHEET_NAME,
                              'shStorage__B001': STORAGES_SHEET_NAME}

        current_nodal_data = mpc.update_nodal_data(current_system_state)

        df_expected = _pd.DataFrame(
            [{ent.CommonLabels.label_unique: 'electricalStorage__B001', 'initial capacity': 0.42},
             {ent.CommonLabels.label_unique: 'shStorage__B001', 'initial capacity': 0.66},
             ])
        _pd.testing.assert_frame_equal(current_nodal_data[STORAGES_SHEET_NAME], df_expected)

    def test_update_nodal_data_with_building(self):
        current_system_state = {'electricalStorage__B001': {'initial capacity': 0.42},
                                'shStorage__B001': {'initial capacity': 0.66},
                                'Building_model__B001': {'tDistributionInit': 25.1, 'tIndoorInit': 23.9,
                                                         'tWallInit': 11.3},
                                'Building_model__B002': {'tDistributionInit': 27.3, 'tIndoorInit': 21.5,
                                                         'tWallInit': 17.8}
                                }
        mpc = mpci.MpcHandler(prediction_window_in_hours=2, time_step_in_minutes=60,
                              nr_of_buildings=1)
        mpc.nodal_data = {
            STORAGES_SHEET_NAME: _pd.DataFrame([
                {ent.CommonLabels.label_unique: 'electricalStorage__B001', 'initial capacity': 0.},
                {ent.CommonLabels.label_unique: 'shStorage__B001', 'initial capacity': 0.},
            ]),
            ent.NodeKeysOptional.building_model_parameters: _pd.DataFrame([
                {ent.BuildingModelParameters.building_unique: 'Building_model__B001', 'tDistributionInit': 30.0,
                 'tIndoorInit': 22.0, 'tWallInit': 10.0},
                {ent.BuildingModelParameters.building_unique: 'Building_model__B002', 'tDistributionInit': 29.0,
                 'tIndoorInit': 20.3, 'tWallInit': 13.0},
            ])
        }
        mpc.label_to_sheet = {'electricalStorage__B001': STORAGES_SHEET_NAME,
                              'shStorage__B001': STORAGES_SHEET_NAME,
                              'Building_model__B001': BUILDING_MODEL_SHEET_NAME,
                              'Building_model__B002': BUILDING_MODEL_SHEET_NAME,
                              }

        current_nodal_data = mpc.update_nodal_data(current_system_state)

        errors = []

        df_expected = _pd.DataFrame(
            [{ent.CommonLabels.label_unique: 'electricalStorage__B001', 'initial capacity': 0.42},
             {ent.CommonLabels.label_unique: 'shStorage__B001', 'initial capacity': 0.66},
             ])
        try:
            _pd.testing.assert_frame_equal(current_nodal_data[STORAGES_SHEET_NAME], df_expected)
        except AssertionError as e:
            errors.append(e)

        df_expected = _pd.DataFrame([
            {ent.BuildingModelParameters.building_unique: 'Building_model__B001', 'tDistributionInit': 25.1,
             'tIndoorInit': 23.9, 'tWallInit': 11.3},
            {ent.BuildingModelParameters.building_unique: 'Building_model__B002', 'tDistributionInit': 27.3,
             'tIndoorInit': 21.5, 'tWallInit': 17.8},
        ])

        try:
            _pd.testing.assert_frame_equal(current_nodal_data[BUILDING_MODEL_SHEET_NAME], df_expected)
        except AssertionError as e:
            errors.append(e)

        if errors:
            raise ExceptionGroup(f"Found {len(errors)} issues", errors)

    def test_get_flow_label_to_sheet(self):
        results = {
            "a": _pd.DataFrame(columns=["1", "2", "3"]),
            "b": _pd.DataFrame(columns=["4", "5", "6"]),
            "c": _pd.DataFrame(columns=["7", "8", "9"]),
        }
        expected_label_to_sheet = {
            "1": "a",
            "2": "a",
            "3": "a",
            "4": "b",
            "5": "b",
            "6": "b",
            "7": "c",
            "8": "c",
            "9": "c",
        }
        mpc = mpci.MpcHandler(prediction_window_in_hours=2, time_step_in_minutes=60,
                              nr_of_buildings=1)
        flow_label_to_sheet = mpc.get_flow_label_to_sheet(results)

        self.assertDictEqual(flow_label_to_sheet, expected_label_to_sheet)

    def test_rename_oemof_labels(self):
        """Unit test
        Describes the expected labels from oemof and the expected behavior for the renaming.

        The dictionary includes the names that should be renamed.
        The other names added to the input_names should be ignored by the renaming, which is why they are not
        added to the initial dictionary.
        """
        input_and_expected_names = {
            "(('pv__Building1', 'electricityProdBus__Building1'), 'flow')": "pv__B001__To__electricityProdBus__B001",
            "(('pv__Building567', 'electricityProdBus__Building567'), 'flow')":
                "pv__B567__To__electricityProdBus__B567",
            "(('electricityBus__Building1', 'excesselectricityBus__Building1'), 'flow')":
                "electricityBus__B001__To__excesselectricityBus__B001",
            "(('electricityProdBus__Building1', 'electricalStorage__Building1'), 'flow')":
                "electricityProdBus__B001__To__electricalStorage__B001",
            "(('electricalStorage__Building1', 'electricityBus__Building1'), 'flow')":
                "electricalStorage__B001__To__electricityBus__B001",
            "(('electricityBus__Building1', 'producedElectricity__Building1'), 'flow')":
                "electricityBus__B001__To__producedElectricity__B001",
            "(('electricityResource__Building1', 'gridBus__Building1'), 'flow')":
                "electricityResource__B001__To__gridBus__B001",
            "(('electricityInBus__Building1', 'HP__Building1'), 'flow')": "electricityInBus__B001__To__HP__B001",
            "(('HP__Building1', 'shSourceBus__Building1'), 'flow')": "HP__B001__To__shSourceBus__B001",
            "(('shSourceBus__Building1', 'shStorage__Building1'), 'flow')": "shSourceBus__B001__To__shStorage__B001",
            "(('shSourceBus__Building1', 'shSource__Building1'), 'flow')": "shSourceBus__B001__To__shSource__B001",
            "(('shStorage__Building1', 'spaceHeatingBus__Building1'), 'flow')":
                "shStorage__B001__To__spaceHeatingBus__B001",
            "(('spaceHeatingBus__Building1', 'spaceHeating__Building1'), 'flow')":
                "spaceHeatingBus__B001__To__spaceHeating__B001",
        }
        input_names = list(input_and_expected_names.keys())
        input_names += ["storage_content",  # TODO: check whether this should become "sh_storage_content"
                        "some_flow_to_be_ignored",
                        0,  # This occurs in the capacity sheets and should be fixed at a different level.
                        42,
                        ]

        rename_dict = mpci.MpcHandler.rename_oemof_labels(input_names)

        self.assertDictEqual(rename_dict, input_and_expected_names)

    def test_get_desired_energy_flows(self):
        """Unit test.
        This method should both rename the columns and collect the desired ones into a single data structure.
        """
        desired_flows_with_new_names = {
            "pv__B001__To__electricityProdBus__B001": "el_pv_produced",
            "electricityBus__B001__To__excesselectricityBus__B001": "el_to_grid",
            "electricityProdBus__B001__To__electricalStorage__B001": "el_pv_to_battery",
            "electricalStorage__B001__To__electricityBus__B001": "el_battery_discharge",
            "electricityBus__B001__To__producedElectricity__B001": "el_produced",
            "electricityResource__B001__To__gridBus__B001": "el_from_grid",
            "electricityInBus__B001__To__HP__B001": "HP_el_in",
            "HP__B001__To__shSourceBus__B001": "HP_heat_out",
            "shSourceBus__B001__To__shStorage__B001": "HP_to_TES",
            "shSourceBus__B001__To__shSource__B001": "HP_to_demand",
            "shStorage__B001__To__spaceHeatingBus__B001": "TES_to_demand",
            "spaceHeatingBus__B001__To__spaceHeating__B001": "sh_delivered",
        }
        expected_energy_flows = _pd.DataFrame(
            {
                "el_pv_produced": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.108543350181667, 8.272728965148124,
                                   50.89640662861397, 17.94914364741515, 7.54176286459802, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
                                   0.0, 0.0, 0.0, 0.0, 0.0],
                "el_to_grid": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 5.586883168290823, 46.5148636963539,
                               4.562246680843671, 6.47183429359802, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
                               15.02745821417941, 0.0, 0.0, 0.0],
                "el_pv_to_battery": [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, ],
                "el_battery_discharge": [0.554028571, 0.469628571, 7.245377247649912, 0.549585714, 0.6267,
                                         3.771141997591101, 6.202756082034924, 5.529049211325205, 5.907222702238744,
                                         3.144218023214221, 0.0, 0.0, 0.0, 0.0, 2.825040474208677, 3.212498410367769,
                                         1.398457143, 1.839342857, 2.005842857, 8.649585714, 12.11352857,
                                         25.47546728336945, 1.689628571, 0.813671429, 0.577228571],
                "el_produced": [0.554028571, 0.469628571, 7.245377247649912, 0.549585714, 0.6267, 3.771141997591101,
                                6.202756082034924, 5.529049211325205, 5.907222702238744, 4.252761373395888,
                                2.6858457968573, 4.381542932260076, 13.38689696657148, 1.069928571, 2.825040474208677,
                                3.212498410367769, 1.398457143, 1.839342857, 2.005842857, 8.649585714, 12.11352857,
                                10.44800906919004, 1.689628571, 0.813671429, 0.577228571],
                "el_from_grid": [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, ],
                "HP_el_in": [0.0, 0.0, 6.788420104649911, 0.0, 0.0, 3.160941997591101, 2.948527511034924,
                             2.792563497325205, 2.451579845238745, 1.688489944395888, 1.3952600828573,
                             0.08261436126007536, 11.45105410957148, 0.0, 1.766354760208677, 1.492741267367769, 0.0,
                             0.0, 0.0, 0.0, 0.0, 6.288094783190043, 0.0, 0.0, 0.0],
                "HP_heat_out": [0.0, 0.0, 28.77093082197741, 0.0, 0.0, 13.39682019424264, 12.49655733424264,
                                11.86780923424264, 10.47549639424264, 7.293487614242636, 6.043188243242636,
                                0.3715253452426365, 52.325, 0.0, 8.007204924272527, 6.730931781940396, 0.0, 0.0, 0.0,
                                0.0, 0.0, 28.0525510618056, 0.0, 0.0, 0.0],
                "HP_to_TES": [0.0, 0.0, 15.59785494197741, 0.0, 0.0, 0.0805135742426365, 0.0805135742426365,
                              0.0805135742426365, 0.0805135742426365, 0.0805135742426365, 0.0805135742426365,
                              0.0805135742426365, 52.325, 0.0, 3.353566187272527, 0.1341832079403957, 0.0, 0.0, 0.0,
                              0.0, 0.0, 20.6793614738056, 0.0, 0.0, 0.0],
                "HP_to_demand": [0.0, 0.0, 13.17307588, 0.0, 0.0, 13.31630662, 12.41604376, 11.78729566, 10.39498282,
                                 7.21297404, 5.962674669, 0.291011771, 0.0, 0.0, 4.653638737, 6.596748574, 0.0, 0.0,
                                 0.0, 0.0, 0.0, 7.373189588, 0.0, 0.0, 0.0],
                "TES_to_demand": [13.14460485, 13.16625478, 0.0, 13.17181806, 13.27046787, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
                                  0.0, 0.0, 3.008074284, 0.0, 0.0, 7.847446237, 8.90450432, 9.358278467, 7.240053475,
                                  6.579958661, 0.0, 9.326260232, 10.91023682, 11.85101617],
                "sh_delivered": [13.14460485, 13.16625478, 13.17307588, 13.17181806, 13.27046787, 13.31630662,
                                 12.41604376, 11.78729566, 10.39498282, 7.21297404, 5.962674669, 0.291011771, 0.0,
                                 3.008074284, 4.653638737, 6.596748574, 7.847446237, 8.90450432, 9.358278467,
                                 7.240053475, 6.579958661, 7.373189588, 9.326260232, 10.91023682, 11.85101617],
            },
            index=_pd.date_range("2018-01-01 00:00:00", "2018-01-02 00:00:00", freq="60min"),
        )
        expected_energy_flows.index.freq = None

        _input_data_path = _pl.Path(
            __file__).parent / "expected_files" / "results_MPC_example_2018_01_01__00_00_00.xlsx"
        data = _pd.ExcelFile(str(_input_data_path))
        results = {}
        for sheet in data.sheet_names:
            if any(sheet.startswith(s) for s in ["cap", "costs_", "env_"]):
                results[sheet] = data.parse(sheet)
            else:
                results[sheet] = data.parse(sheet, index_col=0)
        data.close()

        mpc = mpci.MpcHandler(prediction_window_in_hours=2, time_step_in_minutes=60,
                              nr_of_buildings=1)
        energy_flows = mpc.get_desired_energy_flows(results, desired_flows_with_new_names)

        _pd.testing.assert_frame_equal(energy_flows, expected_energy_flows)

    def test_clip_profiles(self):
        """End2end test for this method.
        Includes assert of part of nodal_data state relevant for MPC.
        """

        # Profile data is located relative to example scripts.
        # Therefore, we need to change directories.
        cur_dir = _os.getcwd()
        _os.chdir(xlsh.EXAMPLE_SCRIPT_DIR)
        input_folder_path = xlsh.ROOT_DATA_DIR / "CSVs" / "MPC_example_CSVs"
        mpc = mpci.MpcHandler(prediction_window_in_hours=24, time_step_in_minutes=60,
                              nr_of_buildings=1)
        mpc.set_full_time_period(2018, 1, 1, 2018, 1, 31)

        mpc.optimization_settings = en.OptimizationProperties(
            optimization_type="costs",
            merge_link_buses=False,
            merge_buses=None,
            merge_heat_source_sink=False,
            temperature_levels=False,
            cluster_size=None,
            dispatch_mode=True,
            include_carbon_benefits=False,
        )
        example_time_steps = _pd.date_range("2018-01-01 00:00:00", "2018-01-01 02:00:00", freq="60min")
        current_time_step = example_time_steps[-1]

        system_state = mpc.get_mpc_scenario_from_csv(input_folder_path)
        current_nodal_data = mpc.update_nodal_data(system_state)
        current_time_period = mpc.get_current_time_period(current_time_step)
        current_nodal_data = mpc.clip_profiles(current_nodal_data, current_time_period)



        _os.chdir(cur_dir)

        errors = []
        try:
            assert False
            
        except AssertionError as e:
            errors.append(e)



        if errors:
            raise ExceptionGroup(f"Found {len(errors)} issues", errors)