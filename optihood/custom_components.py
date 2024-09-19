from pyomo.core.base.block import ScalarBlock
from pyomo.environ import BuildAction
from pyomo.environ import Constraint
from optihood._helpers import *
from oemof.solph import components as solph_components
from oemof.solph._plumbing import sequence as solph_sequence

class PeakObjectiveTransformer(solph_components.Transformer):
    r"""
    A custom component to implement peak minimization
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def constraint_group(self):
        return PeakObjectiveTransformerBlock

class PeakObjectiveTransformerBlock(ScalarBlock):
    r"""Block for the linear relation of nodes
        """
    CONSTRAINT_GROUP = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def _create(self, group=None):
        """Creates the linear constraint
        """
        if group is None:
            return None

        m = self.parent_block()

        in_flows = {n: [i for i in n.inputs.keys()] for n in group}
        out_flows = {n: [o for o in n.outputs.keys()] for n in group}

        def _input_output_relation_rule(block):
            """Connection between input and outputs."""
            for t in m.TIMESTEPS:
                for n in group:
                    for o in out_flows[n]:
                        lhs = sum(m.flow[i, n, t] for i in in_flows[n])
                        rhs = m.flow[n, o, t]
                        block.input_output_relation.add((n, t), (lhs == rhs))

        self.input_output_relation = Constraint(
            group, m.TIMESTEPS, noruleinit=True
        )
        self.input_output_relation_build = BuildAction(
            rule=_input_output_relation_rule
        )