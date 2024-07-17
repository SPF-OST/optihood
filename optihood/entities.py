import enum as _enum


class NodeKeys(_enum.StrEnum):
    buses = "buses"
    grid_connection = "grid_connection"
    commodity_sources = "commodity_sources"
    solar = "solar"
    transformers = "transformers"
    demand = "demand"
    storages = "storages"
    stratified_storage = "stratified_storage"
    profiles = "profiles"


sheet_names = [e.value for e in NodeKeys]


class CsvInputFilePathsRelative(_enum.StrEnum):
    buses = "buses.csv"
    grid_connection = "grid_connection.csv"
    commodity_sources = "commodity_sources.csv"
    solar = "solar.csv"
    transformers = "transformers.csv"
    demand = "demand.csv"
    storages = "storages.csv"
    stratified_storage = "stratified_storage.csv"
    profiles = "profiles.csv"


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
