"""
Minimal PN532 HSU diagnostic — run in REPL with: exec(open('test_pn532.py').read())
Tests both pin directions and prints raw bytes.
"""
from machine import UART, Pin
import utime as time

def test_pn532(tx, rx, label):
    print(f"\n{'='*40}")
    print(f"Test: {label}  TX={tx} RX={rx}  baud=115200")
    print(f"{'='*40}")

    uart = UART(2, baudrate=115200, tx=Pin(tx), rx=Pin(rx), txbuf=256, rxbuf=256)
    time.sleep_ms(100)

    # Drain any stale data
    while uart.any():
        uart.read()

    # Step 1: Wakeup
    print("1) Sending wakeup...")
    uart.write(b'\x55\x55\x55\x00\x00\x00\x00\x00'
               b'\x00\x00\x00\x00\x00\x00\x00\x00')
    time.sleep_ms(100)
    stale = uart.read()
    if stale:
        print(f"   Wakeup got {len(stale)} bytes: {stale.hex()}")
    else:
        print("   Wakeup: no response (normal)")

    # Step 2: GetFirmwareVersion command
    # Frame: 00 00 FF 02 FE D4 02 2A 00
    cmd = b'\x00\x00\xFF\x02\xFE\xD4\x02\x2A\x00'
    print("2) Sending GetFirmwareVersion...")
    uart.write(cmd)

    # Wait up to 500ms for response
    deadline = time.ticks_add(time.ticks_ms(), 500)
    while not uart.any():
        if time.ticks_diff(deadline, time.ticks_ms()) <= 0:
            break
        time.sleep_ms(5)

    time.sleep_ms(50)  # let full frame arrive
    resp = uart.read()
    if resp:
        print(f"   Got {len(resp)} bytes: {resp.hex()}")
        # Parse: look for ACK (00 00 FF 00 FF 00) and firmware response
        h = resp.hex()
        if '0000ff00ff00' in h:
            print("   >> ACK found!")
        if 'd503' in h:
            idx = h.index('d503')
            fw = resp[idx//2:]
            if len(fw) >= 6:
                print(f"   >> FW: IC=0x{fw[2]:02X} Ver={fw[3]}.{fw[4]} Support=0x{fw[5]:02X}")
    else:
        print("   NO RESPONSE (0 bytes)")

    uart.deinit()

# Test both pin configurations
test_pn532(16, 17, "TX=16 RX=17 (current config)")
test_pn532(17, 16, "TX=17 RX=16 (swapped)")

print("\n--- Done ---")
print("If BOTH show 0 bytes: check HSU jumpers, wiring, and 3.3V power")
print("If ONE works: update _cfg_nfc.py with the working pins")
