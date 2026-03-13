############################
# date: 2025-03-11 00:00 #
#
from micropython import const

NET_SSID:       str = const(r"ncs_00101")
NET_PASSWD:     str = const(r"ncs12345")
NET_HIDDEN:     bool = const(False)

# NEW - Add this dictionary:
CLIENT_ADDRESSES = {
    '1': "200.200.201.1",  # CAM1
}

CLIENT_PORT:    int = const(42_000)
# ***** cam - com - cfg ***** #
PRE: bytes = const("begin".encode())
SUF: bytes = const("ending".encode())