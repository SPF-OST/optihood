import pathlib as _pl
import sys as _sys
import unittest as _ut

import numpy as _np

import optihood as oh

_sys.path.append(str(_pl.Path(oh.__file__).resolve().parent / ".." / "data" / "examples"))
from MPC_example import get_current_system_state


class TestMpcExample(_ut.TestCase):
    def test_get_current_system_state(self):
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
                system_state = get_current_system_state(system_state)
                self.assertDictEqual(system_state, expected_state)
            except AssertionError as e:
                errors.append(e)

        if errors:
            raise ExceptionGroup(f"found {len(errors)} issues:", errors)


if __name__ == '__main__':
    _ut.main()
