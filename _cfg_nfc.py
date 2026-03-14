############################
# date: 2026-03-13 00:00 #
#
from micropython import const

# PN532 NFC UART configuration (replaces GM60 on UART2 / GPIO 16/17)
NFC_UART_ID:         int = const(2)
NFC_TX_PIN:          int = const(16)   # ESP32 TX -> PN532 RX
NFC_RX_PIN:          int = const(17)   # PN532 TX -> ESP32 RX
NFC_BAUD:            int = const(9600)
NFC_POLL_INTERVAL_MS: int = const(200)
