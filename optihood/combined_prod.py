from pyomo.core.base.block import ScalarBlock
from pyomo.environ import BuildAction
from pyomo.environ import Constraint

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
            n.inflow = [i for i in list(n.inputs) if "electricity" in i.label or "naturalGasBus" in i.label][0]
            if len(list(n.inputs)) > 1:
                n.inflowQevap = [i for i in list(n.inputs) if "electricity" not in i.label][0]
            else:
                n.inflowQevap = 0
            flows = [k for k, v in n.efficiency.items()]
            n.flowT0 = flows[0]
            n.flowT1 = flows[1]
            n.outputT0 = [o for o in n.outputs if n.flowT0 == o][0]
            n.outputT1 = [o for o in n.outputs if n.flowT1 == o][0]
            n.efficiency_sq = (
                n.efficiency[n.outputT0],
                n.efficiency[n.outputT1]
            )
            if len(flows)==3:
                n.flowT2 = flows[2]
                n.outputT2 = [o for o in n.outputs if n.flowT2 == o][0]
                n.efficiency_sq = (
                    n.efficiency[n.outputT0],
                    n.efficiency[n.outputT1],
                    n.efficiency[n.outputT2])

        def _input_output_relation_rule(block):
            """Connection between input and outputs."""
            for t in m.TIMESTEPS:
                for g in group:
                    lhs = m.flow[g.inflow, g, t]
                    if len(g.efficiency_sq)==3:
                        rhs = (m.flow[g, g.outputT0, t] / g.efficiency_sq[0][t]
                               + m.flow[g, g.outputT1, t] / g.efficiency_sq[1][t]
                               + m.flow[g, g.outputT2, t] / g.efficiency_sq[2][t])
                    else:
                        rhs = (m.flow[g, g.outputT0, t] / g.efficiency_sq[0][t]
                               + m.flow[g, g.outputT1, t] / g.efficiency_sq[1][t])
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
                        lhs = (len(list(g.inputs)) > 1) * m.flow[g.inflowQevap, g, t]
                        rhs = (len(list(g.inputs)) > 1) * (m.flow[g, g.outputSH, t] + m.flow[g, g.outputDHW, t] - m.flow[g.inflow, g, t])
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
            n.flowT0 = flows[0]
            n.flowT1 = flows[1]
            n.flowEl = flows[2]
            n.outputT0 = [o for o in n.outputs if n.flowT0 == o][0]
            n.outputT1 = [o for o in n.outputs if n.flowT1 == o][0]
            n.outputEl = [o for o in n.outputs if n.flowEl == o][0]
            n.efficiency_sq = (
                n.efficiency[n.outputT0],
                n.efficiency[n.outputT1],
                n.efficiency[n.outputEl]
            )
            if len(flows)==4:
                n.flowT2 = flows[2]
                n.flowEl = [k for k, v in n.efficiency.items()][3]
                n.outputT2 = [o for o in n.outputs if n.flowT2 == o][0]
                n.outputEl = [o for o in n.outputs if n.flowEl == o][0]
                n.efficiency_sq = (
                    n.efficiency[n.outputT0],
                    n.efficiency[n.outputT1],
                    n.efficiency[n.outputT2],
                    n.efficiency[n.outputEl])

        def _input_heat_relation_rule(block):
            """Connection between input and heat outputs."""
            for t in m.TIMESTEPS:
                for g in group:
                    lhs = m.flow[g.inflow, g, t]
                    if len(g.efficiency_sq) == 4:
                        rhs = (
                                m.flow[g, g.outputT0, t] / g.efficiency_sq[0][t]
                                + m.flow[g, g.outputT1, t] / g.efficiency_sq[1][t]
                                + m.flow[g, g.outputT2, t] / g.efficiency_sq[2][t]
                        )
                    else:
                        rhs = (
                            m.flow[g, g.outputT0, t] / g.efficiency_sq[0][t]
                            + m.flow[g, g.outputT1, t] / g.efficiency_sq[1][t]
                        )
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
                    rhs = (m.flow[g, g.outputEl, t] / g.efficiency_sq[len(g.efficiency_sq)-1][t])
                    block.input_elec_relation.add((g, t), (lhs == rhs))

        self.input_elec_relation = Constraint(
            group, m.TIMESTEPS, noruleinit=True
        )
        self.input_elec_relation_build = BuildAction(
            rule=_input_elec_relation_rule
        )