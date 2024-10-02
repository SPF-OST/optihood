import pandas as _pd
import collections.abc as _abc
import dataclasses as _dc
import typing as _tp

import optihood.Visualizer.scenario_to_visualizer as _stv


@_dc.dataclass()
class EnergyNetworkGraphData:
    nodes: _abc.Sequence[dict[str, dict[str, _tp.Union[str, float, int]]]]
    edges: _abc.Sequence[dict[str, dict[str, _tp.Union[str, float, int]]]]


def get_converters(initial_nodal_data: dict[str, _pd.DataFrame]) -> _abc.Sequence[_stv.ScenarioToVisualizerAbstract]:
    converters = []
    for sheet_name, sheet in initial_nodal_data.items():
        converter = _stv.scenario_data_factory(sheet_name)

        # ========================================================================
        """ This needs to be removed after all current sheets are implemented. """
        if not converter:
            continue
        # ========================================================================



def get_graph_data(converters: _abc.Sequence[_stv.ScenarioToVisualizerAbstract]) -> EnergyNetworkGraphData:
    pass
