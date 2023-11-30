import os

import datetime
from datetime import time as settime
from workalendar.europe.switzerland import Zurich

import numpy as np
import pandas as pd
from matplotlib import pyplot as plt
from matplotlib.ticker import MaxNLocator

import demandlib.bdew as bdew
import demandlib.particular_profiles as profiles
import numpy as np
from math import floor, ceil, modf

def test(year, holidays, temperature):
    # annual electricity demands in kWh
    ann_el_demand_per_sector = {
        "g0": 3000,
        "h0": 3000,
        "h0_dyn": 3000,
        "i0": 3000,
        "i1": 3000,
        "i2": 3000,
        "g6": 5000,
    }

    # annual heating demands  in kWh
    ann_heat_demands_per_type = {"efh": 25000, "mfh": 80000, "ghd": 140000}

    # annual heating + DHW demands  in kWh
    ann_dhw_demands_per_type = {"efh": 40000, "mfh": 100000, "ghd": 160000}

    #################################
    #  ELECTRICITY DEMAND PROFILES  #
    #################################

    # read standard load profiles
    e_slp = bdew.ElecSlp(year, holidays=holidays)

    # multiply given annual demand with timeseries
    elec_demand = e_slp.get_profile(ann_el_demand_per_sector)

    # Add the slp for the industrial group
    ilp = profiles.IndustrialLoadProfile(e_slp.date_time_index, holidays=holidays)

    # Beginning and end of workday, weekdays and weekend days, and scaling
    # factors by default
    elec_demand["i0"] = ilp.simple_profile(ann_el_demand_per_sector["i0"])

    # Set beginning of workday to 9 am
    elec_demand["i1"] = ilp.simple_profile(
        ann_el_demand_per_sector["i1"], am=settime(9, 0, 0)
    )

    # Change scaling factors
    elec_demand["i2"] = ilp.simple_profile(
        ann_el_demand_per_sector["i2"],
        profile_factors={
            "week": {"day": 1.0, "night": 0.8},
            "weekend": {"day": 0.8, "night": 0.6},
        },
    )

    """ The values in the DataFrame are 15 minute values with a power unit. Summing up a table with 15min values
        the result will be of the unit 'kW15minutes'. The result would then be divided by 4 to get kWh like so:
        print(elec_demand.sum()/4)
    """

    # Resample 15-minute values to hourly values
    elec_demand = elec_demand.resample("H").mean()
    print(elec_demand.sum())

    # Plot demand
    ax = elec_demand.plot()
    ax.set_xlabel("Date")
    ax.set_ylabel("Power demand in kWh")
    plt.show()

    print(elec_demand)

    #################################
    #    HEATING DEMAND PROFILES    #
    #################################

    # Create DataFrame for heating data for 2021
    heat_demand = pd.DataFrame(
        index=pd.date_range(
            datetime.datetime(year, 1, 1, 0), periods=8760, freq="H"
        )
    )

    # Single family house (efh: Einfamilienhaus)
    heat_demand["efh"] = bdew.HeatBuilding(
        heat_demand.index,
        holidays=holidays,
        temperature=temperature,
        shlp_type="EFH",
        building_class=1,
        wind_class=1,
        annual_heat_demand=ann_heat_demands_per_type["efh"],
        ww_incl=False,
        name="EFH",
    ).get_bdew_profile()

    # Multi family house (mfh: Mehrfamilienhaus)
    heat_demand["mfh"] = bdew.HeatBuilding(
        heat_demand.index,
        holidays=holidays,
        temperature=temperature,
        shlp_type="MFH",
        building_class=2,
        wind_class=0,
        annual_heat_demand=ann_heat_demands_per_type["mfh"],
        ww_incl=False,  # decider whether warm water load is included in the heat load profile
        name="MFH",
    ).get_bdew_profile()

    # Industry, trade, service (ghd: Gewerbe, Handel, Dienstleistung)
    heat_demand["ghd"] = bdew.HeatBuilding(
        heat_demand.index,
        holidays=holidays,
        temperature=temperature,
        shlp_type="ghd",
        wind_class=0,
        annual_heat_demand=ann_heat_demands_per_type["ghd"],
        ww_incl=False,
        name="ghd",
    ).get_bdew_profile()

    # Results here are already in hourly timestep
    # Plot demand of building
    ax = heat_demand.plot()
    ax.set_xlabel("Date")
    ax.set_ylabel("Heat demand in kWh")
    plt.show()

    print("Annual SH consumption: \n{}".format(heat_demand.sum()))

    print(heat_demand)

    #################################
    #      DHW DEMAND PROFILES      #
    #################################

    # Create DataFrame for heating data for 2021
    dhw_demand = pd.DataFrame(
        index=pd.date_range(
            datetime.datetime(year, 1, 1, 0), periods=8760, freq="H"
        )
    )

    # Single family house (efh: Einfamilienhaus)
    dhw_demand["efh"] = bdew.HeatBuilding(
        heat_demand.index,
        holidays=holidays,
        temperature=temperature,
        shlp_type="EFH",
        building_class=1,
        wind_class=1,
        annual_heat_demand=ann_dhw_demands_per_type["efh"],
        ww_incl=True,  # decider whether warm water load is included in the heat load profile
        name="EFH",
    ).get_bdew_profile()

    # Multi family house (mfh: Mehrfamilienhaus)
    dhw_demand["mfh"] = bdew.HeatBuilding(
        heat_demand.index,
        holidays=holidays,
        temperature=temperature,
        shlp_type="MFH",
        building_class=2,
        wind_class=0,
        annual_heat_demand=ann_dhw_demands_per_type["mfh"],
        ww_incl=True,  # decider whether warm water load is included in the heat load profile
        name="MFH",
    ).get_bdew_profile()

    # Industry, trade, service (ghd: Gewerbe, Handel, Dienstleistung)
    dhw_demand["ghd"] = bdew.HeatBuilding(
        heat_demand.index,
        holidays=holidays,
        temperature=temperature,
        shlp_type="ghd",
        wind_class=0,
        annual_heat_demand=ann_dhw_demands_per_type["ghd"],
        ww_incl=True,
        name="ghd",
    ).get_bdew_profile()

    # get only DHW demands (subtract heating demands from the time series)
    dhw_demand["efh"] = dhw_demand["efh"] - heat_demand["efh"]
    dhw_demand["mfh"] = dhw_demand["mfh"] - heat_demand["mfh"]
    dhw_demand["ghd"] = dhw_demand["ghd"] - heat_demand["ghd"]

    # Results here are already in hourly timestep
    # Plot demand of building
    ax = dhw_demand.plot()
    ax.set_xlabel("Date")
    ax.set_ylabel("DHW demand in kWh")
    plt.show()

    print("Annual DHW consumption: \n{}".format(heat_demand.sum()))

    print(dhw_demand)
    print("Test run of demand profiles generation was successful")

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

def generateProfiles(building, buildingDict, pathToSave, annualDemands, shift, year, holidays, temperature):

    # percentage of residential space in building, the remaining is for office use
    residential_space = float(annualDemands['mfh'])/(float(annualDemands['mfh']) + float(annualDemands['office']))

    # annual heating demands  in kWh
    ann_heat_demand = float(annualDemands['heat_sh_only'])
    ann_heat = {}
    ann_heat['mfh'] = residential_space*ann_heat_demand       # residential
    ann_heat['office'] = ann_heat_demand - ann_heat['mfh']     # office

    # Create DataFrame for heating data
    heat_demand = pd.DataFrame(0,
        index=pd.date_range(
            datetime.datetime(year, 1, 1, 0), periods=8760, freq="H"
        ), columns=['spaceHeatingDemand']
    )
    # Create DataFrame for heating data
    dhw_demand = pd.DataFrame(0,
        index=pd.date_range(
            datetime.datetime(year, 1, 1, 0), periods=8760, freq="H"
        ), columns=['domesticHotWaterDemand']
    )

    heat = pd.DataFrame()
    dhw = pd.DataFrame()

    for type in ['mfh', 'office']:
        #################################
        #    HEATING DEMAND PROFILES    #
        #################################
        # Results here are already in hourly timestep
        heat['spaceHeatingDemand'] = bdew.HeatBuilding(
            heat_demand.index,
            holidays=holidays,
            temperature=temperature,
            shlp_type=buildingDict[type]['heat'],
            building_class=buildingDict[type]['building_class'],
            wind_class=buildingDict[type]['wind_class'],
            annual_heat_demand=ann_heat[type],
            ww_incl=False,
            name=buildingDict[type]['heat'],
        ).get_bdew_profile()
        heat['spaceHeatingDemand'] = shift_profiles(heat, shift)
        heat_demand['spaceHeatingDemand'] += heat['spaceHeatingDemand'].values
        #################################
        #      DHW DEMAND PROFILES      #
        #################################
        # annual heating + DHW demands  in kWh
        ann_dhw = {}
        ann_dhw[type] = buildingDict[type]['dhw_m2'] * float(annualDemands[type])
        ann_dhw[type] += ann_heat[type]
        # Results here are already in hourly timestep
        dhw["domesticHotWaterDemand"] = bdew.HeatBuilding(
            heat_demand.index,
            holidays=holidays,
            temperature=temperature,
            shlp_type=buildingDict[type]['heat'],
            building_class=buildingDict[type]['building_class'],
            wind_class=buildingDict[type]['wind_class'],
            annual_heat_demand=ann_dhw[type],
            ww_incl=True,  # decider whether warm water load is included in the heat load profile
            name=buildingDict[type]['heat'],
        ).get_bdew_profile()
        dhw['domesticHotWaterDemand'] = shift_profiles(dhw, shift)
        # get only DHW demands (subtract heating demands from the time series)
        dhw["domesticHotWaterDemand"] = dhw["domesticHotWaterDemand"] - heat["spaceHeatingDemand"]
        dhw["domesticHotWaterDemand"][dhw["domesticHotWaterDemand"] < 0] = 0
        dhw_demand['domesticHotWaterDemand'] += dhw['domesticHotWaterDemand'].values
    demand = pd.concat([heat_demand, dhw_demand], axis=1)
    filename = f'{building}.csv'
    demand.index.name = 'timestamp'
    demand.to_csv(os.path.join(pathToSave, filename), sep=';')


if __name__ == '__main__':
    # File with ambient temperature data
    filename = "Temperature.csv"
    weatherDataPath = os.path.join(r"os.getcwd()", r"..\data\excels", filename)

    # path where the profiles should be saved
    profilesFolder = os.path.join(r"os.getcwd()", r"..\data\demand_profiles")

    temperature = pd.read_csv(weatherDataPath, sep=';')["Tamb"]

    year = 2022

    """ # From SIA 2024
    dhw_perm2_res = 16.9       # kWh/ m2 (annual)
    dhw_perm2_off = 3.6    # kWh/ m2 (annual)"""

    # from npro tool
    dhw_perm2_res = 12.5  # kWh/ m2 (annual)
    dhw_perm2_off = 8  # kWh/ m2 (annual)

    cal = Zurich()
    holidays = dict(cal.holidays(year))

    building_class = 1      # based on percentage of old buildings in the building stock

    if not os.path.exists(profilesFolder):
        os.mkdir(profilesFolder)

    # for stochastic profiles
    """standard_dev = 1.5
    rng = np.random.default_rng()
    timeshifts = rng.normal(scale=standard_dev, size=29)
    # Plotting the histogram.
    ax = plt.figure().gca()
    plt.hist(timeshifts, bins=20, alpha=0.6, color='g')
    ax.yaxis.set_major_locator(MaxNLocator(integer=True))
    plt.show()
    np.savetxt(os.path.join(profilesFolder,'timeshifts.csv'), timeshifts, delimiter=',')"""

    timeshifts = pd.Series(pd.read_csv(os.path.join(profilesFolder,'timeshifts.csv'), delimiter=',', header=None)[0])
    # building_class (int) – class of building according to bdew classification possible numbers are: 1 - 11
    # wind_class (int) – wind classification for building location (0=not windy or 1=windy)
    buildingDict = {
        'office': {'heat': 'ghd', 'building_class': 0, 'wind_class': 0, 'dhw_m2': dhw_perm2_off},
        'mfh': {'heat': 'mfh', 'building_class': building_class, 'wind_class': 0, 'dhw_m2': dhw_perm2_res},
        }

    # annual demands  in kWh
    annualDemands = pd.read_csv("profileGen.csv", sep=";")
    demandDict = {}
    for row in annualDemands.itertuples():
        demandDict[row.Building] = {'heat_sh_only': row.Q_heat_kWh,
                                    'mfh': row.Area_Wohnen_m2,
                                    'office': row.Area_Buro_m2}

    #test(year, holidays, temperature)


    i = 0
    for b in demandDict.keys():
        generateProfiles(b, buildingDict, profilesFolder, demandDict[b], timeshifts[i], year, holidays, temperature)
        i += 1