

def get_dhn_pipe_investment_objects(om):
    pipe_capacity_dict = {}
    for (i, o) in om.flows:
        if "pipe" in i.label:
            pipe_capacity_dict[(i, o)] = om.flows[i, o].investment
    return pipe_capacity_dict


def calculate_transformer_capacities(om, investment_objects_dict):
    capacities_invested = {}
    for inflow, outflow in investment_objects_dict:
        index = (str(inflow), str(outflow))
        if (inflow, outflow) in om.InvestmentFlowBlock.invest:
            capacities_invested[index] = om.InvestmentFlowBlock.invest[inflow, outflow].value
        else:
            capacities_invested[index] = om.InvestNonConvexFlowBlock.invest[inflow, outflow].value

    return capacities_invested

def calculate_storage_capacities(om, investment_objects_dict):
    capacities_invested_storages = {}
    storageList = []
    for x in investment_objects_dict:
        index = str(x)
        if x in storageList:  # useful when we want to implement two or more storage units of the same type
            capacities_invested_storages[index] = capacities_invested_storages[index] + \
                                                om.GenericInvestmentStorageBlock.invest[x].value
        else:
            capacities_invested_storages[str(x)] = om.GenericInvestmentStorageBlock.invest[x].value
        storageList.append(x)

    return capacities_invested_storages

def update_for_multi_temp_storage(capacities_invested_storages, investment_object_dict, op_temps, no_buildings):
    removeKeysList = []
    if any("thermalStorage" in key for key in capacities_invested_storages):
        for b in range(no_buildings):
            buildingLabel = "Building" + str(b + 1)
            invest = 0
            for layer in op_temps:
                if f"thermalStorage{int(layer)}__" + buildingLabel in capacities_invested_storages:
                    invest += capacities_invested_storages[f"thermalStorage{int(layer)}__" + buildingLabel]
                    removeKeysList.append(f"thermalStorage{int(layer)}__" + buildingLabel)
            if invest > 0:
                capacities_invested_storages["thermalStorage__" + buildingLabel] = invest
                investment_object_dict["thermalStorage__" + buildingLabel] = invest
                for k in removeKeysList:
                    capacities_invested_storages.pop(k, None)

    return capacities_invested_storages, investment_object_dict, removeKeysList