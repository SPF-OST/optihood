import unittest as _ut

import optihood.Visualizer.scenario_to_visualizer as stv


class TestNodalDataExample(_ut.TestCase):
    def setUp(self):
        self.maxDiff = None
        self.nodalData = stv.NodalDataExample('la', 'Los Angeles', 'van', 'la', 34.03, -118.25)

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
        expected_string = "Los Angeles, -118.25, 34.03"
        self.assertEqual(result, expected_string)

    def test_get_edge_infos(self):
        self.fail()

    def test_read_edge_infos(self):
        self.fail()
