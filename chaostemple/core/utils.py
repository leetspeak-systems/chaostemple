# Short-hand function for putting quotes around an input value, primarily for
# use in CSV exporting.
def quote(input_string):
    return '"%s"' % input_string if input_string not in [None, 'None'] else '""'
