import oemof.solph as solph
import numpy as np
import combined_prod as cp
from oemof.thermal.solar_thermal_collector import flat_plate_precalc

class SolarCollector(solph.Transformer):
    def __init__(self, label, buildingLabel, inputs, outputs, connector, electrical_consumption, peripheral_losses, latitude,
                 longitude,
                 collector_tilt, collector_azimuth, eta_0, a_1, a_2, temp_collector_inlet, delta_temp_n,
                 irradiance_global,
                 irradiance_diffuse, temp_amb_col, capacityMin, capacityMax, epc, base, env_capa, env_flow, varc):

        flatPlateCollectorData = flat_plate_precalc(
            latitude, longitude, collector_tilt, collector_azimuth, eta_0, a_1, a_2, temp_collector_inlet, delta_temp_n,
            irradiance_global, irradiance_diffuse, temp_amb_col
        )

        self.collectors_eta_c = flatPlateCollectorData['eta_c']

        self.collectors_heat = flatPlateCollectorData['collectors_heat']/1000 #flow in kWh per m² of solar thermal panel

        self.__collector_source = solph.Source(
            label='heat_'+label + "__" + buildingLabel,
            outputs={
                connector: solph.Flow(
                    fix=self.collectors_heat,
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
                )
            },
        )

        self.__collector_excess_heat = solph.Sink(
            label='excess_solarheat' + "__" + buildingLabel, inputs={connector: solph.Flow()}
        )

        self.__collector_transformer = solph.Transformer(
            label=label + '__' + buildingLabel,
            inputs={connector: solph.Flow(), inputs: solph.Flow()},
            outputs={outputs: solph.Flow()},
            conversion_factors={
                connector: 1,
                inputs: electrical_consumption * (1 - peripheral_losses),
                outputs: 1 - peripheral_losses
            },
        )

    def getSolar(self, type):
        if type == 'source':
            return self.__collector_source
        elif type == 'transformer':
            return self.__collector_transformer
        elif type == 'sink':
            return self.__collector_excess_heat
        else:
            print("Transformer label not identified...")
            return []


class HeatPumpLinear:
    def __init__(self, buildingLabel, temperatureDHW, temperatureSH, temperatureLow, input, outputSH, outputDHW,
                 capacityMin, capacityMax, nomEff,
                 epc, base, varc, env_flow, env_capa):
        self.__copDHW = self._calculateCop(temperatureDHW, temperatureLow)
        self.__copSH = self._calculateCop(temperatureSH, temperatureLow)
        self.avgCopSh=(sum(self.__copSH)/len(self.__copSH))
        self.nominalEff =nomEff
        self.__heatpump = cp.CombinedTransformer(label='HP' + '__' + buildingLabel,
                                            inputs={input: solph.Flow(
                                                investment=solph.Investment(
                                                    ep_costs=epc*nomEff,
                                                    minimum=capacityMin/nomEff,
                                                    maximum=capacityMax/nomEff,
                                                    nonconvex=True,
                                                    offset=base,
                                                    env_per_capa=env_capa*nomEff,
                                                ),
                                            )},
                                            outputs={outputSH: solph.Flow(
                                                          variable_costs=varc,
                                                          env_per_flow=env_flow,
                                                      ),
                                                      outputDHW: solph.Flow(
                                                          variable_costs=varc,
                                                          env_per_flow=env_flow,
                                                      )
                                                  },
                                            efficiencies={outputSH: self.__copSH,
                                                        outputDHW: self.__copDHW})

    def _calculateCop(self, tHigh, tLow):
        coefW = [0.1600, -1.2369, 19.9391, 19.3448, 7.1057, -1.4048]
        coefQ = [13.8978, 114.8358, -9.3634, -179.4227, 342.3363, -12.4969]
        QCondenser = coefQ[0] + (coefQ[1] * tLow / 273.15) + (coefQ[2] * tHigh / 273.15) + (
                coefQ[3] * tLow / 273.15 * tHigh / 273.15) + (
                             coefQ[4] * (tLow / 273.15) ** 2) + (
                             coefQ[5] * (tHigh / 273.15) ** 2)
        WCompressor = coefW[0] + (coefW[1] * tLow / 273.15) + (coefW[2] * tHigh / 273.15) + (
                coefW[3] * tLow / 273.15 * tHigh / 273.15) + (
                             coefW[4] * (tLow / 273.15) ** 2) + (
                              coefW[5] * (tHigh / 273.15) ** 2)
        cop = np.divide(QCondenser, WCompressor)
        return cop

    def _chargingRule(self, dataLength):
        for t in range(dataLength):
            if any([(t - x) % 24 == 0 for x in self.__DHWChargingTimesteps]):
                    self.__copSH[t] = 0
            else:
                    self.__copDHW[t] = 0

    def getHP(self, type):
        if type == 'sh':
            return self.__heatpump
        else:
            print("Transformer label not identified...")
            return []


class CHP:
    def __init__(self, buildingLabel, input, outputEl, outputSH, outputDHW, efficiencyEl, efficiencySH, efficiencyDHW,
                 capacityMin, capacityEl, capacitySH, capacityDHW, epc, base, varc1, varc2, env_flow1, env_flow2, env_capa, timesteps):
        self._efficiencyEl = [efficiencyEl] * timesteps
        self._efficiencySH = [efficiencySH] * timesteps
        self._efficiencyDHW = [efficiencyDHW] * timesteps
        self.avgEff = efficiencySH
        self.__CHP = cp.CombinedCHP(
                        label='CHP'+'__'+buildingLabel,
                        inputs={
                            input: solph.Flow(
                                investment=solph.Investment(
                                    ep_costs=epc*self.avgEff,
                                    minimum=capacityMin/self.avgEff,
                                    maximum=capacitySH/self.avgEff,
                                    nonconvex=True,
                                    offset=base,
                                    env_per_capa=env_capa*self.avgEff,
                                ),
                            )
                        },
                        outputs={
                            outputSH: solph.Flow(
                                variable_costs=varc2,
                                env_per_flow=env_flow2,
                            ),
                            outputDHW: solph.Flow(
                                variable_costs=varc2,
                                env_per_flow=env_flow2,
                            ),
                            outputEl: solph.Flow(
                                variable_costs=varc1,
                                env_per_flow=env_flow1,
                            ),

                        },
                        efficiencies={outputSH: self._efficiencySH,
                                    outputDHW: self._efficiencyDHW,
                                    outputEl: self._efficiencyEl,
                                    }
                    )

    def _chargingRule(self, dataLength):
        for t in range(dataLength):
            if any([(t - x) % 24 == 0 for x in self.__DHWChargingTimesteps]):
                self._efficiencyElCHPSH[t] = 0
                self._efficiencySH[t] = 0
            else:
                self._efficiencyElCHPDHW[t] = 0
                self._efficiencyDHW[t] = 0

    def getCHP(self, type):
        if type == 'sh':
            return self.__CHP
        else:
            print("Transformer label not identified...")
            return []

class GasBoiler(cp.CombinedTransformer):
    def __init__(self, buildingLabel, input, outputSH, outputDHW, efficiencySH, efficiencyDHW,
                 capacityMin, capacityMax, epc, base, varc, env_flow, env_capa):
        self.__efficiency = efficiencySH
        super(GasBoiler, self).__init__(
            label='GasBoiler'+'__'+buildingLabel,
            inputs={
                input: solph.Flow(
                    investment=solph.Investment(
                        ep_costs=epc*efficiencySH,
                        minimum=capacityMin/efficiencySH,
                        maximum=capacityMax/efficiencySH,
                        nonconvex=True,
                        offset=base,
                        env_per_capa=env_capa*efficiencySH,
                    ),
                )
            },
            outputs={
                outputSH: solph.Flow(
                     variable_costs=varc,
                     env_per_flow=env_flow
                 ),
                outputDHW: solph.Flow(
                    variable_costs=varc,
                    env_per_flow=env_flow
                ),
            },
            efficiencies={outputSH: efficiencySH,
                        outputDHW: efficiencyDHW}
                 )