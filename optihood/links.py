from pyomo.core.base.block import SimpleBlock
from pyomo.environ import BuildAction
from pyomo.environ import Constraint

from oemof.solph import network as solph_network
from oemof.solph.plumbing import sequence as solph_sequence

class Link(solph_network.Transformer):
    r"""
    A transformer to model links between different buildings
    The constraint defined in a new constraint block equates the sum of all the input flows
    to the sum of all the output flows
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def constraint_group(self):
        return LinkBlock

class LinkBlock(SimpleBlock):
    r"""Block for the linear relation of nodes of type Link"""
    CONSTRAINT_GROUP = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def _create(self, group=None):
        """Creates the two linear constraints for nodes of type Link
        """
        if group is None:
            return None

        m = self.parent_block()
        in_flows = {n: [i for i in n.inputs.keys()] for n in group}
        out_flows = {n: [o for o in n.outputs.keys()] for n in group}
        efficiency = [n.conversion_factors[next(iter(n.outputs.keys()))] for n in group][0][0]   # conversion factors of all the output flows of all the groups will be equal, therefore first value is chosen

        def _input_output_relation(block):
            """Constraint defining the relation between input and outputs."""
            self.input_output_relation = Constraint(group, m.TIMESTEPS, noruleinit=True)

            for t in m.TIMESTEPS:
                for g in group:
                    lhs = sum(m.flow[i, g, t] for i in in_flows[g]) * efficiency
                    rhs = sum(m.flow[g, o, t] for o in out_flows[g])
                    block.input_output_relation.add((g, t), (lhs == rhs))

        self.input_output_relation_build = BuildAction(rule=_input_output_relation)