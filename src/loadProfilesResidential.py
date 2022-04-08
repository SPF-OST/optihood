import numpy as np
import pandas as pd
import os


class Residential:
    inputFilePath = "..\data\excels\\"
    outputFilePath = "..\data\excels\demand_profiles\\"
    type = {"Electricity consumption (Light + Equipment) [kWh]": "electricityDemand",
            "Heating demand [W]": "spaceHeatingDemand", "DHW demand [kWh]": "domesticHotWaterDemand"}
    demandProfiles = pd.DataFrame(columns=["electricityDemand", "spaceHeatingDemand", "domesticHotWaterDemand"])

    def __init__(self, df):
        self.label = df["number"]
        self.buildingType = df["type"]  # "MFH30" or "MFH90" or "MFH150"
        self.numberOfFloors = df["nb_floors"]

        self.refBuildingProfile = pd.read_excel(os.path.join(self.inputFilePath, "Profiles_MFH30_90_150.xlsx"),
                                                header=[0, 1],
                                                index_col=[0],
                                                sheet_name=self.buildingType)
        if self.buildingType == "MFH150":
            self.apptPerFloor = 4
        else:
            self.apptPerFloor = 2

    def create_profile(self):
        for key, value in self.type.items():
            if key == "Heating demand [W]":
                div = 1000
            else:
                div = 1

            groundFloor = self.refBuildingProfile[key].iloc[:, 0:self.apptPerFloor].sum(axis=1)/div
            middleFloor = self.refBuildingProfile[key].iloc[:, self.apptPerFloor:2*self.apptPerFloor].sum(axis=1)/div
            topFloor = self.refBuildingProfile[key].iloc[:, 2*self.apptPerFloor:3*self.apptPerFloor].sum(axis=1)/div
            self.demandProfiles[value] = groundFloor + topFloor + middleFloor*(self.numberOfFloors-2)

        index = pd.date_range("2018-01-01 00:00:00", "2018-12-31 23:00:00", freq="60min")
        self.demandProfiles = self.demandProfiles.set_index(index)
        self.demandProfiles.index.name = 'timestamp'

        outputFileName = f"{self.label}_{self.buildingType}_{self.numberOfFloors}Floors.csv"
        if not os.path.exists(self.outputFilePath):
            os.makedirs(self.outputFilePath)
        self.demandProfiles.to_csv(os.path.join(self.outputFilePath, outputFileName), sep=";")









