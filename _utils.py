########################################################
# date: 2025-02-17 00:00 #
# ... utils
# save on unit as: _utils.py

from micropython import const
from config import *
import gc

ESC: str = "\033["
RST: str = const(f"{ESC}39;49m")
RED: str = const(f"{ESC}31m")
GREEN: str = const(f"{ESC}32m")
BLUE: str = const(f"{ESC}34m")
H1: bytes = const(b'\x7e\x00')
H2: bytes = const(b'\x02\x00')
ROK: bytes = const(H2+b'\x00')
READZ: bytes = const(H1+b'\x07') 
WRITEZ: bytes = const(H1+b'\x08')
SAVEZ: bytes = const(H1+b'\x09')
TAIL: bytes = const(b'\xab\xcd\x0a')

def free(): F = gc.mem_free(); A = gc.mem_alloc(); T = F + \
    A; P = '{0:.2f}%'.format(F/T*100); return ('Total:{0} Free:{1} ({2})'.format(T, F, P))

def tb(value: int = 0, length: int = 1, mode: str = 'little'): return int(
    value).to_bytes(length, 'little')

def tohex(bb):
    return hexlify(bb)

def dbg(st: str, e: str = '\n'):
    if DEBUG: print(f'{st}', end=e)

def red(st, nl='\n') -> None: dbg(f'{RED}{st}{RST}', e=nl)
def blue(st, nl='\n') -> None: dbg(f'{BLUE}{st}{RST}', e=nl)
def green(st, nl='\n') -> None: dbg(f'{GREEN}{st}{RST}', e=nl)

# emit native? == less space -- > faster execution
def calculatecrc16(datas: bytes, crc: int = 0) -> bytes:
    from _crc_xmodem_table import CRC16_XMODEM_TABLE as table
    for byte in datas: crc = ((crc << 8) & 0xff00) ^ table[((crc >> 8) & 0xff) ^ byte]
    return int(crc & 0xffff).to_bytes(2, 'big')

# async def async_trySleep(_s:int=0)->bool: # TODO: better import logic
#     import uasyncio as asyncio
#     return asyncio.create_task(trySleep(_s*1000))
# 
# async def async_trySleep_ms(_ms:int=0)-> bool: # test if in globals?
#     import uasyncio as asyncio
#     try:
#         await asyncio.sleep_ms(_s)
#         return True
#     except KeyboardInterrupt k:
#         print("Sleep interupted by keyboard")
#         return False