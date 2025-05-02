import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from dhnx.optimization.precalc_hydraulic import v_max_bisection, calc_mass_flow, calc_power, v_max_secant


class DistrictHeatingPipeHydraulics:
    def __init__(self, pipe_data_file, maximum_pressure_drop):
        self.pipe_df = pd.read_csv(pipe_data_file)
        self.maximum_pressure_drop = maximum_pressure_drop  # in Pa/m
        self.v_max_calc_methods = {"bisection":v_max_bisection,
                                   "secant":v_max_secant}

    def calculate_max_velocity(self, method="bisection"):
        v_max_function = self.v_max_calc_methods.get(method, None)
        if v_max_function:
            # Calculation of maximum fluid velocity in m/s based on max pressure drop
            self.pipe_df['v_max [m/s]'] = self.pipe_df.apply(lambda row: v_max_function(
                d_i=row['Inner diameter [m]'],
                T_average=row['Temperature [Celsius]'],
                k=row['Roughness [mm]'],
                p_max=self.maximum_pressure_drop), axis=1)
        else:
            raise ValueError("v_max_calc_method must be one of bisection, secant")

    def calculate_mass_flow(self):
        # Calculation of mass flow rate in kg/s
        self.pipe_df['Mass flow [kg/s]'] = self.pipe_df.apply(lambda row: calc_mass_flow(
            v=row['v_max [m/s]'], di=row['Inner diameter [m]'],
            T_av=row['Temperature [Celsius]']), axis=1)

    def calculate_max_power(self):
        # Calculation of maximum Power, includes conversion factor 0.001 for returning value in kW
        self.pipe_df['P_max [kW]'] = self.pipe_df.apply(lambda row: 0.001 * calc_power(
            T_vl=row['T_flow [Celsius]'],
            T_rl=row['T_return [Celsius]'],
            mf=row['Mass flow [kg/s]']), axis=1)

    def linear_approximation(self):
        # linear approximation for costs and thermal losses
        self.constants_costs = np.polyfit(self.pipe_df['P_max [kW]'], self.pipe_df['Cost [CHF/m]'], 1)
        self.constants_loss = np.polyfit(self.pipe_df['P_max [kW]'], self.pipe_df['Loss [kW/m]'], 1)

    def calculate_optihood_params(self,pipe_label, v_max_calc_method="bisection"):
        self.calculate_max_velocity(method=v_max_calc_method)
        self.calculate_mass_flow()
        self.calculate_max_power()
        self.linear_approximation()
        self.df_pipes = pd.DataFrame(
            {
                "label": pipe_label,
                "active": 1,
                "nonconvex": 1,
                "l_factor_cap": self.constants_loss[0],
                "l_factor_fix": self.constants_loss[1],
                "capacity_max": self.pipe_df['P_max [kW]'].max(),
                "capacity_min": self.pipe_df['P_max [kW]'].min(),
                "invest_cap": self.constants_costs[0],
                "invest_base": self.constants_costs[1],
            }, index=[0],
        )

    def plot_linear_approximation(self, type):
        x_min = self.pipe_df['P_max [kW]'].min()
        x_max = self.pipe_df['P_max [kW]'].max()
        if type == "cost":
            y_min = self.constants_costs[0] * x_min + self.constants_costs[1]
            y_max = self.constants_costs[0] * x_max + self.constants_costs[1]
            df_col = 'Cost [CHF/m]'
            y_text = 250
        elif type == "thermal loss":
            y_min = self.constants_loss[0] * x_min + self.constants_loss[1]
            y_max = self.constants_loss[0] * x_max + self.constants_loss[1]
            df_col = 'Loss [kW/m]'
            y_text = 0.010
        else:
            raise Warning("Undefined linear approximation type. Choose either 'cost' or 'loss'")

        fig, ax = plt.subplots()
        x = self.pipe_df['P_max [kW]']
        y = self.pipe_df[df_col]
        ax.plot(x, y, lw=0, marker="o")
        ax.plot(
            [x_min, x_max], [y_min, y_max],
            ls=":", color='r', marker="x"
        )
        ax.set_xlabel("Transport capacity [kW]")
        ax.set_ylabel(df_col)
        plt.text(2000, y_text, f"Linear {type} approximation \n"
                            "of district heating pipelines \n"
                            "based on maximum pressure drop \n"
                            f"of {self.maximum_pressure_drop} Pa/m")
        plt.ylim(0, None)
        plt.grid(ls=":")
        plt.show()
