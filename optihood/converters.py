import oemof.solph as solph
import numpy as np
import pandas as pd
import pvlib
import optihood.combined_prod as cp
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
        # Coefficient representing the area used by one unit of capacity of a solar collector
        coeff = -np.sin((zenith_angle+collector_tilt)*np.pi/180)*np.cos(collector_azimuth*np.pi/180)/np.sin(zenith_angle*np.pi/180)
        return coeff

class PVT(solph.Transformer):
    def __init__(self, label, buildingLabel, inputs, outputs, connectors, electrical_consumption, peripheral_losses, latitude,
                 longitude,
                 collector_tilt, roof_area, zenith_angle, collector_azimuth, eta_0, a_1, a_2, temp_collector_inlet,temp_amb,
                 delta_temp_n, irradiance_global,
                 irradiance_diffuse, capacityMin, capacityMax, epc, base, env_capa, env_flow, varc, dispatchMode,
                 pv_efficiency=0.15, taualpha=0.85):

        pvdata = self.computePvSolarPosition(irradiance_diffuse, irradiance_global, latitude, longitude, collector_azimuth,
                                           collector_tilt, temp_amb)
        pv_electricity = np.minimum(self.pvtElPrecalc(temp_amb, temp_collector_inlet, pvdata['pv_ira'] / 1000, delta_temp_n[1]), capacityMax + base)
        pvtCollectorData_sh = self.pvtThPrecalc(latitude, longitude, collector_tilt, collector_azimuth, eta_0, a_1, a_2,
                                                temp_collector_inlet, delta_temp_n[0],
                                       irradiance_global, irradiance_diffuse, temp_amb,  pv_efficiency, taualpha)
        pvtCollectorData_dhw = self.pvtThPrecalc(latitude, longitude, collector_tilt, collector_azimuth, eta_0, a_1, a_2,
                                             temp_collector_inlet, delta_temp_n[1],
                                             irradiance_global, irradiance_diffuse, temp_amb, pv_efficiency, taualpha)
        self.taualpha = taualpha

        self.collectors_heat_sh = pvtCollectorData_sh['collectors_heat']/1000
        self.collectors_heat_dhw = pvtCollectorData_dhw['collectors_heat'] / 1000
        self.collectors_eta_c_sh = pvtCollectorData_sh['eta_c']
        self.collectors_eta_c_dhw = pvtCollectorData_dhw['eta_c']
        self.surface_used = self.calculateArea(zenith_angle, collector_tilt, collector_azimuth)
        surface_used_el = self.calculateArea(zenith_angle, collector_tilt, collector_azimuth, pv_efficiency)
        if dispatchMode:
            investArgsEl = {'ep_costs':0,
                         'minimum':capacityMin,
                         'maximum':capacityMax,
                         'space':self.surface_used,
                         'space_el': surface_used_el,
                         'roof_area':roof_area,
                         'env_per_capa':env_capa}
            investArgsSH = {'ep_costs': 0,
                          'minimum': capacityMin,
                          'maximum': capacityMax,
                          'space': self.surface_used,
                          'space_el': surface_used_el,
                          'roof_area': roof_area,
                          'env_per_capa': env_capa}
            investArgsDHW = {'ep_costs': epc,
                          'minimum': capacityMin,
                          'maximum': capacityMax,
                          'space': self.surface_used,
                          'space_el': surface_used_el,
                          'roof_area': roof_area,
                          'env_per_capa': env_capa}
        else:
            investArgsEl = {'ep_costs': 0,
                            'minimum': capacityMin,
                            'maximum': capacityMax,
                            'nonconvex': True,
                            'space': self.surface_used,
                            'roof_area': roof_area,
                            'offset': 0.000001,
                            'env_per_capa': 0}
            investArgsSH = {'ep_costs': 0,
                            'minimum': capacityMin,
                            'maximum': capacityMax,
                            'nonconvex': True,
                            'space': self.surface_used,
                            'roof_area': roof_area,
                            'offset': 0.000001,
                            'env_per_capa': 0}
            investArgsDHW = {'ep_costs': epc,
                             'minimum': capacityMin,
                             'maximum': capacityMax,
                             'nonconvex': True,
                             'space': self.surface_used,
                             'roof_area': roof_area,
                             'offset': base,
                             'env_per_capa': env_capa}

        self.__PVTel_source = solph.Source(label='elSource_' + label + '__' + buildingLabel,
                                 outputs={outputs[2]: solph.Flow(
                                     investment=solph.Investment(**investArgsEl),
                                     variable_costs=varc,
                                     env_per_flow=env_flow,
                                     max=pv_electricity
                                 )}
                                 )
        self.__PVTheat_source_sh = solph.Source(
            label='heatSource_SH' + label + "__" + buildingLabel,
            outputs={
                connectors[0]: solph.Flow(
                    fix=self.collectors_heat_sh,
                    investment=solph.Investment(**investArgsSH),
                    variable_costs=varc,
                    env_per_flow=env_flow,
                )
            },
        )
        self.__PVT_excessheat_sh = solph.Sink(
            label='excessheat_SH' + label + "__" + buildingLabel, inputs={connectors[0]: solph.Flow()}
        )
        self.__PVTheat_transformer_sh = solph.Transformer(
            label=label + 'SH__' + buildingLabel,
            inputs={connectors[0]: solph.Flow(), inputs: solph.Flow()},
            outputs={outputs[0]: solph.Flow()},
            conversion_factors={
                connectors[0]: 1,
                inputs: electrical_consumption * (1 - peripheral_losses),
                outputs[0]: 1 - peripheral_losses
            },
        )

        self.__PVTheat_source_dhw = solph.Source(
            label='heatSource_DHW' + label + "__" + buildingLabel,
            outputs={
                connectors[1]: solph.Flow(
                    fix=self.collectors_heat_dhw,
                    investment=solph.Investment(**investArgsDHW),
                    variable_costs=varc,
                    env_per_flow=env_flow,
                )
            },
        )
        self.__PVT_excessheat_dhw = solph.Sink(
            label='excessheat_DHW' + label + "__" + buildingLabel, inputs={connectors[1]: solph.Flow()}
        )
        self.__PVTheat_transformer_dhw = solph.Transformer(
            label=label + 'DHW__' + buildingLabel,
            inputs={connectors[1]: solph.Flow(), inputs: solph.Flow()},
            outputs={outputs[1]: solph.Flow()},
            conversion_factors={
                connectors[1]: 1,
                inputs: electrical_consumption * (1 - peripheral_losses),
                outputs[1]: 1 - peripheral_losses
            },
        )

    def pvtThPrecalc(self, latitude, longitude, collector_tilt, collector_azimuth, eta_0, a_1, a_2, temp_collector_inlet, delta_temp_n,
            irradiance_global, irradiance_diffuse, temp_amb,  pv_efficiency, taualpha):
        # function inspired from oemof thermal solar_thermal_collector
        # The calculation of eta_c is overriden
        data = pd.DataFrame(
            {
                'ghi': irradiance_global,
                'dhi': irradiance_diffuse,
                'temp_amb': temp_amb
            }
        )
        solposition = pvlib.solarposition.get_solarposition(
            time=data.index, latitude=latitude, longitude=longitude
        )
        dni = pvlib.irradiance.dni(
            ghi=data['ghi'], dhi=data['dhi'], zenith=solposition['apparent_zenith']
        )
        total_irradiation = pvlib.irradiance.get_total_irradiance(
            surface_tilt=collector_tilt,
            surface_azimuth=collector_azimuth,
            solar_zenith=solposition['apparent_zenith'],
            solar_azimuth=solposition['azimuth'],
            dni=dni.fillna(0),  # fill NaN values with '0'
            ghi=data['ghi'],
            dhi=data['dhi'],
        )
        data['col_ira'] = total_irradiation['poa_global']
        data["eta_c"] = self.calcEtaC(eta_0, a_1, a_2, temp_collector_inlet, delta_temp_n, data['temp_amb'], total_irradiation['poa_global'], pv_efficiency, taualpha)
        collectors_heat = data["eta_c"] * total_irradiation['poa_global']
        data["collectors_heat"] = collectors_heat
        return data

    def calcEtaC(self, eta_0, a_1, a_2, temp_collector_inlet, delta_temp_n, temp_amb, irradiation, pv_efficiency, taualpha):
        delta_t = temp_collector_inlet + delta_temp_n - temp_amb
        eta_c = pd.Series()
        for index, value in irradiation.items():
            if value > 0:
                eta = (eta_0*(1-pv_efficiency/(taualpha))
                        - a_1 * delta_t[index] / value
                        - a_2 * delta_t[index] ** 2 / value)
                eta_c[index] = eta*(eta > 0) + 0
            else:
                eta_c[index] = 0
        return eta_c

    def computePvSolarPosition(self, irradiance_diffuse, irradiance_global, latitude, longitude, pv_azimuth, pv_tilt,
                               temp_amb_pv):
        data = pd.DataFrame(
            {
                'ghi': irradiance_global,
                'dhi': irradiance_diffuse,
                'temp_amb': temp_amb_pv
            }
        )
        solposition = pvlib.solarposition.get_solarposition(
            time=data.index, latitude=latitude, longitude=longitude
        )
        dni = pvlib.irradiance.dni(
            ghi=data['ghi'], dhi=data['dhi'], zenith=solposition['apparent_zenith']
        )
        total_irradiation = pvlib.irradiance.get_total_irradiance(
            surface_tilt=pv_tilt,
            surface_azimuth=pv_azimuth,
            solar_zenith=solposition['apparent_zenith'],
            solar_azimuth=solposition['azimuth'],
            dni=dni.fillna(0),  # fill NaN values with '0'
            ghi=data['ghi'],
            dhi=data['dhi'],
        )
        data['pv_ira'] = total_irradiation['poa_global']
        return data

    # model according to TriHP Energy management algorithms description. D6.2 v1.0
    # nominal power is 1 KW due to the normed optimizer
    def pvtElPrecalc(self, temp_amb, temp_collector_inlet, i_H_t,delta_temp_n, a4=-0.062059,
                   a5=0.04277774, a6=9.692792, a7=-1.885868, a8=6.6):
        temp_cell = temp_collector_inlet + delta_temp_n - temp_amb
        pvPower = np.maximum(0, (a4*i_H_t + a5)*temp_cell + a6*i_H_t + a7) / a8
        return pvPower


    def calculateArea(self, zenith_angle, pv_tilt, pv_azimuth, pv_efficiency=0.0):
        # Coefficient representing the area used by one unit of capacity (kW thermal) of a PVT panel
        coeff = -np.sin((zenith_angle+pv_tilt)*np.pi/180)*np.cos(pv_azimuth*np.pi/180)/np.sin(zenith_angle*np.pi/180)
        if pv_efficiency:
            coeff /= pv_efficiency
        return coeff

    def getPVT(self, type):
        if type == 'heat_source':
            return self.__PVTheat_source_sh, self.__PVTheat_source_dhw
        elif type == 'heat_transformer':
            return self.__PVTheat_transformer_sh, self.__PVTheat_transformer_dhw
        elif type == 'el_source':
            return self.__PVTel_source
        elif type == 'excess_heat_sink':
            return self.__PVT_excessheat_sh, self.__PVT_excessheat_dhw
        else:
            print("Label not identified...")
            return []

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
        inputDict = {input[0]: solph.Flow(investment=solph.Investment(**investArgs))}
        if len(input) > 1:
            # Two input HP, second input is for Q evaporator
            inputDict.update({input[1]: solph.Flow()})
        self.__heatpump = cp.CombinedTransformer(label='HP' + '__' + buildingLabel,
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