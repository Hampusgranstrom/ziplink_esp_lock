########################################################
# date: 2025-02-17 00:00 #
# ... function
# save on unit as: findBaudrate.py

from micropython import const
from machine import UART, Pin
import utime as time
from config import *
from _utils import *
from _cfg_serial import SERIAL_TIMEOUT_NS, GM60_UART_ID, GM60_TX_PIN, GM60_RX_PIN

BAUDS: tuple = const(((56700, 0x0034, 0), (1200, 0x09c4, 1), (4800, 0x0271, 2), (9600, 0x0139, 3), (
    14400, 0x00d0, 4), (19200, 0x009c, 5), (38400, 0x004e, 6), (56700, 0x0034, 7), (115200, 0x001a, 8)))

uart = UART(GM60_UART_ID, baudrate=BAUDS[0][0],
            tx=Pin(GM60_TX_PIN), rx=Pin(GM60_RX_PIN),
            txbuf=256, rxbuf=256)

def serialWait() -> None | bytes:
    while not uart.txdone():
        time.sleep_us(100)
        pass
    data: bytes = b''
    timeout: int = time.time_ns()+SERIAL_TIMEOUT_NS
    while not uart.any() and time.time_ns() < timeout:
        time.sleep_us(100)
    if uart.any():
        while uart.any():
            if tmp := uart.read():
                data += tmp
            dbg('.', '')
            time.sleep(0.001)
        return data
    else:
        dbg('Timeout::', '')
        return None

def wZone(zone: int | bytes = 0x00, values: bytes | int | tuple[int|bytes] = 0x00, lens=1) -> bytes:
    dbg('WZ:', '')
    if type(values) is int:
        dbg('INT  ', '')
        values = tb(values)
    elif type(values) is tuple:
        dbg('TUPLE', '')
        tmp = b''
        for _ in values:
            tmp += tb(_)
        values = tmp
        lens = len(tmp)
    elif type(values) is bytes:
        dbg('BYTES', '')
        lens = len(values)
    dbg('\t', '')
    cmd: bytes = WRITEZ+tb(lens, 2)+tb(zone)+values+TAIL
    uart.write(cmd)
    dbg(cmd.hex(), '\t')
    dbg(values.hex(), '\n')
    return serialWait()


def findBaudrate(retries: int = 1) -> None | tuple:
    dbg(f'findBaudrate: try {retries}')
    found_baud: None | tuble = None
    for baud in BAUDS:
        uart.init(baudrate=baud[0])
        dbg(f'Testing baud:{baud[0]: 8d}', ' ')
        cmd: bytes = READZ+b'\x01\x00\x2a\x02'+TAIL
        dbg(cmd.hex('_'), ' ')
        uart.write(cmd)
        readByte = serialWait()
        if not readByte:
            dbg('No response')
            continue

        dbg(f'{readByte[:6].hex('-')}')
        if readByte[:4] == ROK+b'\x02':
            found_baud = baud
            break
        else:
            dbg('Wrong response:')
            continue

    # TODO - Fix non responsive reader due to data/time conflict.
    if found_baud:
        dbg(f'Found baud: {found_baud[0]}')
        return found_baud
    elif retries > 0:
        dbg('Port-error, waiting for timeout :: ', '')
        retries -= 1
        time.sleep(0.01)
        findBaudrate(retries)
    return None

def getBPS() -> None|tuple:
    bps = findBaudrate(10) # Try to find gm60 10x times.

    if not bps:  # Unrecoverable_error
        while True:
            red("Unrecoverable_error:: Can't find GM60!!!")
            time.sleep(1)

    if bps[0] == BAUDS[7][0]:
        dbg('No change')
    else:
        dbg(f'Changing to: {BAUDS[7][0]}')
        dbg(wZone(0x2a, tb(BAUDS[7][1], 2)).hex(' '))
        dbg('Reinitializing uart!')
        uart.init(BAUDS[7][0])
        bps = BAUDS[7]
    return uart