import collections.abc as _abc
import dataclasses as _dc
import enum as _enum
import pathlib as _pl
import typing as _tp

import pandas as _pd

from optihood.entities import NodeKeys as sheets
from optihood.entities import TransformerLabels as trafo
from optihood.entities import StorageLabels as store


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
                energy_type = get_energy_type_based_on_both_labels(self.id, from_node)
                self.edges_into_node.append({'data': {'source': from_node, 'target': self.id},
                                             "classes": energy_type.value})
        self.edges_out_of_node = []
        if self.to_node:
            if not isinstance(self.to_node, list):
                self.to_node = [self.to_node]
            for to_node in self.to_node:
                energy_type = get_energy_type_based_on_both_labels(self.id, to_node)
                self.edges_out_of_node.append({'data': {'source': self.id, 'target': to_node},
                                               "classes": energy_type.value})

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


def scenario_data_factory(scenario_data_type: str) -> _tp.Optional[_tp.Type[ScenarioToVisualizerAbstract]]:
    scenario_data_types = {ScenarioDataTypes.example: NodalDataExample,
                           sheets.buses: BusesConverter,
                           sheets.commodity_sources: CommoditySourcesConverter,
                           sheets.demand: DemandConverter,
                           sheets.grid_connection: GridConnectionConverter,
                           sheets.transformers: TransformersConverter,
                           sheets.storages: StoragesConverter}

    if scenario_data_type not in scenario_data_types:
        # raise NotImplementedError("received unexpected type")
        return  # <- until all sheets are implemented

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
                             "variable_costs": self.variable_costs, "CO2_impact": self.CO2_impact},
                    'classes': 'source'}

    @staticmethod
    def set_from_dataFrame(df: _pd.DataFrame) -> _abc.Sequence[_tp.Type[ScenarioToVisualizerAbstract]]:
        list_of_demands = []

        if 'active' not in df.columns:
            df['active'] = True

        for i, line in df.iterrows():
            energyType = EnergyTypes.electricity
            if not line['active']:
                line['active'] = True
            list_of_demands.append(CommoditySourcesConverter(line['label'], line['label'], None,
                                                             line['to'].split(sep=','), energyType,
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
                             "shortage_costs": self.shortage_costs},
                    'classes': 'bus'}

    @staticmethod
    def set_from_dataFrame(df: _pd.DataFrame) -> _abc.Sequence[_tp.Type[ScenarioToVisualizerAbstract]]:
        list_of_demands = []

        # TODO: check whether shortage is given without shortage costs.
        if 'shortage' not in df.columns:
            df['shortage'] = None

        if 'shortage costs' not in df.columns:
            df['shortage costs'] = None

        if 'active' not in df.columns:
            df['active'] = True

        for i, line in df.iterrows():
            energyType = EnergyTypes.electricity

            list_of_demands.append(
                BusesConverter(line['label'], line['label'], None, None, energyType,
                               active=line['active'], building=line['building'],
                               excess=line['excess'],
                               excess_costs=line['excess costs'],
                               shortage=line['shortage'],
                               shortage_costs=line['shortage costs']
                               ))
        return list_of_demands


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
                             "building_model": self.building_model},
                    "classes": "demand"}

    @staticmethod
    def set_from_dataFrame(df: _pd.DataFrame) -> _abc.Sequence[_tp.Type[ScenarioToVisualizerAbstract]]:
        list_of_demands = []

        if 'active' not in df.columns:
            df['active'] = True

        for i, line in df.iterrows():
            energyType = EnergyTypes.electricity

            list_of_demands.append(DemandConverter(line['label'], line['label'], line['from'].split(sep=',')
                                                   , None, energyType,
                                                   active=line['active'], building=line['building'],
                                                   fixed=line['fixed'], nominal_value=line['nominal value'],
                                                   building_model=line['building model']))
        return list_of_demands


@_dc.dataclass()
class GridConnectionConverter(ScenarioToVisualizerAbstract):
    building: int
    efficiency: float

    def get_nodal_infos(self) -> _tp.Optional[dict[str, dict[str, _tp.Union[str, int, float, _pl.Path]]]]:
        if self.active:
            return {"data": {'id': self.id, 'label': self.label, "building": self.building,
                             "efficiency": self.efficiency, },
                    "classes": "grid_connection"}

    @staticmethod
    def set_from_dataFrame(df: _pd.DataFrame) -> _abc.Sequence[_tp.Type[ScenarioToVisualizerAbstract]]:
        list_of_demands = []

        if 'active' not in df.columns:
            df['active'] = True

        for i, line in df.iterrows():
            energyType = EnergyTypes.electricity

            list_of_demands.append(GridConnectionConverter(line['label'], line['label'], line['from'].split(sep=','),
                                                           line['to'].split(sep=','),
                                                           energyType, active=line['active'],
                                                           building=line['building'],
                                                           efficiency=line['efficiency']))
        return list_of_demands


@_dc.dataclass()
class TransformersConverter(ScenarioToVisualizerAbstract):
    building: int
    efficiency: float
    capacity_DHW: float
    capacity_SH: float
    capacity_min: float
    lifetime: float
    maintenance: float
    installation: float
    planification: float
    invest_base: float
    invest_cap: float
    heat_impact: float
    elec_impact: float
    impact_cap: float
    capacity_el: _tp.Optional[float] = None

    def get_nodal_infos(self) -> _tp.Optional[dict[str, dict[str, _tp.Union[str, int, float, _pl.Path]]]]:
        if self.active:
            return {"data": {'id': self.id, 'label': self.label, trafo.building.value: self.building,
                             trafo.efficiency.value: self.efficiency,
                             trafo.capacity_DHW.value: self.capacity_DHW,
                             trafo.capacity_SH.value: self.capacity_SH,
                             trafo.capacity_min.value: self.capacity_min,
                             trafo.lifetime.value: self.lifetime,
                             trafo.maintenance.value: self.maintenance,
                             trafo.installation.value: self.installation,
                             trafo.planification.value: self.planification,
                             trafo.invest_base.value: self.invest_base,
                             trafo.invest_cap.value: self.invest_cap,
                             trafo.heat_impact.value: self.heat_impact,
                             trafo.elec_impact.value: self.elec_impact,
                             trafo.impact_cap.value: self.impact_cap,
                             trafo.capacity_el.value: self.capacity_el,
                             },
                    "classes": "transformer"}

    @staticmethod
    def set_from_dataFrame(df: _pd.DataFrame) -> _abc.Sequence[_tp.Type[ScenarioToVisualizerAbstract]]:
        list_of_demands = []

        if 'active' not in df.columns:
            df['active'] = True

        if 'capacity_el' not in df.columns:
            df['capacity_el'] = None

        for i, line in df.iterrows():
            energyType = EnergyTypes.electricity

            list_of_demands.append(
                TransformersConverter(line['label'], line['label'], line['from'].split(sep=','),
                                      line['to'].split(sep=','), energyType, active=line['active'],
                                      building=line[trafo.building.value],
                                      efficiency=line[trafo.efficiency.value],
                                      capacity_DHW=line[trafo.capacity_DHW.value],
                                      capacity_SH=line[trafo.capacity_SH.value],
                                      capacity_min=line[trafo.capacity_min.value],
                                      lifetime=line[trafo.lifetime.value],
                                      maintenance=line[trafo.maintenance.value],
                                      installation=line[trafo.installation.value],
                                      planification=line[trafo.planification.value],
                                      invest_base=line[trafo.invest_base.value],
                                      invest_cap=line[trafo.invest_cap.value],
                                      heat_impact=line[trafo.heat_impact.value],
                                      elec_impact=line[trafo.elec_impact.value],
                                      impact_cap=line[trafo.impact_cap.value]
                                      ))
        return list_of_demands


@_dc.dataclass()
class StoragesConverter(ScenarioToVisualizerAbstract):
    building: int
    efficiency_inflow: _tp.Optional[float]
    efficiency_outflow: _tp.Optional[float]
    initial_capacity: float
    capacity_min: float
    capacity_max: float
    capacity_loss: _tp.Optional[float]
    lifetime: float
    maintenance: float
    installation: float
    planification: float
    invest_base: float
    invest_cap: float
    heat_impact: float
    elec_impact: float
    impact_cap: float

    def get_nodal_infos(self) -> _tp.Optional[dict[str, dict[str, _tp.Union[str, int, float, _pl.Path]]]]:
        if self.active:
            return {"data": {'id': self.id, 'label': self.label, store.building.value: self.building,
                             store.efficiency_inflow.value: self.efficiency_inflow,
                             store.efficiency_outflow.value: self.efficiency_outflow,
                             store.initial_capacity.value: self.initial_capacity,
                             store.capacity_min.value: self.capacity_min,
                             store.capacity_max.value: self.capacity_max,
                             store.capacity_loss.value: self.capacity_loss,
                             store.lifetime.value: self.lifetime,
                             store.maintenance.value: self.maintenance,
                             store.installation.value: self.installation,
                             store.planification.value: self.planification,
                             store.invest_base.value: self.invest_base,
                             store.invest_cap.value: self.invest_cap,
                             store.heat_impact.value: self.heat_impact,
                             store.elec_impact.value: self.elec_impact,
                             store.impact_cap.value: self.impact_cap,
                             },
                    "classes": "storage"}

    @staticmethod
    def set_from_dataFrame(df: _pd.DataFrame) -> _abc.Sequence[_tp.Type[ScenarioToVisualizerAbstract]]:
        list_of_demands = []

        if 'active' not in df.columns:
            df['active'] = True

        if store.efficiency_inflow not in df.columns:
            df[store.efficiency_inflow] = None

        if store.efficiency_outflow not in df.columns:
            df[store.efficiency_outflow] = None

        if store.capacity_loss not in df.columns:
            df[store.capacity_loss] = None

        for i, line in df.iterrows():
            energyType = EnergyTypes.electricity

            list_of_demands.append(
                StoragesConverter(line['label'], line['label'], line['from'].split(sep=','),
                                  line['to'].split(sep=','),
                                  energyType, building=line[store.building.value], active=True,
                                  efficiency_inflow=line[store.efficiency_inflow.value],
                                  efficiency_outflow=line[store.efficiency_outflow.value],
                                  initial_capacity=line[store.initial_capacity.value],
                                  capacity_min=line[store.capacity_min.value],
                                  capacity_max=line[store.capacity_max.value],
                                  capacity_loss=line[store.capacity_loss.value],
                                  lifetime=line[store.lifetime.value],
                                  maintenance=line[store.maintenance.value],
                                  installation=line[store.installation.value],
                                  planification=line[store.planification.value],
                                  invest_base=line[store.invest_base.value],
                                  invest_cap=line[store.invest_cap.value],
                                  heat_impact=line[store.heat_impact.value],
                                  elec_impact=line[store.elec_impact.value],
                                  impact_cap=line[store.impact_cap.value]
                                  )
            )
        return list_of_demands


def get_energy_type(label: str):
    electric_parts = ["electric", "Electric", "grid", "pv"]
    if any(flag in label for flag in electric_parts):
        return EnergyTypes.electricity

    sh_parts = ["sh", "spaceHeating", "chiller", 'heatSource35']
    if any(flag in label for flag in sh_parts):
        return EnergyTypes.space_heating

    dhw_parts = ["dhw", "domesticHotWater", 'heatSource65']
    if any(flag in label for flag in dhw_parts):
        return EnergyTypes.domestic_hot_water

    gas_parts = ["gas", "Gas"]
    if any(flag in label for flag in gas_parts):
        return EnergyTypes.gas

    print(f'Unknown label type found: {label}')
    return EnergyTypes.electricity


def get_energy_type_based_on_both_labels(label: str, other_label: str) -> EnergyTypes:
    """ Edges are based on the current node and another (to or from)."""

    transformer_parts = ["HP", "solar", "GasBoiler", "Dummy", "Dummy"]
    
    if any(flag in label for flag in transformer_parts):
        return get_energy_type(other_label)

    return get_energy_type(label)



@_dc.dataclass()
class LinksConverter(ScenarioToVisualizerAbstract):
    def get_nodal_infos(self):
        raise NotImplementedError

    @staticmethod
    def set_from_dataFrame(df: _pd.DataFrame):
        raise NotImplementedError

