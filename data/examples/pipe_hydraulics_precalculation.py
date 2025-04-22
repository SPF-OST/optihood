import os
import pandas as pd
from optihood.pipe_hydraulics import DistrictHeatingPipeHydraulics


# Set the display option globally
pd.set_option('display.max_columns', None)
pd.set_option('display.width', 1000)

if __name__=="__main__":
    pipe_data_file_path = os.path.join(os.path.dirname(__file__),"..", "CSVs", "pipe_hydraulics_precalculation", 'pipe_data.csv')
    pipe_data = DistrictHeatingPipeHydraulics(pipe_data_file_path, 150)
    pipe_data.calculate_optihood_params(pipe_label="default", v_max_calc_method="bisection")  # alternative method is "secant"
    print("==========================================================================================================================")
    print("DH Pipe parameters for optimization runs with optihood")
    print("==========================================================================================================================")
    print(pipe_data.df_pipes)
    print("==========================================================================================================================")
    pipe_data.df_pipes.to_csv("optihood_pipe_params.csv", index=False)
    pipe_data.plot_linear_approximation(type="cost")
    pipe_data.plot_linear_approximation(type="thermal loss")