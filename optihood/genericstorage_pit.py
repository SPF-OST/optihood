import numbers

from oemof.network import network
from pyomo.core.base.block import ScalarBlock
from pyomo.environ import Binary
from pyomo.environ import Constraint
from pyomo.environ import Expression
from pyomo.environ import NonNegativeReals, PositiveReals
from pyomo.environ import Set
from pyomo.environ import Var

from oemof.solph._helpers import check_node_object_for_missing_attribute
from oemof.solph._options import Investment
from oemof.solph._plumbing import sequence as solph_sequence


class GenericStoragePit(network.Node):
    r"""
    Component `GenericStoragePit`, derived from `GenericStorage`from oemof.solph

    The energy balance equations represent those of a pit storage.

    The GenericStoragePit is designed for one input and one output.

    Parameters
    ----------
    height_multiplication_factor : numeric
        factor for the calculation of height from nominal storage capacity
    temp_h : numeric
        temperature of the hot layer in the storage [°C]
    temp_c : numeric
        return temperature or temperature of the cold layer in the storage [°C]
    rho : numeric
        Density of the fluid in kg/L
    c : numeric
        Specific heat capacity of the fluid in kJ/(kg K)
    nominal_storage_capacity : numeric, :math:`E_{nom}`
        Absolute nominal capacity of the storage
    invest_relation_input_capacity : numeric or None, :math:`r_{cap,in}`
        Ratio between the investment variable of the input Flow and the
        investment variable of the storage:
        :math:`\dot{E}_{in,invest} = E_{invest} \cdot r_{cap,in}`
    invest_relation_output_capacity : numeric or None, :math:`r_{cap,out}`
        Ratio between the investment variable of the output Flow and the
        investment variable of the storage:
        :math:`\dot{E}_{out,invest} = E_{invest} \cdot r_{cap,out}`
    invest_relation_input_output : numeric or None, :math:`r_{in,out}`
        Ratio between the investment variable of the output Flow and the
        investment variable of the input flow. This ratio used to fix the
        flow investments to each other.
        Values < 1 set the input flow lower than the output and > 1 will
        set the input flow higher than the output flow. If None no relation
        will be set:
        :math:`\dot{E}_{in,invest} = \dot{E}_{out,invest} \cdot r_{in,out}`
    initial_storage_level : numeric, :math:`c(-1)`
        The relative storage content in the timestep before the first
        time step of optimization (between 0 and 1).
    balanced : boolean
        Couple storage level of first and last time step.
        (Total inflow and total outflow are balanced.)
    loss_rate : numeric (iterable or scalar)
        The relative loss of the storage content per hour.
    fixed_losses_relative : numeric (iterable or scalar), :math:`\gamma(t)`
        Losses per hour that are independent of the storage content but
        proportional to nominal storage capacity.
    fixed_losses_absolute : numeric (iterable or scalar), :math:`\delta(t)`
        Losses per hour that are independent of storage content and independent
        of nominal storage capacity.
    inflow_conversion_factor : numeric (iterable or scalar), :math:`\eta_i(t)`
        The relative conversion factor, i.e. efficiency associated with the
        inflow of the storage.
    outflow_conversion_factor : numeric (iterable or scalar), :math:`\eta_o(t)`
        see: inflow_conversion_factor
    min_storage_level : numeric (iterable or scalar), :math:`c_{min}(t)`
        The normed minimum storage content as fraction of the
        nominal storage capacity (between 0 and 1).
        To set different values in every time step use a sequence.
    max_storage_level : numeric (iterable or scalar), :math:`c_{max}(t)`
        see: min_storage_level
    investment : :class:`oemof.solph.options.Investment` object
        Object indicating if a nominal_value of the flow is determined by
        the optimization problem. Note: This will refer all attributes to an
        investment variable instead of to the nominal_storage_capacity. The
        nominal_storage_capacity should not be set (or set to None) if an
        investment object is used.
    """

    def __init__(
        self,
        label=None,
        inputs=None,
        outputs=None,
        nominal_storage_capacity=None,
        height_multiplication_factor=None,
        temp_h=None,
        temp_c=None,
        rho=None,
        c=None,
        initial_storage_level=None,
        investment=None,
        invest_relation_input_output=None,
        invest_relation_input_capacity=None,
        invest_relation_output_capacity=None,
        min_storage_level=0,
        max_storage_level=1,
        balanced=True,
        loss_rate=0,
        fixed_losses_relative=0,
        fixed_losses_absolute=0,
        inflow_conversion_factor=1,
        outflow_conversion_factor=1,
        custom_attributes=None,
    ):
        if inputs is None:
            inputs = {}
        if outputs is None:
            outputs = {}
        if custom_attributes is None:
            custom_attributes = {}
        super().__init__(
            label=label,
            inputs=inputs,
            outputs=outputs,
            **custom_attributes,
        )

        self.nominal_storage_capacity = None
        self.height = None
        self.investment = None
        self._invest_group = False
        if isinstance(nominal_storage_capacity, numbers.Real):
            self.nominal_storage_capacity = nominal_storage_capacity
            self.height = (self.nominal_storage_capacity * 3600 * 1e3 / height_multiplication_factor) ** (1 / 3)
        elif isinstance(nominal_storage_capacity, Investment):
            self.investment = nominal_storage_capacity
            self._invest_group = True
        self.initial_storage_level = initial_storage_level
        self.height_multiplication_factor = height_multiplication_factor
        self.temp_h = temp_h
        self.temp_c = temp_c
        self.rho = rho
        self.c = c
        self.balanced = balanced
        self.loss_rate = solph_sequence(loss_rate)
        self.fixed_losses_relative = solph_sequence(fixed_losses_relative)
        self.fixed_losses_absolute = solph_sequence(fixed_losses_absolute)
        self.inflow_conversion_factor = solph_sequence(
            inflow_conversion_factor
        )
        self.outflow_conversion_factor = solph_sequence(
            outflow_conversion_factor
        )
        self.max_storage_level = solph_sequence(max_storage_level)
        self.min_storage_level = solph_sequence(min_storage_level)
        self.investment = investment
        self.invest_relation_input_output = invest_relation_input_output
        self.invest_relation_input_capacity = invest_relation_input_capacity
        self.invest_relation_output_capacity = invest_relation_output_capacity
        self._invest_group = isinstance(self.investment, Investment)

        # Check number of flows.
        self._check_number_of_flows()
        # Check for infeasible parameter combinations
        self._check_infeasible_parameter_combinations()

        # Check attributes for the investment mode.
        if self._invest_group is True:
            self._check_invest_attributes()

    def _set_flows(self):
        for flow in self.inputs.values():
            if (
                self.invest_relation_input_capacity is not None
                and not isinstance(flow.investment, Investment)
            ):
                flow.investment = Investment()
        for flow in self.outputs.values():
            if (
                self.invest_relation_output_capacity is not None
                and not isinstance(flow.investment, Investment)
            ):
                flow.investment = Investment()

    def _check_invest_attributes(self):
        if self.investment and self.nominal_storage_capacity is not None:
            e1 = (
                "If an investment object is defined the invest variable "
                "replaces the nominal_storage_capacity.\n Therefore the "
                "nominal_storage_capacity should be 'None'.\n"
            )
            raise AttributeError(e1)
        if (
            self.invest_relation_input_output is not None
            and self.invest_relation_output_capacity is not None
            and self.invest_relation_input_capacity is not None
        ):
            e2 = (
                "Overdetermined. Three investment object will be coupled"
                "with three constraints. Set one invest relation to 'None'."
            )
            raise AttributeError(e2)
        if (
            self.investment
            and sum(solph_sequence(self.fixed_losses_absolute)) != 0
            and self.investment.existing == 0
            and self.investment.minimum == 0
        ):
            e3 = (
                "With fixed_losses_absolute > 0, either investment.existing "
                "or investment.minimum has to be non-zero."
            )
            raise AttributeError(e3)

        self._set_flows()

    def _check_number_of_flows(self):
        msg = "Only one {0} flow allowed in the GenericStorage {1}."
        check_node_object_for_missing_attribute(self, "inputs")
        check_node_object_for_missing_attribute(self, "outputs")
        if len(self.inputs) > 1:
            raise AttributeError(msg.format("input", self.label))
        if len(self.outputs) > 1:
            raise AttributeError(msg.format("output", self.label))

    def _check_infeasible_parameter_combinations(self):
        """Checks for infeasible parameter combinations and raises error"""
        msg = (
            "initial_storage_level must be greater or equal to "
            "min_storage_level and smaller or equal to "
            "max_storage_level."
        )
        if self.initial_storage_level is not None:
            if (
                self.initial_storage_level < self.min_storage_level[0]
                or self.initial_storage_level > self.max_storage_level[0]
            ):
                raise ValueError(msg)

    def constraint_group(self):
        if self._invest_group is True:
            return GenericInvestmentStorageBlockPit
        else:
            return GenericStorageBlockPit


class GenericStorageBlockPit(ScalarBlock):
    CONSTRAINT_GROUP = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def _create(self, group=None):
        """
        Parameters
        ----------
        group : list
            List containing storage objects.
            e.g. groups=[storage1, storage2,..]
        """
        m = self.parent_block()

        if group is None:
            return None

        i = {n: [i for i in n.inputs][0] for n in group}
        o = {n: [o for o in n.outputs][0] for n in group}

        #  ************* SETS *********************************

        self.STORAGES = Set(initialize=[n for n in group])

        self.STORAGES_BALANCED = Set(
            initialize=[n for n in group if n.balanced is True]
        )

        self.STORAGES_INITITAL_LEVEL = Set(
            initialize=[
                n for n in group if n.initial_storage_level is not None
            ]
        )

        self.STORAGES_WITH_INVEST_FLOW_REL = Set(
            initialize=[
                n for n in group if n.invest_relation_input_output is not None
            ]
        )

        #  ************* VARIABLES *****************************

        def _storage_content_bound_rule(block, n, t):
            """
            Rule definition for bounds of storage_content variable of
            storage n in timestep t.
            """
            bounds = (
                n.nominal_storage_capacity * n.min_storage_level[t],
                n.nominal_storage_capacity * n.max_storage_level[t],
            )
            return bounds

        self.storage_content = Var(
            self.STORAGES, m.TIMEPOINTS, bounds=_storage_content_bound_rule
        )
        self.height = Var(self.STORAGES)

        # set the initial storage content
        for n in group:
            if n.initial_storage_level is not None:
                self.storage_content[n, 0] = (
                    n.initial_storage_level * n.nominal_storage_capacity
                )
                self.storage_content[n, 0].fix()

        #  ************* Constraints ***************************

        def _storage_balance_rule(block, n, t):
            """
            Rule definition for the storage balance of every storage n and
            every timestep.
            """
            expr = 0
            expr += block.storage_content[n, t + 1]
            expr += (
                -block.storage_content[n, t]
                * (1 - n.loss_rate[t] / n.height) ** m.timeincrement[t]
            )
            expr += (
                n.fixed_losses_relative[t] / n.height
                * n.nominal_storage_capacity
                * m.timeincrement[t]
            )
            expr += n.fixed_losses_absolute[t] * m.timeincrement[t]
            expr += (
                -m.flow[i[n], n, t] * n.inflow_conversion_factor[t]
            ) * m.timeincrement[t]
            expr += (
                m.flow[n, o[n], t] / n.outflow_conversion_factor[t]
            ) * m.timeincrement[t]
            return expr == 0

        self.balance = Constraint(
            self.STORAGES, m.TIMESTEPS, rule=_storage_balance_rule
        )

        def _balanced_storage_rule(block, n):
            """
            Storage content of last time step == initial storage content
            if balanced.
            """
            return (
                block.storage_content[n, m.TIMEPOINTS.at(-1)]
                == block.storage_content[n, m.TIMEPOINTS.at(1)]
            )

        self.balanced_cstr = Constraint(
            self.STORAGES_BALANCED, rule=_balanced_storage_rule
        )

        def _power_coupled(block, n):
            """
            Rule definition for constraint to connect the input power
            and output power
            """
            expr = (
                m.InvestmentFlowBlock.invest[n, o[n]]
                + m.flows[n, o[n]].investment.existing
            ) * n.invest_relation_input_output == (
                m.InvestmentFlowBlock.invest[i[n], n]
                + m.flows[i[n], n].investment.existing
            )
            return expr

        self.power_coupled = Constraint(
            self.STORAGES_WITH_INVEST_FLOW_REL, rule=_power_coupled
        )

    def _objective_expression(self):
        r"""
        Objective expression for storages with no investment.
        Note: This adds nothing as variable costs are already
        added in the Block :class:`SimpleFlowBlock`.
        """
        if not hasattr(self, "STORAGES"):
            return 0

        return 0


class GenericInvestmentStorageBlockPit(ScalarBlock):

    CONSTRAINT_GROUP = True

    def __init__(self, *args,**kwargs):
        super().__init__(*args, **kwargs)

    def _create(self, group=None):
        """ """
        m = self.parent_block()
        if group is None:
            return None

        # ########################## SETS #####################################

        self.INVESTSTORAGES = Set(initialize=[n for n in group])

        self.CONVEX_INVESTSTORAGES = Set(
            initialize=[n for n in group if n.investment.nonconvex is False]
        )

        self.NON_CONVEX_INVESTSTORAGES = Set(
            initialize=[n for n in group if n.investment.nonconvex is True]
        )

        self.INVESTSTORAGES_BALANCED = Set(
            initialize=[n for n in group if n.balanced is True]
        )

        self.INVESTSTORAGES_NO_INIT_CONTENT = Set(
            initialize=[n for n in group if n.initial_storage_level is None]
        )

        self.INVESTSTORAGES_INIT_CONTENT = Set(
            initialize=[
                n for n in group if n.initial_storage_level is not None
            ]
        )

        self.INVEST_REL_CAP_IN = Set(
            initialize=[
                n
                for n in group
                if n.invest_relation_input_capacity is not None
            ]
        )

        self.INVEST_REL_CAP_OUT = Set(
            initialize=[
                n
                for n in group
                if n.invest_relation_output_capacity is not None
            ]
        )

        self.INVEST_REL_IN_OUT = Set(
            initialize=[
                n for n in group if n.invest_relation_input_output is not None
            ]
        )

        # The storage content is a non-negative variable, therefore it makes no
        # sense to create an additional constraint if the lower bound is zero
        # for all time steps.
        self.MIN_INVESTSTORAGES = Set(
            initialize=[
                n
                for n in group
                if sum([n.min_storage_level[t] for t in m.TIMESTEPS]) > 0
            ]
        )

        # ######################### Variables  ################################
        self.storage_content = Var(
            self.INVESTSTORAGES, m.TIMESTEPS, within=NonNegativeReals
        )

        self.storage_height = Var(self.INVESTSTORAGES, within=NonNegativeReals)

        self.storage_height_reciprocal = Var(self.INVESTSTORAGES, within=NonNegativeReals)

        def _storage_investvar_bound_rule(block, n):
            """
            Rule definition to bound the invested storage capacity `invest`.
            """
            if n in self.CONVEX_INVESTSTORAGES:
                return n.investment.minimum, n.investment.maximum
            elif n in self.NON_CONVEX_INVESTSTORAGES:
                return 0, n.investment.maximum

        self.invest = Var(
            self.INVESTSTORAGES,
            within=NonNegativeReals,
            bounds=_storage_investvar_bound_rule,
        )

        self.init_content = Var(self.INVESTSTORAGES, within=NonNegativeReals)

        # create status variable for a non-convex investment storage
        self.invest_status = Var(self.NON_CONVEX_INVESTSTORAGES, within=Binary)

        # ######################### CONSTRAINTS ###############################
        i = {n: [i for i in n.inputs][0] for n in group}
        o = {n: [o for o in n.outputs][0] for n in group}

        reduced_timesteps = [x for x in m.TIMESTEPS if x > 0]

        def _inv_storage_init_content_max_rule(block, n):
            """Constraint for a variable initial storage capacity."""
            return (
                block.init_content[n]
                <= n.investment.existing + block.invest[n]
            )

        self.init_content_limit = Constraint(
            self.INVESTSTORAGES_NO_INIT_CONTENT,
            rule=_inv_storage_init_content_max_rule,
        )

        def _inv_storage_init_content_fix_rule(block, n):
            """Constraint for a fixed initial storage capacity."""
            return block.init_content[n] == n.initial_storage_level * (
                n.investment.existing + block.invest[n]
            )

        self.init_content_fix = Constraint(
            self.INVESTSTORAGES_INIT_CONTENT,
            rule=_inv_storage_init_content_fix_rule,
        )

        def _storage_balance_first_rule(block, n):
            """
            Rule definition for the storage balance of every storage n for the
            first time step.
            """
            expr = 0
            expr += block.storage_content[n, 0]
            expr += (
                -block.init_content[n]
                * (1 - n.loss_rate[0] * block.storage_height_reciprocal[n]) * m.timeincrement[0]
            )
            expr += (
                n.fixed_losses_relative[0]
                * block.storage_height_reciprocal[n]
                * (n.investment.existing + self.invest[n])
                * m.timeincrement[0]
            )
            expr += n.fixed_losses_absolute[0] * block.storage_height_reciprocal[n] * m.timeincrement[0]
            expr += (
                -m.flow[i[n], n, 0] * n.inflow_conversion_factor[0]
            ) * m.timeincrement[0]
            expr += (
                m.flow[n, o[n], 0] / n.outflow_conversion_factor[0]
            ) * m.timeincrement[0]
            return expr == 0

        self.balance_first = Constraint(
            self.INVESTSTORAGES, rule=_storage_balance_first_rule
        )

        def _storage_balance_rule(block, n, t):
            """
            Rule definition for the storage balance of every storage n for the
            every time step but the first.
            """
            expr = 0
            expr += block.storage_content[n, t]
            expr += (
                -block.storage_content[n, t - 1]
                * (1 - n.loss_rate[t] * block.storage_height_reciprocal[n]) * m.timeincrement[t]
            )
            expr += (
                n.fixed_losses_relative[t]
                * block.storage_height_reciprocal[n]
                * (n.investment.existing + self.invest[n])
                * m.timeincrement[t]
            )
            expr += n.fixed_losses_absolute[t] * block.storage_height_reciprocal[n] * m.timeincrement[t]
            expr += (
                -m.flow[i[n], n, t] * n.inflow_conversion_factor[t]
            ) * m.timeincrement[t]
            expr += (
                m.flow[n, o[n], t] / n.outflow_conversion_factor[t]
            ) * m.timeincrement[t]
            return expr == 0

        self.balance = Constraint(
            self.INVESTSTORAGES, reduced_timesteps, rule=_storage_balance_rule
        )

        def _balanced_storage_rule(block, n):
            return (
                block.storage_content[n, m.TIMESTEPS.at(-1)]
                == block.init_content[n]
            )

        self.balanced_cstr = Constraint(
            self.INVESTSTORAGES_BALANCED, rule=_balanced_storage_rule
        )

        def _storage_height_capacity_connection_rule(block, n):
            if n.investment.maximum * 3600 / ((n.temp_h-n.temp_c) * n.rho * n.c) <= 30000000:  # Litres
                return (
                    block.storage_height[n] == (0.000127839/(n.temp_h-n.temp_c)) *
                    (n.investment.existing + self.invest[n]) + 4.247933
                )
            else:
                return (
                    block.storage_height[n] == (0.0000357789/(n.temp_h - n.temp_c)) *
                    (n.investment.existing + self.invest[n]) + 8.1381764
                )

        self.height_cstr = Constraint(
            self.INVESTSTORAGES, rule=_storage_height_capacity_connection_rule
        )

        def _storage_height_reciprocal_rule(block, n):
            return block.storage_height_reciprocal[n] * block.storage_height[n] == 1

        self.storage_height_constraints = Constraint(
            self.INVESTSTORAGES, rule=_storage_height_reciprocal_rule
        )

        def _power_coupled(block, n):
            """
            Rule definition for constraint to connect the input power
            and output power
            """
            expr = (
                m.InvestmentFlowBlock.invest[n, o[n]]
                + m.flows[n, o[n]].investment.existing
            ) * n.invest_relation_input_output == (
                m.InvestmentFlowBlock.invest[i[n], n]
                + m.flows[i[n], n].investment.existing
            )
            return expr

        self.power_coupled = Constraint(
            self.INVEST_REL_IN_OUT, rule=_power_coupled
        )

        def _storage_capacity_inflow_invest_rule(block, n):
            """
            Rule definition of constraint connecting the inflow
            `InvestmentFlowBlock.invest of storage with invested capacity
            `invest` by nominal_storage_capacity__inflow_ratio
            """
            expr = (
                m.InvestmentFlowBlock.invest[i[n], n]
                + m.flows[i[n], n].investment.existing
            ) == (
                n.investment.existing + self.invest[n]
            ) * n.invest_relation_input_capacity
            return expr

        self.storage_capacity_inflow = Constraint(
            self.INVEST_REL_CAP_IN, rule=_storage_capacity_inflow_invest_rule
        )

        def _storage_capacity_outflow_invest_rule(block, n):
            """
            Rule definition of constraint connecting outflow
            `InvestmentFlowBlock.invest` of storage and invested capacity
            `invest` by nominal_storage_capacity__outflow_ratio
            """
            expr = (
                m.InvestmentFlowBlock.invest[n, o[n]]
                + m.flows[n, o[n]].investment.existing
            ) == (
                n.investment.existing + self.invest[n]
            ) * n.invest_relation_output_capacity
            return expr

        self.storage_capacity_outflow = Constraint(
            self.INVEST_REL_CAP_OUT, rule=_storage_capacity_outflow_invest_rule
        )

        def _max_storage_content_invest_rule(block, n, t):
            """
            Rule definition for upper bound constraint for the
            storage content.
            """
            expr = (
                self.storage_content[n, t]
                <= (n.investment.existing + self.invest[n])
                * n.max_storage_level[t]
            )
            return expr

        self.max_storage_content = Constraint(
            self.INVESTSTORAGES,
            m.TIMESTEPS,
            rule=_max_storage_content_invest_rule,
        )

        def _min_storage_content_invest_rule(block, n, t):
            """
            Rule definition of lower bound constraint for the
            storage content.
            """
            expr = (
                self.storage_content[n, t]
                >= (n.investment.existing + self.invest[n])
                * n.min_storage_level[t]
            )
            return expr

        # Set the lower bound of the storage content if the attribute exists
        self.min_storage_content = Constraint(
            self.MIN_INVESTSTORAGES,
            m.TIMESTEPS,
            rule=_min_storage_content_invest_rule,
        )

        def maximum_invest_limit(block, n):
            """
            Constraint for the maximal investment in non convex investment
            storage.
            """
            return (
                n.investment.maximum * self.invest_status[n] - self.invest[n]
            ) >= 0

        self.limit_max = Constraint(
            self.NON_CONVEX_INVESTSTORAGES, rule=maximum_invest_limit
        )

        def smallest_invest(block, n):
            """
            Constraint for the minimal investment in non convex investment
            storage if the invest is greater than 0. So the invest variable
            can be either 0 or greater than the minimum.
            """
            return (
                self.invest[n] - (n.investment.minimum * self.invest_status[n])
                >= 0
            )

        self.limit_min = Constraint(
            self.NON_CONVEX_INVESTSTORAGES, rule=smallest_invest
        )

    def _objective_expression(self):
        """Objective expression with fixed and investement costs."""
        if not hasattr(self, "INVESTSTORAGES"):
            return 0

        investment_costs = 0

        for n in self.CONVEX_INVESTSTORAGES:
            investment_costs += self.invest[n] * n.investment.ep_costs
        for n in self.NON_CONVEX_INVESTSTORAGES:
            investment_costs += (
                self.invest[n] * n.investment.ep_costs
                + self.invest_status[n] * n.investment.offset
            )
        self.investment_costs = Expression(expr=investment_costs)

        return investment_costs
