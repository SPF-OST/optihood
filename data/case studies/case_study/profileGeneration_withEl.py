import os

import datetime
from datetime import time as settime
from workalendar.europe.switzerland import Bern

import numpy as np
import pandas as pd
from matplotlib import pyplot as plt

import demandlib.bdew as bdew
import demandlib.particular_profiles as profiles

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

def generateProfiles(type, buildingDict, pathToSave, annualDemands, year, holidays, temperature):

    for n in range(buildingDict['num']):
        # annual electricity demands in kWh
        ann_el_demand= {buildingDict['elec']: annualDemands['elec'][n]}

        # annual heating demands  in kWh
        ann_heat_demand = annualDemands['heat_sh_only'][n]

        # annual heating + DHW demands  in kWh
        ann_dhw_demand = annualDemands['heat_total'][n]

        #################################
        #  ELECTRICITY DEMAND PROFILES  #
        #################################
        e_slp = bdew.ElecSlp(year, holidays=holidays)
        elec_demand = e_slp.get_profile(ann_el_demand)
        """ The values in the DataFrame are 15 minute values with a power unit. Summing up a table with 15min values
            the result will be of the unit 'kW15minutes'. The result would then be divided by 4 to get kWh like so:
            print(elec_demand.sum()/4)
        """
        # Resample 15-minute values to hourly values
        elec_demand = elec_demand.resample("H").mean()
        elec_demand.columns = ['electricityDemand']

        #################################
        #    HEATING DEMAND PROFILES    #
        #################################

        # Create DataFrame for heating data for 2021
        heat_demand = pd.DataFrame(
            index=pd.date_range(
                datetime.datetime(year, 1, 1, 0), periods=8760, freq="H"
            )
        )

        # Results here are already in hourly timestep
        heat_demand['spaceHeatingDemand'] = bdew.HeatBuilding(
            heat_demand.index,
            holidays=holidays,
            temperature=temperature,
            shlp_type=buildingDict['heat'],
            building_class=buildingDict['building_class'],
            wind_class=buildingDict['wind_class'],
            annual_heat_demand=ann_heat_demand,
            ww_incl=False,
            name=buildingDict['heat'],
        ).get_bdew_profile()

        #################################
        #      DHW DEMAND PROFILES      #
        #################################

        # Create DataFrame for heating data for 2021
        dhw_demand = pd.DataFrame(
            index=pd.date_range(
                datetime.datetime(year, 1, 1, 0), periods=8760, freq="H"
            )
        )

        # Results here are already in hourly timestep
        dhw_demand["domesticHotWaterDemand"] = bdew.HeatBuilding(
            heat_demand.index,
            holidays=holidays,
            temperature=temperature,
            shlp_type=buildingDict['heat'],
            building_class=buildingDict['building_class'],
            wind_class=buildingDict['wind_class'],
            annual_heat_demand=ann_dhw_demand,
            ww_incl=True,  # decider whether warm water load is included in the heat load profile
            name=buildingDict['heat'],
        ).get_bdew_profile()

        # get only DHW demands (subtract heating demands from the time series)
        dhw_demand["domesticHotWaterDemand"] = dhw_demand["domesticHotWaterDemand"] - heat_demand["spaceHeatingDemand"]
        dhw_demand["domesticHotWaterDemand"][dhw_demand["domesticHotWaterDemand"] < 0] = 0
        demand = pd.concat([elec_demand, heat_demand, dhw_demand], axis=1)
        filename = f'{type}_{n+1}.csv'
        demand.index.name = 'timestamp'
        demand.to_csv(os.path.join(pathToSave, filename), sep=';')


if __name__ == '__main__':
    # File with ambient temperature data
    filename = "temperature.csv"
    weatherDataPath = os.path.join(os.getcwd(),"data", filename)

    # path where the profiles should be saved
    profilesFolder = os.path.join(os.getcwd(),"data","profiles_all_51")

    temperature = pd.read_csv(weatherDataPath, sep=';')["temperature"]

    year = 2021

    cal = Bern()
    holidays = dict(cal.holidays(year))

    building_class = 1      # based on percentage of old buildings in the building stock

    # building_class (int) – class of building according to bdew classification possible numbers are: 1 - 11
    # wind_class (int) – wind classification for building location (0=not windy or 1=windy)

    buildingDict = {
        'office': {'elec': 'g1', 'heat': 'ghd', 'num': 3, 'building_class': building_class, 'wind_class': 0},
        'sfh': {'elec': 'h0', 'heat': 'efh', 'num': 12, 'building_class': building_class, 'wind_class': 0},
        'trade': {'elec': 'g0', 'heat': 'ghd', 'num': 3, 'building_class': building_class, 'wind_class': 0},
        'hotel': {'elec': 'g2', 'heat': 'gbh', 'num': 2, 'building_class': building_class, 'wind_class': 0},
        'sports': {'elec': 'g2', 'heat': 'ghd', 'num': 1, 'building_class': building_class, 'wind_class': 0},
        'mfh': {'elec': 'h0', 'heat': 'mfh', 'num': 25, 'building_class': building_class, 'wind_class': 0},
        'school': {'elec': 'g1', 'heat': 'ghd', 'num': 1, 'building_class': building_class, 'wind_class': 0},
        'shop': {'elec': 'g4', 'heat': 'gha', 'num': 4, 'building_class': building_class, 'wind_class': 0}
        }

    # annual demands  in kWh
    #old values kWh/m2/a assumption
    """annualDemands = {'office': {'elec':[26134], 'heat_sh_only':[4654], 'heat_total':[5728]},
                    'sfh': {'elec':[680, 672, 828, 1872], 'heat_sh_only':[2210, 4032, 3519, 6240], 'heat_total':[2550, 4256, 4761, 7176]},
                    'trade': {'elec':[38016], 'heat_sh_only':[70752], 'heat_total':[78144]},
                    'hotel': {'elec':[335475], 'heat_sh_only':[521850], 'heat_total':[715680]},
                    'sports': {'elec':[473550], 'heat_sh_only':[249690], 'heat_total':[275520]},
                    'mfh': {'elec':[6006, 5370, 5841, 5874, 7602], 'heat_sh_only':[24024, 23628, 22833, 22962, 23892], 'heat_total':[30030, 28998, 29736, 27768, 30951]},
                    'school': {'elec':[83028], 'heat_sh_only':[207570], 'heat_total':[232101]},
                    'shop': {'elec':[743820], 'heat_sh_only':[918390], 'heat_total':[1020855]}}"""
    # old values MWh/a assumption
    """annualDemands = {'office': {'elec': [73000], 'heat_sh_only': [13000], 'heat_total': [16000]},
                     'sfh': {'elec': [4000, 3000, 4000, 6000], 'heat_sh_only': [13000, 18000, 17000, 20000],
                             'heat_total': [15000, 19000, 23000, 23000]},
                     'trade': {'elec': [36000], 'heat_sh_only': [67000], 'heat_total': [74000]},
                     'hotel': {'elec': [135000], 'heat_sh_only': [210000], 'heat_total': [288000]},
                     'sports': {'elec': [165000], 'heat_sh_only': [87000], 'heat_total': [96000]},
                     'mfh': {'elec': [11000, 10000, 11000, 11000, 14000],
                             'heat_sh_only': [44000, 44000, 43000, 43000, 44000],
                             'heat_total': [55000, 54000, 56000, 52000, 57000]},
                     'school': {'elec': [44000], 'heat_sh_only': [145000], 'heat_total': [162000]},
                     'shop': {'elec': [196000], 'heat_sh_only': [242000], 'heat_total': [269000]}}"""

    annualDemands = {'office': {'elec': [73000, 86000, 58000], 'heat_sh_only': [13000, 45000, 169000], 'heat_total': [16000, 54000, 191000]},
                     'sfh': {'elec': [4000, 3000, 4000, 6000, 9000, 2000, 7000, 3000, 3000, 2000, 8000, 9000], 'heat_sh_only': [13000, 18000, 17000, 20000, 9000, 11000, 12000, 23000, 14000, 16000, 27000, 26000],
                             'heat_total': [15000, 19000, 23000, 23000, 12000, 12000, 14000, 25000, 15000, 18000, 28000, 29000]},
                     'trade': {'elec': [36000, 215000, 20000], 'heat_sh_only': [67000, 17000, 35000], 'heat_total': [74000, 18000, 39000]},
                     'hotel': {'elec': [13500, 106000], 'heat_sh_only': [285000, 128000], 'heat_total': [378000, 236000]},
                     'sports': {'elec': [165000], 'heat_sh_only': [87000], 'heat_total': [96000]},
                     'mfh': {'elec': [11000, 10000, 11000, 11000, 14000, 12000, 16000, 14000, 24000, 59000, 18000, 24000, 22000, 17000, 20000, 20000, 25000, 23000, 21000, 23000, 54000, 18000, 24000, 14000, 15000],
                             'heat_sh_only': [44000, 44000, 43000, 43000, 44000, 44000, 47000, 47000, 113000, 108000, 108000, 99000, 97000, 99000, 88000, 113000, 88000, 112000, 104000, 104000, 92000, 92000, 78000, 59000, 55000],
                             'heat_total': [55000, 54000, 56000, 52000, 57000, 57000, 55000, 59000, 139000, 137000, 131000, 123000, 127000, 124000, 111000, 132000, 118000, 143000, 134000, 133000, 109000, 110000, 106000, 73000, 65000]},
                     'school': {'elec': [44000], 'heat_sh_only': [145000], 'heat_total': [162000]},
                     'shop': {'elec': [196000, 495000, 269000, 129000], 'heat_sh_only': [242000, 320000, 198000, 58000], 'heat_total': [269000, 382000, 239000, 65000]}}

    """annualDemands = {'mfh': {'elec': [31968, 26520, 23980, 18785, 25560, 26640, 32100, 30222, 26838, 29394, 71928, 23976],
                             'heat_sh_only': [150516, 109395, 105730, 109395, 112464, 150516, 112992, 147168, 132912, 132912, 122544, 122544],
                             'heat_total': [185148, 135915, 138430, 137020, 141858, 175824, 151512, 187902, 171252, 169974, 145188, 146520]},}"""

    """annualDemands = {
        'mfh': {'elec': [31968, 31968, 31968, 31968],
                'heat_sh_only': [150516, 150516, 150516, 150516],
                'heat_total': [185148, 185148, 185148, 185148]}, }"""

    #test(year, holidays, temperature)

    if not os.path.exists(profilesFolder):
        os.mkdir(profilesFolder)

    for type in annualDemands.keys():
        generateProfiles(type, buildingDict[type], profilesFolder, annualDemands[type], year, holidays, temperature)

    print("")



