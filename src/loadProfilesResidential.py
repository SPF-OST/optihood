import numpy as np
import pandas as pd
import os

if __name__=="__main__":
    inputFilePath =  "..\data\excels\\"
    outputFilePath = "..\data\excels\demand_profiles\\"

    buildingType = "MFH30"  # "MFH30" or "MFH90" or "MFH150"
    numberOfFloors = 6

    refBuildingProfile = pd.read_excel(os.path.join(inputFilePath, "Profiles_MFH30_90_150.xls"),
                                       header=[0, 1],
                                       index_col=[0],
                                       sheet_name=buildingType)

    demandProfiles = pd.DataFrame(columns=["electricityDemand", "spaceHeatingDemand", "domesticHotWaterDemand"])

    if buildingType == "MFH150":
        apptPerFloor = 4
    else:
        apptPerFloor = 2

    type = {"Electricity consumption (Light + Equipment) [kWh]": "electricityDemand", "Heating demand [W]": "spaceHeatingDemand", "DHW demand [kWh]": "domesticHotWaterDemand"}

    for key, value in type.items():
        if key == "Heating demand [W]":
            div = 1000
        else:
            div = 1

        groundFloor = refBuildingProfile[key].iloc[:, 0:apptPerFloor].sum(axis=1)/div
        middleFloor = refBuildingProfile[key].iloc[:, apptPerFloor:2*apptPerFloor].sum(axis=1)/div
        topFloor = refBuildingProfile[key].iloc[:, 2*apptPerFloor:3*apptPerFloor].sum(axis=1)/div
        demandProfiles[value] = groundFloor + topFloor + middleFloor*(numberOfFloors-2)

    index = pd.date_range("2018-01-01 00:00:00", "2018-12-31 23:00:00", freq="60min")
    demandProfiles = demandProfiles.set_index(index)
    demandProfiles.index.name = 'timestamp'

    outputFileName = f"{buildingType}_{numberOfFloors}Floors.csv"
    if not os.path.exists(outputFilePath):
        os.makedirs(outputFilePath)
    demandProfiles.to_csv(os.path.join(outputFilePath, outputFileName), sep=";")









