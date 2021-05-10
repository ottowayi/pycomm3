from pycomm3 import LogixDriver


def find_attributes():
    with LogixDriver('10.61.50.4/10') as plc:
        ...  # do nothing, we're just letting the plc initialize the tag list

    for typ in plc.data_types:
        print(f'{typ} attributes: ', plc.data_types[typ]['attributes'])


def tag_list_equal():
    with LogixDriver('10.61.50.4/10') as plc:
        tag_list = plc.get_tag_list()
        if {tag['tag_name']: tag for tag in tag_list} == plc.tags:
            print('They are the same!')

    with LogixDriver('10.61.50.4/10', init_tags=False) as plc2:
        plc2.get_tag_list()

    if plc.tags == plc2.tags:
        print('Calling get_tag_list() does the same thing.')
    else:
        print('Calling get_tag_list() does NOT do the same.')


def find_pids():
    with LogixDriver('10.61.50.4/10') as plc:

        # PIDs are structures, the data_type attribute will be a dict with data type definition.
        # For tag types of 'atomic' the data type will a string, we need to skip those first.
        # Then we can just look for tags whose data type name matches 'PID'
        pid_tags = [
            tag
            for tag, _def in plc.tags.items()
            if _def['data_type_name'] == 'PID'
        ]

        print(pid_tags)
