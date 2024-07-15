import pandas as pd

import optihood.IO.groupScenarioWriter as _gsw
import optihood.IO.readers as _rd


def create_scenario_file(configFilePath, building, numberOfBuildings=1):
    """
    function to create the input excel file from a config file
    saves the generated excel file at the path given by excel_file_path
    """

    configData = _rd.parse_config(configFilePath)

    excel_data = {}
    buses, columnNames, sheetToSection, updatedLabels = _gsw.get_excel_variable_names()

    buses['domestichotwaterdemand'] = ['', 'domesticHotWaterBus', '']

    temp_h = {}  # to store temp_h values for stratified storage parameters sheet
    FeedinTariff = 0
    profiles = pd.DataFrame(columns=['name', 'path'])

    for sheet in columnNames:
        excel_data[sheet] = pd.DataFrame(columns=columnNames[sheet])
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
                        for p in params:
                            if sheet == 'transformers' and p[0] == 'capacity_max':
                                newRow.at[0, 'capacity_DHW'] = p[1]
                                newRow.at[0, 'capacity_SH'] = p[1]
                                if updatedLabels[item[0]] == 'CHP':
                                    newRow.at[0, 'capacity_el'] = str(round(
                                        float(p[1]) * float(newRow.at[0, 'efficiency'].split(',')[0]) / float(
                                            newRow.at[0, 'efficiency'].split(',')[1]), 0))
                            elif sheet == 'storages' and p[0] == 'temp_h':
                                temp_h[newRow.at[0, 'label']] = p[1]
                            else:
                                newRow.at[0, p[0]] = p[1]
                    excel_data[sheet] = pd.concat([excel_data[sheet], newRow])
            elif type == 'path':  # demand path
                buildingFolder = [i[1] for i in configData['demands'] if i[0] == 'folders'][0].split(',')[building]
                buildingPath = item[1] + '\\' + buildingFolder
                profiles = pd.concat([profiles, pd.DataFrame({'name': [updatedLabels[type]], 'path': [buildingPath]})])
            elif 'path' in type:  # weather path
                profiles = pd.concat([profiles, pd.DataFrame({'name': [updatedLabels[type]], 'path': [item[1]]})])
            elif sheet == 'demand' and type != 'folders':
                newRow = pd.DataFrame(columns=columnNames[sheet])
                for d in ['electricityDemand', 'spaceHeatingDemand', 'domesticHotWaterDemand']:
                    newRow.at[0, 'label'] = d
                    newRow.at[0, 'from'] = buses[d.lower()][1]
                    if d == 'spaceHeatingDemand' and item[1] == 0:
                        newRow.at[0, 'fixed'] = item[1]
                        newRow.at[0, 'building model'] = 'Yes'
                    else:
                        newRow.at[0, 'fixed'] = 1
                    excel_data[sheet] = pd.concat([excel_data[sheet], newRow])
                excel_data[sheet]['building'] = 1
                excel_data[sheet]['active'] = 1
                excel_data[sheet]['nominal value'] = 1
            elif sheet == 'stratified_storage':
                newRow.at[0, type] = item[1]
                newRow.at[1, type] = item[1]
            else:  # common parameters of all the components of that section
                if type != 'folders':
                    excel_data[sheet][type] = item[1]
        if sheet == 'stratified_storage':
            excel_data[sheet] = pd.concat([excel_data[sheet], newRow])

    excel_data['profiles'] = profiles

    _gsw.add_grid_connections_to_excel_data(excel_data)

    _gsw.add_busses_to_excel_data(FeedinTariff, excel_data)

    _gsw.add_buildings_to_excel_data(excel_data, numberOfBuildings)

    return excel_data
