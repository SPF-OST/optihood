# -*- coding: utf-8 -*-
"""
Created on Wed Jun 22 10:45:54 2016

@author: dcarbone
"""
import models.yumHeatPumpFitReport as fit
#import pytrnsys_spf.models.
import os
import getpass

if __name__ == '__main__':

    pathBase = os.getcwd()

    compareWithTRNSYS = False
    
#    name = "propane"   
#     name = "propane_wTow"

#    name = "CO2"         
#    name = "R134a"
    name = "R410A"
    namePath="C:\Daten\OngoingProject\OptimEase\models\heatpumpfit"
#    name="Propane_Now"
    # name="Propane_Min"
    # name="Propane_Med"

    # name="Propane_Par_Nom"

    # namePath = name

    path = os.path.join(pathBase,namePath,name)
                 
    userName = getpass.getuser()

    inputs = {                 
            'cpFluidEvaporator' : 3816.,
            'cpFluidCondenser' : 4190.,
#            'Model' : "Average Temperature", #  "Inlet/Outlet Temperature","Average Temperature"
            'Model' : "Inlet/Outlet Temperature",
            'User' : userName
    }
         
    tool = fit.YumHeatPumpFitReport(path,name,inputs)
    tool.setHeatPumpData()
            
    tool.calculateFit()
    tool.calculateNominalConditions()
    tool.calculateHeatPump()
#    tool.calculatePerformances()
    tool.doc.cleanMode = True
    tool.createLatexReport()
    
    if(compareWithTRNSYS):
        tool.exportFileAsTrnsysReadIn()
        tool.exportTrnsysDeck()
        tool.executeTRNSYS()
        tool.readTRNSYSOutFile()
        tool.createLatexTrnsysVsPython()