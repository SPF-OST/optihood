def labelDictGenerator(numBuildings, labels, optimType, mergedLinks):
    base = {"electricityLink":"elLink", "shLink":"shLink", "dhwLink":"dhwLink", "naturalGasResource":"natGas", "naturalGasBus":"natGas", "gridBus":"grid", "pv":"pv", "electricityResource":"grid", "gridElectricity":"grid", "GasBoiler":"gasBoiler",
    "CHP":"CHP", "electricityBus":"prodEl", "electricityProdBus":"localEl", "producedElectricity":"prodEl", "electricitySource":"localEl", "electricalStorage":"Bat", "excesselectricityBus":"exEl",
    "excessshDemandBus":"exSh", "electricityInBus":"usedEl", "HP":"HP", "GWHP":"GWHP", "GWHP35":"GWHP35", "GWHP60":"GWHP60", "solarCollector":"solar", "solarConnectBus":"solar","heat_solarCollector":"solar", "excess_solarheat":"exSolar",
    "shSource":"prodSH","shSourceBus":"prodSH", "spaceHeatingBus":"shBus", "spaceHeating":"shBus", "shStorage":"shStor", "shDemandBus":"shBus", "dhwStorageBus":"dhwStor", "dhwStorage":"dhwStor", "domesticHotWaterBus":"dhwBus",
    "domesticHotWater":"dhwBus", "dhwDemandBus":"dhwBus", "electricityDemand":"Q_el", "emobilityDemand":"Q_mob", "spaceHeatingDemand":"Q_sh", "domesticHotWaterDemand":"Q_dhw", "excessshSourceBus":"exSh",
    "ElectricRod":"ElectricRod"}
    if not mergedLinks and optimType == 'group':
        base['electricityInBus'] = "usedEl"
        base['spaceHeatingBus'] = "usedSH"
        base['domesticHotWaterBus'] = "prodDHW"
        if labels != 'default':
            base["electricityInBus"] = labels["usedEl"]
            base["spaceHeatingBus"] = labels["usedSH"]
            base["spaceHeating"] = labels["shBus"]
            base["shDemandBus"] = labels["shBus"]
            base["domesticHotWaterBus"] = labels["prodDHW"]
            base['domesticHotWater'] = labels["dhwBus"]
            base['dhwDemandBus'] = labels["dhwBus"]
    if labels != 'default':
        if "elBus" in labels and ((mergedLinks and optimType=='group') or optimType=='indiv'): base["electricityLink"] = labels["elBus"]
        if "elBus" in labels and not mergedLinks and optimType=='group': base["electricityLink"] = labels["elBus"] + " Link"
        if "shBus" in labels and ((mergedLinks and optimType=='group') or optimType=='indiv'): base["shLink"] = labels["shBus"]
        if "shBus" in labels and not mergedLinks and optimType=='group': base["shLink"] = labels["shBus"] + " Link"
        if "dhwBus" in labels and ((mergedLinks and optimType=='group') or optimType=='indiv'): base["dhwLink"] = labels["dhwBus"]
        if "dhwBus" in labels and not mergedLinks and optimType=='group': base["dhwLink"] = labels["dhwBus"] + " Link"
        if "naturalGas" in labels:
            base["naturalGasResource"] = labels["naturalGas"]
            base["naturalGasBus"] = labels["naturalGas"]
        if "grid" in labels:
            base["gridBus"] = labels["grid"]
            base["electricityResource"] = labels["grid"]
            base["gridElectricity"] = labels["grid"]
        if "pv" in labels: base["pv"]=labels["pv"]
        if "gasBoiler" in labels: base["GasBoiler"]=labels["gasBoiler"]
        if "CHP" in labels:base["CHP"]=labels["CHP"]
        if "prodEl" in labels:
            base["electricityBus"]=labels["prodEl"]
            base["producedElectricity"] = labels["prodEl"]
        if "localEl" in labels:
            base["electricityProdBus"]=labels["localEl"]
            base["electricitySource"]=labels["localEl"]
        if "StorageEl" in labels:base["electricalStorage"]=labels["StorageEl"]
        if "excessEl" in labels:base["excesselectricityBus"]=labels["excessEl"]
        if "excessSh" in labels:
            base["excessshDemandBus"]=labels["excessSh"]
            base["excessshSourceBus"]=labels["excessSh"]
        if "elBus" in labels and (mergedLinks or optimType == 'indiv'):base["electricityInBus"]=labels["elBus"]
        if "HP" in labels:base["HP"]=labels["HP"]
        if "GWHP" in labels:
            base["GWHP"]=labels["GWHP"]
            base["GWHP35"]=labels["GWHP"]+'35'# for splitted GSHP
            base["GWHP60"] = labels["GWHP"]+'60'
        if "solarCollector" in labels:
            base["solarCollector"]=labels["solarCollector"]
            base["solarConnectBus"]=labels["solarCollector"]
            base["heat_solarCollector"]=labels["solarCollector"]
        if "excessSolarCollector" in labels: base["excess_solarheat"]=labels["excessSolarCollector"]
        if "prodSH" in labels:
            base["shSource"]=labels["prodSH"]
            base["shSourceBus"]=labels["prodSH"]
        if "shBus" in labels and (mergedLinks or optimType == 'indiv'):
            base["spaceHeatingBus"]=labels["shBus"]
            base["spaceHeating"]=labels["shBus"]
            base["shDemandBus"] = labels["shBus"]
        if "StorageSh" in labels:base["shStorage"]=labels["StorageSh"]
        if "StorageDhw" in labels:
            base["dhwStorageBus"]=labels["StorageDhw"]
            base["dhwStorage"]=labels["StorageDhw"]
        if "dhwBus" in labels and (mergedLinks or optimType == 'indiv'):
            base["domesticHotWaterBus"]=labels["dhwBus"]
            base["domesticHotWater"]=labels["dhwBus"]
            base["dhwDemandBus"]=labels["dhwBus"]
        if "DemandEl" in labels:base["electricityDemand"]=labels["DemandEl"]
        if "DemandMob" in labels:base["emobilityDemand"]=labels["DemandMob"]
        if "DemandSh" in labels:base["spaceHeatingDemand"]=labels["DemandSh"]
        if "DemandDhw" in labels:base["domesticHotWaterDemand"]=labels["DemandDhw"]
        if "ElectricRod" in labels:base["ElectricRod"]=labels["ElectricRod"]

    labelDict = {}

    for b in range(1,numBuildings+1):
        for key in base:
            if ("grid" in base[key] or "Grid" in base[key]) and mergedLinks:    # combine grid bus for merged links
                value = base[key]
                key = key + "__Building" + str(b)
            elif mergedLinks and (all(v not in key for v in ["electricityLink", "shLink", "dhwLink", "electricityInBus", "domesticHotWater", "spaceHeatingBus", "domesticHotWaterBus", "dhwDemandBus", "spaceHeating", "shDemandBus"])
            or any(v in key for v in ["spaceHeatingDemand", 'domesticHotWaterDemand'])):            # append suffix for all values except links
                value = base[key]+"_B"+str(b)
                key = key+"__Building"+str(b)
            elif ((not mergedLinks and optimType == "group") or optimType == "indiv") and all(v not in key for v in ["electricityLink", "shLink", "dhwLink"]):
                value = base[key] + "_B" + str(b)
                key = key + "__Building" + str(b)
            else:
                value = base[key]
                if mergedLinks and any(v in key for v in ["electricityInBus", "domesticHotWater", "spaceHeatingBus", "domesticHotWaterBus", "dhwDemandBus", "spaceHeating", "shDemandBus"]):            # append suffix for all values except links
                    key = key+"__Building"+str(b)
            labelDict[key] = value

    return labelDict

def positionDictGenerator(labels, optimType, mergedLinks):
    labelsList = ['natGas', 'grid', 'pv', 'CHP', 'gasBoiler', 'localEl', 'prodEl', 'elLink', 'shLink', 'dhwLink', 'Bat',
                  'usedEl', 'HP', 'GWHP', 'ElectricRod', 'solar', 'exSolar', 'prodSH', 'shStor', 'dhwStor', 'exEl',
                  'Q_el', 'Q_mob', 'Q_sh', 'Q_dhw', 'exSh', 'dhwBus', 'shBus']
    if not mergedLinks and optimType == 'group':
        labelsList.extend(['usedEl', 'usedSH', 'prodDHW'])
    if labels != 'default':
        if "elBus" in labels and ((mergedLinks and optimType=='group') or optimType=='indiv'): labelsList[7] = labels["elBus"]
        if "elBus" in labels and not mergedLinks and optimType == 'group': labelsList[7] = labels["elBus"] + " Link"
        if "shBus" in labels and ((mergedLinks and optimType=='group') or optimType=='indiv'): labelsList[8] = labels["shBus"]
        if "shBus" in labels and not mergedLinks and optimType == 'group': labelsList[8] = labels["shBus"] + " Link"
        if "dhwBus" in labels and ((mergedLinks and optimType=='group') or optimType=='indiv'): labelsList[9] = labels["dhwBus"]
        if "dhwBus" in labels and not mergedLinks and optimType == 'group': labelsList[9] = labels["dhwBus"] + " Link"
        if "naturalGas" in labels: labelsList[0] = labels["naturalGas"]
        if "grid" in labels: labelsList[1] = labels["grid"]
        if "pv" in labels: labelsList[2]=labels["pv"]
        if "gasBoiler" in labels: labelsList[4]=labels["gasBoiler"]
        if "CHP" in labels:labelsList[3]=labels["CHP"]
        if "prodEl" in labels: labelsList[6] = labels["prodEl"]
        if "localEl" in labels: labelsList[5]=labels["localEl"]
        if "StorageEl" in labels:labelsList[10]=labels["StorageEl"]
        if "excessEl" in labels:labelsList[20]=labels["excessEl"]
        if "excessSh" in labels:labelsList[25]=labels["excessSh"]
        if "elBus" in labels:labelsList[11]=labels["elBus"]
        if "HP" in labels:labelsList[12]=labels["HP"]
        if "GWHP" in labels:labelsList[13]=labels["GWHP"]
        if "solarCollector" in labels:labelsList[15]=labels["solarCollector"]
        if "excessSolarCollector" in labels: labelsList[16]=labels["excessSolarCollector"]
        if "prodSH" in labels:labelsList[17]=labels["prodSH"]
        if "shBus" in labels:labelsList[27] = labels["shBus"]
        if "StorageSh" in labels:labelsList[18]=labels["StorageSh"]
        if "StorageDhw" in labels:labelsList[19]=labels["StorageDhw"]
        if "dhwBus" in labels:labelsList[26]=labels["dhwBus"]
        if "DemandEl" in labels:labelsList[21]=labels["DemandEl"]
        if "DemandMob" in labels:labelsList[22]=labels["DemandMob"]
        if "DemandSh" in labels:labelsList[23]=labels["DemandSh"]
        if "DemandDhw" in labels:labelsList[24]=labels["DemandDhw"]
        if "ElectricRod" in labels:labelsList[14]=labels["ElectricRod"]
    positionDict = {
        labelsList[0]: [0.001, 0.65],  # X and Y positions should never be set to 0 or 1
        labelsList[1]: [0.001, 0.15],
        labelsList[2]: [0.001, 0.3],
        labelsList[3]: [0.1, 0.7],
        labelsList[4]: [0.1, 0.7],
        labelsList[5]: [0.15, 0.3],
        labelsList[6]: [0.3, 0.3],
        labelsList[10]: [0.2, 0.25],
        labelsList[11]: [0.4, 0.2],
        labelsList[12]: [0.55, 0.5],
        labelsList[13]: [0.55, 0.2],
        labelsList[13]+'35': [0.55, 0.2],
        labelsList[13]+'60': [0.55, 0.5],
        labelsList[14]: [0.6, 0.4],
        labelsList[15]: [0.6, 0.85],
        labelsList[16]: [0.7, 0.95],
        labelsList[17]: [0.65, 0.58],
        # "usedSH":	[0.75, 0.58],
        labelsList[18]: [0.68, 0.37],
        labelsList[19]: [0.65, 0.85],
        # "usedDHW": [0.8, 0.85],
        # "prodDHW": [0.75, 0.85],
        labelsList[20]: [0.999, 0.25],
        labelsList[21]: [0.999, 0.15],
        labelsList[22]: [0.999, 0.4],
        labelsList[23]: [0.999, 0.6],
        labelsList[24]: [0.999, 0.85],
        labelsList[25]: [0.999, 0.7],
        labelsList[26]: [0.8, 0.85],
        labelsList[27]: [0.8, 0.6]
    }

    if mergedLinks and optimType=='group':
        positionDict[labelsList[7]]= [0.4, 0.35]
        positionDict[labelsList[8]]= [0.8, 0.35]
        positionDict[labelsList[9]]= [0.8, 0.5]
    elif optimType!='indiv':
        #links
        positionDict[labelsList[7]] = [0.45, 0.35]
        positionDict[labelsList[8]] = [0.77, 0.35]
        positionDict[labelsList[9]] = [0.85, 0.5]
        # prod DHW, used SH and used El
        if labels != 'default':
            labelsList[28] = labels["usedEl"]
            labelsList[29] = labels["usedSH"]
            labelsList[30] = labels["prodDHW"]
        positionDict[labelsList[28]] = [0.52, 0.35]
        positionDict[labelsList[29]] = [0.75, 0.35]
        positionDict[labelsList[30]] = [0.7, 0.5]

    return positionDict

labelDict = {
    "electricityLink": "elLink",
    "electricityLink1_2": "elLink",
    "electricityLink1_3": "elLink",
    "electricityLink1_4": "elLink",
    "electricityLink1_5": "elLink",
    "electricityLink1_6": "elLink",
    "electricityLink2_3": "elLink",
    "electricityLink2_4": "elLink",
    "electricityLink2_5": "elLink",
    "electricityLink2_6": "elLink",
    "electricityLink3_4": "elLink",
    "electricityLink3_5": "elLink",
    "electricityLink3_6": "elLink",
    "electricityLink4_5": "elLink",
    "electricityLink4_6": "elLink",
    "electricityLink5_6": "elLink",
    "electricityLink2_1": "elLink",
    "electricityLink3_2": "elLink",
    "electricityLink3_1": "elLink",
    "electricityLink4_3": "elLink",
    "electricityLink4_2": "elLink",
    "electricityLink4_1": "elLink",
    "electricityLink5_4": "elLink",
    "electricityLink5_3": "elLink",
    "electricityLink5_2": "elLink",
    "electricityLink5_1": "elLink",
    "electricityLink6_5": "elLink",
    "electricityLink6_4": "elLink",
    "electricityLink6_3": "elLink",
    "electricityLink6_2": "elLink",
    "electricityLink6_1": "elLink",

    "shLink1_2": "shLink",
    "shLink1_3": "shLink",
    "shLink1_4": "shLink",
    "shLink1_5": "shLink",
    "shLink1_6": "shLink",
    "shLink2_3": "shLink",
    "shLink2_4": "shLink",
    "shLink2_5": "shLink",
    "shLink2_6": "shLink",
    "shLink3_4": "shLink",
    "shLink3_5": "shLink",
    "shLink3_6": "shLink",
    "shLink4_5": "shLink",
    "shLink4_6": "shLink",
    "shLink5_6": "shLink",
    "shLink2_1": "shLink",
    "shLink3_2": "shLink",
    "shLink3_1": "shLink",
    "shLink4_3": "shLink",
    "shLink4_2": "shLink",
    "shLink4_1": "shLink",
    "shLink5_1": "shLink",
    "shLink5_2": "shLink",
    "shLink5_3": "shLink",
    "shLink5_4": "shLink",
    "shLink6_5": "shLink",
    "shLink6_4": "shLink",
    "shLink6_3": "shLink",
    "shLink6_2": "shLink",
    "shLink6_1": "shLink",

    "dhwLink1_2": "dhwLink",
    "dhwLink1_3": "dhwLink",
    "dhwLink1_4": "dhwLink",
    "dhwLink1_5": "dhwLink",
    "dhwLink1_6": "dhwLink",
    "dhwLink2_3": "dhwLink",
    "dhwLink2_4": "dhwLink",
    "dhwLink2_5": "dhwLink",
    "dhwLink2_6": "dhwLink",
    "dhwLink3_4": "dhwLink",
    "dhwLink3_5": "dhwLink",
    "dhwLink3_6": "dhwLink",
    "dhwLink4_5": "dhwLink",
    "dhwLink4_6": "dhwLink",
    "dhwLink5_6": "dhwLink",
    "dhwLink2_1": "dhwLink",
    "dhwLink3_2": "dhwLink",
    "dhwLink3_1": "dhwLink",
    "dhwLink4_3": "dhwLink",
    "dhwLink4_2": "dhwLink",
    "dhwLink4_1": "dhwLink",
    "dhwLink5_1": "dhwLink",
    "dhwLink5_2": "dhwLink",
    "dhwLink5_3": "dhwLink",
    "dhwLink5_4": "dhwLink",
    "dhwLink6_5": "dhwLink",
    "dhwLink6_4": "dhwLink",
    "dhwLink6_3": "dhwLink",
    "dhwLink6_2": "dhwLink",
    "dhwLink6_1": "dhwLink",

    "naturalGasResource__Building1": "natGas_B1",
    "naturalGasBus__Building1": "natGas_B1",
    "gridBus__Building1": "grid_B1",
    "pv__Building1": "pv_B1",
    "electricityResource__Building1":"grid_B1",
    "gridElectricity__Building1": "grid_B1",
    "GasBoiler__Building1":"gasBoiler_B1",
    "CHP_SH__Building1": "CHP_B1",
    "CHP_DHW__Building1": "CHP_B1",
    "CHP__Building1": "CHP_B1",
    "electricityBus__Building1": "prodEl_B1",
    "electricityProdBus__Building1":"localEl_B1", #localEl is before the battery, prodEl after the battery but before the elLink
    "producedElectricity__Building1": "prodEl_B1",
    "electricitySource__Building1": "localEl_B1",
    "electricalStorage__Building1": "Bat_B1",
    "excesselectricityBus__Building1": "exEl_B1",
    "excessshDemandBus__Building1": "exSh_B1",
    "electricityInBus__Building1": "usedEl_B1",
    "HP_SH__Building1": "HP_B1",
    "HP_DHW__Building1": "HP_B1",
    "HP__Building1": "HP_B1",
    "GWHP_SH__Building1": "GWHP_B1",
    "GWHP_DHW__Building1": "GWHP_B1",
    "GWHP__Building1": "GWHP_B1",
    "solarCollector__Building1": "solar_B1",
    "solarConnectBus__Building1": "solar_B1",
    'heat_solarCollector__Building1': "solar_B1",
    'excess_solarheat__Building1':"exSolar_B1",
    'shSource__Building1'	: "prodSH_B1",
    'shSourceBus__Building1': "prodSH_B1",
    "spaceHeatingBus__Building1": "shBus_B1",
    "spaceHeating__Building1": "shBus_B1",
    "shStorage__Building1": "shStor_B1",
    "shDemandBus__Building1": "shBus_B1",
    "dhwStorageBus__Building1": "dhwStor_B1",
    "dhwStorage__Building1": "dhwStor_B1",
    "domesticHotWaterBus__Building1": "dhwBus_B1",
    'domesticHotWater__Building1': "dhwBus_B1",
    "dhwDemandBus__Building1": "dhwBus_B1",
    "electricityDemand__Building1": "Q_el_B1",
    "emobilityDemand__Building1": "Q_mob_B1",
    "spaceHeatingDemand__Building1": "Q_sh_B1",
    "domesticHotWaterDemand__Building1": "Q_dhw_B1",
    "excessshSourceBus__Building1": "exSh_B1",
    "ElectricRod__Building1": "ElectricRod_B1",

    "naturalGasResource__Building2": "natGas_B2",
    "naturalGasBus__Building2": "natGas_B2",
    "electricityResource__Building2": "grid_B2",
    "gridBus__Building2": "grid_B2",
    "pv__Building2": "pv_B2",
    "gridElectricity__Building2": "grid_B2",
    "GasBoiler__Building2":"gasBoiler_B2",
    "CHP_SH__Building2": "CHP_B2",
    "CHP_DHW__Building2": "CHP_B2",
    "CHP__Building2": "CHP_B2",
    "electricityBus__Building2": "prodEl_B2",
    "electricityProdBus__Building2": "localEl_B2",
    "producedElectricity__Building2": "prodEl_B2",
    "electricitySource__Building2": "localEl_B2",
    "electricalStorage__Building2": "Bat_B2",
    "excesselectricityBus__Building2": "exEl_B2",
    "excessshDemandBus__Building2": "exSh_B2",
    "electricityInBus__Building2": "usedEl_B2",
    "HP_SH__Building2": "HP_B2",
    "HP_DHW__Building2": "HP_B2",
    "HP__Building2": "HP_B2",
    "GWHP_SH__Building2": "GWHP_B2",
    "GWHP_DHW__Building2": "GWHP_B2",
    "GWHP__Building2": "GWHP_B2",
    "solarCollector__Building2": "solar_B2",
    "solarConnectBus__Building2": "solar_B2",
    'heat_solarCollector__Building2': "solar_B2",
    'excess_solarheat__Building2': "exSolar_B2",
    'shSource__Building2'	: "prodSH_B2",
    'shSourceBus__Building2': "prodSH_B2",
    "spaceHeatingBus__Building2": "shBus_B2",
    "spaceHeating__Building2": "shBus_B2",
    "shStorage__Building2": "shStor_B2",
    "shDemandBus__Building2": "shBus_B2",
    "dhwStorageBus__Building2": "dhwStor_B2",
    "dhwStorage__Building2": "dhwStor_B2",
    "domesticHotWaterBus__Building2": "dhwBus_B2",
    'domesticHotWater__Building2': "dhwBus_B2",
    "dhwDemandBus__Building2": "dhwBus_B2",
    "electricityDemand__Building2": "Q_el_B2",
    "emobilityDemand__Building2": "Q_mob_B2",
    "spaceHeatingDemand__Building2":        "Q_sh_B2",
    "domesticHotWaterDemand__Building2": "Q_dhw_B2",
    "excessshSourceBus__Building2": "exSh_B2",
    "ElectricRod__Building2": "ElectricRod_B2",

    "naturalGasResource__Building3": "natGas_B3",
    "naturalGasBus__Building3": "natGas_B3",
    "electricityResource__Building3": "grid_B3",
    "gridBus__Building3": "grid_B3",
    "GasBoiler__Building3": "gasBoiler_B3",
    "pv__Building3": "pv_B3",
    "gridElectricity__Building3": "grid_B3",
    "CHP_SH__Building3": "CHP_B3",
    "CHP_DHW__Building3": "CHP_B3",
    "CHP__Building3": "CHP_B3",
    "electricityBus__Building3": "prodEl_B3",
    "electricityProdBus__Building3": "localEl_B3",
    "producedElectricity__Building3": "prodEl_B3",
    "electricitySource__Building3": "localEl_B3",
    "electricalStorage__Building3": "Bat_B3",
    "excesselectricityBus__Building3": "exEl_B3",
    "excessshDemandBus__Building3": "exSh_B3",
    "electricityInBus__Building3": "usedEl_B3",
    "HP_SH__Building3": "HP_B3",
    "HP_DHW__Building3": "HP_B3",
    "HP__Building3": "HP_B3",
    "GWHP_SH__Building3": "GWHP_B3",
    "GWHP_DHW__Building3": "GWHP_B3",
    "GWHP__Building3": "GWHP_B3",
    "solarCollector__Building3": "solar_B3",
    "solarConnectBus__Building3": "solar_B3",
    'heat_solarCollector__Building3': "solar_B3",
    'excess_solarheat__Building3': "exSolar_B3",
    'shSource__Building3': "prodSH_B3",
    'shSourceBus__Building3': "prodSH_B3",
    "spaceHeatingBus__Building3": "shBus_B3",
    "spaceHeating__Building3": "shBus_B3",
    "shStorage__Building3": "shStor_B3",
    "shDemandBus__Building3": "shBus_B3",
    "dhwStorageBus__Building3": "dhwStor_B3",
    "dhwStorage__Building3": "dhwStor_B3",
    "domesticHotWaterBus__Building3": "dhwBus_B3",
    'domesticHotWater__Building3': "dhwBus_B3",
    "dhwDemandBus__Building3": "dhwBus_B3",
    "electricityDemand__Building3": "Q_el_B3",
    "emobilityDemand__Building3": "Q_mob_B3",
    "spaceHeatingDemand__Building3":        "Q_sh_B3",
    "domesticHotWaterDemand__Building3": "Q_dhw_B3",
    "excessshSourceBus__Building3": "exSh_B3",
    "ElectricRod__Building3": "ElectricRod_B3",

    "naturalGasResource__Building4": "natGas_B4",
    "naturalGasBus__Building4": "natGas_B4",
    "electricityResource__Building4": "grid_B4",
    "gridBus__Building4": "grid_B4",
    "pv__Building4": "pv_B4",
    "gridElectricity__Building4": "grid_B4",
    "GasBoiler__Building4":"gasBoiler_B4",
    "CHP_SH__Building4": "CHP_B4",
    "CHP_DHW__Building4": "CHP_B4",
    "CHP__Building4": "CHP_B4",
    "electricityBus__Building4": "prodEl_B4",
    "electricityProdBus__Building4": "localEl_B4",
    "producedElectricity__Building4": "prodEl_B4",
    "electricitySource__Building4": "localEl_B4",
    "electricalStorage__Building4": "Bat_B4",
    "excesselectricityBus__Building4": "exEl_B4",
    "excessshDemandBus__Building4": "exSh_B4",
    "electricityInBus__Building4": "usedEl_B4",
    "HP_SH__Building4": "HP_B4",
    "HP_DHW__Building4": "HP_B4",
    "HP__Building4": "HP_B4",
    "GWHP_SH__Building4": "GWHP_B4",
    "GWHP_DHW__Building4": "GWHP_B4",
    "GWHP__Building4": "GWHP_B4",
    "solarCollector__Building4": "solar_B4",
    "solarConnectBus__Building4": "solar_B4",
    'heat_solarCollector__Building4': "solar_B4",
    'excess_solarheat__Building4': "exSolar_B4",
    'shSource__Building4': "prodSH_B4",
    'shSourceBus__Building4': "prodSH_B4",
    "spaceHeatingBus__Building4": "shBus_B4",
    "spaceHeating__Building4": "shBus_B4",
    "shStorage__Building4": "shStor_B4",
    "shDemandBus__Building4": "shBus_B4",
    "dhwStorageBus__Building4": "dhwStor_B4",
    "dhwStorage__Building4": "dhwStor_B4",
    "domesticHotWaterBus__Building4": "dhwBus_B4",
    'domesticHotWater__Building4': "dhwBus_B4",
    "dhwDemandBus__Building4": "dhwBus_B4",
    "electricityDemand__Building4": "Q_el_B4",
    "emobilityDemand__Building4": "Q_mob_B4",
    "spaceHeatingDemand__Building4":        "Q_sh_B4",
    "domesticHotWaterDemand__Building4": "Q_dhw_B4",
    "excessshSourceBus__Building4": "exSh_B4",
    "ElectricRod__Building4": "ElectricRod_B4",

    "naturalGasResource__Building5": "natGas_B5",
    "naturalGasBus__Building5": "natGas_B5",
    "electricityResource__Building5": "grid_B5",
    "gridBus__Building5": "grid_B5",
    "pv__Building5": "pv_B5",
    "gridElectricity__Building5": "grid_B5",
    "GasBoiler__Building5":"gasBoiler_B5",
    "CHP_SH__Building5": "CHP_B5",
    "CHP_DHW__Building5": "CHP_B5",
    "CHP__Building5": "CHP_B5",
    "electricityBus__Building5": "prodEl_B5",
    "electricityProdBus__Building5": "localEl_B5",
    "producedElectricity__Building5": "prodEl_B5",
    "electricitySource__Building5": "prodEl_B5",
    "electricalStorage__Building5": "Bat_B5",
    "excesselectricityBus__Building5": "exEl_B5",
    "excessshDemandBus__Building5": "exSh_B5",
    "excessshSourceBus__Building5": "exSh_B5",
    "electricityInBus__Building5": "usedEl_B5",
    "HP_SH__Building5": "HP_B5",
    "HP_DHW__Building5": "HP_B5",
    "HP__Building5": "HP_B5",
    "GWHP_SH__Building5": "GWHP_B5",
    "GWHP_DHW__Building5": "GWHP_B5",
    "GWHP__Building5": "GWHP_B5",
    "solarCollector__Building5": "solar_B5",
    "solarConnectBus__Building5": "solar_B5",
    'heat_solarCollector__Building5': "solar_B5",
    'excess_solarheat__Building5': "exSolar_B5",
    'shSource__Building5'	: "prodSH_B5",
    'shSourceBus__Building5': "prodSH_B5",
    "spaceHeatingBus__Building5": "usedSH_B5",
    "spaceHeating__Building5": "Q_sh_B5",
    "shStorage__Building5": "shStor_B5",
    "shDemandBus__Building5": "Q_sh_B5",
    "dhwStorageBus__Building5": "dhwStor_B5",
    "dhwStorage__Building5": "dhwStor_B5",
    "domesticHotWaterBus__Building5": "prodDHW_B5",
    'domesticHotWater__Building5': "usedDHW_B5",
    "dhwDemandBus__Building5": "Q_dhw_B5",
    "electricityDemand__Building5": "Q_el_B5",
    "spaceHeatingDemand__Building5":        "Q_sh_B5",
    "domesticHotWaterDemand__Building5": "Q_dhw_B5",
    "ElectricRod__Building5": "ElectricRod_B5",

    "naturalGasResource__Building6": "natGas_B6",
    "naturalGasBus__Building6": "natGas_B6",
    "electricityResource__Building6": "grid_B6",
    "gridBus__Building6": "grid_B6",
    "pv__Building6": "pv_B6",
    "gridElectricity__Building6": "grid_B6",
    "GasBoiler__Building6":"gasBoiler_B6",
    "CHP_SH__Building6": "CHP_B6",
    "CHP_DHW__Building6": "CHP_B6",
    "CHP__Building6": "CHP_B6",
    "electricityBus__Building6": "prodEl_B6",
    "electricityProdBus__Building6": "localEl_B6",
    "producedElectricity__Building6": "prodEl_B6",
    "electricitySource__Building6": "prodEl_B6",
    "electricalStorage__Building6": "Bat_B6",
    "excesselectricityBus__Building6": "exEl_B6",
    "excessshDemandBus__Building6": "exSh_B6",
    "excessshSourceBus__Building6": "exSh_B6",
    "electricityInBus__Building6": "usedEl_B6",
    "HP_SH__Building6": "HP_B6",
    "HP_DHW__Building6": "HP_B6",
    "HP__Building6": "HP_B6",
    "GWHP_SH__Building6": "GWHP_B6",
    "GWHP_DHW__Building6": "GWHP_B6",
    "GWHP__Building6": "GWHP_B6",
    "solarCollector__Building6": "solar_B6",
    "solarConnectBus__Building6": "solar_B6",
    'heat_solarCollector__Building6': "solar_B6",
    'excess_solarheat__Building6': "exSolar_B6",
    'shSource__Building6'	: "prodSH_B6",
    'shSourceBus__Building6': "prodSH_B6",
    "spaceHeatingBus__Building6": "usedSH_B6",
    "spaceHeating__Building6": "Q_sh_B6",
    "shStorage__Building6": "shStor_B6",
    "shDemandBus__Building6": "Q_sh_B6",
    "dhwStorageBus__Building6": "dhwStor_B6",
    "dhwStorage__Building6": "dhwStor_B6",
    "domesticHotWaterBus__Building6": "prodDHW_B6",
    'domesticHotWater__Building6': "usedDHW_B6",
    "dhwDemandBus__Building6": "Q_dhw_B6",
    "electricityDemand__Building6": "Q_el_B6",
    "spaceHeatingDemand__Building6":        "Q_sh_B6",
    "domesticHotWaterDemand__Building6": "Q_dhw_B6",
    "ElectricRod__Building6": "ElectricRod_B6",
}

labelPositionDict={
    "natGas":	[0.001, 0.65], #X and Y positions should never be set to 0 or 1
    "grid":	[0.001, 0.15],
    "pv":   [0.001, 0.3],
    "CHP":	[0.1, 0.7],
    "gasBoiler": [0.1, 0.7],
    "localEl":	[0.15, 0.3],
    "prodEl":[0.3,0.3],
    "elLink":	[0.4, 0.35],
    "shLink": [0.8, 0.35],
    "dhwLink": [0.8, 0.5],
	"Bat":	[0.2, 0.25],
    "usedEl":	[0.4, 0.2],
    "HP":	[0.55, 0.5],
    "GWHP":	[0.55, 0.2],
    "ElectricRod": [0.6, 0.4],
    "solar":	[0.6, 0.85],
    "exSolar": [0.7, 0.95],
    "prodSH": [0.65, 0.58],
    #"usedSH":	[0.75, 0.58],
    "shStor":	[0.68, 0.37],
    "dhwStor":	[0.65, 0.85],
    #"usedDHW": [0.8, 0.85],
    #"prodDHW": [0.75, 0.85],
    "exEl": [0.999, 0.25],
    "Q_el":	[0.999, 0.15],
    "Q_mob":[0.999, 0.4],
    "Q_sh":	[0.999, 0.6],
    "Q_dhw":[0.999, 0.85],
    "exSh": [0.999, 0.7],
    "dhwBus":[0.8, 0.85],
    "shBus": [0.8, 0.6]
	}

fullPositionDict={
        "naturalGas":	[0.001, 0.75],
        "gridBus":	[0.001, 0.2],
        "pv":   [0.001, 0.3],
        "gridElect":	[0.1, 0.05],
        "electricityProdBus": [0.1, 0.2],
        "CHP":	[0.1, 0.6],
        "GasBoiler": [0.1, 0.7],
        "electricitySource": [0.15, 0.2],
        "electricityBus":	[0.2, 0.2],
        "producedElectricity":	[0.3, 0.25],
        "electricityLink":	[0.3, 0.35],
        "electricalStorage":	[0.3, 0.25],
        "excesselect":	[0.5, 0.05],
        "electricityInBus":	[0.5, 0.2],
        "HP":	[0.6, 0.5],
        "GWHP":	[0.6, 0.2],
        "ElectricRod": [0.6, 0.4],
        "heat_solarCollector": [0.4, 0.85],
        "solarConnect": [0.5, 0.85],
        "solarCollector_":	[0.6, 0.85],
        "excess_solarheat":[0.6,0.85],
        'shSource_': [0.63, 0.58],
        'shLink': [0.64, 0.58],
        'shSourceBus': [0.66, 0.58],
        "spaceHeatingBus":	[0.7, 0.58],
        "spaceHeating_":	[0.8, 0.6],
        "shStorage":	[0.8, 0.37],
        "shDemandBus":	[0.9, 0.6],
        "dhwStorageBus":	[0.7, 0.9],
        "dhwStorage_":	[0.8, 0.9],
        "domesticHotWater_":	[0.92, 0.9],
        "domesticHotWaterBus":	[0.9, 0.9],
        "dhwDemandBus":	[0.95, 0.9],
        "electricityDemand":	[0.999, 0.1],
        "spaceHeatingDemand_":	[0.999, 0.6],
        "domesticHotWaterDemand":	[0.999, 0.9]
        }