import pathlib as _pl
import unittest as _ut

import pandas as _pd
import pytest as _pt

import optihood.Visualizer.scenario_to_visualizer as stv

# TODO: solar, storages, transformers
# TOSKIP: stratified storage, profiles

# list of uncertainties
# - check docs
# - demand:
#   - fixed?
#   - nominal_value
#   - building model
# - grid connection
#   - efficiency
#

# TODO: adjust id to provided values.
# TODO: adjust energy types according to actual values.


class TestNodalDataExample(_ut.TestCase):
    def setUp(self):
        self.maxDiff = None
        energyType = stv.EnergyTypes.electricity
        self.nodalData = stv.NodalDataExample('la', 'Los Angeles', 'van', 'hou', energyType, True, 34.03,
                                              -118.25)

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
        expected_dict_0 = {'data': {'source': 'van', 'target': 'la'}, 'classes': 'electricity'}
        expected_dict_1 = {'data': {'source': 'la', 'target': 'hou'}, 'classes': 'electricity'}
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
        self.nodalData = stv.CommoditySourcesConverter('elRes', 'electricityResource', None, 'gridBus', energyType,
                                                       building=1, variable_costs=0.204, CO2_impact=self.path,
                                                       active=True)
        self.nodalDataFalse = stv.CommoditySourcesConverter('elRes', 'electricityResource', None, 'gridBus', energyType,
                                                            building=1, variable_costs=0.204, CO2_impact=self.path,
                                                            active=False)

    def test_get_nodal_infos(self):
        result = self.nodalData.get_nodal_infos()
        expected_dict = {
            'data': {'id': 'elRes', 'label': 'electricityResource', "building": 1, "variable_costs": 0.204,
                     "CO2_impact": self.path},
            'classes': 'source',
        }
        self.assertDictEqual(result, expected_dict)

    def test_get_nodal_infos_ignored(self):
        result = self.nodalDataFalse.get_nodal_infos()
        self.assertIsNone(result)

    def test_get_edge_infos(self):
        result = self.nodalData.get_edge_infos()
        expected_dict = {'data': {'source': 'elRes', 'target': 'gridBus'},
                         'classes': 'electricity', }
        self.assertDictEqual(result[0], expected_dict)

    def test_get_edge_infos_ignored(self):
        result = self.nodalDataFalse.get_edge_infos()
        self.assertListEqual(result, [])

    def test_read_nodal_infos(self):
        data = {'id': 'la', 'label': 'Los Angeles', "building": 1, "variable_costs": 0.024, 'CO2_impact': 0.018}
        result = stv.CommoditySourcesConverter.read_nodal_infos(data)
        expected_string = ("{'id': 'la', 'label': 'Los Angeles', 'building': 1, 'variable_costs': 0.024, 'CO2_impact': "
                           "0.018}")
        self.assertEqual(result, expected_string)

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
            'data': {'id': 'electricityResource', 'label': 'electricityResource', "building": 1,
                     "variable_costs": 0.204, "CO2_impact": self.path},
            'classes': 'source',
        }

        # Flesh out test?
        self.assertDictEqual(result[0].get_nodal_infos(), expected_dict)


class TestBusesConverter(_ut.TestCase):
    def setUp(self):
        self.maxDiff = None
        energyType = stv.EnergyTypes.electricity
        self.path = _pl.Path("..\\excels\\basic_example\\electricity_impact.csv")
        self.nodalData = stv.BusesConverter('gridBus', 'gridBus', None, None, energyType, building=1, excess=1,
                                            excess_costs=0.024, active=True)
        self.nodalDataExtended = stv.BusesConverter('gridBus', 'gridBus', None, None, energyType, building=1, excess=1,
                                                    excess_costs=0.024, active=True, shortage=True,
                                                    shortage_costs=0.012)

    def test_get_nodal_infos(self):
        result = self.nodalData.get_nodal_infos()
        expected_dict = {
            'data': {'id': 'gridBus', 'label': 'gridBus', "building": 1, "excess": 1, "excess_costs": 0.024,
                     'shortage': None, "shortage_costs": None},
            'classes': 'bus',
        }
        self.assertDictEqual(result, expected_dict)

    def test_get_nodal_infos_extended(self):
        result = self.nodalDataExtended.get_nodal_infos()
        expected_dict = {
            'data': {'id': 'gridBus', 'label': 'gridBus', "building": 1, "excess": 1, "excess_costs": 0.024,
                     'shortage': True, "shortage_costs": 0.012},
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
            'data': {'id': 'electricityInBus', 'label': 'electricityInBus', "building": 1, "excess": 1, "excess_costs": -0.09,
                     'shortage': None, "shortage_costs": None},
            'classes': 'bus',
        }

        # Flesh out test?
        self.assertDictEqual(result[2].get_nodal_infos(), expected_dict)


class TestDemandConverter(_ut.TestCase):
    def setUp(self):
        self.maxDiff = None
        energyType = stv.EnergyTypes.electricity
        self.path = _pl.Path("..\\excels\\basic_example\\electricity_impact.csv")
        self.nodalData = stv.DemandConverter('elDem', 'electricityDemand', None, None, energyType, building=1, fixed=1,
                                             nominal_value=1, active=True)
        self.nodalDataExtended = stv.DemandConverter('elDem', 'electricityDemand', None, None, energyType, building=1,
                                                     fixed=1, nominal_value=1, active=True, building_model=True)

    def test_get_nodal_infos(self):
        result = self.nodalData.get_nodal_infos()
        expected_dict = {
            'data': {'id': 'elDem', 'label': 'electricityDemand', "building": 1, "fixed": 1, "nominal_value": 1,
                     'building_model': None},
            'classes': 'demand',
        }
        self.assertDictEqual(result, expected_dict)

    def test_get_nodal_infos_extended(self):
        result = self.nodalDataExtended.get_nodal_infos()
        expected_dict = {
            'data': {'id': 'elDem', 'label': 'electricityDemand', "building": 1, "fixed": 1, "nominal_value": 1,
                     'building_model': True},
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
            'data': {'id': 'electricityDemand', 'label': 'electricityDemand', "building": 1, "fixed": 1,
                     "nominal_value": 1, 'building_model': None},
            'classes': 'demand',
        }

        # Flesh out test?
        self.assertDictEqual(result[0].get_nodal_infos(), expected_dict)


class TestGridConnectionConverter(_ut.TestCase):
    def setUp(self):
        self.maxDiff = None
        energyType = stv.EnergyTypes.electricity
        self.nodalData = stv.GridConnectionConverter('gridEl', 'gridElectricity', "gridBus", "electricityInBus",
                                                     energyType, building=1, efficiency=1, active=True)

    def test_get_nodal_infos(self):
        result = self.nodalData.get_nodal_infos()
        expected_dict = {
            'data': {'id': 'gridEl', 'label': 'gridElectricity', "building": 1, "efficiency": 1},
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
            'data': {'id': 'gridElectricity', 'label': 'gridElectricity', "building": 1, "efficiency": 1, },
            "classes": "grid_connection"
        }

        # Flesh out test?
        self.assertDictEqual(result[0].get_nodal_infos(), expected_dict)
