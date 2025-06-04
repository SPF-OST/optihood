import abc as _abc
import copy as _cp
import pathlib as _pl
import re as _re

import pandas as _pd

import optihood.energy_network as en
import optihood.entities as _ent
from optihood.IO import readers as re
from optihood.Visualizer import convert_scenario as _cs, visualizer_app as _va
from optihood.energy_network import OptimizationProperties, EnergyNetworkClass as EnergyNetwork


# TODO: Figure out if the visualizer should stay here, or be called from the Network class
#       The User would not have access to the nodal_data at this time.

# TODO: EnergyNetworkIndiv vs EnergyNetworkGroup


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
    def required_entries_not_in_data(df) -> bool:  # pragma: no cover
        """As this is always MPC, we will be overwriting these values at all time-steps.
        Thus, the User should always provide all required values.
        When the User misses one, or all, the defaults should be provided instead.
        """
        raise NotImplementedError

    @staticmethod
    @_abc.abstractmethod
    def get_entries(initial_state: dict, row) -> dict:  # pragma: no cover
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
    sheet_name = _ent.NodeKeysOptional.building_model_parameters
    main_labels = [_ent.IceStorageTypes.iceStorage]
    default_values = {_ent.BuildingModelParameters.tIndoorInit.value: 20.0,
                      _ent.BuildingModelParameters.tDistributionInit.value: 15.0,
                      _ent.BuildingModelParameters.tWallInit.value: 25.0,
                      }

    def maybe_get_entries_or_defaults(self, nodal_data: dict[str, _pd.DataFrame]) -> dict:
        df = nodal_data[self.sheet_name]
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


def get_MPC_components_minimal():
    MPC_COMPONENTS: list[type[MpcComponentBasic]] = [
        StoragesMPC,
        IceStorageMPC,
    ]
    return MPC_COMPONENTS


def prep_mpc_inputs(nodal_data: dict[str, _pd.DataFrame],
                    building_model_parameters: _pd.DataFrame | None = None,
                    get_mpc_components=get_MPC_components_minimal
                    ) -> tuple[dict, dict]:
    MPC_COMPONENTS = get_mpc_components()
    initial_state_with_all_configurable_options = {}
    label_to_sheet = {}
    if building_model_parameters is not None:
        MPC_COMPONENTS.append(BuildingMPC)
        nodal_data[_ent.NodeKeysOptional.building_model_parameters] = building_model_parameters

    for i, component in enumerate(MPC_COMPONENTS):
        initial_states_for_component = component().maybe_get_entries_or_defaults(nodal_data)
        initial_state_with_all_configurable_options.update(initial_states_for_component)
        label_to_sheet_for_component = build_label_to_sheet(initial_states_for_component, component.sheet_name)
        label_to_sheet.update(label_to_sheet_for_component)

    return initial_state_with_all_configurable_options, label_to_sheet


def build_label_to_sheet(initial_states_for_component: dict[str: float], sheet_name: str):
    label_to_sheet_for_component = {}
    [label_to_sheet_for_component.update({label: sheet_name}) for label in initial_states_for_component.keys()]
    return label_to_sheet_for_component


class MpcHandler:
    """
    Class to simplify interaction with MPC functionality.
    It has the following responsibilities:
    - preparing the scenario from file.
    - providing the scenario's initial system state for the User to adjust.
    - updating the network with the current system state.
    - adjusting the prediction period to the current time-step.
    """
    time_period_full: _pd.DatetimeIndex
    nodal_data: dict  # change to class with dfs.
    optimization_settings: OptimizationProperties  # provide string literals?
    label_to_sheet: dict[str, str]

    def __init__(self, prediction_window_in_hours: int, time_step_in_minutes: int, nr_of_buildings: int,) -> None:
        self.nr_of_buildings = nr_of_buildings
        self.time_step_in_minutes = time_step_in_minutes
        self.prediction_window_in_hours = prediction_window_in_hours

    def visualize_example(self):
        converters = _cs.get_converters(self.nodal_data, nr_of_buildings=self.nr_of_buildings)
        graphData = _cs.get_graph_data(converters)
        _va.run_cytoscape_visualizer(graphData=graphData)

    def update_network(self, current_time_step, current_state):
        return self._get_network(current_time_step, current_state)

    def _get_network(self, current_time_step, current_state):
        """Temporary function, which slowly recreates the same network over and over.
        This will need to be replaced after rapid refactoring.
        Then, the minor changes required will be applied into the relevant network components directly.
        """
        current_nodal_data = self.update_nodal_data(current_state)
        current_time_period = self.get_current_time_period(current_time_step)
        # TODO: allow user to adjust this, or ensure only one exists.
        network = EnergyNetwork(current_time_period)

        network.check_mutually_exclusive_inputs(self.optimization_settings.merge_link_buses)
        dispatch_mode = self.optimization_settings.dispatch_mode
        if not dispatch_mode:
            raise ValueError("dispatch_mode has to be true for MPC.")

        network._dispatchMode = dispatch_mode
        network._optimizationType = self.optimization_settings.optimization_type
        network._mergeBuses = self.optimization_settings.merge_buses

        network.set_using_nodal_data(
            nodesData=current_nodal_data,
            clusterSize=self.optimization_settings.cluster_size,
            filePath="",  # This is only used in a logging message after processing the data.
            includeCarbonBenefits=self.optimization_settings.include_carbon_benefits,
            mergeBuses=self.optimization_settings.merge_buses,
            mergeHeatSourceSink=self.optimization_settings.merge_heat_source_sink,
            mergeLinkBuses=self.optimization_settings.merge_link_buses,
            numberOfBuildings=self.nr_of_buildings,
            opt=self.optimization_settings.optimization_type,
        )
        return network

    def get_mpc_scenario_from_csv(self, input_folder_path: _pl.Path) -> dict[str, dict[str, float]]:
        csvReader = re.CsvScenarioReader(input_folder_path)
        nodal_data = csvReader.read_scenario()
        nodal_data = re.add_unique_label_columns(nodal_data)
        nodal_data = re.ProfileAndOtherDataReader().read_profiles_and_other_data(
            nodal_data, input_folder_path, self.nr_of_buildings, self.optimization_settings.cluster_size,
            self.time_period_full,
        )
        # TODO: adjust building_model_parameters entry to check nodal_data instead.
        system_state, label_to_sheet = prep_mpc_inputs(nodal_data, building_model_parameters=None)
        self.nodal_data = nodal_data
        self.label_to_sheet = label_to_sheet

        return system_state

    def update_nodal_data(self, current_state: dict[str, dict[str, float]]) -> dict:
        """Requires self.nodal_data"""
        # TODO: clip profiles?
        # TODO: adjust building model parameters to correct implementation.
        nodal_data = _cp.deepcopy(self.nodal_data)
        for label, inputs in current_state.items():
            sheet_name = self.label_to_sheet[label]
            sheet = nodal_data[sheet_name]
            label_column = _ent.CommonLabels.label_unique
            if sheet_name == _ent.NodeKeysOptional.building_model_parameters:
                label_column = _ent.BuildingModelParameters.building_unique
            row_index = sheet[label_column] == label
            for column_name, value in inputs.items():
                # TODO: deal with incompatible dtype. Sometimes int instead of float.
                sheet.loc[row_index, column_name] = value

        return nodal_data

    def get_desired_energy_flows(self, results: dict[str: _pd.DataFrame], desired_flows_with_new_names: dict[str, str]) -> _pd.DataFrame:
        results = self.rename_result_labels(results)
        flow_label_to_sheet = self.get_flow_label_to_sheet(results)
        index = self.get_date_time_index(results)
        energy_flows = _pd.DataFrame(index=index)
        for flow_label, new_label in desired_flows_with_new_names.items():
            sheet = flow_label_to_sheet[flow_label]
            energy_flows[new_label] = results[sheet][flow_label]

        return energy_flows

    def rename_result_labels(self, results: dict[str: _pd.DataFrame]) -> dict[str: _pd.DataFrame]:
        """
        Renames: (('electricityInBus__Building1', 'HP__Building1'), 'flow')
        To: electricityInBus__B001__To__HP__B001
        """
        for sheet, df in results.items():
            df.columns = [str(column) for column in df.columns]
            rename_dict = self.rename_oemof_labels(df.columns)
            df.rename(columns=rename_dict, inplace=True)

        return results

    @staticmethod
    def rename_oemof_labels(columns: list[str]) -> dict[str, str]:
        """
        Renames: (('electricityInBus__Building1', 'HP__Building1'), 'flow')
        To: electricityInBus__B001__To__HP__B001

        Ignores anything without 'flow', e.g.
        - "storage_content"
        - "some_flow_to_be_ignored"

        """
        # TODO: find a better place for this, as it should be used in the new results data class.
        rename_dict = {}
        for column in columns:
            column = str(column)
            if isinstance(column, int) or "'flow'" not in column:
                """Leave the column out, and it will stay the same."""
                continue
            parts = column.split(',')
            from_node = MpcHandler.rename_node(parts[0])
            to_node = MpcHandler.rename_node(parts[1])

            new_name = f"{from_node}__To__{to_node}"
            rename_dict[column] = new_name

        return rename_dict

    @staticmethod
    def rename_node(part: str) -> str:
        node_name = (
            part.replace("((", "")
            .replace(")", "")
            .replace("'", "")
            .replace(" ", "")
        )
        match = _re.search(r"Building(\d+)", node_name)
        if match:
            building_nr = match.group(1)
            node_name = node_name.replace(f"uilding{building_nr}", f'{str(building_nr).zfill(3)}')
        return node_name

    @staticmethod
    def get_flow_label_to_sheet(results):
        flow_label_to_sheet = {}
        for sheet, df in results.items():
            current_labels = df.columns
            [flow_label_to_sheet.update({label: sheet}) for label in current_labels]
        return flow_label_to_sheet

    @staticmethod
    def get_date_time_index(results: dict[str: _pd.DataFrame]) -> _pd.DatetimeIndex:
        index = None
        for sheet, df in results.items():
            match = _re.search("Bus__", sheet)
            if match:
                index = df.index
                break

        if isinstance(index, _pd.DatetimeIndex):
            return index

        raise ValueError("No DateTimeIndex found in results.")

    def set_full_time_period(self, start_year: int, start_month: int, start_day: int, end_year: int, end_month: int,
                             end_day: int, time_step_in_minutes: int) -> None:
        """Prepares date time indices starting at 00:00:00 on the start day and ending at 23:00:00 on the end day."""
        self.time_period_full = _pd.date_range(f"{start_year}-{start_month}-{start_day} 00:00:00",
                                               f"{end_year}-{end_month}-{end_day} 23:00:00",
                                               freq=f"{str(time_step_in_minutes)}min")

    def get_current_time_period(self, current_time_period_start: _pd.DatetimeIndex) -> _pd.DatetimeIndex:
        """Creates the time period for the current prediction window."""
        current_time_period_end = current_time_period_start + _pd.Timedelta(hours=self.prediction_window_in_hours)
        current_time_period = _pd.date_range(current_time_period_start, current_time_period_end,
                                             freq=f"{str(self.time_step_in_minutes)}min")
        return current_time_period

    @staticmethod
    def log_processing(network: en.EnergyNetworkClass, costs: bool = False, env_impacts: bool = False,
                       meta: bool = False) -> None:
        # TODO: redo when new results output is ready.
        if costs:
            network.log_costs()
        if env_impacts:
            network.log_environmental_impacts()
        if meta:
            network.log_meta_results()
