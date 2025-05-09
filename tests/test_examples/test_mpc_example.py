import pathlib as _pl
import sys as _sys
import unittest as _ut
import pytest as _pt

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

    @_pt.mark.manual
    def test_mpc_example(self):
        """End2end test for the User example."""

        xlsh.run_python_script(script_path)


if __name__ == '__main__':
    _ut.main()
