import numpy as np
import pandas as pd
import math
import os
import matplotlib.pyplot as plt


class Shopping:
    """
    docstring to be completed
    
    
    
    
    
    
    """
    outputFilePath = "..\data\excels\demand_profiles\\"

    def __init__(self, df):
        # label of the building
        self.label = int(df["number"])

        # leasable surface
        self.S = df["surface"]
        
        # proportion of food shop
        self.f_food = df["food_proportion"]
        
        # specific annual consumption
        self.spE_fri = df["refrigeration_consumption"]
        self.spE_light = df["light_consumption"]
        self.spE_hvac = df["hvac_consumption"]
        self.spE_othr = df["other_consumption"]
        
        # Opening hours (from - to)
        self.frm = df["opening_hour"]
        self.to = df["closing_hour"]
        self.days = df["days_opened"]

        # Annual energy consumptions (kWh/an) [1][2]
        self.E_fri = self.spE_fri * self.f_food * self.S
        self.E_light = self.spE_light * self.S
        self.E_hvac = self.spE_hvac * self.S
        self.E_othr = self.spE_othr * self.S

    def info(self):
        print("the leasable surface is %g m^2" % self.S)
        print("the fraction of food store is %g" % self.f_food)
        print("the specific energie demand for refrigeration is %g kWh/m^2" % self.spE_fri)
        print("the specific energie demand for lighting is %g kWh/m^2" % self.spE_light)
        print("the specific energie demand for HVAC is %g kWh/m^2" % self.spE_hvac)
        print("the specific energie demand for other usage is %g kWh/m^2" % self.spE_othr)
        print("open %g day from %gh to %gh" % (self.days, self.frm, self.to))

    def create_profile(self):
        """
        create a dataframe in the class object shop
        save dataframe to csv file
        """

        # Refrigeration mean annual power (day/night together) 
        p_fri_mean = self.E_fri / 8760 #kW
        
        self.P = np.zeros(365)
        n = np.linspace(1,365,365)
        # Annual profile of mean refrigeration power [3]
        for i,p in enumerate(self.P):
            self.P[i] = p_fri_mean * ( 1 - 0.22 * math.cos ( 2 * math.pi * n[i] / 365 ))
            
#       plt.plot(self.P)


        # 1 year hourly profile based on Flexynets opening hours: 8h/20h 
        p_tot = np.linspace(1,8760,8760)
        p_fri = np.linspace(1,8760,8760)
        p_light = np.linspace(1,8760,8760)
        p_hvac = np.linspace(1,8760,8760)
        p_othr = np.linspace(1,8760,8760)
        hours = np.linspace(1,8760,8760)

        i = 0 
        k = 0
        K = 0
        for T in p_tot:
            H = T - k * 24
        
            # Night / Day / Week-end
            if H < self.frm or H > self.to or k % 7 >= self.days:
                p_fri[i] = 1.6/1.8 * self.P[k]                   # kW
                p_light[i] = 0                              # kW
                p_hvac[i] = 37.5/137.5 * self.E_hvac / (24*365) # kW
                p_othr[i] = 0
                p_tot[i] = p_fri[i] + p_light[i] + p_hvac[i] + p_othr[i]
                
            else:
                p_fri[i] = 2/1.8 * self.P[k]                     # kW
                p_light[i] = self.E_light / ((self.to-self.frm)*365)       # kW
                p_hvac[i] = 100/137.5 * self.E_hvac / (24*365)  # kW
                p_othr[i] = self.E_othr / ((self.to-self.frm)*365)
                p_tot[i] = p_fri[i] + p_light[i] + p_hvac[i] + p_othr[i]
            hours[i] = H
            K += 1
            k = int(K // 24)
            i += 1
        
        # put profil in dataframe
        index = pd.date_range("2018-01-01 00:00:00", "2018-12-31 23:00:00", freq="60min")
        d = {'electricityDemand': p_fri/3 + p_light + p_othr, 'spaceHeatingDemand': 0.0, 'domesticHotWaterDemand': 0.0}
        profile = pd.DataFrame(data=d)
        profile = profile.set_index(index)
        profile.index.name = 'timestamp'
        
        # save to csv
        outputFileName = f"{self.label}_mall_profile.csv"
        if not os.path.exists(self.outputFilePath):
            os.makedirs(self.outputFilePath)
        profile.to_csv(os.path.join(self.outputFilePath, outputFileName), sep=";")
        
        
        
        