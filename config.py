############################
# date: 2025-02-25 00:00 #
# 
from micropython import const
from _cfg_network import *
from _cfg_serial import *
from _key_old import HASH_KEY
from _key_new import HASH_KEY_NEW

# TODO - seperate SERIAL // GM60 (serial)
DEBUG:         bool = const(True)
WIFI_ACTIVE:   bool = const(True)
SERIAL_ACTIVE: bool = const(True)
PORTS_ACTIVE:  bool = const(True)
TUNE_ACTIVE:   bool = const(True)
NVS_ACTIVE:    bool = const(True)