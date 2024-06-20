from optihood._helpers import *
import oemof.solph as solph
import numpy as np
import pandas as pd
import pvlib


class PV(solph.components.Source):
    def __init__(self, label, buildingLabel, outputs, peripheral_losses, latitude, longitude,
                 pv_tilt, pv_efficiency, roof_area, zenith_angle, pv_azimuth, irradiance_global, irradiance_diffuse, temp_amb_pv, capacityMin,
                 capacityMax, epc, base, env_capa, env_flow, varc, dispatchMode):
        # Creation of a df with 3 columns
        data = self.computePvSolarPosition(irradiance_diffuse, irradiance_global, latitude, longitude, pv_azimuth,
                                           pv_tilt, temp_amb_pv)

        self.pv_electricity = np.minimum(self.pv_precalc(temp_amb_pv, data['pv_ira']/1000), capacityMax)

        if not (np.isnan(roof_area) or np.isnan(zenith_angle) or np.isnan(pv_efficiency)):
            self.surface_used = self._calculateArea(zenith_angle, pv_tilt, pv_azimuth, pv_efficiency)
        else:
            self.surface_used = np.nan
        if dispatchMode:
            investArgs = {'ep_costs':epc,
                         'minimum':capacityMin,
                         'maximum':capacityMax,
                         'custom_attributes': {'env_per_capa': env_capa, 'space': self.surface_used,
                                              'roof_area': roof_area}}
        else:
            investArgs={'ep_costs':epc,
                         'minimum':capacityMin,
                         'maximum':capacityMax,
                         'nonconvex':True,
                         'offset':base,
                         'custom_attributes': {'env_per_capa': env_capa, 'space': self.surface_used,
                                              'roof_area': roof_area}}
        super(PV, self).__init__(label=label + '__' + buildingLabel,
                                 outputs={outputs: solph.Flow(
                                     investment=solph.Investment(**investArgs),
                                     variable_costs=varc,
                                     custom_attributes={'env_per_flow':env_flow},
                                     max=self.pv_electricity
                                 )}
                                 )

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
    def pv_precalc(self, temp_amb, i_H_t, a1=17.23292, a2=0.451708, a3=22.706, a4=-0.062059,
                   a5=0.04277774, a6=9.692792, a7=-1.885868, a8=6.6):

        temp_cell = a1 + a2 * temp_amb + a3 * i_H_t
        pvPower = np.maximum(0, (a4*i_H_t + a5)*temp_cell + a6*i_H_t + a7) / a8
        return pvPower

    def getPV(self):
        return self.__pv

    def _calculateArea(self, zenith_angle, pv_tilt, pv_azimuth, pv_efficiency):
        # Coefficient representing the area used by one unit of capacity of a solar panel
        coeff = -np.sin((zenith_angle+pv_tilt)*np.pi/180)*np.cos(pv_azimuth*np.pi/180)/np.sin(zenith_angle*np.pi/180)/pv_efficiency
        return coeff
