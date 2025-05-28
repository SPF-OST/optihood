import pathlib as _pl
import unittest as _ut
import shutil as _sh

import numpy as _np

import tests.xls_helpers as xlsh

mpc_example = xlsh.import_example_script(xlsh.EXAMPLE_SCRIPT_DIR, "MPC_example")

script_path = xlsh.EXAMPLE_SCRIPT_DIR / "MPC_example.py"


class TestMpcExample(_ut.TestCase):
    def test_get_current_system_state(self):
        """Unit test to check reproducibility of state inputs."""

        system_state = {'electricalStorage__B001': {'initial capacity': 0},
                        'shStorage__B001': {'initial capacity': 0}
                        }

        expected_states = [{'electricalStorage__B001': {'initial capacity': 0.55},
                            'shStorage__B001': {'initial capacity': 0.72}
                            },
                           {'electricalStorage__B001': {'initial capacity': 0.6},
                            'shStorage__B001': {'initial capacity': 0.54}
                            },
                           {'electricalStorage__B001': {'initial capacity': 0.42},
                            'shStorage__B001': {'initial capacity': 0.65}
                            },
                           ]

        errors = []
        _np.random.seed(0)

        for expected_state in expected_states:
            try:
                system_state = mpc_example.get_current_system_state(system_state)
                self.assertDictEqual(system_state, expected_state)
            except AssertionError as e:
                errors.append(e)

        if errors:
            raise ExceptionGroup(f"found {len(errors)} issues:", errors)

    def test_mpc_example(self):
        """End2end test for the User example.
        This has flaky behavior, as the optimizer choices have little effect on the objective function result.

        This is looped through max. twice, because there is a rare occurrence of a 27% difference between steps.
        """
        show_differences = False  # Turn true to plot differences.

        expected_sheet_names = ['gridBus__Building1',
                                'electricityBus__Building1',
                                'electricityProdBus__Building1',
                                'electricityInBus__Building1',
                                'shSourceBus__Building1',
                                'dhwSourceBus__Building1',
                                'spaceHeatingBus__Building1',
                                'shDemandBus__Building1',
                                'costs__Building1',
                                'env_impacts__Building1',
                                'capStorages__Building1',
                                'capTransformers__Building1'
                                ]
        expected_files_dir = _pl.Path(__file__).parent / "expected_files"
        for i in range(2):
            results_path = mpc_example.result_dir_path
            if results_path.exists():
                _sh.rmtree(results_path)

            xlsh.run_python_script(script_path)

            errors = []

            # compare raw results.
            list_of_result_files = list(mpc_example.result_dir_path.glob("*.xlsx"))
            names_of_result_files = [f.name for f in list_of_result_files]

            try:
                self.assertListEqual(names_of_result_files, ["results_MPC_example_2018_01_01__00_00_00.xlsx",
                                                             "results_MPC_example_2018_01_01__01_00_00.xlsx",
                                                             "results_MPC_example_2018_01_01__02_00_00.xlsx",
                                                             ]
                                     )
            except Exception as e:
                errors.append(e)

            for results_file_path in list_of_result_files:
                expected_file_path = expected_files_dir / results_file_path.name
                try:
                    xlsh.compare_xls_files(self, results_file_path, expected_file_path, expected_sheet_names,
                                           manual_test=show_differences, rel_tolerance=1.0)
                except ExceptionGroup as e:
                    errors.append(e)

            # compare desired energy flows.
            list_of_result_files_csv = list(mpc_example.result_dir_path.glob("*.csv"))
            names_of_result_files_csv = [f.name for f in list_of_result_files_csv]

            try:
                self.assertListEqual(names_of_result_files_csv, ["results_MPC_example_2018_01_01__00_00_00.csv",
                                                                 "results_MPC_example_2018_01_01__01_00_00.csv",
                                                                 "results_MPC_example_2018_01_01__02_00_00.csv",
                                                                 ]
                                     )
            except Exception as e:
                errors.append(e)

            for results_file_path in list_of_result_files_csv:
                expected_file_path = expected_files_dir / results_file_path.name
                try:
                    xlsh.compare_csv_files(results_file_path, expected_file_path, "energy_flows",
                                           manual_test=show_differences, rel_tolerance=1.0)
                except ExceptionGroup as e:
                    errors.append(e)

            if errors and i == 0:
                """Ignore the errors the first time around, in case the optimizer makes entirely different choices."""
                print(f"{self.id()} failed the first time around.")
                continue

            elif errors and i == 1:
                """Test fails as errors obtained in both runs."""
                raise ExceptionGroup(f"Found {len(errors)} mismatched prediction windows", errors)

            else:
                """Test passes if no errors found in the first run."""
                break


if __name__ == '__main__':
    _ut.main()
