import oemof.solph as solph
import numpy as np
import optihood.combined_prod as cp
from oemof.thermal.solar_thermal_collector import flat_plate_precalc

class SolarCollector(solph.components.Transformer):
    def __init__(self, label, buildingLabel, inputs, outputs, connector, electrical_consumption, peripheral_losses, latitude,
                 longitude,
                 collector_tilt, roof_area, zenith_angle, collector_azimuth, eta_0, a_1, a_2, temp_collector_inlet,
                 delta_temp_n, irradiance_global,
                 irradiance_diffuse, temp_amb_col, capacityMin, capacityMax, epc, base, env_capa, env_flow, varc, dispatchMode):

        if isinstance(delta_temp_n, float):
            flatPlateCollectorData = flat_plate_precalc(
                latitude, longitude, collector_tilt, collector_azimuth, eta_0, a_1, a_2, temp_collector_inlet, delta_temp_n,
                irradiance_global, irradiance_diffuse, temp_amb_col)
            self.collectors_eta_c = flatPlateCollectorData['eta_c']
            self.collectors_heat = flatPlateCollectorData['collectors_heat'] / 1000  # flow in kWh per m² of solar thermal panel
        else:
            flatPlateCollectorData = []
            self.collectors_heat = {}
            for i in range(len(delta_temp_n)):
                flatPlateCollectorData[i] = flat_plate_precalc(
                    latitude, longitude, collector_tilt, collector_azimuth, eta_0, a_1, a_2, temp_collector_inlet[i],
                    delta_temp_n[i],irradiance_global, irradiance_diffuse, temp_amb_col)
                self.collectors_eta_c[i] = flatPlateCollectorData[i]['eta_c']
                self.collectors_heat[connector[i]] = flatPlateCollectorData[i]['collectors_heat'] / 1000  # flow in kWh per m² of solar thermal panel

        if not (np.isnan(roof_area) or np.isnan(zenith_angle)):
            self.surface_used = self._calculateArea(zenith_angle, collector_tilt, collector_azimuth)
        else:
            self.surface_used = np.nan

        if dispatchMode:
            investArgs = {'ep_costs':epc,
                        'minimum':capacityMin,
                        'maximum':capacityMax,
                        'space':self.surface_used,
                        'roof_area':roof_area,
                        'custom_attributes': {'env_per_capa': env_capa}}
        else:
            investArgs = {'ep_costs':epc,
                        'minimum':capacityMin,
                        'maximum':capacityMax,
                        'nonconvex':True,
                        'space':self.surface_used,
                        'roof_area':roof_area,
                        'offset':base,
                        'custom_attributes': {'env_per_capa': env_capa}}
        if isinstance(delta_temp_n, float):
            connectorOutputDict = {connector: solph.Flow(
                fix=self.collectors_heat,
                investment=solph.Investment(**investArgs),
                variable_costs=varc,
                custom_attributes={'env_per_flow':env_flow},
            )}
            connectorInputDict  = {connector: solph.Flow()}
            TransformerInputDict = {connector: solph.Flow(), inputs: solph.Flow()}
            TransformerOutputDict = {outputs[0]: solph.Flow()}
            convFactors = {connector: 1,
                inputs: electrical_consumption * (1 - peripheral_losses),
                outputs[0]: 1 - peripheral_losses}
        else:
            connectorOutputDict = {c: solph.Flow(
                fix=self.collectors_heat[c],
                investment=solph.Investment(**investArgs),
                variable_costs=varc,
                custom_attributes={'env_per_flow':env_flow},
            ) for c in connector}
            connectorInputDict = {c: solph.Flow() for c in connector}
            TransformerInputDict = connectorInputDict.copy()
            TransformerInputDict.update({inputs: solph.Flow()})
            TransformerOutputDict = {o: solph.Flow() for o in outputs}
            factor = {'connector':1, 'inputs': electrical_consumption * (1 - peripheral_losses), 'outputs':1 - peripheral_losses}
            convFactors = {c: factor['connector'] for c in connector}
            convFactors.update({inputs: factor['inputs']})
            convFactors.update({o: factor['outputs'] for o in outputs})
        self.__collector_source = solph.components.Source(
            label='heat_'+label + "__" + buildingLabel,
            outputs=connectorOutputDict,
        )

        self.__collector_excess_heat = solph.components.Sink(
            label='excess_solarheat' + "__" + buildingLabel, inputs=connectorInputDict
        )

        self.__collector_transformer = solph.components.Transformer(
            label=label + '__' + buildingLabel,
            inputs=TransformerInputDict,
            outputs=TransformerOutputDict,
            conversion_factors=convFactors,
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
    def __init__(self, buildingLabel, operationTempertures, temperatureLow, input, output,
                 capacityMin, capacityMax, nomEff,
                 epc, base, varc, env_flow, env_capa, dispatchMode):
        outputTempertures = {}
        for i in range(len(output)):
            outputTempertures[output[i]] = operationTempertures[i]
        self.__cop = {o:self._calculateCop(t, temperatureLow) for o,t in outputTempertures.items()}
        self.avgCopSh = (sum(self.__cop[output[0]])/len(self.__cop[output[0]])) # cop at lowest temperature, i.e. temperature of space heating
        self.nominalEff = nomEff
        if dispatchMode:
            investArgs = {'ep_costs' : epc * nomEff,
            'minimum' : capacityMin / nomEff,
            'maximum' : capacityMax / nomEff,
            'custom_attributes': {'env_per_capa': env_capa * nomEff}}
        else:
            investArgs = {'ep_costs' : epc * nomEff,
            'minimum' : capacityMin / nomEff,
            'maximum' : capacityMax / nomEff,
            'nonconvex' : True,
            'offset' : base,
            'custom_attributes' : {'env_per_capa': env_capa * nomEff}}
        outputDict = {k:solph.Flow(variable_costs=varc, nominal_value=capacityMax,  min=0, max=1, nonconvex=solph.NonConvex(),
                                   custom_attributes={'env_per_flow': env_flow}, ) for k in output}
        self.__heatpump = cp.CombinedTransformer(label='HP' + '__' + buildingLabel,
                                            inputs={input: solph.Flow(
                                                investment=solph.Investment(**investArgs),
                                            )},
                                            outputs=outputDict,
                                            efficiencies=self.__cop)

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
    def __init__(self, buildingLabel, operationTempertures, temperatureLow, input, output,
                 capacityMin, capacityMax, nomEff,
                 epc, base, varc, env_flow, env_capa, dispatchMode):
        outputTempertures = {}
        for i in range(len(output)):
            outputTempertures[output[i]] = operationTempertures[i]
        self.__cop = {o: self._calculateCop(t, temperatureLow) for o, t in outputTempertures.items()}
        self.avgCopSh = (sum(self.__cop[output[0]]) / len(self.__cop[output[0]]))  # cop at lowest temperature, i.e. temperature of space heating
        self.nominalEff = nomEff
        if dispatchMode:
            investArgs= {'ep_costs':epc*nomEff,
                        'minimum':capacityMin/nomEff,
                        'maximum':capacityMax/nomEff,
                        'custom_attributes': {'env_per_capa': env_capa * nomEff}
                    }
        else:
            investArgs= {'ep_costs':epc*nomEff,
                        'minimum':capacityMin/nomEff,
                        'maximum':capacityMax/nomEff,
                        'nonconvex':True,
                        'offset':base,
                        'custom_attributes': {'env_per_capa': env_capa * nomEff}
                    }
        outputDict = {k: solph.Flow(variable_costs=varc, nominal_value=capacityMax,  min=0, max=1, nonconvex=solph.NonConvex(),
                                   custom_attributes={'env_per_flow': env_flow}, ) for k in output}
        self.__geothermalheatpump = cp.CombinedTransformer(label='GWHP' + '__' + buildingLabel,
                                            inputs={input: solph.Flow(
                                                investment=solph.Investment(**investArgs),
                                            )},
                                            outputs=outputDict,
                                            efficiencies=self.__cop)

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


class CHP:
    "Information about the model can be found in combined_pro.py CombinedCHP"
    def __init__(self, buildingLabel, input, output, efficiency,
                 capacityMin, capacitySH, epc, base, varc1, varc2, env_flow1, env_flow2, env_capa, timesteps, dispatchMode):
        outputEff = {}
        for i in range(len(output)):
            outputEff[output[i]] = [efficiency[i]]*timesteps
        self.avgEff = efficiency[1]
        if dispatchMode:
            investArgs = {'ep_costs': epc * self.avgEff,
                          'minimum': capacityMin / self.avgEff,
                          'maximum': capacitySH / self.avgEff,
                          'custom_attributes': {'env_per_capa': env_capa * self.avgEff}}
        else:
            investArgs={'ep_costs':epc*self.avgEff,
                        'minimum':capacityMin/self.avgEff,
                        'maximum':capacitySH/self.avgEff,
                        'nonconvex':True,
                        'offset':base,
                        'custom_attributes': {'env_per_capa': env_capa * self.avgEff}}
        outputDict = {k: solph.Flow(variable_costs=varc2, env_per_flow=env_flow2) for k in output if k!=output[0]}
        outputDict[output[0]] = solph.Flow(variable_costs=varc1, env_per_flow=env_flow1)
        self.__CHP = cp.CombinedCHP(
                        label='CHP'+'__'+buildingLabel,
                        inputs={
                            input: solph.Flow(
                                investment=solph.Investment(**investArgs),
                            )
                        },
                        outputs=outputDict,
                        efficiencies=outputEff
                    )

    def getCHP(self, type):
        if type == 'sh':
            return self.__CHP
        else:
            print("Transformer label not identified...")
            return []

class GasBoiler(cp.CombinedTransformer):
    "Information about the model can be found in combined_pro.py CombinedTransformer"
    def __init__(self, buildingLabel, input, output, efficiency,
                 capacityMin, capacityMax, epc, base, varc, env_flow, env_capa, dispatchMode):
        self.__efficiency = efficiency[0]
        outputEff = {}
        for i in range(len(output)):
            outputEff[output[i]] = efficiency[i]
        if dispatchMode:
            investArgs= {'ep_costs':epc*efficiency[0],
                        'minimum':capacityMin/efficiency[0],
                        'maximum':capacityMax/efficiency[0],
                        'custom_attributes': {'env_per_capa': env_capa * efficiency[0]}}
        else:
            investArgs= {'ep_costs':epc*efficiency[0],
                        'minimum':capacityMin/efficiency[0],
                        'maximum':capacityMax/efficiency[0],
                        'nonconvex':True,
                        'offset':base,
                        'custom_attributes': {'env_per_capa': env_capa * efficiency[0]}}
        outputDict = {k: solph.Flow(variable_costs=varc, env_per_flow=env_flow) for k in output}
        super(GasBoiler, self).__init__(
            label='GasBoiler'+'__'+buildingLabel,
            inputs={
                input: solph.Flow(
                    investment=solph.Investment(**investArgs),
                )
            },
            outputs=outputDict,
            efficiencies=outputEff
                 )

class ElectricRod(cp.CombinedTransformer):
    def __init__(self, buildingLabel, input, output, efficiency,
                 capacityMin, capacityMax, epc, base, varc, env_flow, env_capa, dispatchMode):
        self.__efficiency = efficiency
        outputEff = {}
        for i in range(len(output)):
            outputEff[output[i]] = efficiency
        if dispatchMode:
            investArgs = {'ep_costs': epc * efficiency,
                          'minimum': capacityMin / efficiency,
                          'maximum': capacityMax / efficiency,
                          'custom_attributes': {'env_per_capa': env_capa * efficiency}}
        else:
            investArgs={'ep_costs':epc*efficiency,
                        'minimum':capacityMin/efficiency,
                        'maximum':capacityMax/efficiency,
                        'nonconvex':True,
                        'offset':base,
                        'custom_attributes': {'env_per_capa': env_capa * efficiency}}
        outputDict = {k: solph.Flow(variable_costs=varc, env_per_flow=env_flow) for k in output}
        super(ElectricRod, self).__init__(
            label='ElectricRod'+'__'+buildingLabel,
            inputs={
                input: solph.Flow(investment=solph.Investment(**investArgs) )
            },
            outputs=outputDict,
            efficiencies=outputEff
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
                            'custom_attributes': {'env_per_capa': env_capa}}
        else:
            investArgs = {'ep_costs':epc,
                            'minimum':0,
                            'maximum':capacityMax,
                            'nonconvex':True,
                            'offset':base,
                             'custom_attributes': {'env_per_capa': env_capa}}
        self.__geothermalheatpump = solph.components.Transformer(label=f'GWHP{str(temperatureH)}' + '__' + buildingLabel,
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