############################
# date: 2026-03-13 00:00 #
#
from micropython import const

NFC_UART_ID:         int = const(2)    # UART2 — same as GM60 (disable GM60 first!)
NFC_TX_PIN:          int = const(17)   # ESP32 TX -> PN532 RX
NFC_RX_PIN:          int = const(16)   # PN532 TX -> ESP32 RX
NFC_BAUD:            int = const(115200)
NFC_POLL_INTERVAL_MS: int = const(200)
