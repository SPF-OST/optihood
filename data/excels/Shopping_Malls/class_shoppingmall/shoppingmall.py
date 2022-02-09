import numpy as np
import pandas as pd
import math
import matplotlib.pyplot as plt

class shop:
    """
    docstring to be completed
    
    
    
    
    
    
    """
    def __init__(self,S,f_food,spE_fri,spE_light, spE_hvac, spE_othr, frm, to, days):
        # leasable surface
        self.S=S
        
        # proportion of food shop
        self.f_food = f_food
        
        # specific annuel comsumption
        self.spE_fri   = spE_fri
        self.spE_light = spE_light
        self.spE_hvac  = spE_hvac 
        self.spE_othr  = spE_othr
        
        # Opening hours (from - to)
        self.frm = frm
        self.to = to
        self.days = days
     
        
    def info(self):
        print("the leasable surface is %g m^2" % self.S)
        print("the fraction of food store is %g" % self.f_food)
        print("the specific energie demand for refrigeration is %g kWh/m^2" % self.spE_fri)
        print("the specific energie demand for lighting is %g kWh/m^2" % self.spE_light)
        print("the specific energie demand for HVAC is %g kWh/m^2" % self.spE_hvac)
        print("the specific energie demand for other usage is %g kWh/m^2" % self.spE_othr)
        print("open %g day from %gh to %gh" % (self.days, self.frm, self.to))
        
     
    def create_profile(self, filename = "mall_profile.csv"):
        """
        create a dataframe in the class object shop
        save dataframe to csv file
        """
        # Annual energy consumptions (kWh/an) [1][2]
        self.E_fri   =  self.spE_fri   * self.f_food * self.S
        self.E_light =  self.spE_light * self.S
        self.E_hvac  =  self.spE_hvac  * self.S 
        self.E_othr  =  self.spE_othr  * self.S
        
        # Refrigeration mean annual power (day/night together) 
        P_fri_mean = self.E_fri / 8760 #kW
        
        self.P = np.zeros(365)
        n = np.linspace(1,365,365)
        # Annual profile of mean refrigeration power [3]
        for i,p in enumerate(self.P):
            self.P[i] = P_fri_mean * ( 1 - 0.22 * math.cos ( 2 * math.pi * n[i] / 365 ))
            
#       plt.plot(self.P)


        # 1 year hourly profile based on Flexynets opening hours: 8h/20h 
        p_tot = np.linspace(1,8760,8760)
        p_fri = np.linspace(1,8760,8760)
        p_light = np.linspace(1,8760,8760)
        p_hvac = np.linspace(1,8760,8760)
        p_othr = np.linspace(1,8760,8760)
        heures = np.linspace(1,8760,8760)

        i = 0 
        k = 0
        K = 0
        for T in p_tot:
            H = T - k * 24
        
            # Night / Day
            if H < self.frm or H > self.to:
                p_fri[i] = 1.6/1.8 * self.P[k]                   # kW
                p_light[i] = 0                              # kW
                p_hvac[i] = 37.5/137.5 * self.E_hvac / (24*self.days) # kW
                p_othr[i] = 0
                p_tot[i] = p_fri[i] + p_light[i] + p_hvac[i] + p_othr[i]
                
            else:
                p_fri[i] = 2/1.8 * self.P[k]                     # kW
                p_light[i] = self.E_light / ((self.to-self.frm)*self.days)       # kW
                p_hvac[i] = 100/137.5 * self.E_hvac / (24*self.days)  # kW
                p_othr[i] = self.E_othr / ((self.to-self.frm)*self.days)
                p_tot[i] = p_fri[i] + p_light[i] + p_hvac[i] + p_othr[i]
            heures[i] = H
            K += 1
            k = int(K // 24)
            i += 1
        
        # put profil in dataframe
        d = {'heures': heures, 'total': p_tot, 'Refrigeration':p_fri, 'Lighting':p_light, 'HVAC':p_hvac, 'Other':p_othr}
        self.profile = pd.DataFrame(data=d)
        
        # save to csv
        self.profile.to_csv(filename)
        
        
        
        