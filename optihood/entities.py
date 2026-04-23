import enum as _enum


class StrEnumWithMethods(_enum.StrEnum):
    """Base class for string enums providing standard utility methods."""

    @classmethod
    def get_values(cls) -> list[str]:
        return [member.value for member in cls]


class CommonLabels(StrEnumWithMethods):
    label = "label"
    label_unique = "label_unique"
    from_bus = "from"
    from_unique = "from_unique"
    to = "to"
    to_unique = "to_unique"
    connect = "connect"
    connect_unique = "connect_unique"
    building = "building"


class NodeKeys(StrEnumWithMethods):
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


class NodeKeysOptional:
    # TODO: move other optional ones here and fix any arising issues.
    building_model_parameters = "building_model_parameters"


class CsvInputFilePathsRelative(StrEnumWithMethods):
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


class BusesLabels(StrEnumWithMethods):
    label = CommonLabels.label.value
    building = "building"
    excess = "excess"
    excess_costs = "excess costs"
    active = "active"


class BusTypes(StrEnumWithMethods):
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
    dhHeatInBus = "districtHeatInBus"
    dhHeatBus = "districtHeatBus"
    electricitySourceBusPVT = "elSource_pvt"


class CommoditySourcesLabels(StrEnumWithMethods):
    label = CommonLabels.label.value
    building = "building"
    to = CommonLabels.to.value
    variable_costs = "variable costs"
    CO2_impact = "CO2 impact"
    active = "active"


class CommoditySourceTypes(StrEnumWithMethods):
    naturalGasResource = "naturalGasResource"
    electricityResource = "electricityResource"


class DemandLabels(StrEnumWithMethods):
    label = CommonLabels.label.value
    building = "building"
    active = "active"
    from_bus = CommonLabels.from_bus.value
    fixed = "fixed"
    nominal_value = "nominal value"
    building_model = "building model"


class DemandTypes(StrEnumWithMethods):
    electricityDemand = "electricityDemand"
    spaceHeatingDemand = "spaceHeatingDemand"
    domesticHotWaterDemand = "domesticHotWaterDemand"


class GridConnectionLabels(StrEnumWithMethods):
    label = CommonLabels.label.value
    building = "building"
    from_bus = CommonLabels.from_bus.value
    to = CommonLabels.to.value
    efficiency = "efficiency"


class GridConnectionTypes(StrEnumWithMethods):
    gridElectricity = "gridElectricity"
    electricitySource = "electricitySource"
    producedElectricity = "producedElectricity"
    domesticHotWater = "domesticHotWater"
    shSource = "shSource"
    spaceHeating = "spaceHeating"


class LinksLabels(StrEnumWithMethods):
    label = CommonLabels.label.value
    active = "active"
    efficiency = "efficiency"
    invest_base = "invest_base"
    invest_cap = "invest_cap"
    investment = "investment"


class LinksTypes(StrEnumWithMethods):
    electricityLink = "electricityLink"
    shLink = "shLink"
    dhwLink = "dhwLink"
    heatLink0 = "heatLink0"
    heatLink2 = "heatLink2"
    lowTempHeatLink = "lowTempHeatLink"
    dhLink = "dhLink"


class ProfileLabels(StrEnumWithMethods):
    name = "name"
    path = "path"
    info = "INFO"


class MandatoryProfileTypes(StrEnumWithMethods):
    demand = "demand_profiles"  # mandatory
    # TODO: make demand profiles consistent throughout the code  # pylint: disable=fixme
    demandProfiles = 'demandProfiles'  # because both implementations exist atm
    weather = "weather_data"  # mandatory
    # TODO: add missing profile types  # pylint: disable=fixme


class NonMandatoryProfileTypes(StrEnumWithMethods):
    internal_gains = "internal_gains"
    building_model_params = "building_model_params"
    fixed_sources = "fixed_source_profiles"
    electricity_impact = 'electricity_impact'
    electricity_cost = 'electricity_cost'


class SolarLabels(StrEnumWithMethods):
    label = CommonLabels.label.value
    building = "building"
    active = "active"
    from_bus = CommonLabels.from_bus.value
    to = CommonLabels.to.value
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


class SolarTypes(StrEnumWithMethods):
    solarCollector = "solarCollector"
    pv = "pv"
    pvt = "pvt"


class StorageLabels(StrEnumWithMethods):
    # --- Mandatory Labels ---
    label = CommonLabels.label.value
    building = "building"
    active = "active"
    from_bus = CommonLabels.from_bus.value
    to = CommonLabels.to.value
    efficiency_inflow = "efficiency inflow"
    efficiency_outflow = "efficiency outflow"
    initial_capacity = "initial capacity"
    initial_temp = "initial_temp"
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

    # --- Optional Labels ---
    min_storage_level = "min_storage_level"
    max_storage_level = "max_storage_level"

    @classmethod
    def get_mandatory_labels(cls) -> list['StorageLabels']:
        """Returns only the mandatory labels"""
        return [cls.label, cls.building, cls.active, cls.from_bus, cls.to, cls.efficiency_inflow,
                cls.efficiency_outflow, cls.initial_capacity, cls.initial_temp,
                cls.capacity_min, cls.capacity_max, cls.capacity_loss, cls.lifetime, cls.maintenance,
                cls.installation, cls.planification, cls.invest_base, cls.invest_cap,
                cls.heat_impact, cls.elec_impact, cls.impact_cap,]

    @classmethod
    def get_optional_labels(cls) -> list['StorageLabels']:
        """Returns only the optional labels"""
        return [
            cls.min_storage_level, cls.max_storage_level
        ]


class StorageTypes(StrEnumWithMethods):
    electricalStorage = "electricalStorage"
    shStorage = "shStorage"
    dhwStorage = "dhwStorage"
    pitStorage = "pitStorage"
    tankGenericStorage = "tankGenericStorage"
    pitGenericStorage = "pitGenericStorage"
    boreholeGenericStorage = "boreholeGenericStorage"
    aquifierGenericStorage = "aquifierGenericStorage"
    thermalStorage = "thermalStorage"
    coolingBufferStorage = "coolingBufferStorage"


class StratifiedStorageLabels(StrEnumWithMethods):
    label = CommonLabels.label.value
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


class StratifiedStorageTypes(StrEnumWithMethods):
    dhwStorage = "dhwStorage"
    shStorage = "shStorage"


class IceStorageLabels(StrEnumWithMethods):
    label = CommonLabels.label.value
    max_ice_fraction = "max_ice_fraction"
    rho_fluid = "rho_fluid"
    h_fluid = "h_fluid"
    cp_fluid = "cp_fluid"
    UA_tank = "UA_tank"
    inflow_conversion_factor = "inflow_conversion_factor"
    outflow_conversion_factor = "outflow_conversion_factor"


class IceStorageTypes(StrEnumWithMethods):
    iceStorage = "iceStorage"


class TransformerLabels(StrEnumWithMethods):
    label = CommonLabels.label.value
    building = "building"
    active = "active"
    from_bus = CommonLabels.from_bus.value
    to = CommonLabels.to.value
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


class HeatPumpCoefficientLabels(StrEnumWithMethods):
    coef_W = "coef_W"
    coef_Q = "coef_Q"


class TransformerTypes(StrEnumWithMethods):
    # TODO: currently the investment object is applied to the input flow for all transformer types
    # If this changes, we need to split this class into
    # (1) transformers with investment on inflow (this class would then be used while converting input capacities to output capacities)
    # (2) transformers with investment on outflow
    CHP = "CHP"
    HP = "HP"
    GWHP = "GWHP"
    GasBoiler = "GasBoiler"
    BiomassBoiler = "BiomassBoiler"
    OilBoiler = "OilBoiler"
    ElectricRod = "ElectricRod"
    Chiller = "Chiller"


class BuildingModelParameters(StrEnumWithMethods):
    building_unique = "building_unique"
    Building_Number = "Building Number"
    Circuit = "Circuit"
    gAreaWindows = "gAreaWindows"
    rDistribution = "rDistribution"
    cDistribution = "cDistribution"
    rIndoor = "rIndoor"
    cIndoor = "cIndoor"
    rWall = "rWall"
    cWall = "cWall"
    qDistributionMin = "qDistributionMin"
    qDistributionMax = "qDistributionMax"
    tIndoorMin = "tIndoorMin"
    tIndoorMax = "tIndoorMax"
    tIndoorInit = "tIndoorInit"
    tDistributionInit = "tDistributionInit"
    tWallInit = "tWallInit"
    tIndoorDay = "tIndoorDay"
    tIndoorNight = "tIndoorNight"


class TransformerOperationalArgs(StrEnumWithMethods):
    """
      Operational parameters for oemof.solph Flow and NonConvex objects,
      which the users can pass
    """
    # --- Flow Args ---
    MIN_FLOW = 'min_flow'
    MAX_FLOW = 'max_flow'

    # --- NonConvex Args ---
    MINIMUM_UPTIME = 'minimum_uptime'
    MINIMUM_DOWNTIME = 'minimum_downtime'
    INITIAL_STATUS = 'initial_status'
    STARTUP_COSTS = 'startup_costs'
    SHUTDOWN_COSTS = 'shutdown_costs'

    @classmethod
    def get_flow_args(cls) -> list['TransformerOperationalArgs']:
        """Returns only the parameters for the Flow object"""
        return [cls.MIN_FLOW, cls.MAX_FLOW]

    @classmethod
    def get_nonconvex_args(cls) -> list['TransformerOperationalArgs']:
        """Returns only the parameters for the NonConvex object"""
        return [
            cls.MINIMUM_UPTIME, cls.MINIMUM_DOWNTIME,
            cls.INITIAL_STATUS, cls.STARTUP_COSTS, cls.SHUTDOWN_COSTS
        ]

    @classmethod
    def get_int_keys(cls) -> list['TransformerOperationalArgs']:
        """Returns the specific parameters that must be cast to integers."""
        return [cls.MINIMUM_UPTIME, cls.MINIMUM_DOWNTIME, cls.INITIAL_STATUS]