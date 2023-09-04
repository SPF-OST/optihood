import oemof.solph as solph
import numpy as np
import optihood.optihood.combined_prod as cp
from oemof.thermal.solar_thermal_collector import flat_plate_precalc
from oemof.solph import network as solph_network
from oemof.solph.plumbing import sequence as solph_sequence
from pyomo.core.base.block import SimpleBlock
from pyomo.environ import BuildAction
from pyomo.environ import Constraint

class SolarCollector:
    def __init__(self, label, buildingLabel, inputs, outputs, connector, electrical_consumption, peripheral_losses, latitude,
                 longitude,
                 collector_tilt, roof_area, zenith_angle, collector_azimuth, eta_0, a_1, a_2, temp_collector_inlet,
                 delta_temp_n, irradiance_global,
                 irradiance_diffuse, temp_amb_col, capacityMin, capacityMax, epc, base, env_capa, env_flow, varc, dispatchMode):

        flatPlateCollectorData = flat_plate_precalc(
            latitude, longitude, collector_tilt, collector_azimuth, eta_0, a_1, a_2, temp_collector_inlet, delta_temp_n,
            irradiance_global, irradiance_diffuse, temp_amb_col
        )

        if not (np.isnan(roof_area) or np.isnan(zenith_angle)):
            self.surface_used = self._calculateArea(zenith_angle, collector_tilt, collector_azimuth)
        else:
            self.surface_used = np.nan

        self.collectors_eta_c = flatPlateCollectorData['eta_c']

        self.collectors_heat = flatPlateCollectorData['collectors_heat']/1000 #flow in kWh per m² of solar thermal panel

        if dispatchMode:
            investArgs = {'ep_costs':epc,
                        'minimum':capacityMin,
                        'maximum':capacityMax,
                        'space':self.surface_used,
                        'roof_area':roof_area,
                        'env_per_capa':env_capa}
        else:
            investArgs = {'ep_costs':epc,
                        'minimum':capacityMin,
                        'maximum':capacityMax,
                        'nonconvex':True,
                        'space':self.surface_used,
                        'roof_area':roof_area,
                        'offset':base,
                        'env_per_capa':env_capa}
        self.__collector_source = solph.Source(
            label='heat_'+label + "__" + buildingLabel,
            outputs={
                connector: solph.Flow(
                    fix=self.collectors_heat,
                    investment=solph.Investment(**investArgs),
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

    def _calculateArea(self, zenith_angle, collector_tilt, collector_azimuth):
        coeff = -np.sin((zenith_angle+collector_tilt)*np.pi/180)*np.cos(collector_azimuth*np.pi/180)/np.sin(zenith_angle*np.pi/180)
        return coeff


class HeatPumpLinear:
    "Information about the model can be found in combined_pro.py CombinedTransformer"
    def __init__(self, buildingLabel, temperatureDHW, temperatureSH, temperatureLow, input, outputSH, outputDHW,
                 capacityMin, capacityMax, nomEff,
                 epc, base, varc, env_flow, env_capa, dispatchMode):
        self.__copDHW = self._calculateCop(temperatureDHW, temperatureLow)
        self.__copSH = self._calculateCop(temperatureSH, temperatureLow)
        self.avgCopSh = (sum(self.__copSH)/len(self.__copSH))
        self.nominalEff = nomEff
        if dispatchMode:
            investArgs = {'ep_costs' : epc * nomEff,
            'minimum' : capacityMin / nomEff,
            'maximum' : capacityMax / nomEff,
            'env_per_capa' : env_capa * nomEff}
        else:
            investArgs = {'ep_costs' : epc * nomEff,
            'minimum' : capacityMin / nomEff,
            'maximum' : capacityMax / nomEff,
            'nonconvex' : True,
            'offset' : base,
            'env_per_capa' : env_capa * nomEff}
        self.__heatpump = cp.CombinedTransformer(label='HP' + '__' + buildingLabel,
                                            inputs={input: solph.Flow(
                                                investment=solph.Investment(**investArgs),
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
        coefW = [0.66610, -2.2365, 15.541, 25.705, -17.407, 3.8145]
        coefQ = [11.833, 96.504, 14.496, -50.064, 161.02, -133.60]
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

    def getHP(self, type):
        if type == 'sh':
            return self.__heatpump
        else:
            print("Transformer label not identified...")
            return []


class GeothermalHeatPumpLinear:
    "Information about the model can be found in combined_pro.py CombinedTransformer"
    def __init__(self, buildingLabel, temperatureDHW, temperatureSH, temperatureLow, input, outputSH, outputDHW,
                 capacityMin, capacityMax, nomEff,
                 epc, base, varc, env_flow, env_capa, dispatchMode):
        self.__copDHW = self._calculateCop(temperatureDHW, temperatureLow)
        self.__copSH = self._calculateCop(temperatureSH, temperatureLow)
        self.avgCopSh = (sum(self.__copSH)/len(self.__copSH))
        self.nominalEff = nomEff
        if dispatchMode:
            investArgs= {'ep_costs':epc*nomEff,
                        'minimum':capacityMin/nomEff,
                        'maximum':capacityMax/nomEff,
                        'env_per_capa':env_capa*nomEff,
                    }
        else:
            investArgs= {'ep_costs':epc*nomEff,
                        'minimum':capacityMin/nomEff,
                        'maximum':capacityMax/nomEff,
                        'nonconvex':True,
                        'offset':base,
                        'env_per_capa':env_capa*nomEff,
                    }
        inputDict = {input[0]: solph.Flow(investment=solph.Investment(**investArgs))}
        if len(input)>1:
            # Two input HP, second input is for Q evaporator
            inputDict.update({input[1]:solph.Flow()})
        self.__geothermalheatpump = cp.CombinedTransformer(label='GWHP' + '__' + buildingLabel,
                                            inputs=inputDict,
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

    def getHP(self, type):
        if type == 'sh':
            return self.__geothermalheatpump
        else:
            print("Transformer label not identified...")
            return []

class Chiller(solph_network.Transformer):
    r"""
       Chiller is a tranformer with two input flows, W_elec and Q_heatin
       and one output flow Q_heatout
       The input relation constraint is defined in a new constraint block
       """
    def __init__(self, tSH, tGround, nomEff, epc, capacityMin, capacityMax, env_capa, base, inputBuses, outputBus, dispatchMode, *args, **kwargs):
        self.cop = solph_sequence(self._calculateCop(tSH,tGround))
        if dispatchMode:
            investArgs= {'ep_costs':epc*nomEff,
                        'minimum':capacityMin/nomEff,
                        'maximum':capacityMax/nomEff,
                        'env_per_capa':env_capa*nomEff,
                    }
        else:
            investArgs= {'ep_costs':epc*nomEff,
                        'minimum':capacityMin/nomEff,
                        'maximum':capacityMax/nomEff,
                        'nonconvex':True,
                        'offset':base,
                        'env_per_capa':env_capa*nomEff,
                    }
        inputDict = {i: solph.Flow(investment=solph.Investment(**investArgs)) for i in inputBuses if "gridBus" in i.label or "electricity" in i.label}
        inputDict.update({i: solph.Flow() for i in inputBuses if "gridBus" not in i.label and "electricity" not in i.label})
        outputDict = {outputBus: solph.Flow()}
        super().__init__(inputs=inputDict, outputs=outputDict, *args, **kwargs)

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

    def constraint_group(self):
        return ChillerBlock

class ChillerBlock(SimpleBlock):
    r"""Block for the linear relation of nodes
    """

    CONSTRAINT_GROUP = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def _create(self, group=None):
        """Creates the linear constraint
        """
        if group is None:
            return None

        m = self.parent_block()

        for n in group:
            n.inflowElec = [i for i in list(n.inputs) if "electricity" in i.label][0]
            n.inflowQcond = [i for i in list(n.inputs) if "electricity" not in i.label][0]
            n.outflow = list(n.outputs)[0]

        def _input_output_relation_rule(block):
            """Connection between input and outputs."""
            for t in m.TIMESTEPS:
                for g in group:
                    lhs = m.flow[g.inflowElec, g, t]
                    rhs = m.flow[g, g.outflow, t] / g.cop[t]
                    block.input_output_relation.add((g, t), (lhs == rhs))

        self.input_output_relation = Constraint(
            group, m.TIMESTEPS, noruleinit=True
        )
        self.input_output_relation_build = BuildAction(
            rule=_input_output_relation_rule
        )

        def _input_relation_rule(block):
            """Connection between inputs."""
            for t in m.TIMESTEPS:
                for g in group:
                    lhs = m.flow[g.inflowElec, g, t] * (g.cop[t] - 1)
                    rhs = m.flow[g.inflowQcond, g, t]
                    block.input_relation.add((g, t), (lhs == rhs))

        self.input_relation = Constraint(
            group, m.TIMESTEPS, noruleinit=True
        )
        self.input_relation_build = BuildAction(
            rule=_input_relation_rule
        )

class CHP:
    "Information about the model can be found in combined_pro.py CombinedCHP"
    def __init__(self, buildingLabel, input, outputEl, outputSH, outputDHW, efficiencyEl, efficiencySH, efficiencyDHW,
                 capacityMin, capacitySH, epc, base, varc1, varc2, env_flow1, env_flow2, env_capa, timesteps, dispatchMode):
        self._efficiencyEl = [efficiencyEl] * timesteps
        self._efficiencySH = [efficiencySH] * timesteps
        self._efficiencyDHW = [efficiencyDHW] * timesteps
        self.avgEff = efficiencySH
        if dispatchMode:
            investArgs = {'ep_costs': epc * self.avgEff,
                          'minimum': capacityMin / self.avgEff,
                          'maximum': capacitySH / self.avgEff,
                          'env_per_capa': env_capa * self.avgEff}
        else:
            investArgs={'ep_costs':epc*self.avgEff,
                        'minimum':capacityMin/self.avgEff,
                        'maximum':capacitySH/self.avgEff,
                        'nonconvex':True,
                        'offset':base,
                        'env_per_capa':env_capa*self.avgEff}
        self.__CHP = cp.CombinedCHP(
                        label='CHP'+'__'+buildingLabel,
                        inputs={
                            input: solph.Flow(
                                investment=solph.Investment(**investArgs),
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

    def getCHP(self, type):
        if type == 'sh':
            return self.__CHP
        else:
            print("Transformer label not identified...")
            return []

class GasBoiler(cp.CombinedTransformer):
    "Information about the model can be found in combined_pro.py CombinedTransformer"
    def __init__(self, buildingLabel, input, outputSH, outputDHW, efficiencySH, efficiencyDHW,
                 capacityMin, capacityMax, epc, base, varc, env_flow, env_capa, dispatchMode):
        self.__efficiency = efficiencySH
        if dispatchMode:
            investArgs= {'ep_costs':epc*efficiencySH,
                        'minimum':capacityMin/efficiencySH,
                        'maximum':capacityMax/efficiencySH,
                        'env_per_capa':env_capa*efficiencySH}
        else:
            investArgs= {'ep_costs':epc*efficiencySH,
                        'minimum':capacityMin/efficiencySH,
                        'maximum':capacityMax/efficiencySH,
                        'nonconvex':True,
                        'offset':base,
                        'env_per_capa':env_capa*efficiencySH}
        super(GasBoiler, self).__init__(
            label='GasBoiler'+'__'+buildingLabel,
            inputs={
                input: solph.Flow(
                    investment=solph.Investment(**investArgs),
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

class ElectricRod(cp.CombinedTransformer):
    def __init__(self, buildingLabel, input, outputSH, outputDHW, efficiency,
                 capacityMin, capacityMax, epc, base, varc, env_flow, env_capa, dispatchMode):

        self.__efficiency = efficiency
        if dispatchMode:
            investArgs = {'ep_costs': epc * efficiency,
                          'minimum': capacityMin / efficiency,
                          'maximum': capacityMax / efficiency,
                          'env_per_capa': env_capa * efficiency}
        else:
            investArgs={'ep_costs':epc*efficiency,
                        'minimum':capacityMin/efficiency,
                        'maximum':capacityMax/efficiency,
                        'nonconvex':True,
                        'offset':base,
                        'env_per_capa':env_capa*efficiency}
        super(ElectricRod, self).__init__(
            label='ElectricRod'+'__'+buildingLabel,
            inputs={
                input: solph.Flow(investment=solph.Investment(**investArgs) )
            },
            outputs={
                outputSH: solph.Flow(
                    variable_costs=varc,
                    env_per_flow=env_flow,
                ),
                outputDHW: solph.Flow(
                    variable_costs=varc,
                    env_per_flow=env_flow,
                ),
            },
            efficiencies={outputSH: efficiency,
                          outputDHW: efficiency}
                 )

class GeothermalHeatPumpLinearSingleUse:
    "Class implementing a linear model for geothermal heat pump for single use only (either DHW or SH but not both)"
    def __init__(self, buildingLabel, temperatureH, temperatureLow, input, outputH,
                 capacityMin, capacityMax, epc, base, varc, env_flow, env_capa, dispatchMode):
        self.__copH = self._calculateCop(temperatureH, temperatureLow)
        #self.avgCopSh = (sum(self.__copH)/len(self.__copH))
        #self.nominalEff = nomEff
        if dispatchMode:
            investArgs = {'ep_costs':epc,
                            'minimum':0,
                            'maximum':capacityMax,
                            'env_per_capa':env_capa}
        else:
            investArgs = {'ep_costs':epc,
                            'minimum':0,
                            'maximum':capacityMax,
                            'nonconvex':True,
                            'offset':base,
                            'env_per_capa':env_capa}
        self.__geothermalheatpump = solph.Transformer(label=f'GWHP{str(temperatureH)}' + '__' + buildingLabel,
                                            inputs={input: solph.Flow()},
                                            outputs={outputH: solph.Flow(
                                                          variable_costs=varc,
                                                          env_per_flow=env_flow,
                                                          investment=solph.Investment(**investArgs),
                                                      )
                                                  },
                                            conversion_factors={outputH: self.__copH})

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

    def getHP(self, type):
        if type == 'sh':
            return self.__geothermalheatpump
        else:
            print("Transformer label not identified...")
            return []