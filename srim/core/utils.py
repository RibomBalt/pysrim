### PYSRIM : Python wrapper for SRIM calculation
### Project initiated by : Christopher Ostrouchov
### Modified by : Victor Garric : victor.garric@gmail.com, 2018

""" Utility functions

"""

def check_input(input_type, condition, value):
    value = input_type(value)
    if not condition(value):
        raise ValueError('type of argument does not satisfy condition')
    return value

def is_zero(value):
    return value == 0


def is_zero_or_one(value):
    return value in range(2)


def is_zero_to_two(value):
    return value in range(3)


def is_zero_to_five(value):
    return value in range(6)


def is_one_to_seven(value):
    return value in range(1, 8)


def is_one_to_eight(value):
    return value in range(1, 9)


def is_srim_degrees(value):
    return 0.0 <= value < 90.0


def is_positive(value):
    return value >= 0.0


def is_greater_than_zero(value):
    return value > 0.0


def is_quoteless(value):
    return '"' not in value
