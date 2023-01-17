import numpy as np
import oemof.solph as solph
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

    def addBus(self, data, opt, mergeLinkBuses):
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

                    if b["excess"]:
                        self.__nodesList.append(
                            solph.Sink(
                                label="excess"+label,
                                inputs={
                                    self.__busDict[label]: solph.Flow(
                                        variable_costs=b["excess costs"]*(opt == "costs")  # if opt = "env" variable costs should be zero
                                    )}))
                    # add the excess production cost to self.__costParam
                    self.__costParam["excess"+label] = b["excess costs"]
        if mergeLinkBuses and self.__buildingLabel=='Building1':
            return self.__busDict

    def addToBusDict(self, busDictBuilding1):
        for label in self.__linkBuses:
            self.__busDict[label] = busDictBuilding1[label]

    def addPV(self, data, data_timeseries, opt):
        # Create Source objects from table 'commodity sources'
        for i, s in data.iterrows():
            if opt == "costs":
                epc=self._calculateInvest(s)[0]
                base=self._calculateInvest(s)[1]
                env_capa=s["impact_cap"] / s["lifetime"]
                env_flow=s["elec_impact"]
                varc=0 # variable cost is only passed for environmental optimization if there are emissions per kWh of energy produced from the unit

                envParam = [0, s["elec_impact"], s["impact_cap"] / s["lifetime"]]

            elif opt == "env":
                epc = s["impact_cap"] / s["lifetime"]
                base = 0
                env_capa = s["impact_cap"] / s["lifetime"]
                env_flow = s["elec_impact"]
                varc = s["elec_impact"] # variable cost is only passed for environmental optimization if there are emissions per kWh of energy produced from the unit

                envParam = [0, s["elec_impact"], s["impact_cap"] / s["lifetime"]]

            # If roof area and zenith do not exist in the excel file
            if 'roof_area' not in s.keys():
                s["roof_area"] = np.nan
            if 'zenith_angle' not in s.keys():
                s["zenith_angle"] = np.nan
            if 'efficiency' not in s.keys():
                s["efficiency"] = np.nan

            self.__nodesList.append(PV(s["label"], self.__buildingLabel,
                                       self.__busDict[s["to"] + '__' + self.__buildingLabel],
                                       s["peripheral_losses"], s["latitude"], s["longitude"],
                                       s["tilt"], s["efficiency"], s["roof_area"],
                                       s["zenith_angle"], s["azimuth"],
                                       data_timeseries['gls'],
                                       data_timeseries['str.diffus'],
                                       data_timeseries['tre200h0'], s["capacity_min"], s["capacity_max"],
                                       epc, base, env_capa, env_flow, varc))

            self.__envParam[s["label"] + '__' + self.__buildingLabel] = envParam

            self.__costParam[s["label"] + '__' + self.__buildingLabel] = [self._calculateInvest(s)[0],
                                                                          self._calculateInvest(s)[1]]
            self.__technologies.append(
                [s["to"] + '__' + self.__buildingLabel, s["label"] + '__' + self.__buildingLabel])

    def addSolar(self, data, data_timeseries, opt, mergeLinkBuses):
        # Create Source objects from table 'commodity sources'
        for i, s in data.iterrows():
            if mergeLinkBuses and s["from"] in self.__linkBuses:
                inputBusLabel = s["from"]
            else:
                inputBusLabel = s["from"] + '__' + self.__buildingLabel

            if opt == "costs":
                epc=self._calculateInvest(s)[0]
                base=self._calculateInvest(s)[1]
                env_capa=s["impact_cap"] / s["lifetime"]
                env_flow=s["heat_impact"]
                varc=0 # variable cost is only passed for environmental optimization if there are emissions per kWh of energy produced from the unit

                envParam = [s["heat_impact"], 0, env_capa]

            elif opt == "env":
                epc=s["impact_cap"] / s["lifetime"]
                base=0
                env_capa= s["impact_cap"] / s["lifetime"]
                env_flow=s["heat_impact"]
                varc= s["heat_impact"] # variable cost is only passed for environmental optimization if there are emissions per kWh of energy produced from the unit

                envParam = [s["heat_impact"], 0, env_capa]

            # If roof area and zenith do not exist in the excel file
            if 'roof_area' not in s.keys():
                s["roof_area"] = np.nan
            if 'zenith_angle' not in s.keys():
                s["zenith_angle"] = np.nan
            collector=SolarCollector(s["label"], self.__buildingLabel,
                                                   self.__busDict[inputBusLabel],
                                                   self.__busDict[s["to"] + '__' + self.__buildingLabel],
                                                   self.__busDict[s["connect"]+ '__' + self.__buildingLabel],
                                                   s["electrical_consumption"], s["peripheral_losses"], s["latitude"],
                                                   s["longitude"], s["tilt"], s["roof_area"],
                                                   s["zenith_angle"], s["azimuth"],
                                                   s["eta_0"], s["a_1"], s["a_2"], s["temp_collector_inlet"],
                                                   s["delta_temp_n"], data_timeseries['gls'], data_timeseries['str.diffus'],
                                                    data_timeseries['tre200h0'], s["capacity_min"], s["capacity_max"],
                                                   epc, base, env_capa, env_flow, varc)
            self.__nodesList.append(collector.getSolar("source"))
            self.__nodesList.append(collector.getSolar("transformer"))
            self.__nodesList.append(collector.getSolar("sink"))

            self.__envParam["heat_"+s["label"] + '__' + self.__buildingLabel] = envParam

            self.__costParam["heat_"+s["label"] + '__' + self.__buildingLabel] = [self._calculateInvest(s)[0],
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
                                                      conversion_factors={self.__busDict[outputBusLabel]: gs["efficiency"]}))

    def addSource(self, data, data_elec, data_cost, opt):
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
                        varCosts = data_cost["cost"]
                    else:
                        varCosts = cs["variable costs"]
                elif 'electricity' in cs["label"]:
                    varCosts = data_elec["impact"]
                else:
                    varCosts = cs["CO2 impact"]

                if 'electricity' in cs["label"]:
                    envImpactPerFlow = data_elec["impact"]
                    envParameter = data_elec["impact"]
                    costParameter = data_cost["cost"]
                else:
                    envImpactPerFlow = cs["CO2 impact"]
                    envParameter = cs["CO2 impact"]
                    costParameter = cs["variable costs"]
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
                    inflow_args = {"nominal_value": de["nominal value"]}
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

    def _addHeatPump(self, data, temperatureDHW, temperatureSH, temperatureAmb, opt, mergeLinkBuses):
        hpSHLabel = data["label"] + '__' + self.__buildingLabel
        if mergeLinkBuses and data["from"] in self.__linkBuses:
            inputBusLabel = data["from"]
        else:
            inputBusLabel = data["from"] + '__' + self.__buildingLabel
        outputSHBusLabel = data["to"].split(",")[0] + '__' + self.__buildingLabel
        outputDHWBusLabel = data["to"].split(",")[1] + '__' + self.__buildingLabel
        envImpactPerCapacity = data["impact_cap"] / data["lifetime"]

        heatPump = HeatPumpLinear(self.__buildingLabel, temperatureDHW, temperatureSH, temperatureAmb,
                                  self.__busDict[inputBusLabel],
                                  self.__busDict[outputSHBusLabel],
                                  self.__busDict[outputDHWBusLabel],
                                  data["capacity_min"], data["capacity_SH"],data["efficiency"],
                                  self._calculateInvest(data)[0] * (opt == "costs") + envImpactPerCapacity*(opt == "env"),
                                  self._calculateInvest(data)[1] * (opt == "costs"),
                                  data["heat_impact"] * (opt == "env"),
                                  data["heat_impact"], envImpactPerCapacity)

        self.__nodesList.append(heatPump.getHP("sh"))

        # set technologies, environment and cost parameters
        self.__technologies.append([outputDHWBusLabel, hpSHLabel])
        self.__technologies.append([outputSHBusLabel, hpSHLabel])

        self.__costParam[hpSHLabel] = [self._calculateInvest(data)[0], self._calculateInvest(data)[1]]

        self.__envParam[hpSHLabel] = [data["heat_impact"], 0, envImpactPerCapacity]

    def _addGeothemalHeatPump(self, data, temperatureDHW, temperatureSH, temperatureAmb, opt, mergeLinkBuses):
        gwhpSHLabel = data["label"] + '__' + self.__buildingLabel
        if mergeLinkBuses and data["from"] in self.__linkBuses:
            inputBusLabel = data["from"]
        else:
            inputBusLabel = data["from"] + '__' + self.__buildingLabel
        outputSHBusLabel = data["to"].split(",")[0] + '__' + self.__buildingLabel
        outputDHWBusLabel = data["to"].split(",")[1] + '__' + self.__buildingLabel
        envImpactPerCapacity = data["impact_cap"] / data["lifetime"]

        geothermalheatPump = GeothermalHeatPumpLinear(self.__buildingLabel, temperatureDHW, temperatureSH, temperatureAmb,
                                  self.__busDict[inputBusLabel],
                                  self.__busDict[outputSHBusLabel],
                                  self.__busDict[outputDHWBusLabel],
                                  data["capacity_min"], data["capacity_SH"],data["efficiency"],
                                  self._calculateInvest(data)[0] * (opt == "costs") + envImpactPerCapacity*(opt == "env"),
                                  self._calculateInvest(data)[1] * (opt == "costs"),
                                  data["heat_impact"] * (opt == "env"),
                                  data["heat_impact"], envImpactPerCapacity)

        self.__nodesList.append(geothermalheatPump.getHP("sh"))

        # set technologies, environment and cost parameters
        self.__technologies.append([outputDHWBusLabel, gwhpSHLabel])
        self.__technologies.append([outputSHBusLabel, gwhpSHLabel])

        self.__costParam[gwhpSHLabel] = [self._calculateInvest(data)[0], self._calculateInvest(data)[1]]

        self.__envParam[gwhpSHLabel] = [data["heat_impact"], 0, envImpactPerCapacity]

    def _addGeothemalHeatPumpSplit(self, data, temperatureDHW, temperatureSH, temperatureAmb, opt, mergeLinkBuses):
        gwhpDHWLabel = data["label"][0:4] + str(temperatureDHW) + '__' + self.__buildingLabel
        gwhpSHLabel = data["label"][0:4] + str(temperatureSH) + '__' + self.__buildingLabel
        if mergeLinkBuses and data["from"] in self.__linkBuses:
            inputBusLabel = data["from"]
        else:
            inputBusLabel = data["from"] + '__' + self.__buildingLabel
        outputSHBusLabel = data["to"].split(",")[0] + '__' + self.__buildingLabel
        outputDHWBusLabel = data["to"].split(",")[1] + '__' + self.__buildingLabel
        envImpactPerCapacity = data["impact_cap"] / data["lifetime"]
        capacityDHW = data["capacity_DHW"]
        capacitySH = data["capacity_SH"]
        if data["capacity_min"] == 'x':
            capacityMinSH = capacitySH
            capacityMinDHW = capacityDHW
        else:
            capacityMinSH = capacityMinDHW = data["capacity_min"]

        geothermalheatPumpSH = GeothermalHeatPumpLinearSingleUse(self.__buildingLabel, temperatureSH, temperatureAmb,
                                  self.__busDict[inputBusLabel],
                                  self.__busDict[outputSHBusLabel],
                                  capacityMinSH, capacitySH,
                                  self._calculateInvest(data)[0] * (opt == "costs") + envImpactPerCapacity*(opt == "env"),
                                  self._calculateInvest(data)[1] * (opt == "costs"),
                                  data["heat_impact"] * (opt == "env"),
                                  data["heat_impact"], envImpactPerCapacity)
        geothermalheatPumpDHW = GeothermalHeatPumpLinearSingleUse(self.__buildingLabel, temperatureDHW,
                                                        temperatureAmb,
                                                        self.__busDict[inputBusLabel],
                                                        self.__busDict[outputDHWBusLabel],
                                                        capacityMinDHW, capacityDHW,
                                                        self._calculateInvest(data)[0] * (
                                                                    opt == "costs") + envImpactPerCapacity * (
                                                                    opt == "env"),
                                                        self._calculateInvest(data)[1] * (opt == "costs"),
                                                        data["heat_impact"] * (opt == "env"),
                                                        data["heat_impact"], envImpactPerCapacity)

        self.__nodesList.append(geothermalheatPumpSH.getHP("sh"))
        self.__nodesList.append(geothermalheatPumpDHW.getHP("sh"))

        # set technologies, environment and cost parameters
        self.__technologies.append([outputDHWBusLabel, gwhpDHWLabel])
        self.__technologies.append([outputSHBusLabel, gwhpSHLabel])

        self.__costParam[gwhpSHLabel] = [self._calculateInvest(data)[0], self._calculateInvest(data)[1]]
        self.__costParam[gwhpDHWLabel] = [self._calculateInvest(data)[0], self._calculateInvest(data)[1]]

        self.__envParam[gwhpSHLabel] = [data["heat_impact"], 0, envImpactPerCapacity]
        self.__envParam[gwhpDHWLabel] = [data["heat_impact"], 0, envImpactPerCapacity]

    def _addCHP(self, data, timesteps, opt):
        chpSHLabel = data["label"] + '__' + self.__buildingLabel
        inputBusLabel = data["from"] + '__' + self.__buildingLabel
        outputElBusLabel = data["to"].split(",")[0] + '__' + self.__buildingLabel
        outputSHBusLabel = data["to"].split(",")[1] + '__' + self.__buildingLabel
        outputDHWBusLabel = data["to"].split(",")[2] + '__' + self.__buildingLabel
        elEfficiency = float(data["efficiency"].split(",")[0])
        shEfficiency = float(data["efficiency"].split(",")[1])
        dhwEfficiency = float(data["efficiency"].split(",")[2])
        envImpactPerCapacity = data["impact_cap"] / data["lifetime"]

        chp = CHP(self.__buildingLabel, self.__busDict[inputBusLabel],
                  self.__busDict[outputElBusLabel],
                  self.__busDict[outputSHBusLabel],
                  self.__busDict[outputDHWBusLabel],
                  elEfficiency, shEfficiency,
                  dhwEfficiency, data["capacity_min"], data["capacity_el"],
                  data["capacity_SH"], data["capacity_DHW"],
                  self._calculateInvest(data)[0] * (opt == "costs") + envImpactPerCapacity * (opt == "env"),
                  self._calculateInvest(data)[1] * (opt == "costs"), data["elec_impact"] * (opt == "env"),
                  data["heat_impact"] * (opt == "env"),
                  data["elec_impact"], data["heat_impact"], envImpactPerCapacity, timesteps)

        self.__nodesList.append(chp.getCHP("sh"))

        # set technologies, environment and cost parameters
        self.__technologies.append([outputElBusLabel, chpSHLabel])
        self.__technologies.append([outputSHBusLabel, chpSHLabel])
        self.__technologies.append([outputDHWBusLabel, chpSHLabel])

        self.__costParam[chpSHLabel] = [self._calculateInvest(data)[0], self._calculateInvest(data)[1]]

        self.__envParam[chpSHLabel] = [data["heat_impact"], data["elec_impact"], envImpactPerCapacity]

    def _addGasBoiler(self, data, opt):
        gasBoilLabel = data["label"] + '__' + self.__buildingLabel
        inputBusLabel = data["from"] + '__' + self.__buildingLabel
        outputSHBusLabel = data["to"].split(",")[0] + '__' + self.__buildingLabel
        outputDHWBusLabel = data["to"].split(",")[1] + '__' + self.__buildingLabel
        shEfficiency = float(data["efficiency"].split(",")[0])
        dhwEfficiency = float(data["efficiency"].split(",")[1])
        envImpactPerCapacity = data["impact_cap"] / data["lifetime"]


        self.__nodesList.append(GasBoiler(self.__buildingLabel, self.__busDict[inputBusLabel],
                  self.__busDict[outputSHBusLabel], self.__busDict[outputDHWBusLabel],
                  shEfficiency, dhwEfficiency, data["capacity_min"], data["capacity_SH"],
                  self._calculateInvest(data)[0] * (opt == "costs") + envImpactPerCapacity * (opt == "env"),
                  self._calculateInvest(data)[1] * (opt == "costs"), data["heat_impact"] * (opt == "env"), data["heat_impact"], envImpactPerCapacity))

        # set technologies, environment and cost parameters
        self.__technologies.append([outputSHBusLabel, gasBoilLabel])
        self.__technologies.append([outputDHWBusLabel, gasBoilLabel])

        self.__costParam[gasBoilLabel] = [self._calculateInvest(data)[0], self._calculateInvest(data)[1]]

        self.__envParam[gasBoilLabel] = [data["heat_impact"], 0, envImpactPerCapacity]

    def _addElectricRod(self, data, opt, mergeLinkBuses):
        elRodLabel = data["label"] + '__' + self.__buildingLabel
        if mergeLinkBuses and data["from"] in self.__linkBuses:
            inputBusLabel = data["from"]
        else:
            inputBusLabel = data["from"] + '__' + self.__buildingLabel
        outputSHBusLabel = data["to"].split(",")[0] + '__' + self.__buildingLabel
        outputDHWBusLabel = data["to"].split(",")[1] + '__' + self.__buildingLabel
        efficiency = float(data["efficiency"])
        envImpactPerCapacity = data["impact_cap"] / data["lifetime"]

        self.__nodesList.append(ElectricRod(self.__buildingLabel, self.__busDict[inputBusLabel],
                                          self.__busDict[outputSHBusLabel], self.__busDict[outputDHWBusLabel],
                                          efficiency, data["capacity_min"], data["capacity_SH"],
                                          self._calculateInvest(data)[0] * (opt == "costs") + envImpactPerCapacity * (
                                                      opt == "env"),
                                          self._calculateInvest(data)[1] * (opt == "costs"),
                                          data["heat_impact"] * (opt == "env"), data["heat_impact"],
                                          envImpactPerCapacity))

        # set technologies, environment and cost parameters
        self.__technologies.append([outputSHBusLabel, elRodLabel])
        self.__technologies.append([outputDHWBusLabel, elRodLabel])

        self.__costParam[elRodLabel] = [self._calculateInvest(data)[0], self._calculateInvest(data)[1]]

        self.__envParam[elRodLabel] = [data["heat_impact"], 0, envImpactPerCapacity]

    def addTransformer(self, data, temperatureDHW, temperatureSH, temperatureAmb, temperatureGround, opt, mergeLinkBuses):
        for i, t in data.iterrows():
            if t["active"]:
                if t["label"] == "HP":
                    self._addHeatPump(t, temperatureDHW, temperatureSH, temperatureAmb, opt, mergeLinkBuses)
                elif t["label"] == "GWHP":
                    self._addGeothemalHeatPump(t, temperatureDHW, temperatureSH, temperatureGround, opt, mergeLinkBuses)
                elif t["label"] == "GWHP split":
                    self._addGeothemalHeatPumpSplit(t, temperatureDHW, temperatureSH, temperatureGround, opt, mergeLinkBuses)
                elif t["label"] == "CHP":
                    self._addCHP(t, len(temperatureAmb), opt)
                elif t["label"] == "GasBoiler":
                    self._addGasBoiler(t, opt)
                elif t["label"] == "ElectricRod":
                    self._addElectricRod(t, opt, mergeLinkBuses)
                else:
                    logging.warning("Transformer label not identified...")

    def addElectricRodBackup(self, opt):
        elRodLabel = "ElectricRod"+'__'+self.__buildingLabel
        inputBusLabel = "electricityInBus"+'__'+self.__buildingLabel
        outputSHBusLabel = "shSourceBus"+'__' + self.__buildingLabel
        outputDHWBusLabel = "dhwStorageBus"+'__' + self.__buildingLabel
        efficiency = 1
        heat_impact = 0
        capacity = 50              # 10kW capacity is assumed to be installed as backup

        self.__nodesList.append(ElectricRodFixed(self.__buildingLabel, self.__busDict[inputBusLabel],
                                          self.__busDict[outputSHBusLabel], self.__busDict[outputDHWBusLabel],
                                          efficiency,
                                          heat_impact * (opt == "env"), heat_impact, capacity))


    def addStorage(self, data, stratifiedStorageParams, opt, mergeLinkBuses):
        for i, s in data.iterrows():
            if s["active"]:
                storageLabel = s["label"]+'__'+self.__buildingLabel
                inputBusLabel = s["from"]+'__'+self.__buildingLabel
                if mergeLinkBuses and s["to"] in self.__linkBuses:
                    outputBusLabel = s["to"]
                else:
                    outputBusLabel = s["to"]+'__'+self.__buildingLabel
                envImpactPerCapacity = s["impact_cap"] / s["lifetime"]         # annualized value
                # set technologies, environment and cost parameters
                self.__costParam[storageLabel] = [self._calculateInvest(s)[0], self._calculateInvest(s)[1]]
                self.__envParam[storageLabel] = [s["heat_impact"], s["elec_impact"], envImpactPerCapacity]
                self.__technologies.append([outputBusLabel, storageLabel])

                if s["label"] == "electricalStorage":
                    self.__nodesList.append(ElectricalStorage(self.__buildingLabel, self.__busDict[inputBusLabel],
                                                              self.__busDict[outputBusLabel], s["capacity loss"],
                                                            s["initial capacity"], s["efficiency inflow"],
                                                            s["efficiency outflow"], s["capacity min"],
                                                            s["capacity max"],
                                                            self._calculateInvest(s)[0]*(opt == "costs") + envImpactPerCapacity*(opt == "env"),
                                                            self._calculateInvest(s)[1]*(opt == "costs"),
                                                            s["elec_impact"]*(opt == "env"),
                                                            s["elec_impact"], envImpactPerCapacity))

                elif s["label"] == "dhwStorage" or s["label"] == "shStorage":
                    self.__nodesList.append(ThermalStorage(storageLabel, s["label"],
                                                           stratifiedStorageParams, self.__busDict[inputBusLabel],
                                                           self.__busDict[outputBusLabel],
                                                        s["initial capacity"], s["capacity min"],
                                                        s["capacity max"],
                                                        self._calculateInvest(s)[0]*(opt == "costs") + envImpactPerCapacity*(opt == "env"),
                                                        self._calculateInvest(s)[1]*(opt == "costs"), s["heat_impact"]*(opt == "env"),
                                                        s["heat_impact"], envImpactPerCapacity))
                else:
                    logging.warning("Storage label not identified")

    def _calculateInvest(self, data):
        # Calculate the CAPEX and the part of the OPEX not related to energy flows (maintenance)
        c = data["installation"] + data["planification"] + 1
        m = data["maintenance"]
        perCapacity = m * data["invest_cap"] + economics.annuity(c * data["invest_cap"], data["lifetime"], intRate)
        base = m * data["invest_base"] + economics.annuity(c * data["invest_base"], data["lifetime"], intRate)
        return perCapacity, base