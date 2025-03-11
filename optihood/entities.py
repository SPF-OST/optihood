import enum as _enum


class NodeKeys(_enum.StrEnum):
    links = 'links'
    buses = "buses"
    grid_connection = "grid_connection"
    commodity_sources = "commodity_sources"
    solar = "solar"
    transformers = "transformers"
    demand = "demand"
    storages = "storages"
    stratified_storage = "stratified_storage"
    ice_storage = "ice_storage"
    profiles = "profiles"


class CsvInputFilePathsRelative(_enum.StrEnum):
    buses = "buses.csv"
    grid_connection = "grid_connection.csv"
    commodity_sources = "commodity_sources.csv"
    solar = "solar.csv"
    transformers = "transformers.csv"
    demand = "demand.csv"
    storages = "storages.csv"
    stratified_storage = "stratified_storage.csv"
    ice_storage = "ice_storage.csv"
    profiles = "profiles.csv"
    links = 'links.csv'


class BusesLabels(_enum.StrEnum):
    label = "label"
    building = "building"
    excess = "excess"
    excess_costs = "excess costs"
    active = "active"


class BusTypes(_enum.StrEnum):
    naturalGasBus = "naturalGasBus"
    gridBus = "gridBus"
    electricityBus = "electricityBus"
    electricityProdBus = "electricityProdBus"
    electricityInBus = "electricityInBus"
    shSourceBus = "shSourceBus"
    spaceHeatingBus = "spaceHeatingBus"
    shDemandBus = "shDemandBus"
    domesticHotWaterBus = "domesticHotWaterBus"
    dhwDemandBus = "dhwDemandBus"
    dhwStorageBus = "dhwStorageBus"
    solarConnectBus = "solarConnectBus"
    heatBus = "heatBus"
    heatDemandBus = "heatDemandBus"
    lowTSourceBus = "lowTSourceBus"
    lowTSinkBus = "lowTSinkBus"


class CommoditySourcesLabels(_enum.StrEnum):
    label = "label"
    building = "building"
    to = "to"
    variable_costs = "variable costs"
    CO2_impact = "CO2 impact"
    active = "active"


class CommoditySourceTypes(_enum.StrEnum):
    naturalGasResource = "naturalGasResource"
    electricityResource = "electricityResource"


class DemandLabels(_enum.StrEnum):
    label = "label"
    building = "building"
    active = "active"
    from_bus = "from"  # 'from' cannot be used as an attribute: 'from package import stuff'
    fixed = "fixed"
    nominal_value = "nominal value"
    building_model = "building model"


class DemandTypes(_enum.StrEnum):
    electricityDemand = "electricityDemand"
    spaceHeatingDemand = "spaceHeatingDemand"
    domesticHotWaterDemand = "domesticHotWaterDemand"


class GridConnectionLabels(_enum.StrEnum):
    label = "label"
    building = "building"
    from_bus = "from"
    to = "to"
    efficiency = "efficiency"


class GridConnectionTypes(_enum.StrEnum):
    gridElectricity = "gridElectricity"
    electricitySource = "electricitySource"
    producedElectricity = "producedElectricity"
    domesticHotWater = "domesticHotWater"
    shSource = "shSource"
    spaceHeating = "spaceHeating"


class LinksLabels(_enum.StrEnum):
    label = "label"
    active = "active"
    efficiency = "efficiency"
    invest_base = "invest_base"
    invest_cap = "invest_cap"
    investment = "investment"


class LinksTypes(_enum.StrEnum):
    electricityLink = "electricityLink"
    shLink = "shLink"
    dhwLink = "dhwLink"
    heatLink0= "heatLink0"
    heatLink2 = "heatLink2"
    lowTempHeatLink = "lowTempHeatLink"


class ProfileLabels(_enum.StrEnum):
    name = "name"
    path = "path"
    info = "INFO"


class ProfileTypes(_enum.StrEnum):
    demand = "demand_profiles"
    weather = "weather_data"


class SolarLabels(_enum.StrEnum):
    label = "label"
    building = "building"
    active = "active"
    from_bus = "from"
    to = "to"
    connect = "connect"
    electrical_consumption = "electrical_consumption"
    peripheral_losses = "peripheral_losses"
    latitude = "latitude"
    longitude = "longitude"
    tilt = "tilt"
    azimuth = "azimuth"
    efficiency = "efficiency"
    eta_0 = "eta_0"
    a_1 = "a_1"
    a_2 = "a_2"
    temp_collector_inlet = "temp_collector_inlet"
    delta_temp_n = "delta_temp_n"
    capacity_max = "capacity_max"
    capacity_min = "capacity_min"
    lifetime = "lifetime"
    maintenance = "maintenance"
    installation = "installation"
    planification = "planification"
    invest_base = "invest_base"
    invest_cap = "invest_cap"
    heat_impact = "heat_impact"
    elec_impact = "elec_impact"
    impact_cap = "impact_cap"
    roof_area = "roof_area"
    zenith_angle = "zenith_angle"


class SolarTypes(_enum.StrEnum):
    solarCollector = "solarCollector"
    pv = "pv"


class StorageLabels(_enum.StrEnum):
    label = "label"
    building = "building"
    active = "active"
    from_bus = "from"
    to = "to"
    efficiency_inflow = "efficiency inflow"
    efficiency_outflow = "efficiency outflow"
    initial_capacity = "initial capacity"
    capacity_min = "capacity min"
    capacity_max = "capacity max"
    capacity_loss = "capacity loss"
    lifetime = "lifetime"
    maintenance = "maintenance"
    installation = "installation"
    planification = "planification"
    invest_base = "invest_base"
    invest_cap = "invest_cap"
    heat_impact = "heat_impact"
    elec_impact = "elec_impact"
    impact_cap = "impact_cap"


class StorageTypes(_enum.StrEnum):
    electricalStorage = "electricalStorage"
    shStorage = "shStorage"
    dhwStorage = "dhwStorage"


class StratifiedStorageLabels(_enum.StrEnum):
    label = "label"
    diameter = "diameter"
    temp_h = "temp_h"
    temp_c = "temp_c"
    temp_env = "temp_env"
    inflow_conversion_factor = "inflow_conversion_factor"
    outflow_conversion_factor = "outflow_conversion_factor"
    s_iso = "s_iso"
    lamb_iso = "lamb_iso"
    alpha_inside = "alpha_inside"
    alpha_outside = "alpha_outside"


class StratifiedStorageTypes(_enum.StrEnum):
    dhwStorage = "dhwStorage"
    shStorage = "shStorage"


class IceStorageLabels(_enum.StrEnum):
    label = "label"
    intitial_temp = "intitial_temp"
    max_ice_fraction = "max_ice_fraction"
    rho_fluid = "rho_fluid"
    h_fluid = "h_fluid"
    cp_fluid = "cp_fluid"
    UA_tank = "UA_tank"
    inflow_conversion_factor = "inflow_conversion_factor"
    outflow_conversion_factor = "outflow_conversion_factor"

class IceStorageTypes(_enum.StrEnum):
    iceStorage = "iceStorage"

class TransformerLabels(_enum.StrEnum):
    label = "label"
    building = "building"
    active = "active"
    from_bus = "from"
    to = "to"
    efficiency = "efficiency"
    capacity_DHW = "capacity_DHW"
    capacity_SH = "capacity_SH"
    capacity_el = "capacity_el"
    capacity_min = "capacity_min"
    lifetime = "lifetime"
    maintenance = "maintenance"
    installation = "installation"
    planification = "planification"
    invest_base = "invest_base"
    invest_cap = "invest_cap"
    heat_impact = "heat_impact"
    elec_impact = "elec_impact"
    impact_cap = "impact_cap"


class TransformerTypes(_enum.StrEnum):
    CHP = "CHP"
    HP = "HP"
    GWHP = "GWHP"
    GasBoiler = "GasBoiler"
