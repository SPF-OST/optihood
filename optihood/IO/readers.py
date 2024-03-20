import configparser as _cp


# Making this a class method would allow us to proved the parser.

def parse_config(configFilePath: str):
    config = _cp.ConfigParser()
    config.read(configFilePath)
    configData = {}
    for section in config.sections():
        configData[section] = config.items(section)
    configData = {k.lower(): v for k, v in configData.items()}

    return configData
