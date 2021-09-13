from pyomo import environ as pyo
from oemof.solph.plumbing import sequence
from math import pi

def moo_limit(om, keyword1, keyword2, limit=None):
    """
    Function to limit the environmental impacts during the multi-objective optimization
    :param om: model
    :param keyword1: keyword for environmental impacts per flow, placed in a solph.Flow() object
    :param keyword2: keyword for environmental impacts per capacity installed, placed in a solph.Investment() object
    :param limit: limit not to be reached
    :return:
    """
    flows = {}
    capa = {}
    capa_s = {}
    for (i, o) in om.flows:
        if hasattr(om.flows[i, o], keyword1):
            flows[(i, o)] = om.flows[i, o]
        if hasattr(om.flows[i, o].investment, keyword2):
            capa[(i, o)] = om.flows[i, o].investment

    for x in om.GenericInvestmentStorageBlock.INVESTSTORAGES:
        if hasattr(x.investment, keyword2):
            capa_s[x] = om.GenericInvestmentStorageBlock.invest[x]

    limit_name = "integral_limit_" + keyword1 + "_" + keyword2

    setattr(
        om,
        limit_name,
        pyo.Expression(
            expr=sum(
                om.flow[inflow, outflow, t]
                * om.timeincrement[t]
                * sequence(getattr(flows[inflow, outflow], keyword1))[t]
                for (inflow, outflow) in flows
                for t in om.TIMESTEPS
            )
            + sum(om.InvestmentFlow.invest[inflow, outflow] * getattr(capa[inflow, outflow], keyword2)
            for (inflow, outflow) in capa)
            + sum(om.GenericInvestmentStorageBlock.invest[x] * getattr(x.investment, keyword2) for x in capa_s)
        ),
    )
    setattr(
        om,
        limit_name + "_constraint",
        pyo.Constraint(expr=(getattr(om, limit_name) <= limit)),
    )
    return om, flows, capa, capa_s
