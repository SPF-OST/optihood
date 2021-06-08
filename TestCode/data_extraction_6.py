from __future__ import print_function
import pandas as pd


def extraction(file_path, result_path):
    """Read Excel input file and prepare a .dat file with every parameter and set defined as expected for the model
    """

    data = open(result_path, 'w')

    print("##", file=data)
    print("## Model hours, technologies, timesteps", file=data)
    print("##", file=data)

    ## Definition of global parameters
    global1 = pd.read_excel(file_path, sheet_name="Global", index_col=0, header=None, engine='openpyxl')
    hours = global1.loc["Time range"]
    buildings = global1.loc["Buildings"]
    uconv = global1.loc["Uconverters"]
    conv = global1.loc["Converters"]
    ustor = global1.loc["Ustorage"]
    stor = global1.loc["Storage"]
    techs = global1.loc["Converters"] + global1.loc["Storage"] + 1
    inp = global1.loc["Inputs"]
    demand = global1.loc["Demand"]

    print("param hours :=", *hours, ";", file=data)
    print("param buildings :=", *buildings, ";", file=data)
    print("param unique_conv :=", *uconv, ";", file=data)
    print("param conv :=", *conv, ";", file=data)
    print("param unique_stor :=", *ustor, ";", file=data)
    print("param stor :=", *stor, ";", file=data)
    print("param techs :=", *techs, ";", file=data)
    print("param inputs :=", *inp, ";", file=data)
    print("param demand :=", *demand, ";\n", file=data)

    print("##", file=data)
    print("## Coupling matrix : In: 1:Grid / 2:CHP1 / 3:CHP2 / 4:CHP3 / 5:HP1 / 6:HP2 / 7:HP3", file=data)  # a choisir
    print("## Out: 1:Elec / 2:SpaceHeat / 3:DHW ", file=data)  # a choisir
    print("##\n", file=data)

    ## Definition of the set of demands
    # Demand = pd.read_excel(file_path, sheet_name="Demand", index_col=0, engine='openpyxl')
    #
    # print("set Out :=", end=' ', file=data)
    # for i in Demand.columns:
    #     print(i, end=' ', file=data)
    # print(";\n", file=data)

    ## Definition of the set of inputs and data recovery
    Inputs = pd.read_excel(file_path, sheet_name="Inputs", index_col=0, engine='openpyxl', usecols="B:AA")

    print("set In :=", end=' ', file=data)
    for i in Inputs.columns:
        print(i, end=' ', file=data)
    print(";\n", file=data)

    print("set InCategory :=", end=' ', file=data)
    for i in list(set(Inputs.loc["ICategory"])):
        print(i, end=' ', file=data)
    print(";\n", file=data)

    for a in Inputs.index:
        print("param", a, ":=", file=data)
        for i in Inputs.columns:
            print(i, Inputs.loc[a][i], file=data)
        print(";\n", file=data)

    ## Definition of the converters set and data recovery
    Technologies = pd.read_excel(file_path, sheet_name="Converters", index_col=0, engine='openpyxl', usecols="B:AA")

    print("set UConv :=", end=' ', file=data)
    for i in Technologies.columns:
        print(i, end=' ', file=data)
    print(";\n", file=data)

    print("set Conv :=", end=' ', file=data)
    for i in Technologies.columns:
        for j in range(Technologies.loc["CNumber_max_per_building"][i]):
            print(i, j + 1, sep='', end=' ', file=data)
    print(";\n", file=data)

    for a in Technologies.index:
        print("param", a, ":=", file=data)
        for i in Technologies.columns:
            for j in range(Technologies.loc["CNumber_max_per_building"][i]):
                print(i, j + 1, sep='', end=' ', file=data)
                print(Technologies.loc[a][i], file=data)
        print(";\n", file=data)

    ## Definition of the storage set and data recovery
    Storage = pd.read_excel(file_path, sheet_name="Storage", index_col=0, engine='openpyxl', usecols="B:AA")

    print("set UStor :=", end=' ', file=data)
    for i in Storage.columns:
        print(i, end=' ', file=data)
    print(";\n", file=data)

    print("set Stor :=", end=' ', file=data)
    for i in Storage.columns:
        for j in range(round(Storage.loc["SNumber_max_per_building"][i])):
            print(i, j + 1, sep='', end=' ', file=data)
    print(";\n", file=data)

    for a in Storage.index:
        print("param", a, ":=", file=data)
        for i in Storage.columns:
            for j in range(round(Storage.loc["SNumber_max_per_building"][i])):
                print(i, j + 1, sep='', end=' ', file=data)
                print(Storage.loc[a][i], file=data)
        print(";\n", file=data)

    ## Definition of the set of every technologies involved
    print("set Techs :=", end=' ', file=data)
    for i in Technologies.columns:
        for j in range(Technologies.loc["CNumber_max_per_building"][i]):
            print(i, j + 1, sep='', end=' ', file=data)
    for i in Storage.columns:
        for j in range(round(Storage.loc["SNumber_max_per_building"][i])):
            print(i, j + 1, sep='', end=' ', file=data)
    print(";\n", file=data)

    ## Definition of the set of technologies that receive electricity, heat and fuel, and those who produce electricity and heat.
    print("set ElecIn :=", end=' ', file=data)
    for i in Technologies.columns:
        if Technologies.loc["CInput"][i] == "elec":
            for j in range(Technologies.loc["CNumber_max_per_building"][i]):
                print(i, j + 1, sep='', end=' ', file=data)
    for i in Storage.columns:
        if Storage.loc["SInput"][i] == "elec":
            for j in range(round(Storage.loc["SNumber_max_per_building"][i])):
                print(i, j + 1, sep='', end=' ', file=data)
    print(";\n", file=data)

    print("set ElecOut :=", end=' ', file=data)
    for i in Technologies.columns:
        if Technologies.loc["COutput"][i] == "elec":
            for j in range(Technologies.loc["CNumber_max_per_building"][i]):
                print(i, j + 1, sep='', end=' ', file=data)
    for i in Storage.columns:
        if Storage.loc["SOutput"][i] == "elec":
            for j in range(round(Storage.loc["SNumber_max_per_building"][i])):
                print(i, j + 1, sep='', end=' ', file=data)
    print(";\n", file=data)

    print("set FuelIn :=", end=' ', file=data)
    for i in Technologies.columns:
        if Technologies.loc["CInput"][i] == "fuel":
            for j in range(Technologies.loc["CNumber_max_per_building"][i]):
                print(i, j + 1, sep='', end=' ', file=data)
    for i in Storage.columns:
        if Storage.loc["SInput"][i] == "fuel":
            for j in range(round(Storage.loc["SNumber_max_per_building"][i])):
                print(i, j + 1, sep='', end=' ', file=data)
    print(";\n", file=data)

    print("set HeatIn :=", end=' ', file=data)
    for i in Technologies.columns:
        if Technologies.loc["CInput"][i] == "heat":
            for j in range(Technologies.loc["CNumber_max_per_building"][i]):
                print(i, j + 1, sep='', end=' ', file=data)
    for i in Storage.columns:
        if Storage.loc["SInput"][i] == "heat":
            for j in range(round(Storage.loc["SNumber_max_per_building"][i])):
                print(i, j + 1, sep='', end=' ', file=data)
    print(";\n", file=data)

    print("set HeatOut :=", end=' ', file=data)
    for i in Technologies.columns:
        if Technologies.loc["COutput"][i] == "heat":
            for j in range(Technologies.loc["CNumber_max_per_building"][i]):
                print(i, j + 1, sep='', end=' ', file=data)
    for i in Storage.columns:
        if Storage.loc["SOutput"][i] == "heat":
            for j in range(round(Storage.loc["SNumber_max_per_building"][i])):
                print(i, j + 1, sep='', end=' ', file=data)
    print(";\n", file=data)

    print("set Fuels :=", end=' ', file=data)
    for i in Inputs.columns:
        if Inputs.loc["ICategory"][i] == "fuel":
            print(i, sep='', end=' ', file=data)
    print(";\n", file=data)

    print("set Elec :=", end=' ', file=data)
    for i in Inputs.columns:
        if Inputs.loc["ICategory"][i] == "elec":
            print(i, sep='', end=' ', file=data)
    print(";\n", file=data)

    data.close()
