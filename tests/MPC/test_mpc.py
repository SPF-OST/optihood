import unittest as _ut

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
                                                           _ent.IceStorageLabels.initial_temp.value: 2.0}})

    def test_maybe_get_entries_or_defaults_ice_storage_with_init(self):
        """Checks whether the initial values are used correctly."""
        nodal_data = {_ent.NodeKeys.storages: _pd.DataFrame(
            {_ent.CommonLabels.label.value: [_ent.IceStorageTypes.iceStorage, 0, 0],
             _ent.CommonLabels.label_unique.value: ["iceStorage__B001", 0, 0],
             _ent.StorageLabels.initial_capacity.value: [0.5, 0, 0],
             # TODO: this currently does not live here. It really should.
             _ent.IceStorageLabels.initial_temp.value: [0.5, 0, 0],
             }
        )}
        result = mpci.IceStorageMPC().maybe_get_entries_or_defaults(nodal_data)
        self.assertDictEqual(result, {"iceStorage__B001": {_ent.StorageLabels.initial_capacity.value: 0.5,
                                                           _ent.IceStorageLabels.initial_temp.value: 0.5}})

    def test_prep_mpc_inputs(self):
        # TODO: should thermal storages have an initial temp as well?
        nodal_data = {_ent.NodeKeys.storages: _pd.DataFrame(
            {_ent.CommonLabels.label.value: [_ent.IceStorageTypes.iceStorage, _ent.StorageTypes.shStorage, _ent.StorageTypes.dhwStorage,
                                             _ent.StorageTypes.electricalStorage, 0, 0],
             _ent.CommonLabels.label_unique.value: ["iceStorage__B001", "shStorage__B001", "dhwStorage__B003", "electricalStorage", 0, 0],
             _ent.StorageLabels.initial_capacity.value: [0.25, 0.5, 0.3, 0.75, 0, 0],
             _ent.IceStorageLabels.initial_temp.value: [1.5, "x", "x", "x", "x", "x"],
             }
        )}
        result = mpci.prep_mpc_inputs(nodal_data)
        self.assertDictEqual(result, {'dhwStorage__B003': {'initial capacity': 0.3},
                                      'electricalStorage': {'initial capacity': 0.75},
                                      'shStorage__B001': {'initial capacity': 0.5},
                                      'iceStorage__B001': {'initial capacity': 0.25, 'intitial_temp': 1.5},
                                      }
                             )

