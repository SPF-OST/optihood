

import pytrnsys.psim.processTrnsysDf as processTrnsys
from pytrnsys.psim import processParallelTrnsys as pParallelTrnsys
import os

if __name__ == '__main__':

    pathBase = os.getcwd()


    tool = pParallelTrnsys.ProcessParallelTrnsys()

    names = []

    names.append("buildingProcess.config")

    for name in names:
        tool.readConfig(pathBase,name)
        tool.process()
