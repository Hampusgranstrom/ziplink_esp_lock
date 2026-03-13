############################
# date: 2025-02-25 00:00 #
#
from micropython import const

# GM60 UART configuration — change these to move GM60 to another port
GM60_UART_ID:    int = const(2)    # UART peripheral (0=debug, 1 or 2)
GM60_TX_PIN:     int = const(17)   # ESP32 TX -> GM60 RX
GM60_RX_PIN:     int = const(16)   # GM60 TX -> ESP32 RX

SERIAL_PORT_DELAY_MS: int = const(100)
SERIAL_TIMEOUT_NS: int = const(600*1_000_000)
GLOBAL_TIME:int = const(10_000)
HOLD_LOCK_TIME_MS: int = const(GLOBAL_TIME)#8000)
HOLD_BLINK_TIME_MS: int = const(GLOBAL_TIME)#8000)
HOLD_ERROR_BLINK_TIME_MS: int = const(GLOBAL_TIME)#8000)
PRE: bytes = const("begin".encode())
SUF: bytes = const("ending".encode())