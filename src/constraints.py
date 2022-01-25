from pyomo import environ as pyo
from oemof.solph.plumbing import sequence
from math import pi

def dailySHStorageConstraint(om):
    """
    Function to limit the SH storage capacity to 2 days
    :param om: model
    :return:
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

def environmentalImpactlimit(om, keyword1, keyword2, limit=None):
    """
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

    for x in om.GenericInvestmentStorageBlock.INVESTSTORAGES:
        if hasattr(x.investment, keyword2):
            storageCapacityDict[x] = om.GenericInvestmentStorageBlock.invest[x]

    envImpact = "totalEnvironmentalImpact"

    setattr(
        om,
        envImpact,
        pyo.Expression(
            expr=sum(
                om.flow[inflow, outflow, t]
                * om.timeincrement[t]
                * sequence(getattr(flows[inflow, outflow], keyword1))[t]
                for (inflow, outflow) in flows
                for t in om.TIMESTEPS
            )
            + sum(om.InvestmentFlow.invest[inflow, outflow] * getattr(transformerFlowCapacityDict[inflow, outflow], keyword2)
            for (inflow, outflow) in transformerFlowCapacityDict)
            + sum(om.GenericInvestmentStorageBlock.invest[x] * getattr(x.investment, keyword2) for x in storageCapacityDict)
        ),
    )
    setattr(
        om,
        envImpact + "_constraint",
        pyo.Constraint(expr=(getattr(om, envImpact) <= limit)),
    )
    return om, flows, transformerFlowCapacityDict, storageCapacityDict
