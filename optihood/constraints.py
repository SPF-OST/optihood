from pyomo import environ as pyo
from optihood._helpers import *
from oemof.solph._plumbing import sequence
from math import pi
from oemof.solph.constraints.flow_count_limit import limit_active_flow_count

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

def sharedStorageCapacityConstraintBuilding1(om):
    storageCapacityDict = {}
    if hasattr(om, 'GenericInvestmentStorageBlock'):
        for x in om.GenericInvestmentStorageBlock.INVESTSTORAGES:
            if 'dhwStorage' in x.label and x.label.endswith("Building1"):
                conv_factor = 4.186 * (60 - 15) / 3600                      # L to kWh conversion factor
            elif 'shStorage' in x.label and x.label.endswith("Building1"):
                conv_factor = 4.186 * (35 - 25) / 3600
            if x.label.endswith("Building1"):
                storageCapacityDict[x] = om.GenericInvestmentStorageBlock.invest[x] / conv_factor
        totalCapacity = sum(storageCapacityDict[x] for x in storageCapacityDict)
        capacity = 6440            # 6440 L
        setattr(
            om,
            "SharedStorage_maxConstraint",
            pyo.Constraint(expr=(totalCapacity <= capacity)),
        )

        setattr(
            om,
            "SharedStorage_minConstraint",
            pyo.Constraint(expr=(totalCapacity >= capacity)),
        )

    return om


def peakObjectiveConstraint(om):
    peakObjectiveInputFlow1 = [(i, o) for (i, o) in om.flows if "peak35bus" in i.label and "peakObjective" in o.label]
    peakObjectiveInputFlow2 = [(i, o) for (i, o) in om.flows if "peak65bus" in i.label and "peakObjective" in o.label]
    flowMatch1 = [(i, o) for (i, o) in om.flows if "spaceHeatingLinkBus" in o.label]
    flowMatch2 = [(i, o) for (i, o) in om.flows if "domesticHotWaterLinkBus" in o.label]

    for t in om.TIMESTEPS:
        lhs_1 = om.flow[peakObjectiveInputFlow1[0][0], peakObjectiveInputFlow1[0][1], t]
        rhs_1 = om.flow[flowMatch1[0][0], flowMatch1[0][1], t]
        lhs_2 = om.flow[peakObjectiveInputFlow2[0][0], peakObjectiveInputFlow2[0][1], t]
        rhs_2 = om.flow[flowMatch2[0][0], flowMatch2[0][1], t]
        setattr(
            om,
            f"peakflow1_{t}",
            pyo.Constraint(expr=(lhs_1 == rhs_1)),
        )
        setattr(
            om,
            f"peakflow2_{t}",
            pyo.Constraint(expr=(lhs_2 == rhs_2)),
        )
    return om

def peakObjectiveConstraint_to_be_merged(om):
    """
    Eventually this constraint would be merged with the peakObjectiveConstraint
    """
    peakObjectiveInputFlow = [(i, o) for (i, o) in om.flows if "peak65bus" in i.label and "peakObjective" in o.label]
    flowMatch = [(i, o) for (i, o) in om.flows if "heatingLinkBus" in o.label]

    for t in om.TIMESTEPS:
        lhs = om.flow[peakObjectiveInputFlow[0][0], peakObjectiveInputFlow[0][1], t]
        rhs = sum(om.flow[f[0], f[1], t] for f in flowMatch)
        setattr(
            om,
            f"peakflow_{t}",
            pyo.Constraint(expr=(lhs == rhs)),
        )
    return om


def multiTemperatureStorageCapacityConstaint(om, storageNodes):
    """Constraint on thermal storage capacity when multiple temperature levels exist"""
    storageCapacityDict = {}
    storageMaxCapacity = {}
    storageMinCapacity = {}
    #storageBaseInvestment = {}
    for x in om.GenericInvestmentStorageBlock.INVESTSTORAGES:
        if "thermalStorage" in x.label:
            if x.label.split("__")[1] not in storageCapacityDict:
                storageCapacityDict[x.label.split("__")[1]] = [x]
                storageMaxCapacity[x.label.split("__")[1]] = [s.capacityMax for s in storageNodes if x.label.split("__")[1] in s.label][0]
                storageMinCapacity[x.label.split("__")[1]] = [s.capacityMin for s in storageNodes if x.label.split("__")[1] in s.label][0]
                #storageBaseInvestment[x.label.split("__")[1]] = [s.baseInvestment for s in storageNodes if x.label.split("__")[1] in s.label][0]
            else:
                storageCapacityDict[x.label.split("__")[1]].append(x)

    for building in storageCapacityDict:
        storageCapacity =sum(om.GenericInvestmentStorageBlock.invest[x] for x in storageCapacityDict[building])
        setattr(
            om,
             "ThermalStorage_maxConstraint" + building[8:],
            pyo.Constraint(expr=(storageCapacity <= storageMaxCapacity[building])),
        )
        setattr(
            om,
            "ThermalStorage_minConstraint" + building[8:],
            pyo.Constraint(expr=(storageCapacity >= storageMinCapacity[building])),
        )
        # if storage is selected then add offset to objective function
        """if optType == "costs":
            offsetThermalStorage = storageBaseInvestment[building]*storageCapacity         #*(storageCapacity>0.001)
            om.objective += offsetThermalStorage"""

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
    transformerFlowCapacityDictNonConvex = {}
    transformerFlowCapacityDictConvex = {}
    storageCapacityDict = {}
    for (i, o) in om.flows:
        if hasattr(om.flows[i, o], keyword1):
            flows[(i, o)] = om.flows[i, o]
        if hasattr(om.flows[i, o].investment, keyword2):
            if om.flows[i, o].nonconvex is not None:
                transformerFlowCapacityDictNonConvex[(i, o)] = om.flows[i, o].investment
            else:
                transformerFlowCapacityDictConvex[(i, o)] = om.flows[i, o].investment

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
                 # fix Environmental impact per transformer capacity from convex and nonconvex flows
                 + sum(om.InvestmentFlowBlock.invest[inflow, outflow] * getattr(
                transformerFlowCapacityDictConvex[inflow, outflow], keyword2)
                       for (inflow, outflow) in transformerFlowCapacityDictConvex)
                 + sum(om.InvestNonConvexFlowBlock.invest[inflow, outflow] * getattr(
                transformerFlowCapacityDictNonConvex[inflow, outflow], keyword2)
                       for (inflow, outflow) in transformerFlowCapacityDictNonConvex)
                 # fix Environmental impact per storage capacity
                 + sum(om.GenericInvestmentStorageBlock.invest[x] * getattr(x.investment, keyword2) for x in
                       storageCapacityDict)
        ),
    )
    setattr(
        om,
        envImpact + "_constraint",
        pyo.Constraint(expr=(getattr(om, envImpact) <= limit)),
    )

    transformerFlowCapacityDictNonConvex.update(transformerFlowCapacityDictConvex)

    return om, flows, transformerFlowCapacityDictNonConvex, storageCapacityDict


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

def PVTElectricalThermalCapacityConstraint(om, numBuildings):
    pvtElOutFlows = [(i, o) for (i, o) in om.flows if ("elSource_pvt" in i.label)]
    pvtShOutFlows = [(i, o) for (i, o) in om.flows if ("heatSource_SHpvt" in i.label)]
    pvtDhwOutFlows = [(i, o) for (i, o) in om.flows if ("heatSource_DHWpvt" in i.label)]
    for b in range(1, numBuildings + 1):
        elCapacity = [om.InvestmentFlow.invest[i, o] for (i, o) in pvtElOutFlows if ((f'__Building{b}') in o.label)]
        shCapacity = [om.InvestmentFlow.invest[i, o] for (i, o) in pvtShOutFlows if ((f'__Building{b}') in o.label)]
        dhwCapacity = [om.InvestmentFlow.invest[i, o] for (i, o) in pvtDhwOutFlows if ((f'__Building{b}') in o.label)]
        areaUnitCapEl = [getattr(om.flows[i, o].investment, 'space_el') for (i, o) in pvtElOutFlows if ((f'__Building{b}') in o.label)]
        areaUnitCapSh = [getattr(om.flows[i, o].investment, 'space') for (i, o) in pvtShOutFlows if ((f'__Building{b}') in o.label)]
        if elCapacity or shCapacity:
            elCapacity = elCapacity[0]
            shCapacity = shCapacity[0]
            dhwCapacity = dhwCapacity[0]
            areaUnitCapEl = areaUnitCapEl[0]
            areaUnitCapSh = areaUnitCapSh[0]
            expr = (elCapacity*areaUnitCapEl == shCapacity*areaUnitCapSh)
            setattr(
                om,
                "PVTSizeConstrElTh_B"+str(b),
                pyo.Constraint(expr=expr),
            )
            expr = (dhwCapacity == shCapacity)
            setattr(
                om,
                "PVTSizeConstrDhwSh_B" + str(b),
                pyo.Constraint(expr=expr),
            )
    return om