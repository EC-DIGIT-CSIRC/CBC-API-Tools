# *********************************************************************
# Copyright (EC DIGIT CSIRC 2022). Licensed under the EUPL-1.2 or later
# *********************************************************************

"""Helper module for export_process_events script

It contains helper functions, such as transform functions.
"""

import socket
import struct

def int2ip(ip):
    """Returns the string representation of an IPv4 in CIDR format from an IPv4 in integer format.
    """    
    return str(socket.inet_ntoa(struct.pack('>i',ip)))