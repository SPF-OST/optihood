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
