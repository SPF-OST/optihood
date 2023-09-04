from pyomo import environ as pyo
from oemof.solph.plumbing import sequence
from math import pi

def dailySHStorageConstraint(om):
    """
    Function to limit the SH storage capacity to 2 days
    :param om: optimization model
    :return: om: optimization model
    """
    for s in om.NODES:
        if "shStorage" in s.label:
            constr = s.label.replace("__Building","") + "_constraint_"
            for t in om.TIMESTEPS:
                if t % 48 == 0 and t!=0:
                    setattr(
                        om,
                        constr + str(t),
                        pyo.Constraint(expr=(om.GenericInvestmentStorageBlock.storage_content[s, t] == 0)),
                    )

    return om

def connectInvestmentRule(om):
    """Constraint to equate the investment objects of all the output flows of a Link"""

    elLinkOutputFlows = [(i, o) for (i, o) in om.flows if (i.label == "electricityLink" or i.label == "elLink")]
    shLinkOutputFlows = [(i, o) for (i, o) in om.flows if i.label == "shLink"]
    dhwLinkOutputFlows = [(i, o) for (i, o) in om.flows if i.label == "dhwLink"]

    if elLinkOutputFlows:
        first = om.InvestmentFlow.invest[next(iter(elLinkOutputFlows))]
        for (i, o) in elLinkOutputFlows:
            expr = (first == om.InvestmentFlow.invest[i, o])
            setattr(
                om,
                "elLinkConstr_" + o.label,
                pyo.Constraint(expr=expr),
            )

    if shLinkOutputFlows:
        first = om.InvestmentFlow.invest[next(iter(shLinkOutputFlows))]
        for (i, o) in shLinkOutputFlows:
            expr = (first == om.InvestmentFlow.invest[i, o])
            setattr(
                om,
                "shLinkConstr_" + o.label,
                pyo.Constraint(expr=expr),
            )

    if dhwLinkOutputFlows:
        first = om.InvestmentFlow.invest[next(iter(dhwLinkOutputFlows))]
        for (i, o) in dhwLinkOutputFlows:
            expr = (first == om.InvestmentFlow.invest[i, o])
            setattr(
                om,
                "dhwLinkConstr_" + o.label,
                pyo.Constraint(expr=expr),
            )

    return om


def environmentalImpactlimit(om, keyword1, keyword2, limit=None):
    """
    Based on: oemof.solph.constraints.emission_limit
    Function to limit the environmental impacts during the multi-objective optimization
    :param om: model
    :param keyword1: keyword for environmental impacts per flow, placed in a solph.Flow() object
    :param keyword2: keyword for environmental impacts per capacity installed, placed in a solph.Investment() object
    :param limit: limit not to be reached
    :return:
    """
    flows = {}
    transformerFlowCapacityDict = {}
    storageCapacityDict = {}
    for (i, o) in om.flows:
        if hasattr(om.flows[i, o], keyword1):
            flows[(i, o)] = om.flows[i, o]
        if hasattr(om.flows[i, o].investment, keyword2):
            transformerFlowCapacityDict[(i, o)] = om.flows[i, o].investment

    if hasattr(om, 'GenericInvestmentStorageBlock'):
        for x in om.GenericInvestmentStorageBlock.INVESTSTORAGES:
            if hasattr(x.investment, keyword2):
                storageCapacityDict[x] = om.GenericInvestmentStorageBlock.invest[x]

    envImpact = "totalEnvironmentalImpact"

    setattr(
        om,
        envImpact,
        pyo.Expression(
            expr=sum(
            # Environmental inpact of input flows
                om.flow[inflow, outflow, t]
                * om.timeincrement[t]
                * sequence(getattr(flows[inflow, outflow], keyword1))[t]
                for (inflow, outflow) in flows
                for t in om.TIMESTEPS
            )
            # fix Environmental impact per transformer capacity
            + sum(om.InvestmentFlow.invest[inflow, outflow] * getattr(transformerFlowCapacityDict[inflow, outflow], keyword2)
            for (inflow, outflow) in transformerFlowCapacityDict)
            # fix Environmental impact per storage capacity
            + sum(om.GenericInvestmentStorageBlock.invest[x] * getattr(x.investment, keyword2) for x in storageCapacityDict)
        ),
    )
    setattr(
        om,
        envImpact + "_constraint",
        pyo.Constraint(expr=(getattr(om, envImpact) <= limit)),
    )
    return om, flows, transformerFlowCapacityDict, storageCapacityDict


def roof_area_limit(model, keyword1, keyword2, nb):
    r"""
    Based on: oemof.solph.constraints.additional_investment_flow_limit
    Constraint to limit the capacity of solar panels installed considering the roof area available
    Parameters
    ----------
    model : oemof.solph.Model
        Model to which constraints are added.
    keyword1 : attribute to consider
        Coefficient representing the area used by one unit of capacity of a solar panel
    keyword2 : attribute to consider
        Total roof area available for panels.
    nb : int
        Number of buildings in the neighbourhood

    Note
    ----
    The Investment attribute of the considered (Investment-)flows requires an
    attribute named like keyword!
    """

    for b in range(1, nb+1):
        limit = 0
        invest_flows = {}
        for (i, o) in model.flows:
            if str(b) in str(i):
                if hasattr(model.flows[i, o].investment, keyword1):
                    invest_flows[(i, o)] = model.flows[i, o].investment
                    limit = getattr(model.flows[i, o].investment, keyword2)

        limit_name = "invest_limit_" + keyword1 + "_building" + str(b)

        setattr(
            model,
            limit_name,
            pyo.Expression(
                expr=sum(
                    model.InvestmentFlow.invest[inflow, outflow]
                    * getattr(invest_flows[inflow, outflow], keyword1)
                    for (inflow, outflow) in invest_flows
                )
            ),
        )

        setattr(
            model,
            limit_name + "_constraint",
            pyo.Constraint(expr=(getattr(model, limit_name) <= limit)),
        )


    return model

def electricRodCapacityConstaint(om, numBuildings):
    """constraint to set the total capacity of electric rod equal to sum of total capacity selected for HP"""
    electricRodInputFlows = [(i, o) for (i, o) in om.flows if ("ElectricRod" in o.label)]
    airHeatPumpInputFlows = [(i, o) for (i, o) in om.flows if ("HP" in o.label and "CHP" not in o.label and "GWHP" not in o.label)]
    groundHeatPumpInputFlows = [(i, o) for (i, o) in om.flows if ("GWHP" in o.label and not any([c.isdigit() for c in o.label.split("__")[0]]))]
    groundHeatPumpOutFlows = [(i, o) for (i, o) in om.flows if ("GWHP" in i.label and any([c.isdigit() for c in i.label.split("__")[0]]))]     # for splitted GSHPs

    elRodCapacityTotal = 0
    airHeatPumpCapacityTotal = 0
    groundHeatPumpCapacityTotal = 0

    for b in range(1,numBuildings+1):
        elRodCapacity = [om.InvestmentFlow.invest[i, o] for (i, o) in electricRodInputFlows if ((f'__Building{b}') in o.label)]
        airHeatPumpCapacity = [om.InvestmentFlow.invest[i, o] for (i, o) in airHeatPumpInputFlows if ((f'__Building{b}') in o.label)]
        if groundHeatPumpInputFlows:
            groundHeatPumpCapacity = [om.InvestmentFlow.invest[i, o] for (i, o) in groundHeatPumpInputFlows if ((f'__Building{b}') in o.label)]
        else:
            groundHeatPumpCapacity = [om.InvestmentFlow.invest[i, o] for (i, o) in groundHeatPumpOutFlows if ((f'__Building{b}') in i.label)]
        if elRodCapacity:
            elRodCapacity = elRodCapacity[0]
            airHeatPumpCapacity = airHeatPumpCapacity[0] if airHeatPumpCapacity else 0
            if groundHeatPumpInputFlows:
                groundHeatPumpCapacity = groundHeatPumpCapacity[0] if groundHeatPumpCapacity else 0
            else:
                groundHeatPumpCapacity = groundHeatPumpCapacity[0] + groundHeatPumpCapacity[1] if groundHeatPumpCapacity else 0
            elRodCapacityTotal = elRodCapacityTotal + elRodCapacity
            airHeatPumpCapacityTotal = airHeatPumpCapacityTotal + airHeatPumpCapacity
            groundHeatPumpCapacityTotal = groundHeatPumpCapacityTotal + groundHeatPumpCapacity

    expr = (elRodCapacityTotal <= (airHeatPumpCapacityTotal + groundHeatPumpCapacityTotal))
    setattr(
        om,
        "electricRodSizeConstr",
        pyo.Constraint(expr=expr),
    )
    return om

def totalPVCapacityConstraint(om, numBuildings):
    pvOutFlows = [(i, o) for (i, o) in om.flows if ("pv" in i.label)]
    pvCapacityTotal = 0
    for b in range(1,numBuildings+1):
        pvCapacity = [om.InvestmentFlow.invest[i, o] for (i, o) in pvOutFlows if ((f'__Building{b}') in o.label)]
        if pvCapacity:
            pvCapacity = pvCapacity[0]
            pvCapacityTotal = pvCapacityTotal + pvCapacity
    expr = (pvCapacityTotal <= 205)
    setattr(
        om,
        "PVSizeConstr",
        pyo.Constraint(expr=expr),
    )
    return om