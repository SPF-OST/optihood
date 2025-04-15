import abc as _abc

import pandas as _pd

import optihood.entities as _ent


# most use: 'initial capacity'
# 'initial capacity' := fIceInit as well
# 'initial_temp' := tStorInit


class MpcComponentBasic:
    sheet_name: str
    main_labels: list[str]
    default_values: dict

    def maybe_get_entries_or_defaults(self, nodal_data: dict[str, _pd.DataFrame]) -> dict:
        df = nodal_data[self.sheet_name]
        obtained_rows = df[_ent.CommonLabels.label].isin(self.main_labels)
        if not any(obtained_rows):
            return {}

        initial_state = {}
        if self.required_entries_not_in_data(df):
            [initial_state.update({row[_ent.CommonLabels.label_unique]: self.default_values}) for i, row in
             df[obtained_rows].iterrows()]

            return initial_state

        for i, row in df[obtained_rows].iterrows():
            initial_state = self.get_entries(initial_state, row)

        return initial_state

    @staticmethod
    @_abc.abstractmethod
    def required_entries_not_in_data(df) -> bool:
        raise NotImplementedError

    @staticmethod
    @_abc.abstractmethod
    def get_entries(initial_state: dict, row) -> dict:
        raise NotImplementedError


class StoragesMPC(MpcComponentBasic):
    main_labels = [_ent.StorageTypes.shStorage, _ent.StorageTypes.dhwStorage, _ent.StorageTypes.electricalStorage]
    sheet_name = _ent.NodeKeys.storages
    default_values = {_ent.StorageLabels.initial_capacity.value: 0.0}

    @staticmethod
    def required_entries_not_in_data(df) -> bool:
        return _ent.StorageLabels.initial_capacity not in df.columns

    @staticmethod
    def get_entries(initial_state: dict, row) -> dict:
        initial_state[row[_ent.CommonLabels.label_unique]] = {
            _ent.StorageLabels.initial_capacity.value: row[_ent.StorageLabels.initial_capacity]}
        return initial_state


MPC_COMPONENTS: list[type[MpcComponentBasic]] = [
    StoragesMPC,

]


def prep_mpc_inputs(nodal_data: dict[str, _pd.DataFrame]) -> dict:
    initial_state_with_all_configurable_options = {}
    # get final labels
    # get values for each case
    #   - from file
    #   - use defaults
    for i, component in enumerate(MPC_COMPONENTS):
        initial_states_for_component = component().maybe_get_entries_or_defaults(nodal_data)
        initial_state_with_all_configurable_options.update(initial_states_for_component)

    return initial_state_with_all_configurable_options
