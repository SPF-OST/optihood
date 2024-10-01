import dataclasses as _dc
import enum as _enum
import typing as _tp


@_dc.dataclass()
class ScenarioToVisualizerAbstract:
    id: str
    label: str

    def get_nodal_infos(self):
        raise NotImplementedError('Do not access parent class directly')

    def get_edge_infos(self):
        raise NotImplementedError('Do not access parent class directly')

    @staticmethod
    def read_nodal_infos(data: dict[str, _tp.Union[str, float, int]]):
        raise NotImplementedError('Do not access parent class directly')

    @staticmethod
    def read_edge_infos(data: dict[str, _tp.Union[str, float, int]]):
        raise NotImplementedError('Do not access parent class directly')


@_dc.dataclass()
class NodalDataExample(ScenarioToVisualizerAbstract):
    id: str
    label: str
    longitude: float
    latitude: float

    def get_nodal_infos(self):
        return {
            'data': {'id': self.id, 'label': self.label, "lat": self.latitude, "long": self.longitude},
            'position': {'x': 20 * self.latitude, 'y': -20 * self.longitude}
        }

    @staticmethod
    def read_nodal_infos(data: dict[str, _tp.Union[str, float, int]]):
        return f"{data['label']}, {data['lat']}, {data['long']}"


class ScenarioDataTypes(_enum.StrEnum):
    example: str = 'example'


def scenario_data_factory(scenario_data_type: ScenarioDataTypes) -> _tp.Type[ScenarioToVisualizerAbstract]:
    scenario_data_types = {ScenarioDataTypes.example: NodalDataExample}

    if scenario_data_type not in scenario_data_types:
        raise NotImplementedError("received unexpected type")

    return scenario_data_types[scenario_data_type]
