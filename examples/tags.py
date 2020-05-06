from pycomm3 import LogixDriver


def find_attributes():
    with LogixDriver('10.61.50.4/10') as plc:
        ...  # do nothing, we're just letting the plc initialize the tag list

    for typ in plc.data_types:
        print(f'{typ} attributes: ', plc.data_types[typ]['attributes'])
