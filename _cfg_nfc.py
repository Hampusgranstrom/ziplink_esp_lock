############################
# date: 2026-03-13 00:00 #
#
from micropython import const

# PN532 NFC UART configuration — change these to move PN532 to another port
# Default: UART1 on GPIO 32/33 (GM60 uses UART2 on GPIO 16/17)
# IMPORTANT: Must not overlap with GM60 UART pins when both are active!
NFC_UART_ID:         int = const(1)
NFC_TX_PIN:          int = const(33)   # ESP32 TX -> PN532 RX
NFC_RX_PIN:          int = const(32)   # PN532 TX -> ESP32 RX
NFC_BAUD:            int = const(115200)
NFC_POLL_INTERVAL_MS: int = const(200)
