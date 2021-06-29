

import pytrnsys.rsim.runParallelTrnsys as runTrnsys
import os, sys

if __name__ == '__main__':

    pathBase = os.getcwd()

    # nameConfig = "buildingRun"
    nameConfig = "runBuildingFit"

    configFile = nameConfig + ".config"

    nameDeck = nameConfig

    runTool = runTrnsys.RunParallelTrnsys(pathBase, nameDeck)

    runTool.readConfig(pathBase, configFile)

    runTool.getConfig()

    runTool.runConfig()

    runTool.runParallel()


