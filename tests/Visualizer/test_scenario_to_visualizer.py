import pathlib as _pl
import unittest as _ut

import pandas as _pd
import pytest as _pt

import optihood.Visualizer.scenario_to_visualizer as stv


# TODO: links
# TODO: add link shape


# TODO: test edges individually
# TODO: include default values from stratified storage ?and profiles?
# TODO: adjust diagram to have sources on the left and demands on the right.

# list of uncertainties
# - check docs
# - demand:
#   - fixed?
#   - nominal_value
#   - building model
# - grid connection
#   - efficiency
#


class TestNodalDataExample(_ut.TestCase):
    """
    This test shows a simple example outside of our problem domain.
    It helped create the architecture and is kept to keep the system flexible for unknown future objects.

    This example comes directly from the Plotly homepage.
    http://dash.plotly.com/cytoscape/events
    """

    def setUp(self):
        """ Currently fails, as this is the only case where IDs are given directly. """
        self.maxDiff = None
        energyType = stv.EnergyTypes.electricity
        self.nodalData = stv.NodalDataExample('Los Angeles', 'van', 'hou', energyType, True, 34.03,
                                              -118.25)
        self.nodalData.id = 'la'

    def test_get_nodal_infos(self):
        result = self.nodalData.get_nodal_infos()
        expected_dict = {
            'data': {'id': 'la', 'label': 'Los Angeles', "lat": -118.25, "long": 34.03},
            'position': {'x': -2365.0, 'y': -680.6}
        }
        self.assertDictEqual(result, expected_dict)

    def test_read_nodal_infos(self):
        data = {'id': 'la', 'label': 'Los Angeles', "lat": -118.25, "long": 34.03}
        result = stv.NodalDataExample.read_nodal_infos(data)
        expected_string = "{'id': 'la', 'label': 'Los Angeles', 'lat': -118.25, 'long': 34.03}"
        self.assertEqual(result, expected_string)

    def test_get_edge_infos(self):
        result = self.nodalData.get_edge_infos()
        expected_dict_0 = {'data': {'source': 'van', 'target': 'la'}, 'classes': 'unknown'}
        expected_dict_1 = {'data': {'source': 'la', 'target': 'hou'}, 'classes': 'unknown'}
        self.assertDictEqual(result[0], expected_dict_0)
        self.assertDictEqual(result[1], expected_dict_1)

    def test_read_edge_infos(self):
        with _pt.raises(NotImplementedError):
            self.nodalData.read_edge_infos({'stuff': 0})


class TestCommoditySourcesConverter(_ut.TestCase):
    def setUp(self):
        self.maxDiff = None
        energyType = stv.EnergyTypes.electricity
        self.path = _pl.Path("..\\excels\\basic_example\\electricity_impact.csv")
        self.nodalData = stv.CommoditySourcesConverter('electricityResource', None, 'gridBus', energyType,
                                                       building=1, variable_costs=0.204, CO2_impact=self.path,
                                                       active=True)
        self.nodalDataFalse = stv.CommoditySourcesConverter('electricityResource', None, 'gridBus', energyType,
                                                            building=1, variable_costs=0.204, CO2_impact=self.path,
                                                            active=False)

    def test_get_nodal_infos(self):
        result = self.nodalData.get_nodal_infos()
        expected_dict = {
            'data': {'id': 'electricityResource_B001', 'label': 'electricityResource', "building": 1,
                     "variable_costs": 0.204,
                     "CO2_impact": self.path, 'color': '#1f78b4'},
            'classes': 'source',
        }
        self.assertDictEqual(result, expected_dict)

    def test_get_nodal_infos_ignored(self):
        result = self.nodalDataFalse.get_nodal_infos()
        self.assertIsNone(result)

    def test_get_edge_infos(self):
        result = self.nodalData.get_edge_infos()
        expected_dict = {'data': {'source': 'electricityResource_B001', 'target': 'gridBus'},
                         'classes': 'electricity', }
        self.assertDictEqual(result[0], expected_dict)

    def test_get_edge_infos_ignored(self):
        result = self.nodalDataFalse.get_edge_infos()
        self.assertListEqual(result, [])

    def test_set_from_dataFrame(self):
        data_df = _pd.DataFrame(index=[0],
                                data={"label": "electricityResource",
                                      "building": 1,
                                      "active": 1,
                                      "to": "gridBus",
                                      "variable costs": 0.204,
                                      "CO2 impact": self.path,
                                      })
        result = stv.CommoditySourcesConverter.set_from_dataFrame(data_df)
        expected_dict = {
            'data': {'id': 'electricityResource_B001', 'label': 'electricityResource', "building": 1,
                     "variable_costs": 0.204, "CO2_impact": self.path, 'color': '#1f78b4'},
            'classes': 'source',
        }

        # Flesh out test?
        self.assertDictEqual(result[0].get_nodal_infos(), expected_dict)


class TestBusesConverter(_ut.TestCase):
    def setUp(self):
        self.maxDiff = None
        energyType = stv.EnergyTypes.electricity
        self.path = _pl.Path("..\\excels\\basic_example\\electricity_impact.csv")
        self.nodalData = stv.BusesConverter('gridBus', None, None, energyType, building=1, excess=1,
                                            excess_costs=0.024, active=True)
        self.nodalDataExtended = stv.BusesConverter('gridBus', None, None, energyType, building=1, excess=1,
                                                    excess_costs=0.024, active=True, shortage=True,
                                                    shortage_costs=0.012)

    def test_get_nodal_infos(self):
        result = self.nodalData.get_nodal_infos()
        expected_dict = {
            'data': {'id': 'gridBus_B001', 'label': 'gridBus', "building": 1, "excess": 1, "excess_costs": 0.024,
                     'shortage': None, "shortage_costs": None, 'color': '#1f78b4'},
            'classes': 'bus',
        }
        self.assertDictEqual(result, expected_dict)

    def test_get_nodal_infos_extended(self):
        result = self.nodalDataExtended.get_nodal_infos()
        expected_dict = {
            'data': {'id': 'gridBus_B001', 'label': 'gridBus', "building": 1, "excess": 1, "excess_costs": 0.024,
                     'shortage': True, "shortage_costs": 0.012, 'color': '#1f78b4'},
            'classes': 'bus',
        }
        self.assertDictEqual(result, expected_dict)

    def test_set_from_dataFrame(self):
        data_df = _pd.DataFrame(index=None,
                                data={"label": ["gridBus", "electricityProdBus", "electricityInBus", "shDemandBus"],
                                      "building": [1, 1, 1, 1],
                                      "active": [1, 1, 1, 1],
                                      "excess": [False, False, True, False],
                                      "excess costs": [None, None, -0.09, None],
                                      })
        result = stv.BusesConverter.set_from_dataFrame(data_df)
        expected_dict = {
            'data': {'id': 'electricityInBus_B001', 'label': 'electricityInBus', "building": 1, "excess": 1,
                     "excess_costs": -0.09,
                     'shortage': None, "shortage_costs": None, 'color': '#1f78b4'},
            'classes': 'bus',
        }

        # Flesh out test?
        self.assertDictEqual(result[2].get_nodal_infos(), expected_dict)


class TestDemandConverter(_ut.TestCase):
    def setUp(self):
        """ TODO: Perhaps another case with a specific building model would make sense.
            Then, the appropriate edges need to be tested.
        """
        self.maxDiff = None
        energyType = stv.EnergyTypes.electricity
        self.path = _pl.Path("..\\excels\\basic_example\\electricity_impact.csv")
        self.nodalData = stv.DemandConverter('electricityDemand', None, None, energyType, building=1, fixed=1,
                                             nominal_value=1, active=True)
        self.nodalDataExtended = stv.DemandConverter('electricityDemand', None, None, energyType, building=1,
                                                     fixed=1, nominal_value=1, active=True, building_model=True)

    def test_get_nodal_infos(self):
        result = self.nodalData.get_nodal_infos()
        expected_dict = {
            'data': {'id': 'electricityDemand_B001', 'label': 'electricityDemand', "building": 1, "fixed": 1,
                     "nominal_value": 1, 'building model': None, 'building model out': None, 'color': '#1f78b4'},
            'classes': 'demand',
        }
        self.assertDictEqual(result, expected_dict)

    def test_get_nodal_infos_extended(self):
        result = self.nodalDataExtended.get_nodal_infos()
        expected_dict = {
            'data': {'id': 'electricityDemand_B001', 'label': 'electricityDemand', "building": 1, "fixed": 1,
                     "nominal_value": 1, 'building model': True, 'building model out': None, 'color': '#1f78b4'},
            'classes': 'demand',
        }
        self.assertDictEqual(result, expected_dict)

    def test_set_from_dataFrame(self):
        data_df = _pd.DataFrame(index=None,
                                data={"label": ["electricityDemand", "spaceHeatingDemand", "domesticHotWaterDemand"],
                                      "building": [1, 1, 1],
                                      "active": [1, 1, 1],
                                      "from": ["electricityInBus", "shDemandBus", "domesticHotWaterBus"],
                                      "fixed": [1, 1, 1],
                                      "nominal value": [1, 1, 1],
                                      "building model": [None, None, None],
                                      })
        result = stv.DemandConverter.set_from_dataFrame(data_df)
        expected_dict = {
            'data': {'id': 'electricityDemand_B001', 'label': 'electricityDemand', "building": 1, "fixed": 1,
                     "nominal_value": 1, 'building model': None, 'building model out': None, 'color': '#1f78b4'},
            'classes': 'demand',
        }

        # Flesh out test?
        self.assertDictEqual(result[0].get_nodal_infos(), expected_dict)


class TestGridConnectionConverter(_ut.TestCase):
    def setUp(self):
        self.maxDiff = None
        energyType = stv.EnergyTypes.electricity
        self.nodalData = stv.GridConnectionConverter('gridElectricity', "gridBus", "electricityInBus",
                                                     energyType, building=1, efficiency=1, active=True)

    def test_get_nodal_infos(self):
        result = self.nodalData.get_nodal_infos()
        expected_dict = {
            'data': {'id': 'gridElectricity_B001', 'label': 'gridElectricity', "building": 1, "efficiency": 1,
                     'color': '#1f78b4'},
            "classes": "grid_connection"
        }
        self.assertDictEqual(result, expected_dict)

    def test_set_from_dataFrame(self):
        data_df = _pd.DataFrame(index=None,
                                data={"label": ["gridElectricity", "electricitySource", "producedElectricity"],
                                      "building": [1, 1, 1],
                                      "active": [1, 1, 1],
                                      "from": ["gridBus", "electricityProdBus", "electricityBus"],
                                      "to": ["electricityInBus", "electricityBus", "electricityInBus"],
                                      "efficiency": [1, 1, 1],
                                      })
        result = stv.GridConnectionConverter.set_from_dataFrame(data_df)
        expected_dict = {
            'data': {'id': 'gridElectricity_B001', 'label': 'gridElectricity', "building": 1, "efficiency": 1,
                     'color': '#1f78b4'},
            "classes": "grid_connection"
        }

        # Flesh out test?
        self.assertDictEqual(result[0].get_nodal_infos(), expected_dict)


class TestTransformersConverter(_ut.TestCase):
    def setUp(self):
        self.maxDiff = None
        energyType = stv.EnergyTypes.electricity
        self.nodalData = stv.TransformersConverter('HP', "electricityInBus", ["shSourceBus", "dhwStorageBus"],
                                                   energyType, building=1, efficiency=3.5, active=True,
                                                   capacity_DHW=500,
                                                   capacity_SH=500,
                                                   capacity_min=5,
                                                   lifetime=20,
                                                   maintenance=0.02,
                                                   installation=0,
                                                   planification=0,
                                                   invest_base=16679,
                                                   invest_cap=2152,
                                                   heat_impact=0,
                                                   elec_impact=0,
                                                   impact_cap=280.9
                                                   )

    def test_get_nodal_infos(self):
        result = self.nodalData.get_nodal_infos()
        expected_dict = {
            'data': {'id': 'HP_B001', 'label': 'HP', "building": 1, "efficiency": 3.5, 'capacity_DHW': 500,
                     'capacity_SH': 500, 'capacity_el': None, 'capacity_min': 5, 'elec_impact': 0, 'heat_impact': 0,
                     'impact_cap': 280.9, 'installation': 0, 'invest_base': 16679, 'invest_cap': 2152,
                     'lifetime': 20, 'maintenance': 0.02, 'planification': 0, 'color': '#1f78b4'},
            "classes": "transformer"
        }
        self.assertDictEqual(result, expected_dict)

    def test_set_from_dataFrame(self):
        data_df = _pd.DataFrame(index=None,
                                data={"label": ["HP", "GWHP"],
                                      "building": [1, 1],
                                      "active": [1, 1],
                                      "from": ["electricityInBus", "electricityInBus"],
                                      "to": ["shSourceBus,dhwStorageBus", "shSourceBus,dhwStorageBus"],
                                      "efficiency": [3.5, 4.5],
                                      "capacity_DHW": [500, 500],
                                      "capacity_SH": [500, 500],
                                      "capacity_el": [None, None],
                                      "capacity_min": [5, 5],
                                      "lifetime": [20, 20],
                                      "maintenance": [0.02, 0.02],
                                      "installation": [0, 0],
                                      "planification": [0, 0],
                                      "invest_base": [16679, 22257],
                                      "invest_cap": [2152, 3052],
                                      "heat_impact": [0, 0],
                                      "elec_impact": [0, 0],
                                      "impact_cap": [280.9, 772]})

        result = stv.TransformersConverter.set_from_dataFrame(data_df)
        expected_dict = {
            'data': {'id': 'HP_B001', 'label': 'HP', "building": 1, "efficiency": 3.5, 'capacity_DHW': 500,
                     'capacity_SH': 500, 'capacity_el': None, 'capacity_min': 5, 'elec_impact': 0, 'heat_impact': 0,
                     'impact_cap': 280.9, 'installation': 0, 'invest_base': 16679, 'invest_cap': 2152,
                     'lifetime': 20, 'maintenance': 0.02, 'planification': 0, 'color': '#1f78b4'},
            "classes": "transformer"
        }

        # Flesh out test?
        self.assertDictEqual(result[0].get_nodal_infos(), expected_dict)

        expected_dict_edge = {'data': {'source': 'HP_B001', 'target': 'shSourceBus_B001'},
                              'classes': 'SH', }

        self.assertDictEqual(result[0].get_edge_infos()[1], expected_dict_edge)


class TestStorageConverter(_ut.TestCase):

    def setUp(self):
        self.maxDiff = None
        energyType = stv.EnergyTypes.electricity
        self.nodalData = stv.StoragesConverter('HP', "electricityInBus", ["shSourceBus", "dhwStorageBus"],
                                               energyType, building=1, active=True,
                                               efficiency_inflow=0.9,
                                               efficiency_outflow=0.86,
                                               initial_capacity=0,
                                               capacity_min=0,
                                               capacity_max=1000000,
                                               capacity_loss=0,
                                               lifetime=15,
                                               maintenance=0,
                                               installation=0,
                                               planification=0,
                                               invest_base=5138,
                                               invest_cap=981,
                                               heat_impact=0,
                                               elec_impact=0,
                                               impact_cap=28.66
                                               )

    def test_get_nodal_infos(self):
        result = self.nodalData.get_nodal_infos()
        expected_dict = {
            'data': {'id': 'HP_B001', 'label': 'HP', "building": 1, "efficiency inflow": 0.9,
                     "efficiency outflow": 0.86,
                     'capacity loss': 0, 'capacity max': 1000000, 'capacity min': 0, 'elec_impact': 0, 'heat_impact': 0,
                     'impact_cap': 28.66, 'installation': 0, 'invest_base': 5138, 'invest_cap': 981,
                     'initial capacity': 0, 'lifetime': 15, 'maintenance': 0, 'planification': 0, 'color': '#1f78b4'},
            "classes": "storage"
        }
        self.assertDictEqual(result, expected_dict)

    def test_set_from_dataFrame(self):
        data_df = _pd.DataFrame(index=None,
                                data={"label": ["electricalStorage", "shStorage", "dhwStorage"],
                                      "building": [1, 1, 1],
                                      "active": [1, 1, 1],
                                      "from": ["electricityProdBus", "shSourceBus", "dhwStorageBus"],
                                      "to": ["electricityBus", "spaceHeatingBus", "domesticHotWaterBus"],
                                      "lifetime": [15, 20, 20],
                                      "maintenance": [0, 0, 0],
                                      "installation": [0, 0, 0],
                                      "planification": [0, 0, 0],
                                      "invest_base": [5138, 1092, 2132],
                                      "invest_cap": [981, 1.41, 6.88],
                                      "heat_impact": [0, 0, 0],
                                      "elec_impact": [0, 0, 0],
                                      "impact_cap": [28.66, 0.49, 0.49],
                                      "efficiency inflow": [0.9, None, None],
                                      "efficiency outflow": [0.86, None, None],
                                      "initial capacity": [0, 0, 0],
                                      "capacity min": [0, 0, 0],
                                      "capacity max": [1000000, 1000000, 1000000],
                                      "capacity loss": [0, None, None],
                                      }
                                )

        result = stv.StoragesConverter.set_from_dataFrame(data_df)
        expected_dict = {
            'data': {'id': 'electricalStorage_B001', 'label': 'electricalStorage', "building": 1,
                     "efficiency inflow": 0.9, "efficiency outflow": 0.86,
                     'capacity loss': 0.0, 'capacity max': 1000000, 'capacity min': 0, 'elec_impact': 0,
                     'heat_impact': 0, 'impact_cap': 28.66, 'installation': 0, 'invest_base': 5138, 'invest_cap': 981.0,
                     'initial capacity': 0, 'lifetime': 15, 'maintenance': 0, 'planification': 0, 'color': '#1f78b4'},
            "classes": "storage"
        }

        # Flesh out test?
        self.assertDictEqual(result[0].get_nodal_infos(), expected_dict)

        expected_dict_edge = {'data': {'source': 'electricityProdBus_B001', 'target': 'electricalStorage_B001'},
                              'classes': 'electricity', }

        self.assertDictEqual(result[0].get_edge_infos()[0], expected_dict_edge)


class TestPVConverter(_ut.TestCase):
    def setUp(self):
        self.maxDiff = None
        self.path = _pl.Path("..\\excels\\basic_example\\electricity_impact.csv")
        self.nodalData = stv.PVConverter('pv', None, 'electricityProdBus',
                                         stv.EnergyTypes.electricity,
                                         active=True,
                                         building=1,
                                         peripheral_losses=0.05,
                                         latitude=47.49,
                                         longitude=7.59,
                                         tilt=30,
                                         azimuth=180,
                                         delta_temp_n=40,
                                         capacity_max=500,
                                         capacity_min=0.4,
                                         lifetime=30,
                                         maintenance=0.02,
                                         installation=0,
                                         planification=0,
                                         invest_base=17950,
                                         invest_cap=1103,
                                         heat_impact=0,
                                         elec_impact=0,
                                         impact_cap=1131,
                                         roof_area=400,
                                         zenith_angle=20)

    def test_get_nodal_infos(self):
        result = self.nodalData.get_nodal_infos()
        expected_dict = {
            'data': {'id': 'pv_B001', 'label': 'pv', "building": 1,
                     'peripheral_losses': 0.05,
                     'latitude': 47.49,
                     'longitude': 7.59,
                     'tilt': 30,
                     'azimuth': 180,
                     'delta_temp_n': 40,
                     'capacity_max': 500,
                     'capacity_min': 0.4,
                     'lifetime': 30,
                     'maintenance': 0.02,
                     'installation': 0,
                     'planification': 0,
                     'invest_base': 17950,
                     'invest_cap': 1103,
                     'heat_impact': 0,
                     'elec_impact': 0,
                     'impact_cap': 1131,
                     'roof_area': 400,
                     'zenith_angle': 20,
                     'color': '#1f78b4', },
            'classes': 'solar',
        }
        self.assertDictEqual(result, expected_dict)


class TestSolarCollectorConverter(_ut.TestCase):
    def setUp(self):
        self.maxDiff = None
        self.nodalData = stv.SolarCollectorConverter('solarCollector', 'electricityInBus', 'dhwStorageBus',
                                                     stv.EnergyTypes.unknown,  # depends on other connections
                                                     active=True,
                                                     building=1,
                                                     connect='solarConnectBus',
                                                     electrical_consumption=0.02,
                                                     peripheral_losses=0.05,
                                                     latitude=47.23,
                                                     longitude=8.34,
                                                     tilt=45,
                                                     azimuth=225,
                                                     eta_0=0.73,
                                                     a_1=1.7,
                                                     a_2=0.016,
                                                     temp_collector_inlet=20,
                                                     delta_temp_n=40,
                                                     capacity_max=100,
                                                     capacity_min=0,
                                                     lifetime=25,
                                                     maintenance=0.05,
                                                     installation=0.15,
                                                     planification=0.05,
                                                     invest_base=11034,
                                                     invest_cap=706.36,
                                                     heat_impact=0,
                                                     elec_impact=0,
                                                     impact_cap=0,
                                                     roof_area=400,
                                                     zenith_angle=20
                                                     )

    def test_get_nodal_infos(self):
        result = self.nodalData.get_nodal_infos()
        expected_dict = {
            'data': {'id': 'solarCollector_B001', 'label': 'solarCollector', "building": 1,
                     'electrical_consumption': 0.02,
                     'peripheral_losses': 0.05,
                     'latitude': 47.23,
                     'longitude': 8.34,
                     'tilt': 45,
                     'azimuth': 225,
                     'eta_0': 0.73,
                     'a_1': 1.7,
                     'a_2': 0.016,
                     'temp_collector_inlet': 20,
                     'delta_temp_n': 40,
                     'capacity_max': 100,
                     'capacity_min': 0,
                     'lifetime': 25,
                     'maintenance': 0.05,
                     'installation': 0.15,
                     'planification': 0.05,
                     'invest_base': 11034,
                     'invest_cap': 706.36,
                     'heat_impact': 0,
                     'elec_impact': 0,
                     'impact_cap': 0,
                     'roof_area': 400,
                     'zenith_angle': 20,
                     'color': '#1f78b4', },
            'classes': 'solar',
        }
        self.assertDictEqual(result, expected_dict)


class TestSolarConverter(_ut.TestCase):
    def setUp(self):
        self.maxDiff = None

    def test_set_from_dataFrame(self):
        data_df = _pd.DataFrame(index=None,
                                data={
                                    "label": ['solarCollector', 'solarCollector', 'solarCollector', 'solarCollector',
                                              'pv', 'pv', 'pv', 'pv'],
                                    "building": [1, 2, 3, 4, 1, 2, 3, 4],
                                    "active": [1, 1, 1, 1, 1, 1, 1, 1],
                                    "from": ['electricityInBus', 'electricityInBus', 'electricityInBus',
                                             'electricityInBus', 'x', 'x', 'x', 'x'],
                                    "to": ['dhwStorageBus', 'dhwStorageBus', 'dhwStorageBus', 'dhwStorageBus',
                                           'electricityProdBus', 'electricityProdBus', 'electricityProdBus',
                                           'electricityProdBus'],
                                    "connect": ['solarConnectBus', 'solarConnectBus', 'solarConnectBus',
                                                'solarConnectBus', 'x', 'x', 'x', 'x'],
                                    "electrical_consumption": [0.02, 0.02, 0.02, 0.02, 'x', 'x', 'x', 'x'],
                                    "peripheral_losses": [0.05, 0.05, 0.05, 0.05, 0.05, 0.05, 0.05, 0.05],
                                    "latitude": [47.23, 47.23, 47.23, 47.23, 47.23, 47.23, 47.23, 47.23],
                                    "longitude": [8.34, 8.34, 8.34, 8.34, 8.34, 8.34, 8.34, 8.34],
                                    "tilt": [45, 45, 45, 45, 45, 45, 45, 45],
                                    "azimuth": [225, 225, 225, 225, 225, 225, 225, 225],
                                    "efficiency": [None, None, None, None, 0.2, 0.2, 0.2, 0.2],
                                    "eta_0": [0.73, 0.73, 0.73, 0.73, 'x', 'x', 'x', 'x'],
                                    "a_1": [1.7, 1.7, 1.7, 1.7, 'x', 'x', 'x', 'x'],
                                    "a_2": [0.016, 0.016, 0.016, 0.016, 'x', 'x', 'x', 'x'],
                                    "temp_collector_inlet": [20, 20, 20, 20, 'x', 'x', 'x', 'x'],
                                    "delta_temp_n": [40, 40, 40, 40, 40, 40, 40, 40],
                                    "capacity_max": [100, 100, 100, 100, 100, 100, 100, 100],
                                    "capacity_min": [0, 0, 0, 0, 0.4, 0.4, 0.4, 0.4],
                                    "lifetime": [25, 25, 25, 25, 30, 30, 30, 30],
                                    "maintenance": [0.05, 0.05, 0.05, 0.05, 0, 0, 0, 0],
                                    "installation": [0.15, 0.15, 0.15, 0.15, 0, 0, 0, 0],
                                    "planification": [0.05, 0.05, 0.05, 0.05, 0.05, 0.05, 0.05, 0.05],
                                    "invest_base": [11034, 11034, 11034, 11034, 17950, 17950, 17950, 17950],
                                    "invest_cap": [706.36, 706.36, 706.36, 706.36, 1103, 1103, 1103, 1103],
                                    "heat_impact": [0, 0, 0, 0, 0, 0, 0, 0],
                                    "elec_impact": [0, 0, 0, 0, 0, 0, 0, 0],
                                    "impact_cap": [0, 0, 0, 0, 0, 0, 0, 0],
                                    "roof_area": [400, 400, 400, 400, 400, 400, 400, 400],
                                    "zenith_angle": [20, 20, 20, 20, 20, 20, 20, 20],
                                })

        result = stv.SolarConverter.set_from_dataFrame(data_df)

        # SolarCollector part
        expected_dict = {
            'data': {'id': 'solarCollector_B001', 'label': 'solarCollector', "building": 1,
                     'a_1': 1.7,
                     'a_2': 0.016,
                     'azimuth': 225,
                     'capacity_max': 100,
                     'capacity_min': 0.0,
                     'color': '#1f78b4',
                     'delta_temp_n': 40,
                     'elec_impact': 0,
                     'electrical_consumption': 0.02,
                     'eta_0': 0.73,
                     'heat_impact': 0,
                     'impact_cap': 0,
                     'installation': 0.15,
                     'invest_base': 11034,
                     'invest_cap': 706.36,
                     'latitude': 47.23,
                     'lifetime': 25,
                     'longitude': 8.34,
                     'maintenance': 0.05,
                     'peripheral_losses': 0.05,
                     'planification': 0.05,
                     'roof_area': 400,
                     'temp_collector_inlet': 20,
                     'tilt': 45,
                     'zenith_angle': 20,
                     },
            'classes': 'solar',
        }

        # Flesh out test?
        self.assertDictEqual(result[0].get_nodal_infos(), expected_dict)

        expected_dict_edge = {'data': {'source': 'electricityInBus_B001', 'target': 'solarCollector_B001'},
                              'classes': 'electricity', }

        self.assertDictEqual(result[0].get_edge_infos()[0], expected_dict_edge)

        expected_dict_edge = {'data': {'source': 'solarCollector_B002', 'target': 'dhwStorageBus_B002'},
                              'classes': 'DHW', }

        self.assertDictEqual(result[1].get_edge_infos()[1], expected_dict_edge)

        # pv part
        expected_dict = {
            'data': {'id': 'pv_B001', 'label': 'pv', "building": 1,
                     'azimuth': 225,
                     'capacity_max': 100,
                     'capacity_min': 0.4,
                     'color': '#1f78b4',
                     'delta_temp_n': 40,
                     'elec_impact': 0,
                     'heat_impact': 0,
                     'impact_cap': 0,
                     'installation': 0.0,
                     'invest_base': 17950,
                     'invest_cap': 1103.0,
                     'latitude': 47.23,
                     'lifetime': 30,
                     'longitude': 8.34,
                     'maintenance': 0.0,
                     'peripheral_losses': 0.05,
                     'planification': 0.05,
                     'roof_area': 400,
                     'tilt': 45,
                     'zenith_angle': 20,
                     },
            'classes': 'solar',
        }

        # Flesh out test?
        self.assertDictEqual(result[4].get_nodal_infos(), expected_dict)

        expected_dict_edge = {'data': {'source': 'pv_B001', 'target': 'electricityProdBus_B001'},
                              'classes': 'electricity', }

        self.assertDictEqual(result[4].get_edge_infos()[0], expected_dict_edge)

        expected_dict_edge = {'data': {'source': 'pv_B002', 'target': 'electricityProdBus_B002'},
                              'classes': 'electricity', }

        self.assertDictEqual(result[5].get_edge_infos()[0], expected_dict_edge)


class TestLinksConverter(_ut.TestCase):
    def setUp(self):
        self.maxDiff = None
        self.nodalData = stv.LinksConverter('electricityLink', None, None, None, active=True, efficiency=0.9999, invest_base=0,
                                            invest_cap=0, investment=1)

    def test_get_nodal_infos(self):
        result = self.nodalData.get_nodal_infos()
        expected_dict = {
            'data': {'id': 'electricityLink', 'label': 'electricityLink', 'efficiency': 0.9999, 'invest_base': 0,
                     'invest_cap': 0, 'investment': 1},
            'classes': 'link',
        }
        self.assertDictEqual(result, expected_dict)

    def test_set_from_dataFrame(self):
        # data_df = _pd.DataFrame(index=[0],
        #                         data={"label": "electricityResource",
        #                               "building": 1,
        #                               "active": 1,
        #                               "to": "gridBus",
        #                               "variable costs": 0.204,
        #                               "CO2 impact": self.path,
        #                               })

        # "label": ['electricityLink', 'shLink', 'dhwLink'],
        # "active": [True, True, True],
        # "efficiency": [0.9999,	0.9,	0.9],
        # "invest_base": [0, 0, 0],
        # "invest_cap": [0, 0, 0],
        # "investment": [1, 1, 1],

        # result = stv.LinksConverter.set_from_dataFrame(data_df)
        # expected_dict = {
        #     'data': {'id': 'electricityResource', 'label': 'electricityResource', "building": 1,
        #              "variable_costs": 0.204, "CO2_impact": self.path},
        #     'classes': 'source',
        # }
        #
        # # Flesh out test?
        # self.assertDictEqual(result[0].get_nodal_infos(), expected_dict)
        #
        # expected_dict_edge = {'data': {'source': 'electricityProdBus', 'target': 'electricalStorage'},
        #                       'classes': 'electricity', }
        #
        # self.assertDictEqual(result[0].get_edge_infos()[0], expected_dict_edge)
        self.fail()
