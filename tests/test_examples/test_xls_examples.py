import os as _os
import pandas as _pd
import pathlib as _pl
import pytest as _pt
import re as _re
import sys
import subprocess as _sp
import unittest as _ut

import optihood as oh

sys.path.append(str(_pl.Path(oh.__file__).resolve().parent / ".." / "data" / "examples"))
from basic_example import plot_sankey_diagram, plot_bokeh

cwd = _os.getcwd()
packageDir = _pl.Path(oh.__file__).resolve().parent
scriptDir = packageDir / ".." / "data" / "examples"
example_path = packageDir / ".." / "data" / "results"
expected_data_dir = _pl.Path(__file__).resolve().parent / "expected_files"
test_results_dir = packageDir / ".." / "results"


def compare_html_files(testCase, file_path, file_path_expected, desired_uuid: str):
    with open(file_path) as f1, open(file_path_expected) as f2:
        contents1 = list(f1)
        contents2 = list(f2)
        contents1 = replace_uuid(contents1, desired_uuid)
        _ut.TestCase.assertListEqual(testCase, contents1[1::], contents2[1::])


def replace_uuid(html_text, desired_uuid: str, html_part: int=61):
    find = _re.compile('[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}')
    html_text[html_part] = find.sub(desired_uuid, html_text[html_part])
    return html_text


class TestXlsExamples(_ut.TestCase):
    def SetUp(self):
        self.maxDiff = None

    def test_basic(self):

        # =============================
        # make into helper
        _os.chdir(scriptDir)
        _sp.run([packageDir / '..' / 'venv' / 'Scripts' / 'python.exe', scriptDir / "basic_example.py", '/H'], shell=True, check=True)
        _os.chdir(cwd)
        # =============================

        excel_file_path = str(example_path / "results_basic_example.xls")
        expected_data_path = str(expected_data_dir / "test_run_basic_example.xls")

        sheet_names = ['naturalGasBus__Building1', 'gridBus__Building1', 'electricityBus__Building1',
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
                       'dhwDemandBus__Building4', 'solarConnectBus__Building4', 'costs__Building1',
                       'env_impacts__Building1', 'capStorages__Building1', 'capTransformers__Building1',
                       'costs__Building2', 'env_impacts__Building2', 'capStorages__Building2',
                       'capTransformers__Building2', 'costs__Building3', 'env_impacts__Building3',
                       'capStorages__Building3', 'capTransformers__Building3', 'costs__Building4',
                       'env_impacts__Building4', 'capStorages__Building4', 'capTransformers__Building4']

        data = _pd.ExcelFile(excel_file_path)

        expected_data = _pd.ExcelFile(expected_data_path)

        for sheet in sheet_names:
            print("")
            print(sheet)
            print("")
            df_new = data.parse(sheet)
            df_expected = expected_data.parse(sheet)

            try:
                _pd.testing.assert_frame_equal(df_new, df_expected)
            except AssertionError as ae:
                # Optihood doesn't export the results in a consistent way.
                # Therefore, this hack reorders the results.
                # Instead, the export should be ordered consistently.

                df_new = df_new.sort_values(by=[df_new.columns[0]], ignore_index=True)
                df_expected = df_expected.sort_values(by=[df_new.columns[0]], ignore_index=True)
                _pd.testing.assert_frame_equal(df_new, df_expected)

    def test_sankey_basic_example(self):
        # figure_file_path = "..\\..\\test-results"
        optimizationType = "costs"
        resultFileName = "test_run_basic_example.xls"
        plot_sankey_diagram(test_results_dir, 4, optimizationType, resultFileName, expected_data_dir, show_figs=False)
        uuid_expected = "0fbea2e5-8f67-4d21-8fe7-897e199ac035"
        compare_html_files(self, test_results_dir / "Sankey_4_costs.html", expected_data_dir / "test_Sankey_basic_example.html", uuid_expected)

    @_pt.mark.skip()
    def test_bokeh_basic_example(self):
        assert False == True

    def test_html_comparison(self):
        uuid_expected = "0fbea2e5-8f67-4d21-8fe7-897e199ac035"
        compare_html_files(self,  expected_data_dir / "Sankey_4_costs_old_uuid.html", expected_data_dir / "test_Sankey_basic_example.html", uuid_expected)


if __name__ == '__main__':
    _ut.main()
