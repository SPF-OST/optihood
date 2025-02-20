from pyomo.core.base.block import ScalarBlock
from pyomo.environ import BuildAction
from pyomo.environ import Constraint
from optihood._helpers import *
from oemof.solph import components as solph_components
from oemof.solph._plumbing import sequence as solph_sequence


class CombinedTransformer(solph_components.Transformer):
    r"""
    A transformer able to produce both SH and DHW in the same timestep
    Pelec_in = Qsh/efficiencySH + Qdhw/efficiencyDHW
    """

    def __init__(self, efficiencies, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.efficiency = {
            k: solph_sequence(v)
            for k, v in efficiencies.items()
        }

    def constraint_group(self):
        return CombinedTransformerBlock


class CombinedTransformerBlock(ScalarBlock):
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

        for n in group:
            n.inflow = [i for i in list(n.inputs) if "electricity" in i.label or list(n.inputs).__len__()==1][0]
            if len(list(n.inputs)) > 1:
                n.inflowQevap = [i for i in list(n.inputs) if "electricity" not in i.label][0]
            else:
                n.inflowQevap = 0
            flows = [k for k, v in n.efficiency.items()]
            n.outputs_ordered = []
            n.efficiency_sq = ()
            for i in range(len(flows)):
                n.outputs_ordered.append([o for o in n.outputs if flows[i] == o][0])
                n.efficiency_sq = n.efficiency_sq + (n.efficiency[n.outputs_ordered[i]],)

        def _input_output_relation_rule(block):
            """Connection between input and outputs."""
            for t in m.TIMESTEPS:
                for g in group:
                    lhs = m.flow[g.inflow, g, t]
                    rhs = sum(m.flow[g, g.outputs_ordered[i], t] / g.efficiency_sq[i][t] for i in range(len(g.efficiency_sq)))
                    block.input_output_relation.add((g, t), (lhs == rhs))

        self.input_output_relation = Constraint(
            group, m.TIMESTEPS, noruleinit=True
        )
        self.input_output_relation_build = BuildAction(
            rule=_input_output_relation_rule
        )

        def _second_input_relation_rule(block):
            """Constraint for evaluation of Q_condensor i.e. the second input"""
            for t in m.TIMESTEPS:
                for g in group:
                    if len(list(g.inputs)) > 1:
                        lhs = m.flow[g.inflowQevap, g, t]
                        rhs = (sum(m.flow[g, g.outputs_ordered[i], t] for i in range(len(g.efficiency_sq))) - m.flow[g.inflow, g, t])
                        block.input_relation.add((g, t), (lhs == rhs))

        self.input_relation = Constraint(
            group, m.TIMESTEPS, noruleinit=True
        )
        self.input_relation_build = BuildAction(
            rule=_second_input_relation_rule
        )


class CombinedCHP(solph_components.Transformer):
    r"""
    A CHP able to produce both SH and DHW in the same timestep
    Pelec_in = Qsh/efficiencySH + Qdhw/efficiencyDHW
             = Pelec_out/efficiencyEl
    """

    def __init__(self, efficiencies, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.efficiency = {
            k: solph_sequence(v)
            for k, v in efficiencies.items()
        }

    def constraint_group(self):
        return CombinedCHPBlock


class CombinedCHPBlock(ScalarBlock):
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

        for n in group:
            n.inflow = list(n.inputs)[0]
            flows = [k for k, v in n.efficiency.items()]
            n.outputs_ordered = []
            n.efficiency_sq = ()
            for i in range(len(flows)):
                if "electricity" not in flows[i].label:
                    n.outputs_ordered.append([o for o in n.outputs if flows[i] == o][0])
                    n.efficiency_sq = n.efficiency_sq + (n.efficiency[n.outputs_ordered[-1]],)
            for i in range(len(flows)):
                if "electricity" in flows[i].label: # add electricity output flow and efficiency as the last element
                    n.outputs_ordered.append([o for o in n.outputs if flows[i] == o][0])
                    n.efficiency_sq = n.efficiency_sq + (n.efficiency[n.outputs_ordered[-1]],)
            print("")
        def _input_heat_relation_rule(block):
            """Connection between input and heat outputs."""
            for t in m.TIMESTEPS:
                for g in group:
                    lhs = m.flow[g.inflow, g, t]
                    rhs = sum(m.flow[g, g.outputs_ordered[i], t] / g.efficiency_sq[i][t] for i in range(len(g.efficiency_sq)-1))
                    block.input_heat_relation.add((g, t), (lhs == rhs))

        self.input_heat_relation = Constraint(
            group, m.TIMESTEPS, noruleinit=True
        )
        self.input_heat_relation_build = BuildAction(
            rule=_input_heat_relation_rule
        )

        def _input_elec_relation_rule(block):
            """Connection between input and elec output."""
            for t in m.TIMESTEPS:
                for g in group:
                    lhs = m.flow[g.inflow, g, t]
                    rhs = (m.flow[g, g.outputs_ordered[-1], t] / g.efficiency_sq[-1][t])
                    block.input_elec_relation.add((g, t), (lhs == rhs))

        self.input_elec_relation = Constraint(
            group, m.TIMESTEPS, noruleinit=True
        )
        self.input_elec_relation_build = BuildAction(
            rule=_input_elec_relation_rule
        )