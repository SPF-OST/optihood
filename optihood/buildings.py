import numpy as np
import oemof.solph as solph
import pandas as pd
from oemof.tools import logger
from oemof.tools import economics
import logging
from optihood.converters import *
from optihood.sources import PV
from optihood.storages import ElectricalStorage, ThermalStorage
from optihood.sinks import SinkRCModel

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
        self.__linkBuses = ["electricityBus", "electricityInBus", "domesticHotWaterBus", "dhwDemandBus", "spaceHeatingBus", "shDemandBus"]

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

    def addBus(self, data, opt, mergeLinkBuses, electricityImpact, clusterSize, includeCarbonBenefits):
        # Create Bus objects from buses table
        for i, b in data.iterrows():
            if b["active"]:
                if mergeLinkBuses and b["label"] in self.__linkBuses:
                    label = b["label"]
                else:
                    label = b["label"] + '__' + self.__buildingLabel

                if not mergeLinkBuses or (mergeLinkBuses and (self.__buildingLabel=='Building1' or label not in self.__linkBuses)):
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
                                    varcost = varcost.append(temp, ignore_index=True)
                                else:
                                    varcost = temp
                    elif opt=='env' and includeCarbonBenefits:varcost=-electricityImpact['impact']
                    else: varcost=0
                    if b["excess"]:
                        self.__nodesList.append(
                            solph.Sink(
                                label="excess"+label,
                                inputs={
                                    self.__busDict[label]: solph.Flow(
                                        variable_costs=varcost
                                    )}))
                        # add the excess production cost to self.__costParam
                        self.__costParam["excess"+label] = float(b["excess costs"])
        if mergeLinkBuses and self.__buildingLabel=='Building1':
            return self.__busDict

    def addToBusDict(self, busDictBuilding1):
        for label in self.__linkBuses:
            self.__busDict[label] = busDictBuilding1[label]

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

    def addSolar(self, data, data_timeseries, opt, mergeLinkBuses, dispatchMode):
        # Create Source objects from table 'commodity sources'
        for i, s in data.iterrows():
            if mergeLinkBuses and s["from"] in self.__linkBuses:
                inputBusLabel = s["from"]
            else:
                inputBusLabel = s["from"] + '__' + self.__buildingLabel

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
                                                   self.__busDict[s["to"] + '__' + self.__buildingLabel],
                                                   self.__busDict[s["connect"]+ '__' + self.__buildingLabel],
                                                   float(s["electrical_consumption"]), float(s["peripheral_losses"]), float(s["latitude"]),
                                                   float(s["longitude"]), float(s["tilt"]), s["roof_area"],
                                                   s["zenith_angle"], float(s["azimuth"]),
                                                   float(s["eta_0"]), float(s["a_1"]), float(s["a_2"]), float(s["temp_collector_inlet"]),
                                                   float(s["delta_temp_n"]), data_timeseries['gls'], data_timeseries['str.diffus'],
                                                    data_timeseries['tre200h0'], float(s["capacity_min"]), float(s["capacity_max"]),
                                                   epc, base, env_capa, env_flow, varc, dispatchMode)
            self.__nodesList.append(collector.getSolar("source"))
            self.__nodesList.append(collector.getSolar("transformer"))
            self.__nodesList.append(collector.getSolar("sink"))

            self.__envParam["heat_"+s["label"] + '__' + self.__buildingLabel] = envParam

            self.__costParam["heat_"+s["label"] + '__' + self.__buildingLabel] = [self._calculateInvest(s)[0],
                                                                          self._calculateInvest(s)[1]]
            self.__technologies.append(
                [s["to"] + '__' + self.__buildingLabel, s["label"] + '__' + self.__buildingLabel])

    def addPVT(self, data, data_timeseries, opt, mergeLinkBuses, dispatchMode):
        # Create Source objects from table 'commodity sources'
        for i, s in data.iterrows():
            if s["active"]:
                if mergeLinkBuses and s["from"] in self.__linkBuses:
                    inputBusLabel = s["from"]
                else:
                    inputBusLabel = s["from"] + '__' + self.__buildingLabel

                outputBusLabels = [self.__busDict[s["to"].split(",")[0] + '__' + self.__buildingLabel], self.__busDict[s["to"].split(",")[1] + '__' + self.__buildingLabel]]

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
                                                       outputBusLabels,
                                                       self.__busDict[s["connect"]+ '__' + self.__buildingLabel],
                                                       float(s["electrical_consumption"]), float(s["peripheral_losses"]), float(s["latitude"]),
                                                       float(s["longitude"]), float(s["tilt"]), s["roof_area"],
                                                       float(s["zenith_angle"]), float(s["azimuth"]),
                                                       float(s["eta_0"]), float(s["a_1"]), float(s["a_2"]), float(s["temp_collector_inlet"]),data_timeseries['tre200h0'],
                                                       float(s["delta_temp_n"]), data_timeseries['gls'], data_timeseries['str.diffus'], float(s["capacity_min"]), float(s["capacity_max"]),
                                                       epc, base, env_capa, env_flow, varc, dispatchMode,
                                                        float(s["pv_efficiency"]))
                self.__nodesList.append(pvtcollector.getPVT("el_source"))
                self.__nodesList.append(pvtcollector.getPVT("heat_source"))
                self.__nodesList.append(pvtcollector.getPVT("heat_transformer"))
                self.__nodesList.append(pvtcollector.getPVT("excess_heat_sink"))

                self.__envParam['heatSource_' + s['label'] + '__' + self.__buildingLabel] = envParam
                self.__costParam['heatSource_' + s['label'] + '__' + self.__buildingLabel] = [self._calculateInvest(s)[0],
                                                                                            self._calculateInvest(s)[1]]
                self.__technologies.append(
                    [s["to"] + '__' + self.__buildingLabel, s["label"] + '__' + self.__buildingLabel])

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
                    self.__nodesList.append(solph.Transformer(label=label,
                                                              inputs={self.__busDict[inputBusLabel]: solph.Flow()},
                                                              outputs={self.__busDict[outputBusLabel]: solph.Flow()},
                                                      conversion_factors={self.__busDict[outputBusLabel]: float(gs["efficiency"])}))

    def addSource(self, data, data_elimpact, data_elcost, data_natGascost, data_natGasImpact, opt):
        # Create Source objects from table 'commodity sources'

        for i, cs in data.iterrows():
            if cs["active"]:
                sourceLabel = cs["label"]+'__' + self.__buildingLabel
                outputBusLabel = cs["to"] + '__' + self.__buildingLabel
                # variable costs = (if opt == "costs") : cs["variable costs"]
                #                  (if opt == "env") and ('electricity' in cs["label"]): data_elec["impact"]
                #                  (if opt == "env") and ('electricity' not in cs["label"]): cs["CO2 impact"]
                # env_per_flow = (if 'electricity' in cs["label"]) : data_elec["impact"]
                #                 (if 'electricity' not in cs["label"]) : cs["CO2 impact"]
                # self.__envParam is assigned the value data_elec["impact"] or cs["CO2 impact"] depending on whether ('electricity' is in cs["label"]) or not
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

                self.__nodesList.append(solph.Source(
                    label=sourceLabel,
                    outputs={self.__busDict[outputBusLabel]: solph.Flow(
                            variable_costs=varCosts,
                            env_per_flow=envImpactPerFlow,
                        )}))

                # set environment and cost parameters
                self.__envParam[sourceLabel] = envParameter
                self.__costParam[sourceLabel] = costParameter

    def addSink(self, data, timeseries, buildingModelParams, mergeLinkBuses):
        # Create Sink objects with fixed time series from 'demand' table
        for i, de in data.iterrows():
            if de["active"]:
                sinkLabel = de["label"]+'__'+self.__buildingLabel
                if mergeLinkBuses and de["from"] in self.__linkBuses:
                    inputBusLabel = de["from"]
                else:
                    inputBusLabel = de["from"]+'__'+self.__buildingLabel

                if de["building model"] == 'Yes':   # Should a building model be used?
                    # Only valid for SH demands at the moment
                    # create sink
                    self.__nodesList.append(
                        SinkRCModel(
                            tAmbient=buildingModelParams['tAmb'].values,
                            totalIrradiationHorizontal=buildingModelParams['IrrH'].values,
                            heatGainOccupants=buildingModelParams['Qocc'].values,
                            label=sinkLabel,
                            inputs={self.__busDict[inputBusLabel]: solph.Flow()},
                        )
                    )
                else:
                    # set static inflow values, if any
                    inflow_args = {"nominal_value": float(de["nominal value"])}
                    # get time series for node and parameter
                    for col in timeseries.columns.values:
                        if col == de["label"]:
                            inflow_args["fix"] = timeseries[col]
                    # create sink
                    self.__nodesList.append(
                        solph.Sink(
                            label=sinkLabel,
                            inputs={self.__busDict[inputBusLabel]: solph.Flow(**inflow_args)},
                        )
                    )

    def _addHeatPump(self, data, temperatureDHW, temperatureSH, temperatureAmb, opt, mergeLinkBuses, dispatchMode):
        hpSHLabel = data["label"] + '__' + self.__buildingLabel
        if mergeLinkBuses and data["from"] in self.__linkBuses:
            inputBusLabel = data["from"]
        else:
            inputBusLabel = data["from"] + '__' + self.__buildingLabel
        outputSHBusLabel = data["to"].split(",")[0] + '__' + self.__buildingLabel
        outputDHWBusLabel = data["to"].split(",")[1] + '__' + self.__buildingLabel
        envImpactPerCapacity = float(data["impact_cap"]) / float(data["lifetime"])
        if data["capacity_min"] == 'x':
            capacityMinSH = float(data["capacity_SH"])
        else:
            capacityMinSH = float(data["capacity_min"])

        heatPump = HeatPumpLinear(self.__buildingLabel, temperatureDHW, temperatureSH, temperatureAmb,
                                  self.__busDict[inputBusLabel],
                                  self.__busDict[outputSHBusLabel],
                                  self.__busDict[outputDHWBusLabel],
                                  capacityMinSH, float(data["capacity_SH"]),float(data["efficiency"]),
                                  self._calculateInvest(data)[0] * (opt == "costs") + envImpactPerCapacity*(opt == "env"),
                                  self._calculateInvest(data)[1] * (opt == "costs"),
                                  float(data["heat_impact"]) * (opt == "env"),
                                  float(data["heat_impact"]), envImpactPerCapacity, dispatchMode)

        self.__nodesList.append(heatPump.getHP("sh"))

        # set technologies, environment and cost parameters
        self.__technologies.append([outputDHWBusLabel, hpSHLabel])
        self.__technologies.append([outputSHBusLabel, hpSHLabel])

        self.__costParam[hpSHLabel] = [self._calculateInvest(data)[0], self._calculateInvest(data)[1]]

        self.__envParam[hpSHLabel] = [float(data["heat_impact"]), 0, envImpactPerCapacity]

    def _addGeothemalHeatPump(self, data, temperatureDHW, temperatureSH, temperatureAmb, opt, mergeLinkBuses, dispatchMode):
        gwhpSHLabel = data["label"] + '__' + self.__buildingLabel
        if mergeLinkBuses and data["from"] in self.__linkBuses:
            inputBusLabel = data["from"]
        else:
            inputBusLabel = data["from"] + '__' + self.__buildingLabel
        outputSHBusLabel = data["to"].split(",")[0] + '__' + self.__buildingLabel
        outputDHWBusLabel = data["to"].split(",")[1] + '__' + self.__buildingLabel
        envImpactPerCapacity = float(data["impact_cap"]) / float(data["lifetime"])
        if data["capacity_min"] == 'x':
            capacityMinSH = float(data["capacity_SH"])
        else:
            capacityMinSH = float(data["capacity_min"])
        geothermalheatPump = GeothermalHeatPumpLinear(self.__buildingLabel, temperatureDHW, temperatureSH, temperatureAmb,
                                  self.__busDict[inputBusLabel],
                                  self.__busDict[outputSHBusLabel],
                                  self.__busDict[outputDHWBusLabel],
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

    def _addGeothemalHeatPumpSplit(self, data, temperatureDHW, temperatureSH, temperatureAmb, opt, mergeLinkBuses, dispatchMode):
        gwhpDHWLabel = data["label"][0:4] + str(temperatureDHW) + '__' + self.__buildingLabel
        gwhpSHLabel = data["label"][0:4] + str(temperatureSH) + '__' + self.__buildingLabel
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

        geothermalheatPumpSH = GeothermalHeatPumpLinearSingleUse(self.__buildingLabel, temperatureSH, temperatureAmb,
                                  self.__busDict[inputBusLabel],
                                  self.__busDict[outputSHBusLabel],
                                  capacityMinSH, capacitySH,
                                  self._calculateInvest(data)[0] * (opt == "costs") + envImpactPerCapacity*(opt == "env"),
                                  self._calculateInvest(data)[1] * (opt == "costs"),
                                  float(data["heat_impact"]) * (opt == "env"),
                                  float(data["heat_impact"]), envImpactPerCapacity, dispatchMode)
        geothermalheatPumpDHW = GeothermalHeatPumpLinearSingleUse(self.__buildingLabel, temperatureDHW,
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
        chpSHLabel = data["label"] + '__' + self.__buildingLabel
        inputBusLabel = data["from"] + '__' + self.__buildingLabel
        outputElBusLabel = data["to"].split(",")[0] + '__' + self.__buildingLabel
        outputSHBusLabel = data["to"].split(",")[1] + '__' + self.__buildingLabel
        outputDHWBusLabel = data["to"].split(",")[2] + '__' + self.__buildingLabel
        elEfficiency = float(data["efficiency"].split(",")[0])
        shEfficiency = float(data["efficiency"].split(",")[1])
        dhwEfficiency = float(data["efficiency"].split(",")[2])
        envImpactPerCapacity = float(data["impact_cap"]) / float(data["lifetime"])
        if data["capacity_min"] == 'x':
            capacityMinSH = float(data["capacity_SH"])
        else:
            capacityMinSH = float(data["capacity_min"])
        chp = CHP(self.__buildingLabel, self.__busDict[inputBusLabel],
                  self.__busDict[outputElBusLabel],
                  self.__busDict[outputSHBusLabel],
                  self.__busDict[outputDHWBusLabel],
                  elEfficiency, shEfficiency,
                  dhwEfficiency, capacityMinSH,
                  float(data["capacity_SH"]),
                  self._calculateInvest(data)[0] * (opt == "costs") + envImpactPerCapacity * (opt == "env"),
                  self._calculateInvest(data)[1] * (opt == "costs"), float(data["elec_impact"]) * (opt == "env"),
                  float(data["heat_impact"]) * (opt == "env"),
                  float(data["elec_impact"]), float(data["heat_impact"]), envImpactPerCapacity, timesteps, dispatchMode)

        self.__nodesList.append(chp.getCHP("sh"))

        # set technologies, environment and cost parameters
        self.__technologies.append([outputElBusLabel, chpSHLabel])
        self.__technologies.append([outputSHBusLabel, chpSHLabel])
        self.__technologies.append([outputDHWBusLabel, chpSHLabel])

        self.__costParam[chpSHLabel] = [self._calculateInvest(data)[0], self._calculateInvest(data)[1]]

        self.__envParam[chpSHLabel] = [float(data["heat_impact"]), float(data["elec_impact"]), envImpactPerCapacity]

    def _addGasBoiler(self, data, opt, dispatchMode):
        gasBoilLabel = data["label"] + '__' + self.__buildingLabel
        inputBusLabel = data["from"] + '__' + self.__buildingLabel
        outputSHBusLabel = data["to"].split(",")[0] + '__' + self.__buildingLabel
        outputDHWBusLabel = data["to"].split(",")[1] + '__' + self.__buildingLabel
        shEfficiency = float(data["efficiency"].split(",")[0])
        dhwEfficiency = float(data["efficiency"].split(",")[1])
        envImpactPerCapacity = float(data["impact_cap"]) / float(data["lifetime"])
        if data["capacity_min"] == 'x':
            capacityMinSH = float(data["capacity_SH"])
        else:
            capacityMinSH = float(data["capacity_min"])

        self.__nodesList.append(GasBoiler(self.__buildingLabel, self.__busDict[inputBusLabel],
                  self.__busDict[outputSHBusLabel], self.__busDict[outputDHWBusLabel],
                  shEfficiency, dhwEfficiency, capacityMinSH, float(data["capacity_SH"]),
                  self._calculateInvest(data)[0] * (opt == "costs") + envImpactPerCapacity * (opt == "env"),
                  self._calculateInvest(data)[1] * (opt == "costs"), float(data["heat_impact"]) * (opt == "env"), float(data["heat_impact"]), envImpactPerCapacity, dispatchMode))

        # set technologies, environment and cost parameters
        self.__technologies.append([outputSHBusLabel, gasBoilLabel])
        self.__technologies.append([outputDHWBusLabel, gasBoilLabel])

        self.__costParam[gasBoilLabel] = [self._calculateInvest(data)[0], self._calculateInvest(data)[1]]

        self.__envParam[gasBoilLabel] = [float(data["heat_impact"]), 0, envImpactPerCapacity]

    def _addElectricRod(self, data, opt, mergeLinkBuses, dispatchMode):
        elRodLabel = data["label"] + '__' + self.__buildingLabel
        if mergeLinkBuses and data["from"] in self.__linkBuses:
            inputBusLabel = data["from"]
        else:
            inputBusLabel = data["from"] + '__' + self.__buildingLabel
        outputSHBusLabel = data["to"].split(",")[0] + '__' + self.__buildingLabel
        outputDHWBusLabel = data["to"].split(",")[1] + '__' + self.__buildingLabel
        efficiency = float(data["efficiency"])
        envImpactPerCapacity = float(data["impact_cap"]) / float(data["lifetime"])
        if data["capacity_min"] == 'x':
            capacityMinSH = float(data["capacity_SH"])
        else:
            capacityMinSH = float(data["capacity_min"])

        self.__nodesList.append(ElectricRod(self.__buildingLabel, self.__busDict[inputBusLabel],
                                          self.__busDict[outputSHBusLabel], self.__busDict[outputDHWBusLabel],
                                          efficiency, capacityMinSH, float(data["capacity_SH"]),
                                          self._calculateInvest(data)[0] * (opt == "costs") + envImpactPerCapacity * (
                                                      opt == "env"),
                                          self._calculateInvest(data)[1] * (opt == "costs"),
                                          float(data["heat_impact"]) * (opt == "env"), float(data["heat_impact"]),
                                          envImpactPerCapacity, dispatchMode))

        # set technologies, environment and cost parameters
        self.__technologies.append([outputSHBusLabel, elRodLabel])
        self.__technologies.append([outputDHWBusLabel, elRodLabel])

        self.__costParam[elRodLabel] = [self._calculateInvest(data)[0], self._calculateInvest(data)[1]]

        self.__envParam[elRodLabel] = [float(data["heat_impact"]), 0, envImpactPerCapacity]

    def addTransformer(self, data, temperatureDHW, temperatureSH, temperatureAmb, temperatureGround, opt, mergeLinkBuses, dispatchMode):
        for i, t in data.iterrows():
            if t["active"]:
                if t["label"] == "HP":
                    self._addHeatPump(t, temperatureDHW, temperatureSH, temperatureAmb, opt, mergeLinkBuses, dispatchMode)
                elif t["label"] == "GWHP":
                    self._addGeothemalHeatPump(t, temperatureDHW, temperatureSH, temperatureGround, opt, mergeLinkBuses, dispatchMode)
                elif t["label"] == "GWHP split":
                    self._addGeothemalHeatPumpSplit(t, temperatureDHW, temperatureSH, temperatureGround, opt, mergeLinkBuses, dispatchMode)
                elif t["label"] == "CHP":
                    self._addCHP(t, len(temperatureAmb), opt, dispatchMode)
                elif t["label"] == "GasBoiler":
                    self._addGasBoiler(t, opt, dispatchMode)
                elif t["label"] == "ElectricRod":
                    self._addElectricRod(t, opt, mergeLinkBuses, dispatchMode)
                else:
                    logging.warning("Transformer label not identified...")

    def addStorage(self, data, stratifiedStorageParams, opt, mergeLinkBuses, dispatchMode):
        for i, s in data.iterrows():
            if s["active"]:
                storageLabel = s["label"]+'__'+self.__buildingLabel
                inputBusLabel = s["from"]+'__'+self.__buildingLabel
                if mergeLinkBuses and s["to"] in self.__linkBuses:
                    outputBusLabel = s["to"]
                else:
                    outputBusLabel = s["to"]+'__'+self.__buildingLabel
                envImpactPerCapacity = float(s["impact_cap"]) / float(s["lifetime"])         # annualized value
                # set technologies, environment and cost parameters
                self.__costParam[storageLabel] = [self._calculateInvest(s)[0], self._calculateInvest(s)[1]]
                self.__envParam[storageLabel] = [float(s["heat_impact"]), float(s["elec_impact"]), envImpactPerCapacity]
                self.__technologies.append([outputBusLabel, storageLabel])

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

                elif s["label"] == "dhwStorage" or s["label"] == "shStorage":
                    self.__nodesList.append(ThermalStorage(storageLabel, s["label"],
                                                           stratifiedStorageParams, self.__busDict[inputBusLabel],
                                                           self.__busDict[outputBusLabel],
                                                        float(s["initial capacity"]), float(s["capacity min"]),
                                                        float(s["capacity max"]),
                                                        self._calculateInvest(s)[0]*(opt == "costs") + envImpactPerCapacity*(opt == "env"),
                                                        self._calculateInvest(s)[1]*(opt == "costs"), float(s["heat_impact"])*(opt == "env"),
                                                        float(s["heat_impact"]), envImpactPerCapacity, dispatchMode))
                else:
                    logging.warning("Storage label not identified")

    def _calculateInvest(self, data):
        # Calculate the CAPEX and the part of the OPEX not related to energy flows (maintenance)
        c = data["installation"] + data["planification"] + 1
        m = data["maintenance"]
        perCapacity = m * data["invest_cap"] + economics.annuity(c * data["invest_cap"], data["lifetime"], intRate)
        base = m * data["invest_base"] + economics.annuity(c * data["invest_base"], data["lifetime"], intRate)
        return perCapacity, base