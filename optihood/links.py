from pyomo.core.base.block import ScalarBlock
from pyomo.environ import BuildAction
from pyomo.environ import Constraint

from oemof.solph import components as solph_components
from oemof.solph._plumbing import sequence as solph_sequence

class Link(solph_components.Transformer):
    r"""
    A transformer to model links between different buildings
    The constraint defined in a new constraint block equates the sum of all the input flows
    to the sum of all the output flows
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def constraint_group(self):
        return LinkBlock

class LinkBlock(ScalarBlock):
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

class LinkTemperatureDemand(solph_components.Transformer):
    r"""
        A transformer to model links between different different temperature levels and demand sink component
        The constraint defined in a new constraint block equates the weighted sum of all the input flows
        to the output flow.
        """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def constraint_group(self):
        return LinkTemperatureDemandBlock


class LinkTemperatureDemandBlock(ScalarBlock):
    r"""Block for the linear relation of nodes of type LinkTemperatureDemand"""
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

        def _input_output_relation(block):
            """Constraint defining the relation between input and outputs."""
            self.input_output_relation = Constraint(group, m.TIMESTEPS, noruleinit=True)

            for t in m.TIMESTEPS:
                for g in group:
                    lhs = sum(m.flow[i, g, t]*g.conversion_factors[i][t] for i in in_flows[g])
                    rhs = sum(m.flow[g, o, t] for o in out_flows[g])
                    block.input_output_relation.add((g, t), (lhs == rhs))

        self.input_output_relation_build = BuildAction(rule=_input_output_relation)

class LinkStorageDummyInput(solph_components.Transformer):
    r"""
        A transformer to model links between output from different temperature levels and inputs in multi-temperature
        level thermal storages. This transformer takes two input flows, one coming from energy converter and the other
        from a storage volume.
        The constraint defined in a new constraint block equates the two input flows to ensure volume from lower
        temperature to higher temperature within the storage. Moreover, the output flow would be equal to the input flow.
        input_flow_1 == input_flow_2 == output_flow
        """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def constraint_group(self):
        return LinkStorageDummyInputBlock


class LinkStorageDummyInputBlock(ScalarBlock):
    r"""Block for the linear relation of nodes of type LinkStorageDummyInput"""
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

        def _input_relation(block):
            """Constraint defining the relation between two inputs and one output of the component."""
            self.input_relation = Constraint(group, m.TIMESTEPS, noruleinit=True)

            for t in m.TIMESTEPS:
                for g in group:
                    lhs = m.flow[in_flows[g][0], g, t]*g.conversion_factors[in_flows[g][0]][t]
                    rhs = m.flow[in_flows[g][1], g, t]*g.conversion_factors[in_flows[g][1]][t]
                    block.input_relation.add((g, t), (lhs == rhs))

        self.input_relation_build = BuildAction(rule=_input_relation)

        def _input_output_relation(block):
            """Constraint defining the relation between two inputs and one output of the component."""
            self.input_output_relation = Constraint(group, m.TIMESTEPS, noruleinit=True)

            for t in m.TIMESTEPS:
                for g in group:
                    lhs = m.flow[in_flows[g][0], g, t]*g.conversion_factors[in_flows[g][0]][t]
                    rhs = m.flow[g, out_flows[g][0], t]
                    block.input_output_relation.add((g, t), (lhs == rhs))

        self.input_output_relation_build = BuildAction(rule=_input_output_relation)