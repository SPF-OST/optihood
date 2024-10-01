import collections.abc as _abc
import dataclasses as _dc
import enum as _enum
import pathlib as _pl
import typing as _tp

import pandas as _pd


class ScenarioDataTypes(_enum.StrEnum):
    example: str = 'example'


class EnergyTypes(_enum.StrEnum):
    electricity = 'electricity'
    domestic_hot_water = "DHW"
    space_heating = "SH"
    gas = 'gas'
    oil = 'oil'
    hydrogen = 'H2'


@_dc.dataclass()
class ScenarioToVisualizerAbstract:
    """ From node and to node could also use enums. """
    id: str
    label: str
    from_node: _tp.Optional[_tp.Union[str, _abc.Sequence[str]]]  # sources do not have this
    to_node: _tp.Optional[_tp.Union[str, _abc.Sequence[str]]]  # sinks do not have this
    energy_type: EnergyTypes
    active: bool
    edges_into_node: list[dict[str, dict[str, _tp.Union[str, float, int]]]] = _dc.field(init=False)
    edges_out_of_node: list[dict[str, dict[str, _tp.Union[str, float, int]]]] = _dc.field(init=False)

    def get_nodal_infos(self):
        raise NotImplementedError('Do not access parent class directly')

    def get_edge_infos(self) -> list[dict[str, dict[str, _tp.Union[str, float, int]]]]:
        if not self.active:
            return []
        self.edges_into_node = []
        if self.from_node:
            if not isinstance(self.from_node, list):
                self.from_node = [self.from_node]
            for from_node in self.from_node:
                self.edges_into_node.append({'data': {'source': from_node, 'target': self.id,
                                                      'energy_type': self.energy_type.value}})
        self.edges_out_of_node = []
        if self.to_node:
            if not isinstance(self.to_node, list):
                self.to_node = [self.to_node]
            for to_node in self.to_node:
                self.edges_out_of_node.append({'data': {'source': self.id, 'target': to_node,
                                                        'energy_type': self.energy_type.value}})

        all_edges = self.edges_into_node + self.edges_out_of_node
        return all_edges

    @staticmethod
    def read_nodal_infos(data: dict[str, _tp.Union[str, float, int]]) -> _tp.Optional[str]:
        """ Adding line breaks for every entry would look cleaner. """
        return f"{data}"

    @staticmethod
    def read_edge_infos(data: dict[str, _tp.Union[str, float, int]]):
        """ This may never be needed. """
        raise NotImplementedError('Do not access parent class directly')

    @staticmethod
    def set_from_dataFrame(df: _pd.DataFrame):  # -> _tp.Type[ScenarioToVisualizerAbstract]
        """ Typing does not allow usage of this class's type."""
        raise NotImplementedError('Do not access parent class directly')


def scenario_data_factory(scenario_data_type: ScenarioDataTypes) -> _tp.Type[ScenarioToVisualizerAbstract]:
    scenario_data_types = {ScenarioDataTypes.example: NodalDataExample}

    if scenario_data_type not in scenario_data_types:
        raise NotImplementedError("received unexpected type")

    return scenario_data_types[scenario_data_type]


@_dc.dataclass()
class NodalDataExample(ScenarioToVisualizerAbstract):
    longitude: float
    latitude: float

    def get_nodal_infos(self):
        return {
            'data': {'id': self.id, 'label': self.label, "lat": self.latitude, "long": self.longitude},
            'position': {'x': 20 * self.latitude, 'y': -20 * self.longitude}
        }


@_dc.dataclass()
class CommoditySourcesConverter(ScenarioToVisualizerAbstract):
    building: int
    variable_costs: _tp.Union[float, _pl.Path]
    CO2_impact: _tp.Union[float, _pl.Path]

    def __post_init__(self):
        if self.from_node:
            raise Warning(f'Commodity sources do not have a from node. Received {self.from_node}.')

    def get_nodal_infos(self) -> _tp.Optional[dict[str, dict[str, _tp.Union[str, int, float, _pl.Path]]]]:
        if self.active:
            return {"data": {'id': self.id, 'label': self.label, "building": self.building,
                             "variable_costs": self.variable_costs, "CO2_impact": self.CO2_impact}}

    @staticmethod
    def set_from_dataFrame(df: _pd.DataFrame) -> _abc.Sequence[_tp.Type[ScenarioToVisualizerAbstract]]:
        list_of_demands = []
        for i, line in df.iterrows():
            energyType = EnergyTypes.electricity
            list_of_demands.append(CommoditySourcesConverter(line['label'], line['label'], None, line['to'], energyType,
                                                             active=line['active'], building=line['building'],
                                                             variable_costs=line['variable costs'],
                                                             CO2_impact=line['CO2 impact']))
        return list_of_demands


@_dc.dataclass()
class BusesConverter(ScenarioToVisualizerAbstract):
    building: int
    excess: int
    excess_costs: _tp.Union[float, _pl.Path]
    shortage: _tp.Optional[bool] = None
    shortage_costs: _tp.Optional[_tp.Union[float, _pl.Path]] = None

    def __post_init__(self):
        if self.from_node:
            raise Warning(f'Buses tend not to have a from node assigned in the scenario. Received {self.from_node}.')
        if self.to_node:
            raise Warning(f'Buses tend not to have a from node assigned in the scenario. Received {self.from_node}.')

    def get_nodal_infos(self) -> _tp.Optional[dict[str, dict[str, _tp.Union[str, int, float, _pl.Path]]]]:
        if self.active:
            return {"data": {'id': self.id, 'label': self.label, "building": self.building,
                             "excess": self.excess, "excess_costs": self.excess_costs, "shortage": self.shortage,
                             "shortage_costs": self.shortage_costs}}


@_dc.dataclass()
class DemandConverter(ScenarioToVisualizerAbstract):
    building: int
    fixed: int
    nominal_value: int
    building_model: _tp.Optional[bool] = None

    def __post_init__(self):
        if self.to_node:
            raise Warning(f'Buses tend not to have a from node assigned in the scenario. Received {self.from_node}.')

    def get_nodal_infos(self) -> _tp.Optional[dict[str, dict[str, _tp.Union[str, int, float, _pl.Path]]]]:
        if self.active:
            return {"data": {'id': self.id, 'label': self.label, "building": self.building,
                             "fixed": self.fixed, "nominal_value": self.nominal_value,
                             "building_model": self.building_model}}

    @staticmethod
    def set_from_dataFrame(df: _pd.DataFrame) -> _abc.Sequence[_tp.Type[ScenarioToVisualizerAbstract]]:
        list_of_demands = []
        for i, line in df.iterrows():
            energyType = EnergyTypes.electricity
            list_of_demands.append(DemandConverter(line['label'], line['label'], line['from'], None, energyType,
                                                   active=line['active'], building=line['building'],
                                                   fixed=line['fixed'], nominal_value=line['nominal value'],
                                                   building_model=line['building model']))
        return list_of_demands
