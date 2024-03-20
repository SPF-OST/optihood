from configparser import ConfigParser
import numpy as np
import pandas as pd

import optihood.IO.readers as _rd

# self is never used!


def createScenarioFile(self, configFilePath, excelFilePath, numberOfBuildings, writeToFileOrReturnData='file'):
        """
        function to create the input excel file from a config file
        saves the generated excel file at the path given by excelFilePath
        """

        configData = _rd.parse_config(configFilePath)

        excelData = {}
        columnNames = {'commodity_sources': ['label', 'building', 'to', 'variable costs', 'CO2 impact', 'active'],
                       # column names are defined for each sheet (key of dict) in the excel file
                       'solar': ['label', 'building', 'from', 'to', 'connect', 'electrical_consumption',
                                 'peripheral_losses', 'latitude', 'longitude', 'tilt', 'azimuth', 'eta_0', 'a_1', 'a_2',
                                 'temp_collector_inlet', 'delta_temp_n', 'capacity_max', 'capacity_min', 'lifetime',
                                 'maintenance', 'installation', 'planification', 'invest_base', 'invest_cap',
                                 'heat_impact', 'elec_impact', 'impact_cap'],
                       'demand': ['label', 'building', 'active', 'from', 'fixed', 'nominal value', 'building model'],
                       'transformers': ['label', 'building', 'active', 'from', 'to', 'efficiency', 'capacity_DHW',
                                        'capacity_SH', 'capacity_el', 'capacity_min', 'lifetime', 'maintenance',
                                        'installation', 'planification', 'invest_base', 'invest_cap', 'heat_impact',
                                        'elec_impact', 'impact_cap'],
                       'storages': ['label', 'building', 'active', 'from', 'to', 'efficiency inflow',
                                    'efficiency outflow', 'initial capacity', 'capacity min', 'capacity max',
                                    'capacity loss', 'lifetime', 'maintenance', 'installation', 'planification',
                                    'invest_base', 'invest_cap', 'heat_impact', 'elec_impact', 'impact_cap'],
                       'stratified_storage': ['label', 'diameter', 'temp_h', 'temp_c', 'temp_env',
                                              'inflow_conversion_factor', 'outflow_conversion_factor', 's_iso',
                                              'lamb_iso', 'alpha_inside', 'alpha_outside'],
                       'links': ['label', 'active', 'efficiency', 'invest_base', 'invest_cap', 'investment']
                       }
        buses = {'naturalgasresource': ['naturalGasBus', '', ''], 'electricityresource': ['gridBus', '', ''],
                 'solarcollector': ['dhwStorageBus', 'electricityInBus', 'solarConnectBus'],
                 # [to, from, connect] columns in the excel file
                 'pv': ['electricityProdBus', '', ''], 'electricitydemand': ['', 'electricityInBus', ''],
                 'spaceheatingdemand': ['', 'shDemandBus', ''],
                 'domestichotwaterdemand': ['', 'dhwDemandBus', ''],
                 'gasboiler': ['shSourceBus,dhwStorageBus', 'naturalGasBus', ''],
                 'electricrod': ['shSourceBus,dhwStorageBus', 'electricityInBus', ''],
                 'chp': ['electricityProdBus,shSourceBus,dhwStorageBus', 'naturalGasBus', ''],
                 'ashp': ['shSourceBus,dhwStorageBus', 'electricityInBus', ''],
                 'gshp': ['shSourceBus,dhwStorageBus', 'electricityInBus', ''],
                 'electricalstorage': ['electricityBus', 'electricityProdBus', ''],
                 'shstorage': ['spaceHeatingBus', 'shSourceBus', ''],
                 'dhwstorage': ['domesticHotWaterBus', 'dhwStorageBus', '']}
        sheetToSection = {'commodity_sources': 'CommoditySources', 'solar': 'Solar', 'demand': 'Demands',
                          'transformers': 'Transformers', 'storages': 'Storages',
                          'stratified_storage': 'StratifiedStorage', 'links':'Links'}

        profiles = pd.DataFrame(columns=['name', 'path'])
        updatedLabels = {'weatherpath': 'weather_data', 'path': 'demand_profiles', 'ashp': 'HP', 'gshp': 'GWHP',
                         'electricityresource': 'electricityResource', 'naturalgasresource': 'naturalGasResource',
                         'chp': 'CHP', 'gasboiler': 'GasBoiler', 'electricrod': 'ElectricRod', 'pv': 'pv',
                         'solarcollector': 'solarCollector', 'electricalstorage': 'electricalStorage',
                         'shstorage': 'shStorage', 'dhwstorage': 'dhwStorage', 'stratifiedstorage': 'StratifiedStorage',
                         'ellink': 'electricityLink', 'shlink': 'shLink', 'dhwlink': 'dhwLink'}
        efficiencyLinks = {'ellink': 0.9999, 'shlink': 0.9, 'dhwlink': 0.9}
        temp_h = {}  # to store temp_h values for stratified storage parameters sheet
        FeedinTariff = 0

        for sheet in columnNames:
            excelData[sheet] = pd.DataFrame(columns=columnNames[sheet])
            if sheet == 'stratified_storage':
                newRow = pd.DataFrame(columns=columnNames[sheet])
                newRow.at[0, 'label'] = list(temp_h)[0]
                newRow.at[0, 'temp_h'] = list(temp_h.values())[0]
                newRow.at[1, 'label'] = list(temp_h)[1]
                newRow.at[1, 'temp_h'] = list(temp_h.values())[1]
            for item in configData[sheetToSection[sheet].lower()]:
                type = item[0]
                if item[1] in ['True', 'False']:  # defines whether or not a component is to be added
                    if item[1] == 'True':
                        newRow = pd.DataFrame(columns=columnNames[sheet])
                        newRow.at[0, 'label'] = updatedLabels[item[0]]
                        newRow.at[0, 'active'] = int(bool(item[1] == 'True'))
                        # sheet specific options
                        cols = newRow.columns
                        if 'building' in cols:
                            newRow.at[0, 'building'] = 1
                        if 'to' in cols:
                            newRow.at[0, 'to'] = buses[type][0]
                        if 'from' in cols:
                            newRow.at[0, 'from'] = buses[type][1]
                        if 'connect' in cols:
                            newRow.at[0, 'connect'] = buses[type][2]
                        if type in ['shlink', 'dhwlink']:
                            params = configData['thermallink']
                        else:
                            params = configData[type]
                        if sheet == 'commodity_sources':
                            index = [x for x, y in enumerate(params) if y[0] == 'cost'][0]
                            newRow.at[0, 'variable costs'] = params[index][1]
                            index = [x for x, y in enumerate(params) if y[0] == 'impact'][0]
                            newRow.at[0, 'CO2 impact'] = params[index][1]
                            if type == 'electricityresource':
                                index = [x for x, y in enumerate(params) if y[0] == 'feedintariff'][0]
                                FeedinTariff = -float(params[index][1])
                        else:
                            if sheet == 'links':
                                if not [x for x, y in enumerate(params) if y[0] == 'efficiency']:
                                    newRow.at[0, 'efficiency'] = efficiencyLinks[type]
                                newRow.at[0, 'investment'] = 1
                            for p in params:
                                if sheet == 'transformers' and p[0] == 'capacity_max':
                                    newRow.at[0, 'capacity_DHW'] = p[1]
                                    newRow.at[0, 'capacity_SH'] = p[1]
                                    if updatedLabels[item[0]]=='CHP':
                                        newRow.at[0, 'capacity_el'] = str(round(float(p[1])*float(newRow.at[0, 'efficiency'].split(',')[0])/float(newRow.at[0, 'efficiency'].split(',')[1]),0))
                                elif sheet == 'storages' and p[0] == 'temp_h':
                                    temp_h[newRow.at[0, 'label']] = p[1]
                                else:
                                    newRow.at[0, p[0]] = p[1]
                        excelData[sheet] = pd.concat([excelData[sheet], newRow])
                elif 'path' in type:  # weather path or demand path
                    profiles = pd.concat([profiles, pd.DataFrame({'name': [updatedLabels[type]], 'path': [item[1]]})])
                elif sheet == 'demand':
                    newRow = pd.DataFrame(columns=columnNames[sheet])
                    for d in ['electricityDemand', 'spaceHeatingDemand', 'domesticHotWaterDemand']:
                        newRow.at[0, 'label'] = d
                        newRow.at[0, 'from'] = buses[d.lower()][1]
                        if d == 'spaceHeatingDemand' and item[1] == 0:
                            newRow.at[0, 'fixed'] = item[1]
                            newRow.at[0, 'building model'] = 'Yes'
                        else:
                            newRow.at[0, 'fixed'] = 1
                        excelData[sheet] = pd.concat([excelData[sheet], newRow])
                    excelData[sheet]['building'] = 1
                    excelData[sheet]['active'] = 1
                    excelData[sheet]['nominal value'] = 1
                elif sheet == 'stratified_storage':
                    newRow.at[0, type] = item[1]
                    newRow.at[1, type] = item[1]
                else:  # common parameters of all the components of that section
                    excelData[sheet][type] = item[1]
            if sheet == 'stratified_storage':
                excelData[sheet] = pd.concat([excelData[sheet], newRow])
        excelData['profiles'] = profiles
        excelData['grid_connection'] = pd.DataFrame(
            {'label': ['gridElectricity', 'electricitySource', 'producedElectricity', 'domesticHotWater', 'shSource', 'spaceHeating'],
             'building': [1, 1, 1, 1, 1, 1],
             'from': ['gridBus', 'electricityProdBus', 'electricityBus', 'domesticHotWaterBus', 'shSourceBus', 'spaceHeatingBus'],
             'to': ['electricityInBus', 'electricityBus', 'electricityInBus', 'dhwDemandBus', 'spaceHeatingBus', 'shDemandBus'],
             'efficiency': [1, 1, 1, 1, 1, 1]})

        df = pd.DataFrame(columns=['buses'])
        for sheet, data in excelData.items():
            for col in ['from', 'to', 'connect']:
                if col in data.columns:
                    newBuses = pd.DataFrame(columns=['buses'])
                    newBuses['buses'] = data[col].values
                    df = pd.concat([df, newBuses])
        df = df.assign(buses=df.buses.str.split(',')).explode('buses')['buses'].unique()
        df = df[df != '']
        excelData['buses'] = pd.DataFrame(columns=['label', 'building', 'excess', 'excess costs', 'active'])
        for index in range(len(df)):
            excelData['buses'].at[index, 'label'] = df[index]
            if df[index] == 'electricityBus' and FeedinTariff != 0:
                excelData['buses'].at[index, 'excess'] = 1
                excelData['buses'].at[index, 'excess costs'] = FeedinTariff
        excelData['buses']['building'] = 1
        excelData['buses']['active'] = 1
        excelData['buses'].loc[excelData['buses']['excess'] != 1, 'excess'] = 0
        for sheet, data in excelData.items():
            if 'building' in data.columns:
                buildingNo = [i for i in range(1, numberOfBuildings + 1)] * len(excelData[sheet].index)
                excelData[sheet] = pd.DataFrame(np.repeat(data.values, numberOfBuildings, axis=0), columns=data.columns)
                excelData[sheet]['building'] = buildingNo
        if writeToFileOrReturnData == 'file':
            with pd.ExcelWriter(excelFilePath, engine='xlwt') as writer:
                for sheet, data in excelData.items():
                    data.to_excel(writer, sheet_name=sheet, index=False)
                writer.save()
                writer.close()
            return
        elif writeToFileOrReturnData == 'data':
            return excelData
