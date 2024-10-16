import collections.abc as _abc
import dataclasses as _dc
import enum as _enum
import pathlib as _pl
import typing as _tp

import pandas as _pd
import numpy as _np
import matplotlib as _mpl
import matplotlib.pyplot as _plt

from optihood.entities import NodeKeys as sheets
from optihood.entities import TransformerLabels as trafo
from optihood.entities import StorageLabels as store
from optihood.entities import SolarLabels as solar
from optihood.entities import SolarTypes


class ScenarioDataTypes(_enum.StrEnum):
    example: str = 'example'


class EnergyTypes(_enum.StrEnum):
    electricity = 'electricity'
    domestic_hot_water = "DHW"
    space_heating = "SH"
    gas = 'gas'
    oil = 'oil'
    hydrogen = 'H2'
    unknown = 'unknown'


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
    return EnergyTypes.unknown


def get_energy_type_based_on_both_labels(label: str, other_label: str) -> EnergyTypes:
    """ Edges are based on the current node and another (to or from)."""

    transformer_parts = ["HP", "solar", "GasBoiler", "Dummy", "Dummy"]

    if any(flag in label for flag in transformer_parts):
        return get_energy_type(other_label)

    return get_energy_type(label)


class MplColorHelper:
    """ Taken from https://stackoverflow.com/questions/26108436/how-can-i-get-the-matplotlib-rgb-color-given-the-colormap-name-boundrynorm-an#26109298
    """

    def __init__(self, cmap_name: str, start_val: _tp.Union[int, float], stop_val: _tp.Union[int, float]):
        self.cmap_name = cmap_name
        self.stop_val = stop_val
        self.cmap = _plt.get_cmap(cmap_name)
        self.norm = _mpl.colors.Normalize(vmin=start_val, vmax=stop_val)
        self.scalarMap = _mpl.cm.ScalarMappable(norm=self.norm, cmap=self.cmap)

    def get_rgb(self, val: _tp.Union[int, float, _np.ndarray]) -> _np.ndarray:
        val = val % self.stop_val
        return self.scalarMap.to_rgba(val)

    def get_hex(self, val: _tp.Union[int, float, _np.ndarray]) -> str:
        # val = val % self.stop_val
        return _mpl.colors.to_hex(self.get_rgb(val))


@_dc.dataclass()
class ScenarioToVisualizerAbstract:
    """ From node and to node could also use enums. """
    label: str
    from_node: _tp.Optional[_tp.Union[str, _abc.Sequence[str]]]  # sources do not have this
    to_node: _tp.Optional[_tp.Union[str, _abc.Sequence[str]]]  # sinks do not have this
    energy_type: EnergyTypes
    active: bool
    edges_into_node: list[dict[str, dict[str, _tp.Union[str, float, int]]]] = _dc.field(init=False)
    edges_out_of_node: list[dict[str, dict[str, _tp.Union[str, float, int]]]] = _dc.field(init=False)
    color: str = _dc.field(init=False)

    def __post_init__(self):
        colorHelper = MplColorHelper('Paired', 0, 12)
        if hasattr(self, 'building'):
            self.color = colorHelper.get_hex(self.building)
        else:
            self.color = colorHelper.get_hex(0)

    @property
    def id(self):
        """ The id does not show up in the image.
        It is used to identify those nodes, to which the edges connect. """

        if not hasattr(self, "building"):
            return self.label

        return self.get_id_with_building(self.label, self.building)

    @staticmethod
    def get_id_with_building(label: str, building: str) -> str:
        flags_to_be_ignored = ['link', 'Link']

        if any(flag in label for flag in flags_to_be_ignored):
            return label

        zero_padding_level = 3
        return f"{label}_B{str(building).zfill(zero_padding_level)}"

    def get_nodal_infos(self) -> _tp.Optional[dict[str, dict[str, _tp.Union[str, int, float, _pl.Path]]]]:
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

    @staticmethod
    def get_to_and_from_nodes(line):
        building = line['building']
        to_nodes = line['to'].split(sep=',')
        from_nodes = line['from'].split(sep=',')

        for iNode, from_node in enumerate(from_nodes):
            from_nodes[iNode] = ScenarioToVisualizerAbstract.get_id_with_building(from_node, building)

        for iNode, to_node in enumerate(to_nodes):
            to_nodes[iNode] = ScenarioToVisualizerAbstract.get_id_with_building(to_node, building)

        return from_nodes, to_nodes


def scenario_data_factory(scenario_data_type: str) -> _tp.Optional[_tp.Type[ScenarioToVisualizerAbstract]]:
    scenario_data_types = {ScenarioDataTypes.example: NodalDataExample,
                           sheets.buses: BusesConverter,
                           sheets.commodity_sources: CommoditySourcesConverter,
                           sheets.demand: DemandConverter,
                           sheets.grid_connection: GridConnectionConverter,
                           sheets.transformers: TransformersConverter,
                           sheets.storages: StoragesConverter,
                           sheets.solar: SolarConverter}

    if scenario_data_type not in scenario_data_types:
        # raise NotImplementedError("received unexpected type")
        return  # <- until all sheets are implemented

    return scenario_data_types[scenario_data_type]


@_dc.dataclass()
class NodalDataExample(ScenarioToVisualizerAbstract):
    longitude: float
    latitude: float
    _id: str = _dc.field(init=False)

    @property
    def id(self):
        return self._id

    @id.setter
    def id(self, value):
        self._id = value

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
        super().__post_init__()
        if self.from_node:
            raise Warning(f'Commodity sources do not have a from node. Received {self.from_node}.')

    def get_nodal_infos(self) -> _tp.Optional[dict[str, dict[str, _tp.Union[str, int, float, _pl.Path]]]]:
        if self.active:
            return {"data": {'id': self.id, 'label': self.label, "building": self.building,
                             "variable_costs": self.variable_costs, "CO2_impact": self.CO2_impact, 'color': self.color},
                    'classes': 'source'}

    @staticmethod
    def set_from_dataFrame(df: _pd.DataFrame) -> _abc.Sequence[_tp.Type[ScenarioToVisualizerAbstract]]:
        list_of_demands = []

        if 'active' not in df.columns:
            df['active'] = True

        for i, line in df.iterrows():
            energyType = EnergyTypes.electricity

            to_nodes = line['to'].split(sep=',')
            building = line['building']

            for iNode, to_node in enumerate(to_nodes):
                to_nodes[iNode] = ScenarioToVisualizerAbstract.get_id_with_building(to_node, building)

            list_of_demands.append(CommoditySourcesConverter(line['label'], None,
                                                             to_nodes, energyType,
                                                             active=line['active'], building=building,
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
        super().__post_init__()
        if self.from_node:
            raise Warning(f'Buses tend not to have a from node assigned in the scenario. Received {self.from_node}.')
        if self.to_node:
            raise Warning(f'Buses tend not to have a from node assigned in the scenario. Received {self.from_node}.')

    def get_nodal_infos(self) -> _tp.Optional[dict[str, dict[str, _tp.Union[str, int, float, _pl.Path]]]]:
        if self.active:
            return {"data": {'id': self.id, 'label': self.label, "building": self.building,
                             "excess": self.excess, "excess_costs": self.excess_costs, "shortage": self.shortage,
                             "shortage_costs": self.shortage_costs, 'color': self.color},
                    'classes': 'bus'}

    def get_edge_infos(self) -> list[dict[str, dict[str, _tp.Union[str, float, int]]]]:
        # TODO: fix building node as dummy and chiller not connecting properly.
        if not self.active:
            return []

        all_normal_edges = super().get_edge_infos()

        excess_edges = []
        if self.excess:
            excess_node_label = 'excess_' + self.id
            energy_type = get_energy_type_based_on_both_labels(self.id, excess_node_label)
            excess_edges.append({'data': {'source': self.id, 'target': excess_node_label},
                                 "classes": energy_type.value})

        shortage_edges = []
        if self.shortage:
            shortage_node_label = 'shortage_' + self.id
            energy_type = get_energy_type_based_on_both_labels(shortage_node_label, self.id)
            excess_edges.append({'data': {'source': shortage_node_label, 'target': self.id},
                                 "classes": energy_type.value})

        self.edges_out_of_node += excess_edges + shortage_edges

        return all_normal_edges + excess_edges + shortage_edges

    @staticmethod
    def set_from_dataFrame(df: _pd.DataFrame) -> _abc.Sequence[_tp.Type[ScenarioToVisualizerAbstract]]:
        list_of_buses = []

        # TODO: check whether shortage is given without shortage costs.
        if 'shortage' not in df.columns:
            df['shortage'] = None

        if 'shortage costs' not in df.columns:
            df['shortage costs'] = None

        if 'excess' not in df.columns:
            df['excess'] = None

        if 'excess costs' not in df.columns:
            df['excess costs'] = None

        if 'active' not in df.columns:
            df['active'] = True

        for i, line in df.iterrows():
            energyType = EnergyTypes.electricity

            list_of_buses.append(
                BusesConverter(line['label'], None, None, energyType,
                               active=line['active'], building=line['building'],
                               excess=line['excess'],
                               excess_costs=line['excess costs'],
                               shortage=line['shortage'],
                               shortage_costs=line['shortage costs']
                               ))

            if line['excess']:
                list_of_buses.append(
                    DemandConverter("excess_" + line['label'], None, None, energyType,
                                    active=line['active'], building=line['building'],
                                    fixed=line['excess costs'],
                                    nominal_value=0)

                )

            if line['shortage']:
                list_of_buses.append(
                    CommoditySourcesConverter("shortage_" + line['label'], None, None, energyType,
                                              active=line['active'], building=line['building'],
                                              variable_costs=line['shortage costs'],
                                              CO2_impact=0)

                )

        return list_of_buses


@_dc.dataclass()
class DemandConverter(ScenarioToVisualizerAbstract):
    building: int
    fixed: int
    nominal_value: int
    building_model: _tp.Optional[bool] = None
    building_model_out: _tp.Optional[str] = None

    def __post_init__(self):
        super().__post_init__()
        if self.to_node:
            raise Warning(f'Buses tend not to have a from node assigned in the scenario. Received {self.from_node}.')

    def get_nodal_infos(self) -> _tp.Optional[dict[str, dict[str, _tp.Union[str, int, float, _pl.Path]]]]:
        if self.active:
            return {"data": {'id': self.id, 'label': self.label, "building": self.building,
                             "fixed": self.fixed, "nominal_value": self.nominal_value, 'color': self.color,
                             "building model": self.building_model, "building model out": self.building_model_out},
                    "classes": "demand"}

    def get_edge_infos(self) -> list[dict[str, dict[str, _tp.Union[str, float, int]]]]:
        if not self.active:
            return []

        all_normal_edges = super().get_edge_infos()

        building_model_edges = []
        if self.building_model_out:
            if not isinstance(self.building_model_out, list):
                self.building_model_out = [self.building_model_out]
            for building_model_out in self.building_model_out:
                energy_type = get_energy_type_based_on_both_labels(self.id, building_model_out)
                building_model_edges.append({'data': {'source': self.id, 'target': building_model_out},
                                             "classes": energy_type.value})

        self.edges_out_of_node += building_model_edges

        return all_normal_edges + building_model_edges

    @staticmethod
    def set_from_dataFrame(df: _pd.DataFrame) -> _abc.Sequence[_tp.Type[ScenarioToVisualizerAbstract]]:
        list_of_demands = []

        if 'active' not in df.columns:
            df['active'] = True

        if 'building model' not in df.columns:
            df['building model'] = None

        if 'building model out' not in df.columns:
            df['building model out'] = None

        for i, line in df.iterrows():
            energyType = EnergyTypes.electricity

            if not line['building model'] == 'yes' and not line['building model'] == 'Yes':
                line['building model out'] = None
                building_model_out_nodes = None

            building = line['building']
            from_nodes = line['from'].split(sep=',')

            for iNode, from_node in enumerate(from_nodes):
                from_nodes[iNode] = ScenarioToVisualizerAbstract.get_id_with_building(from_node, building)

            if line['building model out']:
                building_model_out_nodes = line['building model out'].split(sep=',')

                for iNode, building_model_out in enumerate(building_model_out_nodes):
                    building_model_out_nodes[iNode] = ScenarioToVisualizerAbstract.get_id_with_building(
                        building_model_out, building)

            list_of_demands.append(DemandConverter(line['label'], from_nodes,
                                                   None, energyType,
                                                   active=line['active'], building=line['building'],
                                                   fixed=line['fixed'], nominal_value=line['nominal value'],
                                                   building_model=line['building model'],
                                                   building_model_out=building_model_out_nodes))
        return list_of_demands


@_dc.dataclass()
class GridConnectionConverter(ScenarioToVisualizerAbstract):
    building: int
    efficiency: float

    def __post_init__(self):
        super().__post_init__()

    def get_nodal_infos(self) -> _tp.Optional[dict[str, dict[str, _tp.Union[str, int, float, _pl.Path]]]]:
        if self.active:
            return {"data": {'id': self.id, 'label': self.label, "building": self.building,
                             "efficiency": self.efficiency, 'color': self.color},
                    "classes": "grid_connection"}

    @staticmethod
    def set_from_dataFrame(df: _pd.DataFrame) -> _abc.Sequence[_tp.Type[ScenarioToVisualizerAbstract]]:
        list_of_demands = []

        if 'active' not in df.columns:
            df['active'] = True

        for i, line in df.iterrows():
            energyType = EnergyTypes.electricity

            if not GridConnectionConverter.has_building_model(line):
                line['building model out'] = None

            building = line['building']
            to_nodes = line['to'].split(sep=',')
            from_nodes = line['from'].split(sep=',')

            for iNode, from_node in enumerate(from_nodes):
                from_nodes[iNode] = ScenarioToVisualizerAbstract.get_id_with_building(from_node, building)

            for iNode, to_node in enumerate(to_nodes):
                to_nodes[iNode] = ScenarioToVisualizerAbstract.get_id_with_building(to_node, building)

            list_of_demands.append(GridConnectionConverter(line['label'], from_nodes,
                                                           to_nodes,
                                                           energyType, active=line['active'],
                                                           building=line['building'],
                                                           efficiency=line['efficiency']))
        return list_of_demands

    @staticmethod
    def has_building_model(line):
        if 'building model' not in line.keys():
            return False

        if not line['building model'] == 'yes' and not line['building model'] == 'Yes':
            return False

        return True


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

    def __post_init__(self):
        super().__post_init__()

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
                             'color': self.color,
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

            building = line['building']
            to_nodes = line['to'].split(sep=',')
            from_nodes = line['from'].split(sep=',')

            for iNode, from_node in enumerate(from_nodes):
                from_nodes[iNode] = ScenarioToVisualizerAbstract.get_id_with_building(from_node, building)

            for iNode, to_node in enumerate(to_nodes):
                to_nodes[iNode] = ScenarioToVisualizerAbstract.get_id_with_building(to_node, building)

            list_of_demands.append(
                TransformersConverter(line['label'], from_nodes,
                                      to_nodes, energyType, active=line['active'],
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

    def __post_init__(self):
        super().__post_init__()

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
                             'color': self.color,
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

            building = line['building']
            to_nodes = line['to'].split(sep=',')
            from_nodes = line['from'].split(sep=',')

            for iNode, from_node in enumerate(from_nodes):
                from_nodes[iNode] = ScenarioToVisualizerAbstract.get_id_with_building(from_node, building)

            for iNode, to_node in enumerate(to_nodes):
                to_nodes[iNode] = ScenarioToVisualizerAbstract.get_id_with_building(to_node, building)

            list_of_demands.append(
                StoragesConverter(line['label'], from_nodes,
                                  to_nodes,
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


@_dc.dataclass()
class PVConverter(ScenarioToVisualizerAbstract):
    building: int
    peripheral_losses: float
    latitude: float
    longitude: float
    tilt: float
    azimuth: float
    delta_temp_n: int
    capacity_max: float
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
    roof_area: float
    zenith_angle: float

    def __post_init__(self):
        super().__post_init__()

    def get_nodal_infos(self) -> _tp.Optional[dict[str, dict[str, _tp.Union[str, int, float, _pl.Path]]]]:
        if self.active:
            return {"data": {'id': self.id, 'label': self.label, solar.building.value: self.building,
                             solar.peripheral_losses.value: self.peripheral_losses,
                             solar.latitude.value: self.latitude,
                             solar.longitude.value: self.longitude,
                             solar.tilt.value: self.tilt,
                             solar.azimuth.value: self.azimuth,
                             solar.delta_temp_n.value: self.delta_temp_n,
                             solar.capacity_max.value: self.capacity_max,
                             solar.capacity_min.value: self.capacity_min,
                             solar.lifetime.value: self.lifetime,
                             solar.maintenance.value: self.maintenance,
                             solar.installation.value: self.installation,
                             solar.planification.value: self.planification,
                             solar.invest_base.value: self.invest_base,
                             solar.invest_cap.value: self.invest_cap,
                             solar.heat_impact.value: self.heat_impact,
                             solar.elec_impact.value: self.elec_impact,
                             solar.impact_cap.value: self.impact_cap,
                             solar.roof_area.value: self.roof_area,
                             solar.zenith_angle.value: self.zenith_angle,
                             'color': self.color,
                             },
                    "classes": "solar"}


@_dc.dataclass()
class SolarCollectorConverter(ScenarioToVisualizerAbstract):
    building: int
    connect: _tp.Union[str, _abc.Sequence[str]]
    electrical_consumption: float
    peripheral_losses: float
    latitude: float
    longitude: float
    tilt: float
    azimuth: float
    eta_0: float
    a_1: float
    a_2: float
    temp_collector_inlet: float
    delta_temp_n: float
    capacity_max: float
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
    roof_area: float
    zenith_angle: float

    def __post_init__(self):
        super().__post_init__()

    def get_nodal_infos(self):
        if self.active:
            return {"data": {'id': self.id, 'label': self.label, solar.building.value: self.building,
                             solar.electrical_consumption.value: self.electrical_consumption,
                             solar.peripheral_losses.value: self.peripheral_losses,
                             solar.latitude.value: self.latitude,
                             solar.longitude.value: self.longitude,
                             solar.tilt.value: self.tilt,
                             solar.azimuth.value: self.azimuth,
                             solar.eta_0.value: self.eta_0,
                             solar.a_1.value: self.a_1,
                             solar.a_2.value: self.a_2,
                             solar.temp_collector_inlet.value: self.temp_collector_inlet,
                             solar.delta_temp_n.value: self.delta_temp_n,
                             solar.capacity_max.value: self.capacity_max,
                             solar.capacity_min.value: self.capacity_min,
                             solar.lifetime.value: self.lifetime,
                             solar.maintenance.value: self.maintenance,
                             solar.installation.value: self.installation,
                             solar.planification.value: self.planification,
                             solar.invest_base.value: self.invest_base,
                             solar.invest_cap.value: self.invest_cap,
                             solar.heat_impact.value: self.heat_impact,
                             solar.elec_impact.value: self.elec_impact,
                             solar.impact_cap.value: self.impact_cap,
                             solar.roof_area.value: self.roof_area,
                             solar.zenith_angle.value: self.zenith_angle,
                             'color': self.color,
                             },
                    "classes": "solar"}

    def get_edge_infos(self) -> list[dict[str, dict[str, _tp.Union[str, float, int]]]]:
        if not self.active:
            return []

        all_normal_edges = super().get_edge_infos()

        edges_from_connect_column = []
        if self.connect:
            if not isinstance(self.connect, list):
                self.connect = [self.connect]

            for connect_from in self.connect:
                connect_from = ScenarioToVisualizerAbstract.get_id_with_building(connect_from, self.building)
                energy_type = get_energy_type_based_on_both_labels(connect_from, self.id)
                edges_from_connect_column.append({'data': {'source': connect_from, 'target': self.id},
                                                  "classes": energy_type.value})

        return all_normal_edges + edges_from_connect_column


class SolarConverter(ScenarioToVisualizerAbstract):
    def get_nodal_infos(self):
        # , 'color': self.color
        raise NotImplementedError

    @staticmethod
    def set_from_dataFrame(df: _pd.DataFrame):
        list_of_solar = []

        if 'active' not in df.columns:
            df['active'] = True

        for i, line in df.iterrows():
            from_nodes, to_nodes = ScenarioToVisualizerAbstract.get_to_and_from_nodes(line)

            label = line['label']
            if label == SolarTypes.pv:
                list_of_solar.append(
                    SolarConverter.get_PVConverter(line, to_nodes)
                )
            elif label == SolarTypes.solarCollector:
                list_of_solar.append(
                    SolarConverter.get_SolarCollectorConverter(line, from_nodes, to_nodes)
                )
            else:
                raise ValueError(f'Received unknown solar technology type: {label}')

        return list_of_solar

    @staticmethod
    def get_PVConverter(line, to_nodes):
        energyType = EnergyTypes.electricity

        return PVConverter(line['label'], None, to_nodes, energyType,
                           building=line[solar.building.value], active=True,
                           peripheral_losses=line[solar.peripheral_losses.value],
                           latitude=line[solar.latitude.value],
                           longitude=line[solar.longitude.value],
                           tilt=line[solar.tilt.value],
                           azimuth=line[solar.azimuth.value],
                           delta_temp_n=line[solar.delta_temp_n.value],
                           capacity_max=line[solar.capacity_max.value],
                           capacity_min=line[solar.capacity_min.value],
                           lifetime=line[solar.lifetime.value],
                           maintenance=line[solar.maintenance.value],
                           installation=line[solar.installation.value],
                           planification=line[solar.planification.value],
                           invest_base=line[solar.invest_base.value],
                           invest_cap=line[solar.invest_cap.value],
                           heat_impact=line[solar.heat_impact.value],
                           elec_impact=line[solar.elec_impact.value],
                           impact_cap=line[solar.impact_cap.value],
                           roof_area=line[solar.roof_area.value],
                           zenith_angle=line[solar.zenith_angle.value]
                           )

    @staticmethod
    def get_SolarCollectorConverter(line, from_nodes, to_nodes):
        energyType = EnergyTypes.domestic_hot_water

        return SolarCollectorConverter(line['label'], from_nodes, to_nodes, energyType,
                                       building=line[solar.building.value], active=True,
                                       connect=line[solar.connect.value],
                                       peripheral_losses=line[solar.peripheral_losses.value],
                                       latitude=line[solar.latitude.value],
                                       longitude=line[solar.longitude.value],
                                       tilt=line[solar.tilt.value],
                                       azimuth=line[solar.azimuth.value],
                                       delta_temp_n=line[solar.delta_temp_n.value],
                                       capacity_max=line[solar.capacity_max.value],
                                       capacity_min=line[solar.capacity_min.value],
                                       lifetime=line[solar.lifetime.value],
                                       maintenance=line[solar.maintenance.value],
                                       installation=line[solar.installation.value],
                                       planification=line[solar.planification.value],
                                       invest_base=line[solar.invest_base.value],
                                       invest_cap=line[solar.invest_cap.value],
                                       heat_impact=line[solar.heat_impact.value],
                                       elec_impact=line[solar.elec_impact.value],
                                       impact_cap=line[solar.impact_cap.value],
                                       electrical_consumption=line[solar.electrical_consumption.value],
                                       eta_0=line[solar.eta_0.value],
                                       a_1=line[solar.a_1.value],
                                       a_2=line[solar.a_2.value],
                                       temp_collector_inlet=line[solar.temp_collector_inlet.value],
                                       roof_area=line[solar.roof_area.value],
                                       zenith_angle=line[solar.zenith_angle.value]
                                       )


@_dc.dataclass()
class LinksConverter(ScenarioToVisualizerAbstract):
    def __post_init__(self):
        super().__post_init__()

    def get_nodal_infos(self):
        # , 'color': self.color
        raise NotImplementedError

    @staticmethod
    def set_from_dataFrame(df: _pd.DataFrame):
        raise NotImplementedError
