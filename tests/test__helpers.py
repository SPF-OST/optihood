import pytest as _pt

import optihood._helpers as hlpr


@_pt.mark.parametrize("component_label, building_info, expected_full_name, expected_building, expected_component_name",
                      [
                          ("Chiller1", "Building1", "Chiller1__Building1", "Building1", "Chiller"),
                          ("HeatPump2", "Building3", "HeatPump2__Building3", "Building3", "HeatPump"),
                      ])
def test_create_label_string(component_label, building_info, expected_full_name, expected_building,
                             expected_component_name
                             ):
    label = hlpr.create_label_string(component_label, building_info)

    errors = []
    try:
        assert label.full_name == expected_full_name
    except AssertionError as e:
        errors.append(e)

    try:
        assert label.component_name == expected_component_name
    except AssertionError as e:
        errors.append(e)

    try:
        assert label.building == expected_building
    except AssertionError as e:
        errors.append(e)

    try:
        assert label.prefix == component_label
    except AssertionError as e:
        errors.append(e)

    if errors:
        raise ExceptionGroup(f"Found {len(errors)} issues: ", errors)


@_pt.mark.parametrize("component_label, building_info", [
    ("Chiller", "stuff"),
    ("Chiller", 1.3),
    ("Chiller", 2),
])
def test_create_label_string_raises(component_label, building_info):
    with _pt.raises(ValueError):
        hlpr.create_label_string(component_label, building_info)


@_pt.mark.parametrize("building_info, expected_label", [
    (1, "Building1"),
    ("2", "Building2"),
    ("02", "Building2"),
])
def test_create_building_label(building_info, expected_label):
    label = hlpr.create_building_label(building_info)
    assert label == expected_label


@_pt.mark.parametrize("building_info", [
    1.3,
    "1.3",
    "Building2",
])
def test_create_building_label_raises(building_info):
    with _pt.raises(ValueError):
        hlpr.create_building_label(building_info)


@_pt.mark.parametrize("label, expected", [
    ("gasBoiler_B1", 1),
    ("exEl_B2", 2),
    ("Q_el_B003", 3),
    ("solarCollectorSH__Building1", 1),
])
def test_int_at_end_of_string(label, expected):
    assert hlpr.int_at_end_of_string(label) == expected
