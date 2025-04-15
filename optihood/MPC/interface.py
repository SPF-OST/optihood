import abc as _abc

import pandas as _pd

import optihood.entities as _ent


# most use: 'initial capacity'
# 'initial capacity' := fIceInit as well
# 'intitial_temp' := tStorInit

# Building model specifics
# https://gitlab.ost.ch/spf/gridmpc/-/blob/main/MPCRunner/ToOptihood/APIreader.py?ref_type=heads

class MpcComponentBasic:
    @_abc.abstractmethod
    def maybe_get_entries_or_defaults(self, nodal_data: dict[str, _pd.DataFrame]) -> dict:
        raise NotImplementedError


class SpaceHeatingStorageMPC(MpcComponentBasic):
    main_label = _ent.StorageTypes.shStorage
    sheet_name = _ent.NodeKeys.storages
    default_values = {_ent.StorageLabels.initial_capacity.value: 0.0}

    def maybe_get_entries_or_defaults(self, nodal_data: dict[str, _pd.DataFrame]) -> dict:
        df = nodal_data[self.sheet_name]
        if self.main_label not in df[_ent.StorageLabels.label]:
            return {}

        # get rows where equal
        # get final label
        # get relevant values
        # build


MPC_COMPONENTS: list[type[MpcComponentBasic]] = [
    SpaceHeatingStorageMPC,

]


def prep_mpc_inputs(nodal_data: dict[str, _pd.DataFrame]) -> dict:

    initial_state_with_all_configurable_options = {}
    # get final labels
    # get values for each case
    #   - from file
    #   - use defaults
    for i, component in enumerate(MPC_COMPONENTS):
        for label, values in component().maybe_get_entries_or_defaults(nodal_data).items():
            initial_state_with_all_configurable_options[label] = values

    return initial_state_with_all_configurable_options
