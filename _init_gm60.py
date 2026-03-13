########################################################
# date: 2025-04-17 00:00 #
# gm60 init function
# save on unit as: _init_gm60.py
from config import *
from findBaudrate import wZone
from _cfg_serial import PRE,SUF

# TODO - Importante, check retrigger time. Same QR is "off" but retrigger is to fast!
wZone(0x00, 0b1_000_01_01)  # Triggermode=suspend=fast response.
wZone(0x02, (0x00,0b00)) # Notrigger / no settlement
wZone(0x05, 0x00)  # (I)nterval in x100ms ( like response )
wZone(0x06, 0x00)  # (T)ime active in x100ms ( I=10,T=5, Scanner 5 on, 5 off)
wZone(0x07, 0x00) # Autosleep
wZone(0x0b, 0x15) #0x25)  # Time for sound = BLINK speed (no response)
wZone(0x0d, 0b0000_0000)  # Input / Output Coding
wZone(0x0e, 0x00) # Turn off sounds
wZone(0x13, 1 << 7 | 0xff)  # 90)  # Same QR read delay x 100ms (Off)
wZone(0x14, 0x00)  # Reserved time for information output (x10ms)
wZone(0x15, 0x63)  # Lamp brightness
wZone(0x1a, 0b0100_0001)  # OutConfig 0x04+2bytes (len)
wZone(0x1b, (0b1001_1111, 0b1011_1010, 0b1101_1100, 0b1111_1110))
wZone(0x1f, 0x1)  # Cycle time for singel led/zone  x100ms
wZone(0x60, 0b1010_1010)  # Output format
wZone(0x62, len(PRE) << 4 | len(SUF))  # B7-4=PRE/B3-0=SUF
wZone(0x63, PRE)  # Prefix 0x63 -> 0x71
wZone(0x72, SUF)  # Suffix ...
wZone(0xb0,0) # Output whole datastring
wZone(0x00, 0b1_000_01_10)  # Trigger mode Continous
del wZone