from __future__ import (
    unicode_literals,
    absolute_import,
    print_function,
    division,
    )

import os
import subprocess
import sys
import aaf2
import json
from pprint import pprint

def serialize_auid(auid, name=None):
    if name:
        return "{} {}".format(str(auid), name)

    return str(auid)

def serialize_value(typedef, value, type_definitions):

    assert isinstance(typedef, aaf2.types.TypeDef)
    type_definitions[typedef.auid] = typedef

    type_name = typedef.type_name
    pretty_type_name = serialize_auid(typedef.auid,  type_name)
    if type_name in ('aafInt8', 'aafUInt16', 'aafInt32', 'aafUInt32', 'aafString', 'Boolean'):
        return [pretty_type_name, value]

    elif type_name in ('Rational', "AUID", ):
        return [pretty_type_name, str(value)]

    elif type_name in ('AvidBagOfBits',
                       'AvidString4',
                       'AudioSuitePIChunkData',
                       'AvidBounds',
                       'AvidColor',
                       'AvidCrop',
                       'AvidScale',
                       'AvidPosition',
                       'AvidSpillSupress',
                       'AvidGlobalKeyFrame'):
        hex_value = ""
        for v in value:
            hex_value += "%x" % v

        return [pretty_type_name, hex_value]

    elif type_name in ('AvidWideString32', ):

        hex_value = ""
        for v in value:
            hex_value += "%02x" % v

        return [pretty_type_name, hex_value]

    elif type_name in ('AudioSuitePIChunkArray', 'EqualizationBandArray') :
        values = []
        for v in value:
            values.append(serialize_value(typedef.element_typedef ,v, type_definitions))

        return [pretty_type_name, values]

    elif type_name in ('AudioSuitePlugInChunk', 'EqualizationBand'):
        values = []
        for key, member_typedef in zip(typedef.member_names, typedef.member_types):
            values.append(serialize_value(member_typedef, value[key], type_definitions))

        return [pretty_type_name, values]

    print(typedef)
    print(type_name)
    print(value)
    assert False

def extract_operation(op_group):
    op_def = op_group.operation

    parameter_definitions = {}
    type_definitions = {}
    data_definitions = {}

    operation_group_name = None

    # for key in op_group.keys():
    #     if key not in ( 'Parameters', 'InputSegments', 'Operation', 'Length', 'DataDefinition', 'ComponentAttributeList', 'OpGroupMotionCtlOffsetMapAdjust'):
    #         print("??", key)
    #         op_group.dump()
    #         assert False
    #         pass

    d = {}
    for p in op_def.properties():
        # print(p.name, p.value)

        if p.name == 'ParametersDefined':
            params = []
            for param_def in p.value:
                param_id = param_def.auid
                parameter_definitions[param_id] =  param_def
                params.append(serialize_auid(param_id, param_def.name))

            d[p.name] = params

        elif p.name in ("DataDefinition",):
            d[p.name] = str(p.value.name)
        elif p.name in ('Identification',):
            d[p.name] = str(p.value)
        else:
            d[p.name] = p.value

    # op_group.dump()

    operation_group_name = d['Name']
    operation_def = d


    d = {}
    for t in op_group['ComponentAttributeList']:
        type_name = t.value_typedef.type_name
        type_definitions[t.value_typedef.auid] = t.value_typedef
        d[t.name] = serialize_value(t.value_typedef, t.value, type_definitions)

    component_attrs = d

    parameters = []
    for p in op_group["Parameters"]:
        param_def = p.parameterdef
        parameter_definitions[param_def.auid] = param_def
        pretty_param_name = serialize_auid(param_def.auid, param_def.name)

        value = [pretty_param_name]
        if isinstance(p, aaf2.misc.VaryingValue):
            typedef = p.typedef
            type_name = typedef.type_name
            type_definitions[typedef.auid] = typedef

            pretty_type_name = serialize_auid(typedef.auid,  type_name)
            value.append("VaryingValue")
            value.append(pretty_type_name)

            value.append(p.interpolation.name)
            varying_values = []

            for point in p.pointlist:
                sample_time = point['Time'].value

                # wow this is annoying
                indirect_typedef = point['Value'].typedef.decode_typedef(point['Value'].data)
                type_definitions[indirect_typedef.auid] = indirect_typedef
                sample_value = serialize_value(indirect_typedef, point['Value'].value, type_definitions)

                d = {'Time': str(sample_time), 'Value' : sample_value}
                if 'ControlPointPointProperties' in point:
                    for point_prop in point['ControlPointPointProperties']:
                        type_definitions[indirect_typedef.auid] = point_prop.typedef.auid
                        d[p.name] = serialize_value(point_prop.typedef, point_prop.value, type_definitions)

                varying_values.append(d)

            value.append(varying_values)
            assert p.interpolation.name in ('LinearInterp', 'ConstantInterp', 'AvidCubicInterpolator', 'AvidBezierInterpolator')

        elif isinstance(p, aaf2.misc.ConstantValue):
            value.append("ConstantValue")
            value.extend(serialize_value(p.typedef, p.value, type_definitions))

        else:
            assert False

        parameters.append(value)

    parameters_defs = {}
    for key, p in parameter_definitions.items():
        type_definitions[p.typedef.auid] = p.typedef
        value = [serialize_auid(p.typedef.auid,  p.typedef.type_name),  p.name, p.description]
        parameters_defs[str(key)] = value


    types = {}

    for key, typedef in type_definitions.items():
        if isinstance(typedef, aaf2.types.TypeDefInt):
            if 'ints' not in types:
                types['ints'] = {}

            types['ints'][typedef.type_name] = (str(key), typedef.size, typedef.signed)

        elif isinstance(typedef, aaf2.types.TypeDefString):
            if 'strings' not in types:
                types['strings'] = {}

            types['strings'][typedef.type_name] = (str(key), serialize_auid(typedef.element_typedef.auid, typedef.element_typedef.type_name))

        elif isinstance(typedef, aaf2.types.TypeDefVarArray):
            if 'var_arrays' not in types:
                types['var_arrays'] = {}

            types['var_arrays'][typedef.type_name] = (str(key), serialize_auid(typedef.element_typedef.auid, typedef.element_typedef.type_name))

        elif isinstance(typedef, aaf2.types.TypeDefFixedArray):
            if 'fixed_arrays' not in types:
                types['fixed_arrays'] = {}

            types['fixed_arrays'][typedef.type_name] = (str(key), serialize_auid(typedef.element_typedef.auid, typedef.element_typedef.type_name), typedef.size)

        elif isinstance(typedef, aaf2.types.TypeDefRecord):
            if 'records' not in types:
                types['records'] = {}

            members = []
            for name, member_typedef in zip(typedef.member_names, typedef.member_types):
                members.append( (name, serialize_auid(member_typedef.auid, member_typedef.type_name)) )

            types['records'][typedef.type_name] = (str(key), members)

        elif isinstance(typedef, aaf2.types.TypeDefEnum):
            if 'enums' not in types:
                types['enums'] = {}

            types['enums'][typedef.type_name] = (str(key), serialize_auid(typedef.element_typedef.auid, typedef.element_typedef.type_name), typedef.elements)

        else:
            print(typedef)
            assert False

    result = {}
    result['TypeDefinitions'] = types
    result['ParameterDefinitions'] = parameters_defs
    result['OperationDefinition'] = operation_def
    result['ComponentAttributeList'] = component_attrs
    result['Parameters'] = parameters

    return operation_group_name, result

def iter_operation_group_components(segment):
    if isinstance(segment, aaf2.components.OperationGroup):
        yield segment
        for c in segment.segments:
            for comp in iter_operation_group_components(c):
                yield comp

    elif isinstance(segment, aaf2.components.Sequence):
        for c in segment.components:
            for comp in iter_operation_group_components(c):
                yield comp

    elif isinstance(segment, aaf2.components.NestedScope):
        for slot in segment.slots:
            for comp in iter_operation_group_components(slot):
                yield comp


def find_operation_groups(f):
    operations = []
    operation_name = None
    for mob in f.content.compositionmobs():
        operation_name = mob.name.split(".Exported")[0]
        for slot in mob.slots:
            for operation_group in iter_operation_group_components(slot.segment):
                operations.append(operation_group)

    return operation_name, operations

def extract_operation_group(f, json_file):
    operation_mob_name, operations = find_operation_groups(f)
    extracted_operations = {}
    for op in operations:
        # print(" ", op.operation.name)
        operation_name, data = extract_operation(op)
        extracted_operations[operation_name] = data

    data = {'name': operation_mob_name, 'operations': extracted_operations}
    # pprint(data)
    with open(json_file, 'w') as outfile:
        json.dump(data, outfile, indent=4)


if __name__ == "__main__":

    dir_path = sys.argv[1]
    assert os.path.isdir(dir_path)

    for root, dirs, files in os.walk(dir_path, topdown=False):
        for filename in files:
            name, ext = os.path.splitext(filename)
            aaf_file = os.path.join(root, filename)
            json_file = os.path.join(root, name + ".json")

            if ext.lower() in ('.aaf',) and name[0] != '.':
                print(aaf_file)
                with aaf2.open(aaf_file) as f:
                    extract_operation_group(f, json_file)

                # print("")
