import unittest as _ut
import pytest as _pt

import pandas as _pd

import optihood.MPC.interface as mpci
import optihood.entities as _ent


class TestPrepMpcInputs(_ut.TestCase):
    def setUp(self):
        self.maxDiff = None

    def test_maybe_get_entries_or_defaults_sh_storage_nothing(self):
        """Ensures nothing is returned, when nothing found."""
        nodal_data = {_ent.NodeKeys.storages: _pd.DataFrame(0, index=[0, 1], columns=[_ent.StorageLabels.label.value])}
        result = mpci.StoragesMPC().maybe_get_entries_or_defaults(nodal_data)
        self.assertDictEqual(result, {})

    def test_maybe_get_entries_or_defaults_sh_storage_no_init(self):
        """Checks whether the default is used correctly."""
        nodal_data = {_ent.NodeKeys.storages: _pd.DataFrame(
            {_ent.CommonLabels.label.value: [_ent.StorageTypes.shStorage, 0, 0],
             _ent.CommonLabels.label_unique.value: ["shStorage__B001", 0, 0],
             }
        )}
        result = mpci.StoragesMPC().maybe_get_entries_or_defaults(nodal_data)
        self.assertDictEqual(result, {"shStorage__B001": {_ent.StorageLabels.initial_capacity.value: 0.0}})

    def test_maybe_get_entries_or_defaults_sh_storage_with_init(self):
        """Checks whether the initial capacity is used correctly."""
        nodal_data = {_ent.NodeKeys.storages: _pd.DataFrame(
            {_ent.CommonLabels.label.value: [_ent.StorageTypes.shStorage, 0, 0],
             _ent.CommonLabels.label_unique.value: ["shStorage__B001", 0, 0],
             _ent.StorageLabels.initial_capacity.value: [0.5, 0, 0],
             }
        )}
        result = mpci.StoragesMPC().maybe_get_entries_or_defaults(nodal_data)
        self.assertDictEqual(result, {"shStorage__B001": {_ent.StorageLabels.initial_capacity.value: 0.5}})

    def test_maybe_get_entries_or_defaults_all_similar_storages_with_init(self):
        """Check whether all cases work together."""
        nodal_data = {_ent.NodeKeys.storages: _pd.DataFrame(
            {_ent.CommonLabels.label.value: [_ent.StorageTypes.shStorage, _ent.StorageTypes.dhwStorage,
                                             _ent.StorageTypes.electricalStorage, 0, 0],
             _ent.CommonLabels.label_unique.value: ["shStorage__B001", "dhwStorage__B003", "electricalStorage", 0, 0],
             _ent.StorageLabels.initial_capacity.value: [0.5, 0.3, 0.75, 0, 0],
             }
        )}
        result = mpci.StoragesMPC().maybe_get_entries_or_defaults(nodal_data)
        self.assertDictEqual(result, {'dhwStorage__B003': {'initial capacity': 0.3},
                                      'electricalStorage': {'initial capacity': 0.75},
                                      'shStorage__B001': {'initial capacity': 0.5}}
                             )

    def test_maybe_get_entries_or_defaults_ice_storage_nothing(self):
        """Checks whether this is ignored correctly."""
        nodal_data = {_ent.NodeKeys.storages: _pd.DataFrame(0, index=[0, 1], columns=[_ent.StorageLabels.label.value])}
        result = mpci.IceStorageMPC().maybe_get_entries_or_defaults(nodal_data)
        self.assertDictEqual(result, {})

    def test_maybe_get_entries_or_defaults_ice_storage_no_init(self):
        """Checks whether the default is used correctly."""
        nodal_data = {_ent.NodeKeys.storages: _pd.DataFrame(
            {_ent.CommonLabels.label.value: [_ent.IceStorageTypes.iceStorage, 0, 0],
             _ent.CommonLabels.label_unique.value: ["iceStorage__B001", 0, 0],
             }
        )}
        result = mpci.IceStorageMPC().maybe_get_entries_or_defaults(nodal_data)
        self.assertDictEqual(result, {"iceStorage__B001": {_ent.StorageLabels.initial_capacity.value: 0.0,
                                                           _ent.StorageLabels.initial_temp.value: 2.0}})

    def test_maybe_get_entries_or_defaults_ice_storage_with_init(self):
        """Checks whether the initial values are used correctly."""
        nodal_data = {_ent.NodeKeys.storages: _pd.DataFrame(
            {_ent.CommonLabels.label.value: [_ent.IceStorageTypes.iceStorage, 0, 0],
             _ent.CommonLabels.label_unique.value: ["iceStorage__B001", 0, 0],
             _ent.StorageLabels.initial_capacity.value: [0.5, 0, 0],
             _ent.StorageLabels.initial_temp.value: [0.5, 0, 0],
             }
        )}
        result = mpci.IceStorageMPC().maybe_get_entries_or_defaults(nodal_data)
        self.assertDictEqual(result, {"iceStorage__B001": {_ent.StorageLabels.initial_capacity.value: 0.5,
                                                           _ent.StorageLabels.initial_temp.value: 0.5}})

    def test_maybe_get_entries_or_defaults_building_nothing(self):
        """Users should get proper feedback when no data is in the csv."""
        building_model_params = _pd.DataFrame(columns=[_ent.BuildingModelParameters.tWallInit])
        with _pt.raises(ValueError) as e:
            mpci.BuildingMPC().maybe_get_entries_or_defaults(building_model_params)

    def test_maybe_get_entries_or_defaults_building_no_init(self):
        """Checks whether the default is used correctly."""
        building_model_params = _pd.DataFrame(
            {_ent.BuildingModelParameters.building_unique.value: ["1_0", "1_1", "2_0"],
             }
        )
        result = mpci.BuildingMPC().maybe_get_entries_or_defaults(building_model_params)
        self.assertDictEqual(result, {'1_0': {'tDistributionInit': 15.0, 'tIndoorInit': 20.0, 'tWallInit': 25.0},
                                      '1_1': {'tDistributionInit': 15.0, 'tIndoorInit': 20.0, 'tWallInit': 25.0},
                                      '2_0': {'tDistributionInit': 15.0, 'tIndoorInit': 20.0, 'tWallInit': 25.0}})

    def test_maybe_get_entries_or_defaults_building_with_init(self):
        """Checks whether the default is used correctly."""
        building_model_params = _pd.DataFrame(
            {_ent.BuildingModelParameters.building_unique.value: ["1_0", "1_1", "2_0"],
             _ent.BuildingModelParameters.tWallInit: [10., 12., 13.],
             _ent.BuildingModelParameters.tIndoorInit: [22., 21., 20.3],
             _ent.BuildingModelParameters.tDistributionInit: [30., 26., 29.],
             }
        )
        result = mpci.BuildingMPC().maybe_get_entries_or_defaults(building_model_params)
        self.assertDictEqual(result, {'1_0': {'tDistributionInit': 30.0, 'tIndoorInit': 22.0, 'tWallInit': 10.0},
                                      '1_1': {'tDistributionInit': 26.0, 'tIndoorInit': 21.0, 'tWallInit': 12.0},
                                      '2_0': {'tDistributionInit': 29.0, 'tIndoorInit': 20.3, 'tWallInit': 13.0}})

    def test_prep_mpc_inputs(self):
        nodal_data = {_ent.NodeKeys.storages: _pd.DataFrame(
            {_ent.CommonLabels.label.value: [_ent.IceStorageTypes.iceStorage, _ent.StorageTypes.shStorage,
                                             _ent.StorageTypes.dhwStorage,
                                             _ent.StorageTypes.electricalStorage, 0, 0],
             _ent.CommonLabels.label_unique.value: ["iceStorage__B001", "shStorage__B001", "dhwStorage__B003",
                                                    "electricalStorage", 0, 0],
             _ent.StorageLabels.initial_capacity.value: [0.25, 0.5, 0.3, 0.75, 0, 0],
             _ent.StorageLabels.initial_temp.value: [1.5, "x", "x", "x", "x", "x"],
             }
        )}
        result = mpci.prep_mpc_inputs(nodal_data)
        self.assertDictEqual(result, {'dhwStorage__B003': {'initial capacity': 0.3},
                                      'electricalStorage': {'initial capacity': 0.75},
                                      'shStorage__B001': {'initial capacity': 0.5},
                                      'iceStorage__B001': {'initial capacity': 0.25, 'initial_temp': 1.5},
                                      }
                             )

    def test_prep_mpc_inputs_with_building(self):
        nodal_data = {_ent.NodeKeys.storages: _pd.DataFrame(
            {_ent.CommonLabels.label.value: [_ent.IceStorageTypes.iceStorage, _ent.StorageTypes.shStorage,
                                             _ent.StorageTypes.dhwStorage,
                                             _ent.StorageTypes.electricalStorage, 0, 0],
             _ent.CommonLabels.label_unique.value: ["iceStorage__B001", "shStorage__B001", "dhwStorage__B003",
                                                    "electricalStorage", 0, 0],
             _ent.StorageLabels.initial_capacity.value: [0.25, 0.5, 0.3, 0.75, 0, 0],
             _ent.StorageLabels.initial_temp.value: [1.5, "x", "x", "x", "x", "x"],
             }
        )}
        building_model_params = _pd.DataFrame(
            {_ent.BuildingModelParameters.building_unique.value: ["1", "2"],
             _ent.BuildingModelParameters.tWallInit: [10., 13.],
             _ent.BuildingModelParameters.tIndoorInit: [22., 20.3],
             _ent.BuildingModelParameters.tDistributionInit: [30., 29.],
             }
        )
        result = mpci.prep_mpc_inputs(nodal_data, building_model_params)
        self.assertDictEqual(result, {'dhwStorage__B003': {'initial capacity': 0.3},
                                      'electricalStorage': {'initial capacity': 0.75},
                                      'shStorage__B001': {'initial capacity': 0.5},
                                      'iceStorage__B001': {'initial capacity': 0.25, 'initial_temp': 1.5},
                                      '1': {'tDistributionInit': 30.0, 'tIndoorInit': 22.0, 'tWallInit': 10.0},
                                      '2': {'tDistributionInit': 29.0, 'tIndoorInit': 20.3, 'tWallInit': 13.0}
                                      }
                             )
