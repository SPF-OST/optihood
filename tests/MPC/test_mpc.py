import unittest as _ut

import pandas as _pd

import optihood.MPC.interface as mpci
import optihood.entities as _ent


class TestMpc(_ut.TestCase):
    def test_maybe_get_entries_or_defaults_sh_storage_nothing(self):
        nodal_data = {_ent.NodeKeys.storages: _pd.DataFrame(0, index=[0, 1], columns=[_ent.StorageLabels.label.value])}
        result = mpci.SpaceHeatingStorageMPC().maybe_get_entries_or_defaults(nodal_data)
        self.assertDictEqual(result, {})

    def test_maybe_get_entries_or_defaults_sh_storage(self):
        nodal_data = {_ent.NodeKeys.storages: _pd.DataFrame(0, index=[0, 1], columns=[_ent.StorageLabels.label.value])}
        result = mpci.SpaceHeatingStorageMPC().maybe_get_entries_or_defaults(nodal_data)
        self.assertDictEqual(result, {"shStorage__B001": {_ent.StorageLabels.initial_capacity.value: 0.0}})
