import re as _re
import typing as _tp
import unittest as _ut

import pytest as _pt

import tests.xls_helpers as xlsh
bex = xlsh.import_example_script(xlsh.EXAMPLE_SCRIPT_DIR, "basic_example")

scriptDir = xlsh.EXAMPLE_SCRIPT_DIR
script_path = scriptDir / "basic_example.py"
example_path = xlsh.EXAMPLE_RESULTS_DIR
current_file_dir = xlsh.get_current_file_dir(__file__)
expected_data_dir = current_file_dir / "expected_files"

_SHEET_NAMES = ['naturalGasBus__Building1', 'gridBus__Building1', 'electricityBus__Building1',
                'electricityProdBus__Building1', 'electricityInBus__Building1', 'shSourceBus__Building1',
                'spaceHeatingBus__Building1', 'shDemandBus__Building1', 'domesticHotWaterBus__Building1',
                'dhwDemandBus__Building1', 'solarConnectBus__Building1', 'naturalGasBus__Building2',
                'gridBus__Building2', 'electricityBus__Building2', 'electricityProdBus__Building2',
                'electricityInBus__Building2', 'shSourceBus__Building2', 'spaceHeatingBus__Building2',
                'shDemandBus__Building2', 'domesticHotWaterBus__Building2', 'dhwDemandBus__Building2',
                'solarConnectBus__Building2', 'naturalGasBus__Building3', 'gridBus__Building3',
                'electricityBus__Building3', 'electricityProdBus__Building3', 'electricityInBus__Building3',
                'shSourceBus__Building3', 'spaceHeatingBus__Building3', 'shDemandBus__Building3',
                'domesticHotWaterBus__Building3', 'dhwDemandBus__Building3', 'solarConnectBus__Building3',
                'naturalGasBus__Building4', 'gridBus__Building4', 'electricityBus__Building4',
                'electricityProdBus__Building4', 'electricityInBus__Building4', 'shSourceBus__Building4',
                'spaceHeatingBus__Building4', 'shDemandBus__Building4', 'domesticHotWaterBus__Building4',
                'dhwDemandBus__Building4', 'solarConnectBus__Building4', 'storage_content__Building1',
                'costs__Building1', 'env_impacts__Building1', 'capStorages__Building1', 'capTransformers__Building1',
                'storage_content__Building2', 'costs__Building2', 'env_impacts__Building2', 'capStorages__Building2',
                'capTransformers__Building2', 'storage_content__Building3', 'costs__Building3',
                'env_impacts__Building3', 'capStorages__Building3', 'capTransformers__Building3',
                'storage_content__Building4', 'costs__Building4',
                'env_impacts__Building4', 'capStorages__Building4', 'capTransformers__Building4']


def compare_html_files(testCase, file_path, file_path_expected, desired_uuid: _tp.Optional[str] = None):
    with open(file_path, encoding="utf8") as f1, open(file_path_expected, encoding="utf8") as f2:
        contents1 = list(f1)
        contents2 = list(f2)
        if desired_uuid:
            contents1 = replace_uuid(contents1, desired_uuid)
        _ut.TestCase.assertListEqual(testCase, contents1[1::], contents2[1::])


def replace_uuid(html_text, desired_uuid: str, html_part: int = 61):
    find = _re.compile('[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}')
    html_text[html_part] = find.sub(desired_uuid, html_text[html_part])
    return html_text


class TestXlsExamples(_ut.TestCase):
    def setUp(self):
        self.maxDiff = None

    @_pt.mark.skipif(True, reason='waiting for evaluation. needs to be skipped for CI for now.')
    def test_basic_before_merge(self):
        xlsh.run_python_script(script_path)

        excel_file_path = str(example_path / "results_basic_example.xls")
        expected_data_path = str(expected_data_dir / "test_run_basic_example.xls")

        xlsh.compare_xls_files(self, excel_file_path, expected_data_path, _SHEET_NAMES, abs_tolerance=1e-4)

    def test_basic_after_merge(self):
        """ End2End test to ensure user example is reproducible.
            This test will need to be adjusted, as Gurobi doesn't reproduce exact values between computing systems.
        """
        manual = False

        xlsh.run_python_script(script_path)

        excel_file_path = str(example_path / "results_basic_example.xlsx")
        expected_data_path = str(expected_data_dir / "test_results_basic_example_after_merge.xlsx")

        xlsh.compare_xls_files(self, excel_file_path, expected_data_path, _SHEET_NAMES, abs_tolerance=1e-4,
                               manual_test=manual)

    @_pt.mark.skip(reason='Waiting for evaluation of merge differences.')
    def test_sankey_basic_example(self):
        """ End2End test to ensure the Sankey diagram of the user example is reproduced.
            This test is deterministic, as it uses a given result.
        """
        optimizationType = "costs"
        resultFileName = "test_run_basic_example.xls"
        bex.plot_sankey_diagram(xlsh.TEST_RESULTS_DIR, 4, optimizationType, resultFileName, expected_data_dir,
                                show_figs=False)
        uuid_expected = "0fbea2e5-8f67-4d21-8fe7-897e199ac035"
        compare_html_files(self, xlsh.TEST_RESULTS_DIR / "Sankey_4_costs.html",
                           expected_data_dir / "test_Sankey_basic_example.html", uuid_expected)

    def test_sankey_basic_example_after_merge(self):
        """ End2End test to ensure the Sankey diagram of the user example is reproduced.
            This test is deterministic, as it uses a given result.
            However, some of the requirements show up as well, so this will likely be very brittle.
            Needs to be adjusted as more fine-grained tests exist.
        """
        optimizationType = "costs"
        resultFileName = "test_run_basic_example.xls"
        bex.plot_sankey_diagram(xlsh.TEST_RESULTS_DIR, 4, optimizationType, resultFileName, expected_data_dir,
                                show_figs=False)
        compare_html_files(self, xlsh.TEST_RESULTS_DIR / "Sankey_4_costs.html",
                           expected_data_dir / "test_Sankey_basic_example_after_merge.html")

    @_pt.mark.skip()
    def test_bokeh_basic_example(self):
        assert False == True

    def test_html_comparison(self):
        """ The html files tend to only differ by a random UUID.
        """
        uuid_expected = "0fbea2e5-8f67-4d21-8fe7-897e199ac035"
        compare_html_files(self, expected_data_dir / "Sankey_4_costs_old_uuid.html",
                           expected_data_dir / "test_Sankey_basic_example.html", uuid_expected)

    @_pt.mark.manual
    def test_compare_results_before_and_after_merge_sheets_missing(self):
        """ Used to show the quality of feedback between different xls files.
            These examples also show a change in the optimization results, which needs to be evaluated.
        """
        old_data_path = str(expected_data_dir / "test_run_basic_example.xls")
        new_data_path = str(expected_data_dir / "test_results_basic_example_after_merge.xlsx")
        xlsh.compare_xls_files(self, old_data_path, new_data_path, _SHEET_NAMES, abs_tolerance=1e-4, manual_test=True)

    @_pt.mark.manual
    def test_compare_results_before_and_after_merge_shape_and_data_mismatch(self):
        """ Used to show the quality of feedback between different xls files.
            These examples also show a change in the optimization results, which needs to be evaluated.
        """
        old_data_path = str(expected_data_dir / "test_results_basic_example_after_merge.xls")
        new_data_path = str(expected_data_dir / "test_results_basic_example_after_merge.xlsx")
        xlsh.compare_xls_files(self, old_data_path, new_data_path, _SHEET_NAMES, abs_tolerance=1e-4, manual_test=True)


if __name__ == '__main__':
    _ut.main()
