############################
# date: 2026-03-13 00:00 #
# PN532 HSU (UART) driver for MicroPython
# Reads NDEF Text Records from NTAG213/215/216 tags
#
from machine import UART, Pin
import utime as time

# PN532 Commands
_CMD_GETFIRMWAREVERSION = 0x02
_CMD_SAMCONFIGURATION   = 0x14
_CMD_INLISTPASSIVETARGET = 0x4A
_CMD_INDATAEXCHANGE     = 0x40

# NTAG READ command (MIFARE Ultralight compatible)
_NTAG_CMD_READ = 0x30

# PN532 frame constants
_PREAMBLE   = 0x00
_STARTCODE1 = 0x00
_STARTCODE2 = 0xFF
_POSTAMBLE  = 0x00
_HOST_TO_PN532 = 0xD4
_PN532_TO_HOST = 0xD5

_ACK = bytes([0x00, 0x00, 0xFF, 0x00, 0xFF, 0x00])


class NFC_PN532:

    def __init__(self, uart_id, tx_pin, rx_pin, baud=115200):
        self._uart = UART(uart_id, baudrate=baud,
                          tx=Pin(tx_pin), rx=Pin(rx_pin),
                          txbuf=256, rxbuf=256)
        self._last_uid = None
        self._last_uid_time = 0
        self._uid_cooldown_ms = 3000
        self._wakeup()
        time.sleep_ms(50)
        if not self.sam_config():
            print("PN532: SAMConfig failed")

    def _wakeup(self):
        """Send wakeup sequence for HSU mode."""
        self._uart.write(bytes([0x55, 0x55, 0x00, 0x00, 0x00,
                                0x00, 0x00, 0x00, 0x00, 0x00,
                                0x00, 0x00, 0x00, 0x00, 0x00, 0x00]))
        time.sleep_ms(100)
        # Flush any stale data
        while self._uart.any():
            self._uart.read()

    def _write_frame(self, data):
        """Build and send a PN532 HSU frame.
        data: bytes to send (TFI + command + params)
        Frame: [0x00 0x00 0xFF] [LEN] [LCS] [data...] [DCS] [0x00]
        """
        length = len(data)
        lcs = (~length + 1) & 0xFF  # Length checksum
        dcs = (~sum(data) + 1) & 0xFF  # Data checksum

        frame = bytes([_PREAMBLE, _STARTCODE1, _STARTCODE2,
                       length, lcs]) + bytes(data) + bytes([dcs, _POSTAMBLE])
        self._uart.write(frame)

    def _read_response(self, timeout_ms=200):
        """Read a PN532 response frame. Returns payload (after TFI) or None."""
        deadline = time.ticks_add(time.ticks_ms(), timeout_ms)

        # Wait for data
        while not self._uart.any():
            if time.ticks_diff(deadline, time.ticks_ms()) <= 0:
                return None
            time.sleep_ms(1)

        # Read available bytes with short delays for remaining data
        time.sleep_ms(10)
        raw = self._uart.read()
        if not raw:
            return None

        # Find preamble + start code: 0x00 0x00 0xFF
        idx = 0
        while idx < len(raw) - 5:
            if raw[idx] == 0x00 and raw[idx+1] == 0x00 and raw[idx+2] == 0xFF:
                break
            idx += 1
        else:
            return None

        idx += 3  # Past start code

        # Check for ACK frame (LEN=0x00, LCS=0xFF)
        if raw[idx] == 0x00 and idx + 1 < len(raw) and raw[idx+1] == 0xFF:
            return b''  # ACK

        length = raw[idx]
        lcs = raw[idx+1]
        if (length + lcs) & 0xFF != 0:
            return None  # Bad length checksum

        idx += 2  # Past LEN + LCS

        if idx + length + 1 > len(raw):
            return None  # Incomplete frame

        payload = raw[idx:idx+length]

        dcs = raw[idx+length]
        if (sum(payload) + dcs) & 0xFF != 0:
            return None  # Bad data checksum

        # Skip TFI byte (0xD5), return command response + data
        if payload[0] == _PN532_TO_HOST:
            return bytes(payload[1:])
        return None

    def _wait_for_ack(self, timeout_ms=200):
        """Wait for ACK frame after sending a command."""
        deadline = time.ticks_add(time.ticks_ms(), timeout_ms)
        buf = b''
        while time.ticks_diff(deadline, time.ticks_ms()) > 0:
            if self._uart.any():
                chunk = self._uart.read()
                if chunk:
                    buf += chunk
                    if _ACK in buf:
                        return True
            time.sleep_ms(1)
        return False

    def _send_command(self, cmd, params=b'', timeout_ms=200):
        """Send command, wait for ACK, then read response."""
        data = bytes([_HOST_TO_PN532, cmd]) + bytes(params)
        self._write_frame(data)

        if not self._wait_for_ack(timeout_ms):
            return None

        return self._read_response(timeout_ms)

    def get_firmware_version(self):
        """Get PN532 firmware version. Returns (IC, Ver, Rev, Support) or None."""
        resp = self._send_command(_CMD_GETFIRMWAREVERSION, timeout_ms=500)
        if resp and len(resp) >= 5:
            # resp[0] = command response code (0x03)
            return resp[1], resp[2], resp[3], resp[4]
        return None

    def sam_config(self):
        """Configure SAM to normal mode."""
        # Mode=1 (Normal), Timeout=0, IRQ=0
        resp = self._send_command(_CMD_SAMCONFIGURATION,
                                  bytes([0x01, 0x00, 0x00]),
                                  timeout_ms=500)
        return resp is not None

    def read_passive_target(self, timeout_ms=100):
        """Detect an ISO14443A tag. Returns UID bytes or None."""
        # MaxTg=1, BrTy=0x00 (106 kbps type A)
        resp = self._send_command(_CMD_INLISTPASSIVETARGET,
                                  bytes([0x01, 0x00]),
                                  timeout_ms=timeout_ms)
        if not resp or len(resp) < 3:
            return None
        # resp[0] = command code (0x4B), resp[1] = number of targets
        num_targets = resp[1]
        if num_targets < 1:
            return None
        # resp[2] = Tg (logical number)
        # resp[3:5] = ATQA
        # resp[5] = SAK
        # resp[6] = UID length
        if len(resp) < 7:
            return None
        uid_len = resp[6]
        if len(resp) < 7 + uid_len:
            return None
        return bytes(resp[7:7+uid_len])

    def _ntag_read_page(self, page):
        """Read 4 pages (16 bytes) starting at given page number.
        Uses InDataExchange with NTAG READ command.
        Returns 16 bytes or None.
        """
        resp = self._send_command(_CMD_INDATAEXCHANGE,
                                  bytes([0x01, _NTAG_CMD_READ, page]),
                                  timeout_ms=200)
        if not resp or len(resp) < 2:
            return None
        # resp[0] = command code (0x41), resp[1] = status
        if resp[1] != 0x00:
            return None
        return bytes(resp[2:])  # 16 bytes (4 pages)

    def read_ndef_text(self):
        """Read NTAG memory from page 4, parse NDEF, extract Text Record payload.
        Returns the key string or None.
        """
        # Read enough pages to cover NTAG213 (max ~45 pages)
        # Each read returns 4 pages (16 bytes), start at page 4
        data = b''
        for page in range(4, 40, 4):
            chunk = self._ntag_read_page(page)
            if not chunk:
                break
            data += chunk
            # Stop early if we find the terminator TLV
            if 0xFE in chunk:
                break

        if len(data) < 4:
            return None

        return _parse_ndef_text(data)

    def poll(self):
        """Non-blocking poll for NFC tag. Returns (success, key_string)."""
        uid = self.read_passive_target(timeout_ms=100)
        if uid is None:
            # No tag present — clear last UID after cooldown
            if self._last_uid and time.ticks_diff(
                    time.ticks_ms(), self._last_uid_time) > self._uid_cooldown_ms:
                self._last_uid = None
            return (False, None)

        # Anti-repeat: skip if same tag still present
        now = time.ticks_ms()
        if self._last_uid == uid:
            self._last_uid_time = now
            return (False, None)

        self._last_uid = uid
        self._last_uid_time = now

        # Tag detected — read NDEF
        payload = self.read_ndef_text()
        if payload:
            return (True, payload)
        return (False, None)


def _parse_ndef_text(data):
    """Parse NDEF TLV data and extract Text Record payload.
    Returns the text string or None.
    """
    i = 0
    while i < len(data):
        tlv_type = data[i]
        if tlv_type == 0x00:
            # NULL TLV — skip
            i += 1
            continue
        if tlv_type == 0xFE:
            # Terminator TLV
            return None
        if i + 1 >= len(data):
            return None

        tlv_len = data[i+1]
        i += 2

        if tlv_type == 0x03:
            # NDEF Message TLV — parse the NDEF record
            if i + tlv_len > len(data):
                return None
            return _parse_ndef_record(data[i:i+tlv_len])

        # Skip unknown TLV
        i += tlv_len

    return None


def _parse_ndef_record(record):
    """Parse a single NDEF record and return Text Record payload.
    Expected: TNF=0x01 (Well-Known), Type='T' (Text).
    """
    if len(record) < 3:
        return None

    header = record[0]
    tnf = header & 0x07
    sr = (header >> 4) & 0x01  # Short Record flag

    type_len = record[1]

    if sr:
        payload_len = record[2]
        offset = 3
    else:
        if len(record) < 6:
            return None
        payload_len = (record[2] << 24) | (record[3] << 16) | (record[4] << 8) | record[5]
        offset = 6

    # Read type
    if offset + type_len > len(record):
        return None
    rec_type = record[offset:offset+type_len]
    offset += type_len

    # Verify: TNF must be 0x01 (Well-Known) and Type must be 'T'
    if tnf != 0x01:
        return None
    if rec_type != b'T':
        return None

    # Read payload
    if offset + payload_len > len(record):
        return None
    payload = record[offset:offset+payload_len]

    if len(payload) < 1:
        return None

    # Status byte: bit 7 = encoding (0=UTF-8), bits 5:0 = language code length
    status = payload[0]
    lang_len = status & 0x3F

    if 1 + lang_len >= len(payload):
        return None

    # The actual text starts after status byte + language code
    text_bytes = payload[1+lang_len:]
    return text_bytes.decode('utf-8')
