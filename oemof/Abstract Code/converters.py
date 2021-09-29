import oemof.solph as solph
import numpy as np
from oemof.thermal.facades import SolarThermalCollector


class SolarCollector:
    def __init__(self, label, buildingLabel, inputs, outputs, electrical_consumption, peripheral_losses, aperture_area, latitude, longitude,
                 collector_tilt, collector_azimuth, eta_0, a_1, a_2, temp_collector_inlet, delta_temp_n, irradiance_global,
                 irradiance_diffuse, temp_amb_col, epc, capacityMin, capacityMax, base, env_capa, env_flow, varc):
        collectorModel = SolarThermalCollector(label=label+'__'+buildingLabel, heat_out_bus=outputs,
                                                  electricity_in_bus=inputs, electrical_consumption=electrical_consumption,
                                                  peripheral_losses=peripheral_losses, aperture_area=aperture_area,
                                                  latitude=latitude, longitude=longitude, collector_tilt=collector_tilt,
                                                  collector_azimuth=collector_azimuth, eta_0=eta_0, a_1=a_1, a_2=a_2,
                                                  temp_collector_inlet=temp_collector_inlet, delta_temp_n=delta_temp_n,
                                                  irradiance_global=irradiance_global, irradiance_diffuse=irradiance_diffuse,
                                                  temp_amb_col=temp_amb_col)

        # data = flat_plate_precalc(
        #     self.latitude,
        #     self.longitude,
        #     self.collector_tilt,
        #     self.collector_azimuth,
        #     self.eta_0,
        #     self.a_1,
        #     self.a_2,
        #     self.temp_collector_inlet,
        #     self.delta_temp_n,
        #     self.irradiance_global,
        #     self.irradiance_diffuse,
        #     self.temp_amb,
        # )
        #
        # self.collectors_eta_c = data['eta_c']
        #
        # self.collectors_heat = data['collectors_heat']
        #
        print(collectorModel)
        self.__solarCollector = solph.Transformer(label=label+'__'+buildingLabel, inputs={inputs: solph.Flow()},
                                                  outputs={outputs: solph.Flow(
                                                    investment=solph.Investment(
                                                        ep_costs=epc,
                                                        minimum=capacityMin,
                                                        maximum=capacityMax,
                                                        nonconvex=True,
                                                        offset=base,
                                                        env_per_capa=env_capa,
                                                    ),
                                                    variable_costs=varc,
                                                    env_per_flow=env_flow,
                                                    )},
                                                  conversion_factors={outputs: collectorModel.collectors_eta_c})

    def getSolarCollector(self):
        return self.__solarCollector

class HeatPumpLinear:
    def __init__(self, buildingLabel, temperatureDHW, temperatureSH, temperatureLow, input, outputSH, outputDHW, capacityMin, capacityMax,
                 epc, base, varc, env_flow, env_capa):
        self.__copDHW = self._calculateCop(temperatureDHW, temperatureLow)
        self.__copSH = self._calculateCop(temperatureSH, temperatureLow)
        self.__DHWChargingTimesteps = [5, 6, 16, 17]     # Data in the scenario file is from 01:00 H onwards (instead of 00:00)
        self._chargingRule()
        self.__heatpumpSH = solph.Transformer(label='HP_SH'+'__'+buildingLabel, inputs={input: solph.Flow()},
                                              outputs={outputSH: solph.Flow(
                                                        investment=solph.Investment(
                                                            ep_costs=epc,
                                                            minimum=capacityMin,
                                                            maximum=capacityMax,
                                                            nonconvex=True,
                                                            offset=base,
                                                            env_per_capa=env_capa,
                                                        ),
                                                        variable_costs=varc,
                                                        env_per_flow=env_flow,

                                                        )},
                                              conversion_factors={outputSH: self.__copSH})
        self.__heatpumpDHW = solph.Transformer(label='HP_DHW'+'__'+buildingLabel, inputs={input: solph.Flow()},
                                               outputs={outputDHW: solph.Flow(
                                                        investment=solph.Investment(
                                                            ep_costs=epc,
                                                            minimum=capacityMin,
                                                            maximum=capacityMax,
                                                            nonconvex=True,
                                                            offset=base,
                                                            env_per_capa=env_capa,
                                                        ),
                                                        variable_costs=varc,
                                                        env_per_flow=env_flow,

                                                        )},
                                               conversion_factors={outputDHW: self.__copDHW})

    def _calculateCop(self, tHigh, tLow):
        coefCOP = [12.4896, 64.0652, -83.0217, -230.1195, 173.2122]
        coefQ = [13.8603, 120.2178, -7.9046, -164.1900, -17.9805]
        QCondenser = coefQ[0] + (coefQ[1] * tLow / 273.15) + (coefQ[2] * tHigh / 273.15) + (
                coefQ[3] * tLow / 273.15 * tHigh / 273.15) + (
                                 coefQ[4] * tHigh / 273.15 * tHigh / 273.15)
        WCompressor = coefCOP[0] + (coefCOP[1] * tLow / 273.15) + (coefCOP[2] * tHigh / 273.15) + (
                coefCOP[3] * tLow / 273.15 * tHigh / 273.15) + (
                                  coefCOP[4] * tHigh / 273.15 * tHigh / 273.15)
        cop = np.divide(QCondenser, WCompressor)
        return cop

    def _chargingRule(self):
        for t in range(8760):
            if any([(t - x) % 24 == 0 for x in self.__DHWChargingTimesteps]):
                    self.__copSH[t] = 0
            else:
                    self.__copDHW[t] = 0

    def getHP(self, type):
        if type == 'sh':
            return self.__heatpumpSH
        elif type == 'dhw':
            return self.__heatpumpDHW
        else:
            print("Transformer label not identified...")
            return []


class CHP:
    def __init__(self, buildingLabel, input, outputEl, outputSH, outputDHW, efficiencyEl, efficiencySH, efficiencyDHW,
                 capacityMin, capacityEl, capacitySH, capacityDHW, epc, base, varc1, varc2, env_flow1, env_flow2, env_capa):
        self.__DHWChargingTimesteps = [5, 6, 16, 17]                    # Data in the scenario file is from 01:00 H onwards (instead of 00:00)
        self._efficiencyElCHPSH = [efficiencyEl] * 8760
        self._efficiencyElCHPDHW = [efficiencyEl] * 8760
        self._efficiencySH = [efficiencySH] * 8760
        self._efficiencyDHW = [efficiencyDHW] * 8760
        #self._chargingRule()
        self.__CHPSH = solph.Transformer(
                        label='CHP_SH'+'__'+buildingLabel,
                        inputs={
                            input: solph.Flow()
                        },
                        outputs={
                            outputEl: solph.Flow(
                                investment=solph.Investment(
                                    ep_costs=epc,
                                    minimum=float(capacityMin) * efficiencyEl / efficiencyEl + efficiencySH,
                                    maximum=float(capacityEl) * efficiencyEl / efficiencyEl + efficiencySH,
                                    nonconvex=True,
                                    offset=base,
                                    env_per_capa=env_capa,
                                ),
                                variable_costs=varc1,
                                env_per_flow=env_flow1,

                            ),
                            outputSH: solph.Flow(
                                investment=solph.Investment(
                                    ep_costs=epc,
                                    minimum=float(capacityMin) * efficiencySH / efficiencyEl + efficiencySH,
                                    maximum=float(capacitySH) * efficiencySH / efficiencyEl + efficiencySH,
                                    nonconvex=True,
                                    offset=base,
                                    env_per_capa=env_capa,
                                ),
                                variable_costs=varc2,
                                env_per_flow=env_flow2,

                            ),
                        },
                        conversion_factors={outputEl: self._efficiencyElCHPSH,
                                            outputSH: self._efficiencySH,
                                            }
                    )
        self.__CHPDHW = solph.Transformer(
            label='CHP_DHW' + '__' + buildingLabel,
            inputs={
                input: solph.Flow()
            },
            outputs={
                outputEl: solph.Flow(
                    investment=solph.Investment(
                        ep_costs=epc,
                        minimum=float(capacityMin) * efficiencyEl / efficiencyEl + efficiencyDHW,
                        maximum=float(capacityEl) * efficiencyEl / efficiencyEl + efficiencyDHW,
                        nonconvex=True,
                        offset=base,
                        env_per_capa=env_capa,
                    ),
                    variable_costs=varc1,
                    env_per_flow=env_flow1,

                ),
                outputDHW: solph.Flow(
                    investment=solph.Investment(
                        ep_costs=epc,
                        minimum=float(capacityMin) * efficiencyDHW / efficiencyEl + efficiencyDHW,
                        maximum=float(capacityDHW) * efficiencyDHW / efficiencyEl + efficiencyDHW,
                        nonconvex=True,
                        offset=base,
                        env_per_capa=env_capa,
                    ),
                    variable_costs=varc2,
                    env_per_flow=env_flow2,

                ),
            },
            conversion_factors={outputEl: self._efficiencyElCHPDHW,
                                outputDHW: self._efficiencyDHW,
                                }
        )

    def _chargingRule(self):
        for t in range(8760):
            if any([(t - x) % 24 == 0 for x in self.__DHWChargingTimesteps]):
                self._efficiencyElCHPSH[t] = 0
                self._efficiencySH[t] = 0
            else:
                self._efficiencyElCHPDHW[t] = 0
                self._efficiencyDHW[t] = 0

    def getCHP(self, type):
        if type == 'sh':
            return self.__CHPSH
        elif type == 'dhw':
            return self.__CHPDHW
        else:
            print("Transformer label not identified...")
            return []
