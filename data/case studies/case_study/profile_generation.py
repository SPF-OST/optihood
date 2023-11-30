import os

import datetime
from datetime import time as settime
from workalendar.europe.switzerland import Bern

import numpy as np
import pandas as pd
from matplotlib import pyplot as plt
from matplotlib.ticker import MaxNLocator

import demandlib.bdew as bdew
import demandlib.particular_profiles as profiles
import numpy as np
from math import floor, ceil, modf

def shift_profiles(df, shift):
    # time shift value
    df['demand_shifted'] = 0
    demand_col = [c for c in df.columns if 'Demand' in c][0]
    for r in df.itertuples():
        frac, whole = modf(shift)
        frac = abs(frac)
        if shift > 0:
            period_high = ceil(shift)
        else:
            period_high = floor(shift)
        id = r.Index + datetime.timedelta(hours=period_high)
        if id in df.index:
            df.loc[id, 'demand_shifted'] += r.__getattribute__(demand_col) * frac
        id = r.Index + datetime.timedelta(hours=whole)
        if id in df.index:
            df.loc[id, 'demand_shifted'] += r.__getattribute__(demand_col) * (1 - frac)
    return df['demand_shifted'].values

def generateProfiles(building, buildingDict, pathToSave, demandDict, shift, year, holidays, temperature):
    all_elec_demand = pd.DataFrame()
    for building_type, building_data in buildingDict.items():
        type = building_data['elec']
        ann_el_demand = {type: (demandDict[type] * building_data['elec_m2'])}
        e_slp = bdew.ElecSlp(year, holidays=holidays)
        elec_demand: type = e_slp.get_profile(ann_el_demand)
        elec_demand = elec_demand.resample("H").mean()

        all_elec_demand = pd.concat([all_elec_demand, elec_demand], axis=1)

    all_elec_demand['Total'] = all_elec_demand.sum(axis=1)

    filename = f'{building}.csv'
    all_elec_demand.index.name = 'timestamp'
    all_elec_demand.to_csv(os.path.join(pathToSave, filename), sep=';')

if __name__ == '__main__':
    # File with ambient temperature data
    filename = "Temperature.csv"
    weatherDataPath = os.path.join(r"os.getcwd()", r"..\data\excels", filename)

    profileGenFolderName = "profileGen.csv"
    profileGenPath = os.path.join(r"os.getcwd()", r"..\data\excels", "profileGen.csv")

    # path where the profiles should be saved
    profilesFolder = os.path.join(r"os.getcwd()", r"..\data\demand_profiles")

    temperature = pd.read_csv(weatherDataPath, sep=';')["Tamb"]

    year = 2022

    elecw_perm2_res = 17.7      #gained from the SIA 2024 data Wohnen MFH on page 44 under Leistungbedarf pro Raumnutzung
    elecw_perm2_off = 24.8      #gained from the SIA 2024 data Grossraumbüro on page 44 under Leistungbedarf pro Raumnutzung

    cal = Bern()
    holidays = dict(cal.holidays(year))

    building_class = 1      # based on percentage of old buildings in the building stock

    if not os.path.exists(profilesFolder):
        os.mkdir(profilesFolder)

    # for stochastic profiles
    standard_dev = 1.5
    rng = np.random.default_rng()
    timeshifts = rng.normal(scale=standard_dev, size=6)
    # Plotting the histogram.
    ax = plt.figure().gca()
    plt.hist(timeshifts, bins=20, alpha=0.6, color='g')
    ax.yaxis.set_major_locator(MaxNLocator(integer=True))
    plt.show()
    np.savetxt(os.path.join(profilesFolder, 'timeshifts.csv'), timeshifts, delimiter=',')

    #test(year, holidays, temperature)

    buildingDict = {
        'office': {'elec': 'g1', 'building_class': building_class, 'elec_m2': elecw_perm2_off},
        'mfh': {'elec': 'h0', 'building_class': building_class, 'elec_m2': elecw_perm2_res}
    }

    annualDemands = pd.read_csv(profileGenPath, sep=";")
    timeshifts = pd.Series(pd.read_csv(os.path.join(profilesFolder, 'timeshifts.csv'), delimiter=',', header=None)[0])
    demandDict = {}
    for row in annualDemands.itertuples():
        demandDict[row.Building] = {'h0': row.Area_Wohnen_m2,
                                    'g1': row.Area_Buro_m2}

    i = 0
    for b in demandDict.keys():
        #generateProfiles(b, buildingDict, profilesFolder, demandDict[b], year, holidays, temperature)       #Only one function should be active at a time.
        nProDemands = pd.read_csv(os.path.join(profilesFolder, f'{b}.csv'), sep=';')
        nProDemands['timestamp'] = pd.to_datetime(nProDemands['timestamp'], format="%d.%m.%Y %H:%M")
        nProDemands.set_index('timestamp', inplace=True)

        nProDemands['electricityDemand'] = shift_profiles(pd.DataFrame(nProDemands['electricityDemand'], index=nProDemands.index), timeshifts[i])
        nProDemands['domesticHotWaterDemand'] = shift_profiles(pd.DataFrame(nProDemands['domesticHotWaterDemand'], index=nProDemands.index), timeshifts[i])

        filename = f'shifted_{b}.csv'
        nProDemands.to_csv(os.path.join(profilesFolder, filename), sep=';')

        i += 1