import abc as _abc

import pandas as _pd

import optihood.entities as _ent


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
        """As this is always MPC, we will be overwriting these values at all time-steps.
        Thus, the User should always provide all required values.
        When the User misses one, or all, the defaults should be provided instead.
        """
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


class IceStorageMPC(MpcComponentBasic):
    sheet_name = _ent.NodeKeys.storages
    main_labels = [_ent.IceStorageTypes.iceStorage]
    default_values = {_ent.StorageLabels.initial_capacity.value: 0.0, _ent.StorageLabels.initial_temp.value: 2.0}

    @staticmethod
    def required_entries_not_in_data(df) -> bool:
        """As this is always MPC, we will be overwriting these values at all time-steps.
        Thus, the User should always provide all required values.
        When the User misses one, or all, the defaults should be provided instead.
        """
        return _ent.StorageLabels.initial_capacity not in df.columns and _ent.StorageLabels.initial_temp not in df.columns

    @staticmethod
    def get_entries(initial_state: dict, row) -> dict:
        initial_state[row[_ent.CommonLabels.label_unique]] = {
            _ent.StorageLabels.initial_capacity.value: row[_ent.StorageLabels.initial_capacity],
            _ent.StorageLabels.initial_temp.value: row[_ent.StorageLabels.initial_temp],
        }
        return initial_state


class BuildingMPC(MpcComponentBasic):
    """These need to be defined in a separate file.
    This file is declared in the profiles sheet
    As part of MPC, this file should already have been read in before running this.
    """
    main_labels = [_ent.IceStorageTypes.iceStorage]
    default_values = {_ent.BuildingModelParameters.tIndoorInit.value: 20.0,
                      _ent.BuildingModelParameters.tDistributionInit.value: 15.0,
                      _ent.BuildingModelParameters.tWallInit.value: 25.0,
                      }

    def maybe_get_entries_or_defaults(self, building_model_params: _pd.DataFrame) -> dict:
        df = building_model_params
        if df.empty:
            raise ValueError("Building model parameters should not be empty. Either add buildings, or do not include "
                             "the parameters to get_mpc_iputs")

        initial_state = {}
        if self.required_entries_not_in_data(df):
            [initial_state.update({row[_ent.BuildingModelParameters.building_unique.value]: self.default_values}) for
             i, row in df.iterrows()]

            return initial_state

        for i, row in df.iterrows():
            initial_state = self.get_entries(initial_state, row)

        return initial_state

    @staticmethod
    def required_entries_not_in_data(df) -> bool:
        """As this is always MPC, we will be overwriting these values at all time-steps.
        Thus, the User should always provide all required values.
        When the User misses one, or all, the defaults should be provided instead.
        """
        return (_ent.BuildingModelParameters.tIndoorInit not in df.columns
                and _ent.BuildingModelParameters.tDistributionInit not in df.columns
                and _ent.BuildingModelParameters.tWallInit not in df.columns
                )

    @staticmethod
    def get_entries(initial_state: dict, row) -> dict:
        initial_state[row[_ent.BuildingModelParameters.building_unique]] = {
            _ent.BuildingModelParameters.tIndoorInit.value: row[_ent.BuildingModelParameters.tIndoorInit],
            _ent.BuildingModelParameters.tDistributionInit.value: row[_ent.BuildingModelParameters.tDistributionInit],
            _ent.BuildingModelParameters.tWallInit.value: row[_ent.BuildingModelParameters.tWallInit],
        }
        return initial_state


MPC_COMPONENTS: list[type[MpcComponentBasic]] = [
    StoragesMPC,
    IceStorageMPC,
]


def prep_mpc_inputs(nodal_data: dict[str, _pd.DataFrame],
                    building_model_parameters: _pd.DataFrame | None = None) -> dict:
    initial_state_with_all_configurable_options = {}

    for i, component in enumerate(MPC_COMPONENTS):
        initial_states_for_component = component().maybe_get_entries_or_defaults(nodal_data)
        initial_state_with_all_configurable_options.update(initial_states_for_component)

    if building_model_parameters is not None:
        initial_states_for_component = BuildingMPC().maybe_get_entries_or_defaults(building_model_parameters)
        initial_state_with_all_configurable_options.update(initial_states_for_component)

    return initial_state_with_all_configurable_options
