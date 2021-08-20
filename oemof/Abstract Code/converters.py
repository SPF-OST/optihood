import oemof.solph as solph
import numpy as np

class HeatPumpLinear:
    def __init__(self, buildingLabel, temperatureDHW, temperatureSH, temperatureLow, input, outputSH, outputDHW, capacityMin, capacityMax,
                 epc, base, varc, env_flow, env_capa):
        self.__copDHW = self._calculate_cop(temperatureDHW, temperatureLow)
        self.__copSH = self._calculate_cop(temperatureSH, temperatureLow)
        self.__heatpumpSH = solph.Transformer(label='HP_SH'+'__'+buildingLabel, inputs={input: solph.Flow()}, outputs={outputSH: solph.Flow(
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
        self.__heatpumpDHW = solph.Transformer(label='HP_DHW'+'__'+buildingLabel, inputs={input: solph.Flow()}, outputs={outputDHW: solph.Flow(
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

    def _calculate_cop(self, tHigh, tLow):
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

    def getHP(self, type):
        if type == 'sh':
            return self.__heatpumpSH
        elif type == 'dhw':
            return self.__heatpumpDHW
        else:
            print("Transformer label not identified...")
            return []


class CHP(solph.Transformer):
    def __init__(self, buildingLabel, input, outputEl, outputSH, outputDHW, efficiencyEl, efficiencySH, efficiencyDHW,
                 capacityMin, CapacityEl, capacitySH, capacityDHW, epc, base, varc1, varc2, env_flow1, env_flow2, env_capa):
        super(CHP, self).__init__(
                        label='CHP'+'__'+buildingLabel,
                        inputs={
                            input: solph.Flow()
                        },
                        outputs={
                            outputEl: solph.Flow(
                                investment=solph.Investment(
                                    ep_costs=epc,
                                    minimum=capacityMin,
                                    maximum=CapacityEl,
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
                                    minimum=capacityMin,
                                    maximum=capacitySH,
                                    nonconvex=True,
                                    #offset=base,
                                    env_per_capa=env_capa,
                                ),
                                variable_costs=varc2,
                                env_per_flow=env_flow2,

                            ),
                            outputDHW: solph.Flow(
                                investment=solph.Investment(
                                    ep_costs=epc,
                                    minimum=capacityMin,
                                    maximum=capacityDHW,
                                    nonconvex=True,
                                    #offset=base,
                                    env_per_capa=env_capa,
                                ),
                                variable_costs=varc2,
                                env_per_flow=env_flow2,

                            ),
                        },
                        conversion_factors={outputEl: efficiencyEl,
                                            outputSH: efficiencySH,
                                            outputDHW: efficiencyDHW,
                                            }
                    )
