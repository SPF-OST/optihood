import pandas as pd
import os
import xlrd


def getData():
    cwd = os.path.dirname(os.path.realpath(__file__))
    inputDataPath = os.path.join(cwd, "InputData")
    data = {}

    ## Primary data
    globall = pd.read_excel(os.path.join(inputDataPath, 'SpatialDataTest', 'data_indiv.xlsx'),
                            sheet_name="Global", index_col=0, header=None, engine='openpyxl')
    numberOfTimeSteps = globall.loc["Time range"]

    data.update({'Global, numberOfTimeSteps': numberOfTimeSteps})

    ## Demand data
    operationRateFix_elec = pd.read_excel(os.path.join(inputDataPath, 'SpatialDataTest', 'data_indiv.xlsx'),
                                          sheet_name="ElecDemand", index_col=0, header=0, engine='openpyxl')
    operationRateFix_sh = pd.read_excel(os.path.join(inputDataPath, 'SpatialDataTest', 'data_indiv.xlsx'),
                                        sheet_name="SHDemand", index_col=0, header=0, engine='openpyxl')
    operationRateFix_dhw = pd.read_excel(os.path.join(inputDataPath, 'SpatialDataTest', 'data_indiv.xlsx'),
                                         sheet_name="DHWDemand", index_col=0, header=0, engine='openpyxl')

    data.update({'Electricity demand, operationRateFix': operationRateFix_elec})
    data.update({'Space heat demand, operationRateFix': operationRateFix_sh})
    data.update({'Domestic hot water demand, operationRateFix': operationRateFix_dhw})

    ## Weather data
    T_amb = pd.read_excel(os.path.join(inputDataPath, 'SpatialDataTest', 'data_indiv.xlsx'),
                          sheet_name="Weather", index_col=0, header=None, engine='openpyxl')
    data.update({'T_amb': T_amb})

    ## Input data
    Inputs = pd.read_excel(os.path.join(inputDataPath, 'SpatialDataTest', 'data_indiv.xlsx'),
                           sheet_name="Inputs", index_col=0, engine='openpyxl', usecols="B:AA")

    # Electricity grid
    operationCost = Inputs.loc['Cost', 'Electricity_grid']
    feedinCost = Inputs.loc['FeedIn', 'Electricity_grid']
    operationGWP = Inputs.loc['GWP', 'Electricity_grid']
    operationRateMax = Inputs.loc['Max', 'Electricity_grid']

    data.update({'Electricity grid, operationCost': operationCost})
    data.update({'Electricity grid, feedinCost': feedinCost})
    data.update({'Electricity grid, operationGWP': operationGWP})
    data.update({'Electricity grid, operationRateMax': operationRateMax})

    # Natural gas
    operationCost = Inputs.loc['Cost', 'Natural_gas']
    operationGWP = Inputs.loc['GWP', 'Natural_gas']

    data.update({'Natural gas, operationCost': operationCost})
    data.update({'Natural gas, operationGWP': operationGWP})

    ## Converters data
    Converters = pd.read_excel(os.path.join(inputDataPath, 'SpatialDataTest', 'data_indiv.xlsx'),
                               sheet_name="Converters", index_col=0, engine='openpyxl', usecols="B:AA")

    # CHP
    minCapa = Converters.loc['Min_capacity', 'CHP']
    maxCapa = Converters.loc['Max_capacity', 'CHP']
    maintenanceCost = Converters.loc['MaintenanceCost', 'CHP']
    installationCost = Converters.loc['InstallationCost', 'CHP']
    planificationCost = Converters.loc['PlanificationCost', 'CHP']
    investmentCost = Converters.loc['InvestmentCost', 'CHP']
    investmentBaseCost = Converters.loc['InvestmentCostBase', 'CHP']
    operationGWP = Converters.loc['GWP', 'CHP']

    data.update({'CHP, minCapa': minCapa})
    data.update({'CHP, maxCapa': maxCapa})
    data.update({'CHP, maintenanceCost': maintenanceCost})
    data.update({'CHP, installationCost': installationCost})
    data.update({'CHP, planificationCost': planificationCost})
    data.update({'CHP, investmentCost': investmentCost})
    data.update({'CHP, investmentBaseCost': investmentBaseCost})
    data.update({'CHP, operationGWP': operationGWP})

    # HP
    minCapa = Converters.loc['Min_capacity', 'Heat_Pump']
    maxCapa = Converters.loc['Max_capacity', 'Heat_Pump']
    maintenanceCost = Converters.loc['MaintenanceCost', 'Heat_Pump']
    installationCost = Converters.loc['InstallationCost', 'Heat_Pump']
    planificationCost = Converters.loc['PlanificationCost', 'Heat_Pump']
    investmentCost = Converters.loc['InvestmentCost', 'Heat_Pump']
    investmentBaseCost = Converters.loc['InvestmentCostBase', 'Heat_Pump']
    operationGWP = Converters.loc['GWP', 'Heat_Pump']

    data.update({'HP, minCapa': minCapa})
    data.update({'HP, maxCapa': maxCapa})
    data.update({'HP, maintenanceCost': maintenanceCost})
    data.update({'HP, installationCost': installationCost})
    data.update({'HP, planificationCost': planificationCost})
    data.update({'HP, investmentCost': investmentCost})
    data.update({'HP, investmentBaseCost': investmentBaseCost})
    data.update({'HP, operationGWP': operationGWP})

    ## Storage data
    Storage = pd.read_excel(os.path.join(inputDataPath, 'SpatialDataTest', 'data_indiv.xlsx'),
                            sheet_name="Storage", index_col=0, engine='openpyxl', usecols="B:AA")

    #Battery
    minCapa = Storage.loc['Min_capacity', 'Battery']
    maxCapa = Storage.loc['Max_capacity', 'Battery']
    maxSOC = Storage.loc['MaxSOC', 'Battery']
    minSOC = Storage.loc['MinSOC', 'Battery']
    effCharge = Storage.loc['Efficiency_of_charging', 'Battery']
    effDischarge = Storage.loc['Efficiency_of_discharging', 'Battery']
    installationCost = Storage.loc['InstallationCost', 'Battery']
    planificationCost = Storage.loc['PlanificationCost', 'Battery']
    investmentCost = Storage.loc['InvestmentCost', 'Battery']
    investmentBaseCost = Storage.loc['InvestmentCostBase', 'Battery']
    operationGWP = Storage.loc['GWP', 'Battery']

    data.update({'Battery, minCapa': minCapa})
    data.update({'Battery, maxCapa': maxCapa})
    data.update({'Battery, maxSOC': maxSOC})
    data.update({'Battery, minSOC': minSOC})
    data.update({'Battery, effCharge': effCharge})
    data.update({'Battery, effDischarge': effDischarge})
    data.update({'Battery, installationCost': installationCost})
    data.update({'Battery, planificationCost': planificationCost})
    data.update({'Battery, investmentCost': investmentCost})
    data.update({'Battery, investmentBaseCost': investmentBaseCost})
    data.update({'Battery, operationGWP': operationGWP})

    # Hot water storage
    minCapa = Storage.loc['Min_capacity', 'Hot_water']
    maxCapa = Storage.loc['Max_capacity', 'Hot_water']
    maxSOC = Storage.loc['MaxSOC', 'Hot_water']
    minSOC = Storage.loc['MinSOC', 'Hot_water']
    effCharge = Storage.loc['Efficiency_of_charging', 'Hot_water']
    effDischarge = Storage.loc['Efficiency_of_discharging', 'Hot_water']
    installationCost = Storage.loc['InstallationCost', 'Hot_water']
    planificationCost = Storage.loc['PlanificationCost', 'Hot_water']
    investmentCost = Storage.loc['InvestmentCost', 'Hot_water']
    investmentBaseCost = Storage.loc['InvestmentCostBase', 'Hot_water']
    operationGWP = Storage.loc['GWP', 'Hot_water']

    data.update({'HW, minCapa': minCapa})
    data.update({'HW, maxCapa': maxCapa})
    data.update({'HW, maxSOC': maxSOC})
    data.update({'HW, minSOC': minSOC})
    data.update({'HW, effCharge': effCharge})
    data.update({'HW, effDischarge': effDischarge})
    data.update({'HW, installationCost': installationCost})
    data.update({'HW, planificationCost': planificationCost})
    data.update({'HW, investmentCost': investmentCost})
    data.update({'HW, investmentBaseCost': investmentBaseCost})
    data.update({'HW, operationGWP': operationGWP})

    return data
