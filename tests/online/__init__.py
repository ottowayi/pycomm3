from tests import REAL

BASE_ATOMIC_TESTS = [

    ('_sint1', 'SINT', 0),
    ('_sint2', 'SINT', 100),
    ('_sint_max', 'SINT', 127),
    ('_sint_min', 'SINT', -128),

    ('_int1', 'INT', 0),
    ('_int2', 'INT', 100),
    ('_int_max', 'INT', 32_767),
    ('_int_min', 'INT', -32_768),

    ('_dint1', 'DINT', 0),
    ('_dint2', 'DINT', 100),
    ('_dint_max', 'DINT', 2_147_483_647),
    ('_dint_min', 'DINT', -2_147_483_648),

    ('_lint1', 'LINT', 0),
    ('_lint2', 'LINT', 100),
    ('_lint_max', 'LINT', 9_223_372_036_854_775_807),
    ('_lint_min', 'LINT', -9_223_372_036_854_775_808),

    ('_real1', 'REAL', 0.0),
    ('_real2', 'REAL', 100.0),
    ('_real_max1', 'REAL', REAL(3.40282306e38)),
    ('_real_min1', 'REAL', REAL(-3.40282306e38)),
    ('_real_max2', 'REAL', REAL(1.17549435e-38)),
    ('_real_min2', 'REAL', REAL(-1.17549435e-38)),

    ('_bool1', 'BOOL', False),
    ('_bool2', 'BOOL', True),

    # include bits of integers as well
    ('_dint_max.31', 'BOOL', False),
    ('_dint_min.31', 'BOOL', True),
    ('_dint_max.0', 'BOOL', True),
    ('_dint_min.0', 'BOOL', False),
    ('_dint_max.1', 'BOOL', True),
    ('_dint_min.1', 'BOOL', False),
]

_sint_array = [x for x in range(20)]
_int_array = [x * 10 for x in range(25)]
_dint_array = [x * 100 for x in range(30)]
_lint_array = [0, 100, 9_223_372_036_854_775_807, -9_223_372_036_854_775_808, 0, 0, 0, 0, 0, 0]
_real_array = [REAL(x * 100.1234) for x in range(20)]
_bool_array = [
    True, False, False, False, False, False, True, False, False, False,
    False, True, False, False, False, False, False, True, False, False,
    False, False, True, False, False, True, False, False, False, False,
    False, True
] + [False for _ in range(32)] + [True for _ in range(32)]

BASE_ATOMIC_ARRAY_TESTS = [
    # make sure both with [0] and without work
    ('_sint_ary1[0]{20}', 'SINT[20]', _sint_array),
    ('_int_ary1[0]{25}', 'INT[25]', _int_array),
    ('_dint_ary1[0]{30}', 'DINT[30]', _dint_array),
    ('_lint_ary1[0]{10}', 'LINT[10]', _lint_array),
    ('_real_ary1[0]{20}', 'REAL[20]', _real_array),
    ('_bool_ary1[0]{3}', 'BOOL[96]', _bool_array),  # bool-arrays element count is DWORDs (1 element = 32 bools)

    ('_dint_2d_ary1[0,0]{25}', 'DINT[25]', _dint_array[:25]),
    ('_dint_3d_ary1[0,0,0]{27}', 'DINT[27]', _dint_array[:27]),

    ('_sint_ary1{20}', 'SINT[20]', _sint_array),
    ('_int_ary1{25}', 'INT[25]', _int_array),
    ('_dint_ary1{30}', 'DINT[30]', _dint_array),
    ('_lint_ary1{10}', 'LINT[10]', _lint_array),
    ('_real_ary1{20}', 'REAL[20]', _real_array),
    ('_bool_ary1{3}', 'BOOL[96]', _bool_array),

    # TODO: add these to tests for 'bad' tags
    # ('_dint_2d_ary1[0]{25}', 'DINT25]', _dint_array[:25]),
    # ('_dint_2d_ary1{25}', 'DINT[25]', _dint_array[:25]),
    # ('_dint_3d_ary1[0,0]{27}', 'DINT[27]', _dint_array[:27]),
    # ('_dint_3d_ary1[0]{27}', 'DINT[27]', _dint_array[:27]),
    # ('_dint_3d_ary1{27}', 'DINT[27]', _dint_array[:27]),

    # also test slicing arrays
    ('_sint_ary1[5]{10}', 'SINT[10]', _sint_array[5:15]),
    ('_int_ary1[1]{3}', 'INT[3]', _int_array[1:4]),
    ('_dint_ary1[6]{20}', 'DINT[20]', _dint_array[6:26]),
    ('_lint_ary1[3]{5}', 'LINT[5]', _lint_array[3:8]),
    ('_real_ary1[18]{2}', 'REAL[2]', _real_array[18:20]),
    ('_bool_ary1[1]{2}', 'BOOL[64]', _bool_array[32:]),
    ('_dint_2d_ary1[2,3]{10}', 'DINT[10]', _dint_array[13:23]),
    ('_dint_3d_ary1[1,2,1]{5}', 'DINT[5]', _dint_array[16:21]),

    # and single elements
    ('_sint_ary1[5]', 'SINT', _sint_array[5]),
    ('_int_ary1[0]', 'INT', _int_array[0]),
    ('_dint_ary1[6]', 'DINT', _dint_array[6]),
    ('_lint_ary1[3]', 'LINT', _lint_array[3]),
    ('_real_ary1[19]', 'REAL', _real_array[19]),
    ('_bool_ary1[0]', 'BOOL', _bool_array[0]),
    ('_bool_ary1[12]', 'BOOL', _bool_array[12]),
    ('_bool_ary1[29]', 'BOOL', _bool_array[29]),
]

_udt1_values = {'bool': True, 'sint': -1, 'int': 1, 'dint': 10, 'lint': 100, 'real': REAL(1000.009)}
_udt1_values_empty = {'bool': False, 'sint': 0, 'int': 0, 'dint': 0, 'lint': 0, 'real': REAL(0)}

_udt2_bool_array = [False for _ in range(64)]
_udt2_bool_array[5] = True

_udt2_sint_array = [0, 0, -2, 0, 0, 0, 0, 0]
_udt2_int_array = [0, 0, 0, 2]
_udt2_dint_array = [0, 0, 0, 0, 0, 0, 0, 0, 4, 0]
_udt2_lint_array = [0, 0, 100, 0]

_udt2_real_array = [REAL(0) for _ in range(10)]
_udt2_real_array[1] = REAL(88.8888)

_udt2_values = {
     'bools': _udt2_bool_array,
     'sints': _udt2_sint_array,
     'ints': _udt2_int_array,
     'dints': _udt2_dint_array,
     'lints': _udt2_lint_array,
     'reals': _udt2_real_array,
}

_udt2_values_empty = {
    'bools': [False for _ in range(64)],
    'sints': [0 for _ in range(8)],
    'ints': [0, 0, 0, 0],
    'dints': [0 for _ in range(10)],
    'lints': [0, 0, 0, 0],
    'reals': [REAL(0) for _ in range(10)],
}


_str82_part = 'A normal built-in string type'
_str82_full = 'Lorem ipsum dolor sit amet, consectetur adipiscing elit. Pellentesque sodales vel.'
_str20_part = 'A shorter string'
_str20_full = 'Lorem ipsum vivamus.'
_str480_part = 'A longer string with up to 480 characters.'
_str480_full = ('Lorem ipsum dolor sit amet, consectetur adipiscing elit. Mauris rhoncus elit nec mauris convallis '
'convallis. Nunc tristique volutpat dapibus. Suspendisse potenti. Quisque eget augue vitae ante congue malesuada. '
'Cras sed aliquam est. Integer sagittis, mauris id bibendum ornare, metus lectus accumsan ex, non egestas sem tortor at '
'nibh. Vestibulum consectetur ex tellus. Pellentesque nisl quam, bibendum nec lectus at, tempus varius purus. '
'Donec tristique, ipsum a ornare eleifend.')
_str_symbols = '¡¢£¤¥¦¨§©ª«¬­®¯¯±²³´µ¶·¸¹º»¼½¾¿'

_str_ary1_values = ['', _str82_full, '', '', _str82_part, '', 'A', 'B', 'C', '123']
_str480_ary1_values = ['', _str480_full, '', _str20_full]

_nested_udt1_values = {
    'udt1': _udt1_values,
    'udt_ary1': [_udt1_values_empty, _udt1_values_empty, _udt1_values, _udt1_values_empty, _udt1_values_empty],
    'udt2': _udt2_values,
    'udt_ary2': [_udt2_values_empty, _udt2_values, _udt2_values_empty, _udt2_values_empty, _udt2_values_empty],
    'str1': _str82_full,
    'str_ary1': ['', '', '', '', '']
}

BASE_STRUCT_TESTS = [
    # struct of just atomic values
    ('_udt1', 'pycomm3_AtomicUDT', _udt1_values),
    ('_udt1.bool', 'BOOL', _udt1_values['bool']),
    ('_udt1.sint', 'SINT', _udt1_values['sint']),
    ('_udt1.int', 'INT', _udt1_values['int']),
    ('_udt1.dint', 'DINT', _udt1_values['dint']),
    ('_udt1.lint', 'LINT', _udt1_values['lint']),
    ('_udt1.real', 'REAL', _udt1_values['real']),

    # struct of atomic arrays
    ('_udt2', 'pycomm3_AtomicArrayUDT', _udt2_values),
    ('_udt2.bools{2}', 'BOOL[64]', _udt2_bool_array),
    ('_udt2.bools[5]', 'BOOL', _udt2_bool_array[5]),
    ('_udt2.sints{8}', 'SINT[8]', _udt2_sint_array),
    ('_udt2.sints[5]', 'SINT', _udt2_sint_array[5]),  # also read a single element too
    ('_udt2.ints{4}', 'INT[4]', _udt2_int_array),
    ('_udt2.ints[3]', 'INT', _udt2_int_array[3]),
    ('_udt2.dints{10}', 'DINT[10]', _udt2_dint_array),
    ('_udt2.dints[6]', 'DINT', _udt2_dint_array[6]),
    ('_udt2.lints{4}', 'LINT[4]', _udt2_lint_array),
    ('_udt2.lints[0]', 'LINT', _udt2_lint_array[0]),
    ('_udt2.reals{10}', 'REAL[10]', _udt2_real_array),
    ('_udt2.reals[2]', 'REAL', _udt2_real_array[2]),

    ('_nested_udt1', 'pycomm3_NestedUDT', _nested_udt1_values),
    ('_nested_udt1.udt1', 'pycomm3_AtomicUDT', _nested_udt1_values['udt1']),
    ('_nested_udt1.udt_ary1{5}', 'pycomm3_AtomicUDT[5]', _nested_udt1_values['udt_ary1']),
    ('_nested_udt1.udt2', 'pycomm3_AtomicArrayUDT', _nested_udt1_values['udt2']),
    ('_nested_udt1.udt_ary2{5}', 'pycomm3_AtomicArrayUDT[5]', _nested_udt1_values['udt_ary2']),

    # strings
    ('_str1', 'STRING', _str82_part),
    ('_str2', 'STRING', ''),
    ('_str3', 'STRING', _str82_full),
    ('_str20_1', 'STRING20', _str20_part),
    ('_str20_2', 'STRING20', ''),
    ('_str20_3', 'STRING20', _str20_full),
    ('_str480_1', 'STRING480', _str480_part),
    ('_str480_2', 'STRING480', ''),
    ('_str480_3', 'STRING480', _str480_full),
    ('_str_symbols', 'STRING', _str_symbols),
    ('_str_ary1{10}', 'STRING[10]', _str_ary1_values),
    ('_str_ary1[0]{10}', 'STRING[10]', _str_ary1_values),
    ('_str_ary1[0]', 'STRING', _str_ary1_values[0]),
    ('_str_ary1[9]', 'STRING', _str_ary1_values[9]),
    ('_str_ary1[3]{3}', 'STRING[3]', _str_ary1_values[3:6]),
    ('_str480_ary1{4}', 'STRING480[4]', _str480_ary1_values),
    ('_str480_ary1[0]{4}', 'STRING480[4]', _str480_ary1_values),
    ('_str480_ary1[3]', 'STRING480', _str480_ary1_values[3]),
    ('_str480_ary1[1]{2}', 'STRING480[2]', _str480_ary1_values[1:3]),

]
