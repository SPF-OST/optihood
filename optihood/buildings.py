import numpy as np
import oemof.solph as solph
import pandas as pd
from oemof.tools import logger
from oemof.tools import economics
import logging
from optihood.converters import *
from optihood.sources import PV
from optihood.storages import *
from optihood.sinks import SinkRCModel
from optihood.links import LinkTemperatureDemand
from optihood._helpers import *
import optihood.entities as _ent

intRate = 0.05

class Building:
    def __init__(self, label):
        self.__nodesList = []
        self.__inputs = []
        self.__technologies = []
        self.__costParam = {}
        self.__envParam = {}
        self.__busDict = {}
        self.__buildingLabel = label
        self.__linkBuses = []
        self.__heatSourceSinkBuses = ["heatSourceBus", "heatSinkBus"]


    def getBuildingLabel(self):
        return self.__buildingLabel

    def getNodesList(self):
        return self.__nodesList

    def getBusDict(self):
        return self.__busDict

    def getInputs(self):
        return self.__inputs

    def getTechnologies(self):
        return self.__technologies

    def getCostParam(self):
        return self.__costParam

    def getEnvParam(self):
        return self.__envParam

    def addBus(self, data, opt, mergeLinkBuses, mergeHeatSourceSink, electricityImpact, clusterSize, includeCarbonBenefits):
        # Create Bus objects from buses table
        for i, b in data.iterrows():
                if (mergeLinkBuses and b["label"] in self.__linkBuses) or (mergeHeatSourceSink and b["label"] in self.__heatSourceSinkBuses):
                    label = b["label"]
                else:
                    label = b["label"] + '__' + self.__buildingLabel

                if ((not mergeLinkBuses and not mergeHeatSourceSink) or (mergeLinkBuses and (self.__buildingLabel=='Building1' or label not in self.__linkBuses))) or ((not mergeHeatSourceSink and not mergeLinkBuses) or (mergeHeatSourceSink and (self.__buildingLabel=='Building1' or label not in self.__heatSourceSinkBuses))):
                    bus = solph.Bus(label=label)
                    self.__nodesList.append(bus)
                    self.__busDict[label] = bus
                    if opt=='costs':
                        if not clusterSize: varcost=float(b["excess costs"])
                        else:
                            varcost = None
                            for d in clusterSize:
                                temp = pd.Series(np.tile([float(b["excess costs"])*clusterSize[d]], 24))
                                if varcost is not None:
                                    varcost = varcost._append(temp, ignore_index=True)
                                else:
                                    varcost = temp
                    elif opt=='env' and includeCarbonBenefits:varcost=-electricityImpact['impact']
                    else: varcost=0
                    if b["excess"]:
                        self.__nodesList.append(
                            solph.components.Sink(
                                label="excess"+label,
                                inputs={
                                    self.__busDict[label]: solph.Flow(
                                        variable_costs=varcost
                                    )}))
                        # add the excess production cost to self.__costParam
                        self.__costParam["excess"+label] = float(b["excess costs"])
                    if "shortage" in b:
                        if b["shortage"]:
                            self.__nodesList.append(
                                solph.components.Source(
                                    label="shortage"+label,
                                    outputs={
                                        self.__busDict[label]: solph.Flow(
                                            variable_costs=float(b["shortage costs"])*(opt == "costs")  # if opt = "env" variable costs should be zero
                                        )}))
                            # add the excess production cost to self.__costParam
                            self.__costParam["shortage"+label] = float(b["shortage costs"])

        if (mergeLinkBuses or mergeHeatSourceSink) and self.__buildingLabel=='Building1':
            return self.__busDict

    def addToBusDict(self, busDictBuilding1, mergeType):
        if mergeType=='links':
            buses = self.__linkBuses
        elif mergeType =='heatSourceSink':
            buses = self.__heatSourceSinkBuses
        for label in buses:
            self.__busDict[label] = busDictBuilding1[label]

    def linkBuses(self, busesToMerge):
        for b in busesToMerge:
            if b == "electricity":
                self.__linkBuses.extend(["electricityBus", "electricityInBus"])
            elif b == "space_heat":
                self.__linkBuses.extend(["spaceHeatingBus", "shDemandBus"])
            elif b == "domestic_hot_water":
                self.__linkBuses.extend(["domesticHotWaterBus", "dhwDemandBus"])
            elif b == "heat_buses":
                self.__linkBuses.extend(["heatDemandBus0", "heatDemandBus2"])
            else:
                self.__linkBuses.append(b)

    def addPV(self, data, data_timeseries, opt, dispatchMode):
        # Create Source objects from table 'commodity sources'
        for i, s in data.iterrows():
                if opt == "costs":
                    epc=self._calculateInvest(s)[0]
                    base=self._calculateInvest(s)[1]
                    env_capa=float(s["impact_cap"]) / float(s["lifetime"])
                    env_flow=float(s["elec_impact"])
                    varc=0 # variable cost is only passed for environmental optimization if there are emissions per kWh of energy produced from the unit

                    envParam = [0, float(s["elec_impact"]), float(s["impact_cap"]) / float(s["lifetime"])]

                elif opt == "env":
                    epc = float(s["impact_cap"]) / float(s["lifetime"])
                    base = 0
                    env_capa = float(s["impact_cap"]) / float(s["lifetime"])
                    env_flow = float(s["elec_impact"])
                    varc = float(s["elec_impact"]) # variable cost is only passed for environmental optimization if there are emissions per kWh of energy produced from the unit

                    envParam = [0, float(s["elec_impact"]), float(s["impact_cap"]) / float(s["lifetime"])]

                # If roof area and zenith do not exist in the excel file
                if 'roof_area' not in s.keys():
                    s["roof_area"] = np.nan
                if 'zenith_angle' not in s.keys():
                    s["zenith_angle"] = np.nan
                if 'efficiency' not in s.keys():
                    s["efficiency"] = np.nan

                self.__nodesList.append(PV(s["label"], self.__buildingLabel,
                                           self.__busDict[s["to"] + '__' + self.__buildingLabel],
                                           float(s["peripheral_losses"]), float(s["latitude"]), float(s["longitude"]),
                                           float(s["tilt"]), float(s["efficiency"]), s["roof_area"],
                                           s["zenith_angle"], s["azimuth"],
                                           data_timeseries['gls'],
                                           data_timeseries['str.diffus'],
                                           data_timeseries['tre200h0'], float(s["capacity_min"]), float(s["capacity_max"]),
                                           epc, base, env_capa, env_flow, varc, dispatchMode))

                self.__envParam[s["label"] + '__' + self.__buildingLabel] = envParam

                self.__costParam[s["label"] + '__' + self.__buildingLabel] = [self._calculateInvest(s)[0],
                                                                              self._calculateInvest(s)[1]]
                self.__technologies.append(
                    [s["to"] + '__' + self.__buildingLabel, s["label"] + '__' + self.__buildingLabel])

    def addSolar(self, data, data_timeseries, opt, mergeLinkBuses, dispatchMode, temperatureLevels):
        # Create Source objects from table 'commodity sources'
        for i, s in data.iterrows():
                if mergeLinkBuses and s["from"] in self.__linkBuses:
                    inputBusLabel = s["from"]
                else:
                    inputBusLabel = s["from"] + '__' + self.__buildingLabel
                outputBuses = [self.__busDict[o + '__' + self.__buildingLabel] for o in s["to"].split(",")]
                connectBuses = [self.__busDict[c + '__' + self.__buildingLabel] for c in s["connect"].split(",")]
                if isinstance(s["delta_temp_n"], float) or isinstance(s["delta_temp_n"], int):
                    delta_temp_n = [float(s["delta_temp_n"])]
                else:
                    delta_temp_n = [float(t) for t in s["delta_temp_n"].split(",")]
                if opt == "costs":
                    epc=self._calculateInvest(s)[0]
                    base=self._calculateInvest(s)[1]
                    env_capa=float(s["impact_cap"]) / float(s["lifetime"])
                    env_flow=float(s["heat_impact"])
                    varc=0 # variable cost is only passed for environmental optimization if there are emissions per kWh of energy produced from the unit

                    envParam = [env_flow, 0, env_capa]

                elif opt == "env":
                    epc=float(s["impact_cap"]) / float(s["lifetime"])
                    base=0
                    env_capa= float(s["impact_cap"]) / float(s["lifetime"])
                    env_flow=float(s["heat_impact"])
                    varc= float(s["heat_impact"]) # variable cost is only passed for environmental optimization if there are emissions per kWh of energy produced from the unit

                    envParam = [env_flow, 0, env_capa]

                # If roof area and zenith do not exist in the excel file
                if 'roof_area' not in s.keys():
                    s["roof_area"] = np.nan
                if 'zenith_angle' not in s.keys():
                    s["zenith_angle"] = np.nan
                collector=SolarCollector(s["label"], self.__buildingLabel,
                                                       self.__busDict[inputBusLabel],
                                                       outputBuses,
                                                       connectBuses,
                                                       float(s["electrical_consumption"]), float(s["peripheral_losses"]), float(s["latitude"]),
                                                       float(s["longitude"]), float(s["tilt"]), s["roof_area"],
                                                       s["zenith_angle"], float(s["azimuth"]),
                                                       float(s["eta_0"]), float(s["a_1"]), float(s["a_2"]), float(s["temp_collector_inlet"]),
                                                       delta_temp_n, data_timeseries['gls'], data_timeseries['str.diffus'],
                                                        data_timeseries['tre200h0'], float(s["capacity_min"]), float(s["capacity_max"]),
                                                       epc, base, env_capa, env_flow, varc, dispatchMode)

                nodes = []
                for t in ["source", "transformer", "sink"]:
                    sh, T2, dhw = collector.getSolar(t)
                    if outputBuses.__len__() == 2:
                        nodes.extend([sh, dhw])
                    elif outputBuses.__len__() == 3:
                        nodes.extend([sh, T2, dhw])
                    else:
                        nodes.extend([sh])
                for x in nodes:
                    self.__nodesList.append(x)

                self.__envParam['heatSource_SH' + s['label'] + '__' + self.__buildingLabel] = envParam
                self.__costParam['heatSource_SH' + s['label'] + '__' + self.__buildingLabel] = [self._calculateInvest(s)[0],
                                                                                                self._calculateInvest(s)[1]]
                self.__technologies.append(
                    [outputBuses[0], s["label"] + 'SH__' + self.__buildingLabel])

                if outputBuses.__len__() >= 2:
                    self.__envParam['heatSource_DHW' + s['label'] + '__' + self.__buildingLabel] = [env_flow, 0, 0]
                    self.__costParam['heatSource_DHW' + s['label'] + '__' + self.__buildingLabel] = [0, 0]
                    self.__technologies.append(
                        [outputBuses[-1], s["label"] + 'DHW__' + self.__buildingLabel])

                if outputBuses.__len__() == 3:
                    self.__envParam['heatSource_T2' + s['label'] + '__' + self.__buildingLabel] = [env_flow, 0, 0]
                    self.__costParam['heatSource_T2' + s['label'] + '__' + self.__buildingLabel] = [0, 0]
                    self.__technologies.append(
                        [outputBuses[1], s["label"] + 'T2__' + self.__buildingLabel])

    def addPVT(self, data, data_timeseries, opt, mergeLinkBuses, dispatchMode):
        # Create Source objects from table 'commodity sources'
        for i, s in data.iterrows():
                if mergeLinkBuses and s["from"] in self.__linkBuses:
                    inputBusLabel = s["from"]
                else:
                    inputBusLabel = s["from"] + '__' + self.__buildingLabel
                outputBuses = [self.__busDict[o + '__' + self.__buildingLabel] for o in s["to"].split(",")]
                connectBuses = [self.__busDict[c + '__' + self.__buildingLabel] for c in s["connect"].split(",")]
                if isinstance(s["delta_temp_n"], float) or isinstance(s["delta_temp_n"], int):
                    delta_temp_n = [float(s["delta_temp_n"])]
                else:
                    delta_temp_n = [float(t) for t in s["delta_temp_n"].split(",")]
                if opt == "costs":
                    epc = self._calculateInvest(s)[0]
                    base = self._calculateInvest(s)[1]
                    env_capa = float(s["impact_cap"]) / float(s["lifetime"])
                    env_flow = float(s["heat_impact"])
                    varc = 0  # variable cost is only passed for environmental optimization if there are emissions per kWh of energy produced from the unit

                    envParam = [env_flow, 0, env_capa]

                elif opt == "env":
                    epc = float(s["impact_cap"]) / float(s["lifetime"])
                    base = 0
                    env_capa = float(s["impact_cap"]) / float(s["lifetime"])
                    env_flow = float(s["heat_impact"])
                    varc = float(s[
                                     "heat_impact"])  # variable cost is only passed for environmental optimization if there are emissions per kWh of energy produced from the unit

                    envParam = [env_flow, 0, env_capa]

                # If roof area does not exist in the excel file
                if 'roof_area' not in s.keys():
                    s["roof_area"] = np.nan
                else:
                    s["roof_area"] = float(s["roof_area"])
                pvtcollector = PVT(s["label"], self.__buildingLabel,
                                                       self.__busDict[inputBusLabel],
                                                       outputBuses,
                                                       connectBuses,
                                                       float(s["electrical_consumption"]), float(s["peripheral_losses"]), float(s["latitude"]),
                                                       float(s["longitude"]), float(s["tilt"]), s["roof_area"],
                                                       float(s["zenith_angle"]), float(s["azimuth"]),
                                                       float(s["eta_0"]), float(s["a_1"]), float(s["a_2"]), float(s["temp_collector_inlet"]),data_timeseries['tre200h0'],
                                                       delta_temp_n, data_timeseries['gls'], data_timeseries['str.diffus'], float(s["capacity_min"]), float(s["capacity_max"]),
                                                       epc, base, env_capa, env_flow, varc, dispatchMode)
                nodes = [pvtcollector.getPVT("el_source")]
                for t in ["heat_source", "heat_transformer", "excess_heat_sink"]:
                    sh, T2, dhw = pvtcollector.getPVT(t)
                    if outputBuses.__len__() == 3:
                        nodes.extend([sh, dhw])
                    elif outputBuses.__len__() == 4:
                        nodes.extend([sh, T2, dhw])
                    else:
                        nodes.extend([sh])
                for x in nodes:
                    self.__nodesList.append(x)

                self.__envParam['heatSource_SH' + s['label'] + '__' + self.__buildingLabel] = envParam
                self.__costParam['heatSource_SH' + s['label'] + '__' + self.__buildingLabel] = [self._calculateInvest(s)[0],
                                                                                                self._calculateInvest(s)[1]]
                self.__technologies.append(
                    [outputBuses[0], s["label"] + 'SH__' + self.__buildingLabel])

                if outputBuses.__len__() >= 3:
                    self.__envParam['heatSource_DHW' + s['label'] + '__' + self.__buildingLabel] = [env_flow, 0, 0]
                    self.__costParam['heatSource_DHW' + s['label'] + '__' + self.__buildingLabel] = [0, 0]
                    self.__technologies.append(
                        [outputBuses[-2], s["label"] + 'DHW__' + self.__buildingLabel])

                if outputBuses.__len__() == 4:
                    self.__envParam['heatSource_T2' + s['label'] + '__' + self.__buildingLabel] = [env_flow, 0, 0]
                    self.__costParam['heatSource_T2' + s['label'] + '__' + self.__buildingLabel] = [0, 0]
                    self.__technologies.append(
                        [outputBuses[1], s["label"] + 'T2__' + self.__buildingLabel])


    def addGridSeparation(self, dataGridSeparation, mergeLinkBuses):
        if not dataGridSeparation.empty:
            for i, gs in dataGridSeparation.iterrows():
                if mergeLinkBuses:
                    if gs["label"] in ['gridElectricity','electricitySource','shSource']:
                        label = gs["label"]+'__'+self.__buildingLabel
                    else:
                        label = gs["label"]
                    if gs["from"] in self.__linkBuses:
                        inputBusLabel = gs["from"]
                    else:
                        inputBusLabel = gs["from"]+'__'+self.__buildingLabel
                    if gs["to"] in self.__linkBuses:
                        outputBusLabel = gs["to"]
                    else:
                        outputBusLabel = gs["to"]+'__'+self.__buildingLabel
                else:
                    label = gs["label"]+'__'+self.__buildingLabel
                    inputBusLabel = gs["from"]+'__'+self.__buildingLabel
                    outputBusLabel = gs["to"] + '__' + self.__buildingLabel

                if (self.__buildingLabel in label) or (mergeLinkBuses and self.__buildingLabel=='Building1'):
                    self.__nodesList.append(solph.components.Transformer(label=label,
                                                              inputs={self.__busDict[inputBusLabel]: solph.Flow()},
                                                              outputs={self.__busDict[outputBusLabel]: solph.Flow()},
                                                      conversion_factors={self.__busDict[outputBusLabel]: float(gs["efficiency"])}))

    def addSource(self, data, data_elimpact, data_elcost, data_natGascost, data_natGasImpact, opt, mergeHeatSourceSink, mergeLinkBuses):
        # Create Source objects from table 'commodity sources'

        for i, cs in data.iterrows():
                sourceLabel = cs["label"]+'__' + self.__buildingLabel
                if (mergeHeatSourceSink and cs["to"] in self.__heatSourceSinkBuses) or \
                        (mergeLinkBuses and cs["to"] in self.__linkBuses):
                    outputBusLabel = cs["to"]
                else:
                    outputBusLabel = cs["to"] + '__' + self.__buildingLabel
                if opt == "costs":
                    if 'electricity' in cs["label"]:
                        varCosts = data_elcost["cost"]
                    elif 'naturalGas' in cs['label']:
                        varCosts = data_natGascost["cost"]
                    else:
                        varCosts = float(cs["variable costs"])
                elif 'electricity' in cs["label"]:
                    varCosts = data_elimpact["impact"]
                elif 'naturalGas' in cs["label"]:
                    varCosts = data_natGasImpact["impact"]
                else:
                    varCosts = float(cs["CO2 impact"])

                if 'electricity' in cs["label"]:
                    envImpactPerFlow = data_elimpact["impact"]
                    envParameter = data_elimpact["impact"]
                    costParameter = data_elcost["cost"]
                elif 'naturalGas' in cs['label']:
                    envImpactPerFlow = data_natGasImpact["impact"]
                    envParameter = data_natGasImpact["impact"]
                    costParameter = data_natGascost["cost"]
                else:
                    envImpactPerFlow = float(cs["CO2 impact"])
                    envParameter = float(cs["CO2 impact"])
                    costParameter = float(cs["variable costs"])
                    # add the inputs (natural gas, wood, etc...) to self.__inputs
                    self.__inputs.append([sourceLabel, outputBusLabel])
                flowargs = {'variable_costs':varCosts,
                            'custom_attributes': {'env_per_flow': envImpactPerFlow},}
                if "potential" in cs["label"].lower():
                    flowargs.update({'full_load_time_max': cs["full_load_time_max"], "nominal_value": cs["nominal_value"]})
                self.__nodesList.append(solph.components.Source(
                    label=sourceLabel,
                    outputs={self.__busDict[outputBusLabel]: solph.Flow(**flowargs)}))

                # set environment and cost parameters
                self.__envParam[sourceLabel] = envParameter
                self.__costParam[sourceLabel] = costParameter

    def addSink(self, data, timeseries, buildingModelParams, mergeLinkBuses, mergeHeatSourceSink, temperatureLevels):
        # Create Sink objects with fixed time series from 'demand' table
        for i, de in data.iterrows():
                sinkLabel = de["label"]+'__'+self.__buildingLabel
                if (mergeLinkBuses and de["from"] in self.__linkBuses) or (mergeHeatSourceSink and de["from"] in self.__heatSourceSinkBuses):
                    inputBusLabel = de["from"]
                elif temperatureLevels and "," in de["from"]:
                    inputBusLabel = [bus+'__'+self.__buildingLabel for bus in de["from"].split(",")]
                    weights = {self.__busDict[b]: float(w) for b,w in zip(inputBusLabel, de["weight"].split(","))}
                else:
                    inputBusLabel = de["from"]+'__'+self.__buildingLabel

                if de["building model"] == 'Yes':   # Should a building model be used?
                    # Only valid for SH demands at the moment
                    if "spaceHeatingDemand" not in sinkLabel:
                        logging.error("Building model has been selected for one or more demands other than space heating. "
                                      "This is not supported in optihood.")
                    if temperatureLevels and "," in de["from"]:
                        inputBusDict = {self.__busDict[k]: solph.Flow() for k in inputBusLabel}
                    else:
                        inputBusDict = {self.__busDict[inputBusLabel]: solph.Flow()}
                    # create sink
                    # Building model with a possibility of output bus
                    outputBusLabel = de['building model out']+'__'+self.__buildingLabel
                    args = {'label': sinkLabel,
                            'inputs': inputBusDict,
                            'outputs': {self.__busDict[outputBusLabel]: solph.Flow()},
                            'tAmbient': buildingModelParams["timeseries"]['tAmb'].values,
                            'totalIrradiationHorizontal': buildingModelParams["timeseries"]['IrrH'].values,
                            'heatGainOccupants': buildingModelParams["timeseries"]["Qocc"].values,
                            }
                    paramList = ['gAreaWindows', 'rDistribution', 'cDistribution', 'rWall', 'cWall', 'rIndoor',
                              'cIndoor', 'qDistributionMin', 'qDistributionMax', 'tIndoorMin', 'tIndoorMax',
                              'tIndoorInit', 'tWallInit', 'tDistributionInit']
                    for param in paramList:
                        if 'tIndoorSet' in buildingModelParams['timeseries'].columns and param in ['tIndoorMin', 'tIndoorMax']:
                            continue
                        if buildingModelParams[param] != '' and param != 'tIndoorMin':
                            args.update({param:buildingModelParams[param]})
                        elif param == 'tIndoorMin':
                            tIndoorNight = 20
                            tIndoorDay = 22
                            tlow = [tIndoorNight, tIndoorNight, tIndoorNight, tIndoorNight, tIndoorNight, tIndoorNight,
                                  tIndoorNight, tIndoorDay, tIndoorDay, tIndoorDay, tIndoorDay, tIndoorDay, tIndoorDay,
                                  tIndoorDay, tIndoorDay, tIndoorDay, tIndoorDay, tIndoorDay, tIndoorDay, tIndoorDay,
                                  tIndoorNight, tIndoorNight, tIndoorNight, tIndoorNight]*365
                            args.update({'tIndoorMin': np.array(tlow)})
                    self.__nodesList.append(SinkRCModel(**args))
                else:
                    # set static inflow values, if any
                    inflow_args = {}
                    if int(de["fixed"])==1:
                        inflow_args["nominal_value"] = float(de["nominal value"])
                        # get time series for node and parameter
                        for col in timeseries.columns.values:
                            if col == de["label"]:
                                inflow_args["fix"] = timeseries[col]
                                if temperatureLevels and "," in de["from"]:
                                    demandInputLabel = col + "Bus" + '__' + self.__buildingLabel
                                    bus = solph.Bus(label=demandInputLabel)
                                    self.__nodesList.append(bus)
                                    self.__busDict[demandInputLabel] = bus
                        if temperatureLevels and "," in de["from"]:
                            inputDummyBusDict = {self.__busDict[k]: solph.Flow() for k in inputBusLabel}
                            self.__nodesList.append(LinkTemperatureDemand(
                                label="dummy_"+sinkLabel,
                                inputs=inputDummyBusDict,
                                outputs={self.__busDict[demandInputLabel]: solph.Flow()},
                                conversion_factors={k: weights[k] for k in inputDummyBusDict}
                            ))
                            inputBusDict = {self.__busDict[demandInputLabel]: solph.Flow(**inflow_args)}
                        else:
                            inputBusDict = {self.__busDict[inputBusLabel]: solph.Flow(**inflow_args)}
                        # create sink
                        self.__nodesList.append(
                        solph.components.Sink(
                                label=sinkLabel,
                                inputs=inputBusDict,
                            )
                        )

    def _addHeatPump(self, data, operationTempertures, temperatureAmb, opt, mergeLinkBuses, mergeHeatSourceSink, dispatchMode, temperatureLevels):
        hpSHLabel = data["label"] + '__' + self.__buildingLabel
        if mergeLinkBuses and data["from"] in self.__linkBuses:
            inputBusLabel = [data["from"]]
        elif mergeLinkBuses and any([b in self.__linkBuses for b in data["from"].split(',')]):
            inputBusLabel = [i + '__' + self.__buildingLabel for i in data["from"].split(",") if
                             i not in self.__linkBuses]
            inputBusLabel.extend([i for i in data["from"].split(",") if i in self.__linkBuses])
        elif mergeHeatSourceSink and any([b in self.__heatSourceSinkBuses for b in data["from"].split(',')]):
            inputBusLabel = [i + '__' + self.__buildingLabel for i in data["from"].split(",") if
                             i not in self.__heatSourceSinkBuses]
            inputBusLabel.extend([i for i in data["from"].split(",") if i in self.__heatSourceSinkBuses])
        else:
            inputBusLabel = [i + '__' + self.__buildingLabel for i in data["from"].split(",")]
        inputBuses = [self.__busDict[i] for i in inputBusLabel]
        outputBuses = []
        outputSHBusLabel = data["to"].split(",")[0] + '__' + self.__buildingLabel
        outputDHWBusLabel = data["to"].split(",")[1] + '__' + self.__buildingLabel
        outputBuses.append(self.__busDict[outputSHBusLabel])
        outputBuses.append(self.__busDict[outputDHWBusLabel])
        if temperatureLevels:
            outputBusLabel3 = data["to"].split(",")[2] + '__' + self.__buildingLabel  # outputSHBusLabel, outputDHWBusLabel, outputBusLabel3 are in the order of increasing temperatures
            outputBuses.append(self.__busDict[outputBusLabel3])
        envImpactPerCapacity = float(data["impact_cap"]) / float(data["lifetime"])
        if data["capacity_min"] == 'x':
            capacityMinSH = float(data["capacity_SH"])
        else:
            capacityMinSH = float(data["capacity_min"])

        heatPump = HeatPumpLinear(self.__buildingLabel, operationTempertures, temperatureAmb,
                                  inputBuses,
                                  outputBuses,
                                  capacityMinSH, float(data["capacity_SH"]),float(data["efficiency"]),
                                  self._calculateInvest(data)[0] * (opt == "costs") + envImpactPerCapacity*(opt == "env"),
                                  self._calculateInvest(data)[1] * (opt == "costs"),
                                  float(data["heat_impact"]) * (opt == "env"),
                                  float(data["heat_impact"]), envImpactPerCapacity, dispatchMode)

        self.__nodesList.append(heatPump.getHP("sh"))

        # set technologies, environment and cost parameters
        self.__technologies.append([outputDHWBusLabel, hpSHLabel])
        self.__technologies.append([outputSHBusLabel, hpSHLabel])
        if temperatureLevels:
            self.__technologies.append([outputBusLabel3, hpSHLabel])

        self.__costParam[hpSHLabel] = [self._calculateInvest(data)[0], self._calculateInvest(data)[1]]

        self.__envParam[hpSHLabel] = [float(data["heat_impact"]), 0, envImpactPerCapacity]

    def _addGeothemalHeatPump(self, data, operationTempertures, temperatureAmb, opt, mergeLinkBuses, mergeHeatSourceSink, dispatchMode, temperatureLevels):
        gwhpSHLabel = data["label"] + '__' + self.__buildingLabel
        if mergeLinkBuses and data["from"] in self.__linkBuses:
            inputBusLabel = [data["from"]]
        elif mergeLinkBuses and any([b in self.__linkBuses for b in data["from"].split(',')]):
            inputBusLabel = [i + '__' + self.__buildingLabel for i in data["from"].split(",") if
                             i not in self.__linkBuses]
            inputBusLabel.extend([i for i in data["from"].split(",") if i in self.__linkBuses])
        elif mergeHeatSourceSink and any([b in self.__heatSourceSinkBuses for b in data["from"].split(',')]):
            inputBusLabel = [i + '__' + self.__buildingLabel for i in data["from"].split(",") if i not in self.__heatSourceSinkBuses]
            inputBusLabel.extend([i for i in data["from"].split(",") if i in self.__heatSourceSinkBuses])
        else:
            inputBusLabel = [i + '__' + self.__buildingLabel for i in data["from"].split(",")]
        inputBuses = [self.__busDict[i] for i in inputBusLabel]
        outputBuses = []
        outputSHBusLabel = data["to"].split(",")[0] + '__' + self.__buildingLabel
        outputDHWBusLabel = data["to"].split(",")[1] + '__' + self.__buildingLabel
        outputBuses.append(self.__busDict[outputSHBusLabel])
        outputBuses.append(self.__busDict[outputDHWBusLabel])
        if temperatureLevels:
            outputBusLabel3 = data["to"].split(",")[2] + '__' + self.__buildingLabel  # outputSHBusLabel, outputDHWBusLabel, outputBusLabel3 are in the order of increasing temperatures
            outputBuses.append(self.__busDict[outputBusLabel3])
        envImpactPerCapacity = float(data["impact_cap"]) / float(data["lifetime"])
        if data["capacity_min"] == 'x':
            capacityMinSH = float(data["capacity_SH"])
        else:
            capacityMinSH = float(data["capacity_min"])
        geothermalheatPump = GeothermalHeatPumpLinear(self.__buildingLabel, operationTempertures, temperatureAmb,
                                  inputBuses,
                                  outputBuses,
                                  capacityMinSH, float(data["capacity_SH"]),float(data["efficiency"]),
                                  self._calculateInvest(data)[0] * (opt == "costs") + envImpactPerCapacity*(opt == "env"),
                                  self._calculateInvest(data)[1] * (opt == "costs"),
                                  float(data["heat_impact"]) * (opt == "env"),
                                  float(data["heat_impact"]), envImpactPerCapacity, dispatchMode)

        self.__nodesList.append(geothermalheatPump.getHP("sh"))

        # set technologies, environment and cost parameters
        self.__technologies.append([outputDHWBusLabel, gwhpSHLabel])
        self.__technologies.append([outputSHBusLabel, gwhpSHLabel])

        self.__costParam[gwhpSHLabel] = [self._calculateInvest(data)[0], self._calculateInvest(data)[1]]

        self.__envParam[gwhpSHLabel] = [float(data["heat_impact"]), 0, envImpactPerCapacity]

    def _addGeothemalHeatPumpSplit(self, data, operationTemperatures, temperatureAmb, opt, mergeLinkBuses, dispatchMode):
        if len(operationTemperatures)==3:
            logging.error("The transformer type GSHP split is not supported with discrete temperature levels. "
                          "Set temperatureLevels to False or use the transformer GSHP")
        gwhpDHWLabel = data["label"][0:4] + str(operationTemperatures[1]) + '__' + self.__buildingLabel
        gwhpSHLabel = data["label"][0:4] + str(operationTemperatures[0]) + '__' + self.__buildingLabel
        if mergeLinkBuses and data["from"] in self.__linkBuses:
            inputBusLabel = data["from"]
        else:
            inputBusLabel = data["from"] + '__' + self.__buildingLabel
        outputSHBusLabel = data["to"].split(",")[0] + '__' + self.__buildingLabel
        outputDHWBusLabel = data["to"].split(",")[1] + '__' + self.__buildingLabel
        envImpactPerCapacity = float(data["impact_cap"]) / float(data["lifetime"])
        capacityDHW = float(data["capacity_DHW"])
        capacitySH = float(data["capacity_SH"])
        if data["capacity_min"] == 'x':
            capacityMinSH = capacitySH
            capacityMinDHW = capacityDHW
        else:
            capacityMinSH = capacityMinDHW = float(data["capacity_min"])

        geothermalheatPumpSH = GeothermalHeatPumpLinearSingleUse(self.__buildingLabel, operationTemperatures[0], temperatureAmb,
                                  self.__busDict[inputBusLabel],
                                  self.__busDict[outputSHBusLabel],
                                  capacityMinSH, capacitySH,
                                  self._calculateInvest(data)[0] * (opt == "costs") + envImpactPerCapacity*(opt == "env"),
                                  self._calculateInvest(data)[1] * (opt == "costs"),
                                  float(data["heat_impact"]) * (opt == "env"),
                                  float(data["heat_impact"]), envImpactPerCapacity, dispatchMode)
        geothermalheatPumpDHW = GeothermalHeatPumpLinearSingleUse(self.__buildingLabel, operationTemperatures[1],
                                                        temperatureAmb,
                                                        self.__busDict[inputBusLabel],
                                                        self.__busDict[outputDHWBusLabel],
                                                        capacityMinDHW, capacityDHW,
                                                        self._calculateInvest(data)[0] * (
                                                                    opt == "costs") + envImpactPerCapacity * (
                                                                    opt == "env"),
                                                        self._calculateInvest(data)[1] * (opt == "costs"),
                                                        float(data["heat_impact"]) * (opt == "env"),
                                                        float(data["heat_impact"]), envImpactPerCapacity, dispatchMode)

        self.__nodesList.append(geothermalheatPumpSH.getHP("sh"))
        self.__nodesList.append(geothermalheatPumpDHW.getHP("sh"))

        # set technologies, environment and cost parameters
        self.__technologies.append([outputDHWBusLabel, gwhpDHWLabel])
        self.__technologies.append([outputSHBusLabel, gwhpSHLabel])

        self.__costParam[gwhpSHLabel] = [self._calculateInvest(data)[0], self._calculateInvest(data)[1]]
        self.__costParam[gwhpDHWLabel] = [self._calculateInvest(data)[0], self._calculateInvest(data)[1]]

        self.__envParam[gwhpSHLabel] = [float(data["heat_impact"]), 0, envImpactPerCapacity]
        self.__envParam[gwhpDHWLabel] = [float(data["heat_impact"]), 0, envImpactPerCapacity]

    def _addCHP(self, data, timesteps, opt, dispatchMode):
        chpLabel = data["label"] + '__' + self.__buildingLabel
        inputBusLabel = data["from"] + '__' + self.__buildingLabel
        outputBuses = [self.__busDict[o + '__' + self.__buildingLabel] for o in data["to"].split(",")]
        efficiency = [float(e) for e in data["efficiency"].split(",")]
        envImpactPerCapacity = float(data["impact_cap"]) / float(data["lifetime"])
        if data["capacity_min"] == 'x':
            capacityMinSH = float(data["capacity_SH"])
        else:
            capacityMinSH = float(data["capacity_min"])
        chp = CHP(self.__buildingLabel, self.__busDict[inputBusLabel],
                  outputBuses,
                  efficiency,
                  capacityMinSH,
                  float(data["capacity_SH"]),
                  self._calculateInvest(data)[0] * (opt == "costs") + envImpactPerCapacity * (opt == "env"),
                  self._calculateInvest(data)[1] * (opt == "costs"), float(data["elec_impact"]) * (opt == "env"),
                  float(data["heat_impact"]) * (opt == "env"),
                  float(data["elec_impact"]), float(data["heat_impact"]), envImpactPerCapacity, timesteps, dispatchMode)

        self.__nodesList.append(chp.getCHP())

        # set technologies, environment and cost parameters
        for i in range(len(outputBuses)):
            self.__technologies.append([data["to"].split(",")[i] + '__' + self.__buildingLabel, chpLabel])

        self.__costParam[chpLabel] = [self._calculateInvest(data)[0], self._calculateInvest(data)[1]]

        self.__envParam[chpLabel] = [float(data["heat_impact"]), float(data["elec_impact"]), envImpactPerCapacity]

    def _addBoiler(self, data, opt, dispatchMode):
        label = data["label"] + '__' + self.__buildingLabel
        inputBusLabel = data["from"] + '__' + self.__buildingLabel
        outputBuses = [self.__busDict[o + '__' + self.__buildingLabel] for o in data["to"].split(",")]
        efficiency = [float(e) for e in str(data["efficiency"]).split(",")]
        envImpactPerCapacity = float(data["impact_cap"]) / float(data["lifetime"])
        if data["capacity_min"] == 'x':
            capacityMinSH = float(data["capacity_SH"])
        else:
            capacityMinSH = float(data["capacity_min"])

        self.__nodesList.append(GenericCombinedTransformer(label, self.__busDict[inputBusLabel],
                  outputBuses,
                  efficiency, capacityMinSH, float(data["capacity_SH"]),
                  self._calculateInvest(data)[0] * (opt == "costs") + envImpactPerCapacity * (opt == "env"),
                  self._calculateInvest(data)[1] * (opt == "costs"), float(data["heat_impact"]) * (opt == "env"), float(data["heat_impact"]), envImpactPerCapacity, dispatchMode))

        # set technologies, environment and cost parameters
        for i in range(len(outputBuses)):
            self.__technologies.append([data["to"].split(",")[i] + '__' + self.__buildingLabel, label])

        self.__costParam[label] = [self._calculateInvest(data)[0], self._calculateInvest(data)[1]]

        self.__envParam[label] = [float(data["heat_impact"]), 0, envImpactPerCapacity]

    def _addElectricRod(self, data, opt, mergeLinkBuses, dispatchMode, temperatureLevels):
        elRodLabel = data["label"] + '__' + self.__buildingLabel
        if mergeLinkBuses and data["from"] in self.__linkBuses:
            inputBusLabel = data["from"]
        else:
            inputBusLabel = data["from"] + '__' + self.__buildingLabel
        outputBuses = [self.__busDict[o + '__' + self.__buildingLabel] for o in data["to"].split(",")]
        efficiency = [float(e) for e in data["efficiency"].split(",")]
        envImpactPerCapacity = float(data["impact_cap"]) / float(data["lifetime"])
        if data["capacity_min"] == 'x':
            capacityMinSH = float(data["capacity_SH"])
        else:
            capacityMinSH = float(data["capacity_min"])

        self.__nodesList.append(GenericCombinedTransformer(elRodLabel, self.__busDict[inputBusLabel],
                                          outputBuses,
                                          efficiency, capacityMinSH, float(data["capacity_SH"]),
                                          self._calculateInvest(data)[0] * (opt == "costs") + envImpactPerCapacity * (
                                                      opt == "env"),
                                          self._calculateInvest(data)[1] * (opt == "costs"),
                                          float(data["heat_impact"]) * (opt == "env"), float(data["heat_impact"]),
                                          envImpactPerCapacity, dispatchMode))

        # set technologies, environment and cost parameters
        for i in range(len(outputBuses)):
            self.__technologies.append([data["to"].split(",")[i] + '__' + self.__buildingLabel, elRodLabel])

        self.__costParam[elRodLabel] = [self._calculateInvest(data)[0], self._calculateInvest(data)[1]]
        self.__envParam[elRodLabel] = [float(data["heat_impact"]), 0, envImpactPerCapacity]
    
    def _addChiller(self, data, temperatureSH, temperatureGround, opt, mergeLinkBuses, mergeHeatSourceSink, dispatchMode):
        chillerLabel = data["label"] + '__' + self.__buildingLabel
        if (mergeLinkBuses and data["from"] in self.__linkBuses):
            inputBusLabel = [data["from"]]
        else:
            inputBusLabel = [i + '__' + self.__buildingLabel for i in data["from"].split(",")]
        inputBuses = [self.__busDict[i] for i in inputBusLabel]
        if (mergeHeatSourceSink and data["to"] in self.__heatSourceSinkBuses):
            outputBusLabel = data['to']
        else:
            outputBusLabel = data['to']+ '__' + self.__buildingLabel
        outputBus = self.__busDict[outputBusLabel]
        envImpactPerCapacity = float(data["impact_cap"]) / float(data["lifetime"])
        if data["capacity_min"] == 'x':
            capacityMinSH = float(data["capacity_SH"])
        else:
            capacityMinSH = float(data["capacity_min"])
        self.__nodesList.append(Chiller(label=chillerLabel,
                          tSH=temperatureSH,
                          tGround=temperatureGround,
                          inputBuses=inputBuses,
                          outputBus= outputBus,
                          nomEff=float(data['efficiency']), capacityMin=capacityMinSH, capacityMax=float(data["capacity_SH"]),
                          epc=self._calculateInvest(data)[0] * (opt == "costs") + envImpactPerCapacity*(opt == "env"), base=self._calculateInvest(data)[1] * (opt == "costs"), env_capa=envImpactPerCapacity,
                          dispatchMode=dispatchMode
                        ))
        self.__technologies.append([outputBusLabel, chillerLabel])

        self.__costParam[chillerLabel] = [self._calculateInvest(data)[0], self._calculateInvest(data)[1]]

        self.__envParam[chillerLabel] = [float(data["heat_impact"]), 0, envImpactPerCapacity]

    def _addGenericTransformer(self, data):
        inputBusLabel = data['from']+ '__Building1'
        outputBusLabels = [b + '__' + self.__buildingLabel for b in data['to'].split(",")]
        outputDict = {self.__busDict[o]:solph.Flow(variable_costs=0, nominal_value=100000000000, custom_attributes={'env_per_flow': 0}) for o in outputBusLabels}
        convFactors = {self.__busDict[o]:1 for o in outputBusLabels}
        self.__nodesList.append(solph.components.Transformer(label=data['label'] + '__Building1',
                                                  inputs={self.__busDict[inputBusLabel]: solph.Flow()},
                                                  outputs=outputDict,
                                                  conversion_factors=convFactors))
    
    def addTransformer(self, data, operationTemperatures, temperatureAmb, temperatureGround, opt, mergeLinkBuses, mergeHeatSourceSink, dispatchMode, temperatureLevels):
        for i, t in data.iterrows():
            if t["active"]:
                if pattern_at_start_followed_by_number("HP", t["label"]):
                    self._addHeatPump(t, operationTemperatures, temperatureAmb, opt, mergeLinkBuses, mergeHeatSourceSink, dispatchMode, temperatureLevels)
                elif pattern_at_start_followed_by_number("GWHP", t["label"]):
                    self._addGeothemalHeatPump(t, operationTemperatures, temperatureGround, opt, mergeLinkBuses, mergeHeatSourceSink, dispatchMode, temperatureLevels)
                elif t["label"] == "GWHP split":
                    self._addGeothemalHeatPumpSplit(t, operationTemperatures, temperatureGround, opt, mergeLinkBuses, dispatchMode)
                elif "CHP" in t["label"]:
                    self._addCHP(t, len(temperatureAmb), opt, dispatchMode)
                elif "Boiler" in t["label"]:
                    self._addBoiler(t, opt, dispatchMode)
                elif pattern_at_start_followed_by_number("ElectricRod", t["label"]):
                    self._addElectricRod(t, opt, mergeLinkBuses, dispatchMode, temperatureLevels)
                elif pattern_at_start_followed_by_number("Chiller", t["label"]):
                    self._addChiller(t, operationTemperatures[0], temperatureGround, opt, mergeLinkBuses, mergeHeatSourceSink, dispatchMode)
                else:
                    logging.warning("Transformer label not identified, adding generic transformer component...")
                    self._addGenericTransformer(t)

    def addStorage(self, data, storageParams, ambientTemperature, opt, mergeLinkBuses, dispatchMode, temperatureLevels):
        sList = []
        for i, s in data.iterrows():
                storageLabel = s["label"]+'__'+self.__buildingLabel
                if temperatureLevels and s["label"] == "thermalStorage":
                    inputBuses = [self.__busDict[iLabel + '__' + self.__buildingLabel] for iLabel in s["from"].split(",")]
                    outputBuses = [self.__busDict[oLabel + '__' + self.__buildingLabel] for oLabel in s["to"].split(",")]
                    storTemperatures = storageParams["stratified_storage"].at[s["label"],"temp_h"].split(",")
                    self.__technologies.append([outputBuses[0].label, f'dummy_{storageLabel.replace("thermalStorage",f"thermalStorage{int(storTemperatures[0])}")}'])
                    self.__technologies.append([outputBuses[1].label, storageLabel.replace("thermalStorage",f"thermalStorage{int(storTemperatures[-1])}")])
                else:
                    if mergeLinkBuses and s["from"] in self.__linkBuses:
                        inputBusLabel = s["from"]
                    else:
                        inputBusLabel = s["from"]+'__'+self.__buildingLabel
                    if mergeLinkBuses and s["to"] in self.__linkBuses:
                        outputBusLabel = s["to"]
                    else:
                        outputBusLabel = s["to"]+'__'+self.__buildingLabel
                    self.__technologies.append([outputBusLabel, storageLabel])
                envImpactPerCapacity = float(s["impact_cap"]) / float(s["lifetime"])         # annualized value
                # set technologies, environment and cost parameters
                self.__costParam[storageLabel] = [self._calculateInvest(s)[0], self._calculateInvest(s)[1]]
                self.__envParam[storageLabel] = [float(s["heat_impact"]), float(s["elec_impact"]), envImpactPerCapacity]

                if s["label"] == "electricalStorage":
                    self.__nodesList.append(ElectricalStorage(self.__buildingLabel, self.__busDict[inputBusLabel],
                                                              self.__busDict[outputBusLabel], float(s["capacity loss"]),
                                                            float(s["initial capacity"]), float(s["efficiency inflow"]),
                                                            float(s["efficiency outflow"]), float(s["capacity min"]),
                                                            float(s["capacity max"]),
                                                            self._calculateInvest(s)[0]*(opt == "costs") + envImpactPerCapacity*(opt == "env"),
                                                            self._calculateInvest(s)[1]*(opt == "costs"),
                                                            float(s["elec_impact"])*(opt == "env"),
                                                            float(s["elec_impact"]), envImpactPerCapacity, dispatchMode))

                elif (s["label"] == "dhwStorage" or s["label"] == "shStorage") and not temperatureLevels:
                    self.__nodesList.append(ThermalStorage(storageLabel,
                                                           storageParams["stratified_storage"], self.__busDict[inputBusLabel],
                                                           self.__busDict[outputBusLabel],
                                                        float(s["initial capacity"]), float(s["capacity min"]),
                                                        float(s["capacity max"]),
                                                        self._calculateInvest(s)[0]*(opt == "costs") + envImpactPerCapacity*(opt == "env"),
                                                        self._calculateInvest(s)[1]*(opt == "costs"), float(s["heat_impact"])*(opt == "env"),
                                                        float(s["heat_impact"]), envImpactPerCapacity, dispatchMode))
                elif s["label"] == "thermalStorage" and temperatureLevels:
                    storage = ThermalStorageTemperatureLevels(storageLabel,
                               storageParams["stratified_storage"], inputBuses,
                               outputBuses,
                               float(s["initial capacity"]), float(s["capacity min"]),
                               float(s["capacity max"]),
                               self._calculateInvest(s)[0] * (
                                           opt == "costs") + envImpactPerCapacity * (
                                           opt == "env"),
                               self._calculateInvest(s)[1] * (opt == "costs"),
                               float(s["heat_impact"]) * (opt == "env"),
                               float(s["heat_impact"]), envImpactPerCapacity, dispatchMode)
                    sList.append(storage)
                    for i in range(len(inputBuses)):
                        self.__nodesList.append(storage.getStorageLevel(i))
                        self.__nodesList.extend(storage.getDummyComponents(i))
                elif "iceStorage" in s["label"]:
                    if not np.isnan(s["initial capacity"]):
                        initial_ice_frac = float(s["initial capacity"])
                    else:
                        initial_ice_frac = 0

                    self.__nodesList.append(
                        IceStorage(label=storageLabel,
                                   input=self.__busDict[inputBusLabel],
                                   output=self.__busDict[outputBusLabel],
                                   tStorInit=float(s[_ent.StorageLabels.initial_temp]),
                                   fIceInit=initial_ice_frac,
                                   fMax=float(storageParams["ice_storage"].at[s["label"], "max_ice_fraction"]),
                                   rho=float(storageParams["ice_storage"].at[s["label"], "rho_fluid"]),
                                   V=float(s["capacity max"])/1000,  # conversion from L to m3
                                   hfluid=float(storageParams["ice_storage"].at[s["label"], "h_fluid"]),
                                   cp=float(storageParams["ice_storage"].at[s["label"], "cp_fluid"]),
                                   Tamb=ambientTemperature,
                                   UAtank=float(storageParams["ice_storage"].at[s["label"], "UA_tank"]),
                                   inflow_conversion_factor=float(storageParams["ice_storage"].at[s["label"], "inflow_conversion_factor"]),
                                   outflow_conversion_factor=float(storageParams["ice_storage"].at[s["label"], "outflow_conversion_factor"])
                                   )
                    )

                elif s["label"] not in ["dhwStorage", "shStorage", "thermalStorage"] and "Storage" in s["label"]:
                    is_tank = False
                    self.__nodesList.append(ThermalStorage(storageLabel,
                           storageParams["stratified_storage"], self.__busDict[inputBusLabel],
                           self.__busDict[outputBusLabel],
                           float(s["initial capacity"]), float(s["capacity min"]),
                           float(s["capacity max"]),
                           self._calculateInvest(s)[0] * (
                                       opt == "costs") + envImpactPerCapacity * (
                                       opt == "env"),
                           self._calculateInvest(s)[1] * (opt == "costs"),
                           float(s["heat_impact"]) * (opt == "env"),
                           float(s["heat_impact"]), envImpactPerCapacity, dispatchMode, is_tank))
                else:
                    logging.error("One of the following issues were encountered: (i) Storage label not identified. Storage label"
                                  "should either match one of the following: electricalStorage, dhwStorage, shStorage or thermalStorage,"
                                  "or contain the substring \'Storage\'"
                                  "(ii) Separate dhwStorage and/or shStorage selected when temperatureLevels is set as True."
                                  "Either set temperatureLevels to False or rename the storage label to thermalStorage.")
        return sList

    def _calculateInvest(self, data):
        # Calculate the CAPEX and the part of the OPEX not related to energy flows (maintenance)
        c = data["installation"] + data["planification"] + 1
        m = data["maintenance"]
        perCapacity = m * data["invest_cap"] + economics.annuity(c * data["invest_cap"], data["lifetime"], intRate)
        base = m * data["invest_base"] + economics.annuity(c * data["invest_base"], data["lifetime"], intRate)
        return perCapacity, base