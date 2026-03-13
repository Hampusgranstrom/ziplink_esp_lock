############################
# date: 2025-02-25 00:00 #
#
from micropython import const
SERIAL_PORT_DELAY_MS: int = const(100)
SERIAL_TIMEOUT_NS: int = const(600*1_000_000)
GLOBAL_TIME:int = const(10_000)
HOLD_LOCK_TIME_MS: int = const(GLOBAL_TIME)#8000)
HOLD_BLINK_TIME_MS: int = const(GLOBAL_TIME)#8000)
HOLD_ERROR_BLINK_TIME_MS: int = const(GLOBAL_TIME)#8000)
PRE: bytes = const("begin".encode())
SUF: bytes = const("ending".encode())