import collections.abc as _abc
import dataclasses as _dc
import enum as _enum
import pathlib as _pl
import typing as _tp


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
    energy_type: _tp.Type[EnergyTypes]
    edges_into_node: list[dict[str, dict[str, _tp.Union[str, float, int]]]] = _dc.field(init=False)
    edges_out_of_node: list[dict[str, dict[str, _tp.Union[str, float, int]]]] = _dc.field(init=False)

    def get_nodal_infos(self):
        raise NotImplementedError('Do not access parent class directly')

    def get_edge_infos(self) -> list[dict[str, dict[str, _tp.Union[str, float, int]]]]:
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
    def read_nodal_infos(data: dict[str, _tp.Union[str, float, int]]):
        raise NotImplementedError('Do not access parent class directly')

    @staticmethod
    def read_edge_infos(data: dict[str, _tp.Union[str, float, int]]):
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

    @staticmethod
    def read_nodal_infos(data: dict[str, _tp.Union[str, float, int]]) -> str:
        return f"{data['label']}, {data['lat']}, {data['long']}"

    # def get_edge_infos(self) -> dict[str, dict[str, _tp.Union[str, float, int]]]:
    #     """ no edge exists if one or the other is missing. """
    #     if self.from_node and self.to_node:
    #         return {'data': {'source': self.from_node, 'target': self.to_node, 'energy_type': self.energy_type.value}}

    @staticmethod
    def read_edge_infos(data: dict[str, _tp.Union[str, float, int]]):
        raise NotImplementedError


@_dc.dataclass()
class CommoditySourcesConverter(ScenarioToVisualizerAbstract):
    building: int
    variable_costs: _tp.Union[float, _pl.Path]
    CO2_impact: _tp.Union[float, _pl.Path]
    active: bool

    def __post_init__(self):
        if self.from_node:
            raise Warning(f'Commodity sources do not have a from node. Received {self.from_node}.')

    def get_nodal_infos(self) -> _tp.Optional[dict[str, dict[str, _tp.Union[str, int, float, _pl.Path]]]]:
        if self.active:
            return {"data": {'id': self.id, 'label': self.label, "building": self.building,
                             "variable_costs": self.variable_costs, "CO2_impact": self.CO2_impact}}
        return

    def get_edge_infos(self):
        pass

    @staticmethod
    def read_nodal_infos(data: dict[str, _tp.Union[str, float, int]]):
        pass
