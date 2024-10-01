import dataclasses as _dc
import enum as _enum
import typing as _tp

@_dc.dataclass()
class NodalDataExample:
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


def scenario_data_factory(scenario_data_type: ScenarioDataTypes):
    scenario_data_types = {ScenarioDataTypes.example: NodalDataExample}

    if scenario_data_type not in scenario_data_types:
        raise NotImplementedError("received unexpected type")

    return scenario_data_types[scenario_data_type]
