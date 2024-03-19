import pandas as _pd
import configparser as _cp


def parse_config(configFilePath: str):
    config = _cp.ConfigParser()
    config.read(configFilePath)
    configData = {}
    for section in config.sections():
        configData[section]=config.items(section)
    configData = {k.lower(): v for k, v in configData.items()}

    return configData


def write_prepared_data_and_sheets_to_excel(excel_file_path: str, excel_data: dict):
    # better to use pathlib paths.
    with _pd.ExcelWriter(excel_file_path, engine='xlwt') as writer:
        for sheet, data in excel_data.items():
            data.to_excel(writer, sheet_name=sheet, index=False)
        writer.save()
        writer.close()  # is this needed when using "with"?
