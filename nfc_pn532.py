############################
# date: 2026-03-13 00:00 #
# PN532 HSU (UART) driver for MicroPython
# Reads NDEF Text Records from NTAG213/215/216 tags
# Production-grade: non-blocking, memory-safe, self-recovering
#
from machine import UART, Pin
import utime as time
import gc

# PN532 Commands
_CMD_GETFIRMWAREVERSION  = const(0x02)
_CMD_SAMCONFIGURATION    = const(0x14)
_CMD_INLISTPASSIVETARGET = const(0x4A)
_CMD_INDATAEXCHANGE      = const(0x40)
_CMD_INRELEASE           = const(0x52)

# NTAG READ command (MIFARE Ultralight compatible)
_NTAG_CMD_READ = const(0x30)

# PN532 frame constants
_HOST_TO_PN532 = const(0xD4)
_PN532_TO_HOST = const(0xD5)

# Max pages to read from NTAG (page 4..39 = 144 bytes, covers NTAG213)
_MAX_READ_PAGE = const(40)
# Pre-allocated read buffer size (16 bytes per read * 9 reads = 144 bytes)
_READ_BUF_SIZE = const(144)
# Max consecutive errors before triggering re-init
_MAX_ERRORS_BEFORE_REINIT = const(10)


class NFC_PN532:

    def __init__(self, uart_id, tx_pin, rx_pin, baud=115200):
        self._uart_id = uart_id
        self._tx_pin = tx_pin
        self._rx_pin = rx_pin
        self._baud = baud
        self._uart = None
        self._last_uid = None
        self._last_uid_time = 0
        self._uid_cooldown_ms = 3000
        self._consecutive_errors = 0
        self._initialized = False
        # Pre-allocate buffers to avoid heap fragmentation
        self._rx_buf = bytearray(270)  # Max PN532 frame = 265 bytes
        self._page_buf = bytearray(_READ_BUF_SIZE)
        self._init_hardware()

    def _init_hardware(self):
        """Initialize or re-initialize the PN532 hardware."""
        try:
            if self._uart:
                self._uart.deinit()
        except Exception:
            pass

        self._uart = UART(self._uart_id, baudrate=self._baud,
                          tx=Pin(self._tx_pin), rx=Pin(self._rx_pin),
                          txbuf=256, rxbuf=256)
        self._wakeup()
        time.sleep_ms(50)

        ok = self.sam_config()
        self._initialized = ok
        self._consecutive_errors = 0
        if not ok:
            print("PN532: SAMConfig failed - check wiring")
        return ok

    def _wakeup(self):
        """Send wakeup sequence for HSU mode."""
        # PN532 HSU wakeup: long preamble of 0x55 followed by 0x00s
        self._uart.write(b'\x55\x55\x55\x00\x00\x00\x00\x00'
                         b'\x00\x00\x00\x00\x00\x00\x00\x00')
        time.sleep_ms(100)
        self._flush_rx()

    def _flush_rx(self):
        """Drain any stale data from UART RX buffer."""
        while self._uart.any():
            self._uart.read()

    def _write_frame(self, data):
        """Build and send a PN532 HSU frame.
        Frame: [0x00 0x00 0xFF] [LEN] [LCS] [data...] [DCS] [0x00]
        """
        length = len(data)
        lcs = (~length + 1) & 0xFF
        dcs = (~sum(data) + 1) & 0xFF

        # Build frame in one allocation
        frame = bytearray(5 + length + 2)
        frame[0] = 0x00  # Preamble
        frame[1] = 0x00  # Start code 1
        frame[2] = 0xFF  # Start code 2
        frame[3] = length
        frame[4] = lcs
        frame[5:5+length] = data
        frame[5+length] = dcs
        frame[6+length] = 0x00  # Postamble

        self._flush_rx()  # Clear stale RX data before every command
        self._uart.write(frame)

    def _read_bytes(self, timeout_ms):
        """Read all available bytes from UART into self._rx_buf.
        Returns number of bytes read. Uses incremental reads with
        short inter-byte gaps to ensure complete frames.
        """
        deadline = time.ticks_add(time.ticks_ms(), timeout_ms)
        n = 0
        max_n = len(self._rx_buf)

        # Wait for first byte
        while not self._uart.any():
            if time.ticks_diff(deadline, time.ticks_ms()) <= 0:
                return 0
            time.sleep_ms(1)

        # Read with inter-byte timeout to catch full frame
        while time.ticks_diff(deadline, time.ticks_ms()) > 0:
            if self._uart.any():
                chunk = self._uart.read(max_n - n)
                if chunk:
                    cl = len(chunk)
                    if n + cl > max_n:
                        cl = max_n - n
                    self._rx_buf[n:n+cl] = chunk[:cl]
                    n += cl
                    if n >= max_n:
                        break
            else:
                # Short gap — wait for more bytes or declare frame complete
                time.sleep_ms(3)
                if not self._uart.any():
                    break  # No more bytes coming

        return n

    def _parse_frame(self, buf, n):
        """Parse a PN532 response frame from buffer.
        Returns payload bytes (after TFI) or None.
        Skips ACK frames automatically.
        """
        # Scan for preamble: 0x00 0x00 0xFF
        i = 0
        result = None
        while i < n - 5:
            if buf[i] == 0x00 and buf[i+1] == 0x00 and buf[i+2] == 0xFF:
                i += 3

                # ACK frame: LEN=0x00 LCS=0xFF
                if i + 1 < n and buf[i] == 0x00 and buf[i+1] == 0xFF:
                    i += 2
                    continue  # Skip ACK, look for response frame after it

                if i + 1 >= n:
                    return None

                length = buf[i]
                lcs = buf[i+1]
                if (length + lcs) & 0xFF != 0:
                    return None  # Bad length checksum

                i += 2

                if i + length + 1 > n:
                    return None  # Incomplete frame

                # Verify data checksum
                dcs = buf[i + length]
                dcs_calc = 0
                for j in range(length):
                    dcs_calc += buf[i+j]
                if (dcs_calc + dcs) & 0xFF != 0:
                    return None  # Bad data checksum

                # Verify TFI
                if buf[i] != _PN532_TO_HOST:
                    return None

                # Return payload (skip TFI byte)
                result = bytes(buf[i+1:i+length])
                return result
            else:
                i += 1

        return None

    def _send_command(self, cmd, params=b'', timeout_ms=200):
        """Send command, read ACK + response in one pass."""
        data = bytes([_HOST_TO_PN532, cmd]) + bytes(params)
        self._write_frame(data)

        # Read everything: ACK + response arrive in sequence
        n = self._read_bytes(timeout_ms)
        if n == 0:
            return None

        return self._parse_frame(self._rx_buf, n)

    def _record_error(self):
        """Track consecutive errors. Trigger re-init if threshold exceeded."""
        self._consecutive_errors += 1
        if self._consecutive_errors >= _MAX_ERRORS_BEFORE_REINIT:
            print("PN532: Too many errors, re-initializing...")
            self._init_hardware()

    def _record_success(self):
        """Reset error counter on successful operation."""
        self._consecutive_errors = 0

    def get_firmware_version(self):
        """Get PN532 firmware version. Returns (IC, Ver, Rev, Support) or None."""
        resp = self._send_command(_CMD_GETFIRMWAREVERSION, timeout_ms=500)
        if resp and len(resp) >= 4:
            # resp[0] = IC, resp[1] = Ver, resp[2] = Rev, resp[3] = Support
            return resp[0], resp[1], resp[2], resp[3]
        return None

    def sam_config(self):
        """Configure SAM to normal mode."""
        resp = self._send_command(_CMD_SAMCONFIGURATION,
                                  b'\x01\x00\x00', timeout_ms=500)
        return resp is not None

    def read_passive_target(self, timeout_ms=150):
        """Detect an ISO14443A tag. Returns UID bytes or None."""
        resp = self._send_command(_CMD_INLISTPASSIVETARGET,
                                  b'\x01\x00', timeout_ms=timeout_ms)
        if not resp or len(resp) < 6:
            return None
        # resp[0] = num targets, resp[1] = Tg
        # resp[2:4] = ATQA, resp[4] = SAK, resp[5] = UID length
        num_targets = resp[0]
        if num_targets < 1:
            return None
        uid_len = resp[5]
        if len(resp) < 6 + uid_len:
            return None
        return bytes(resp[6:6+uid_len])

    def _release_target(self):
        """Release the current target to allow re-detection."""
        self._send_command(_CMD_INRELEASE, b'\x00', timeout_ms=100)

    def _ntag_read_page(self, page):
        """Read 4 pages (16 bytes) starting at given page.
        Returns 16 bytes or None.
        """
        resp = self._send_command(_CMD_INDATAEXCHANGE,
                                  bytes([0x01, _NTAG_CMD_READ, page]),
                                  timeout_ms=200)
        if not resp or len(resp) < 2:
            return None
        # resp[0] = status byte
        if resp[0] != 0x00:
            return None
        if len(resp) < 17:  # 1 status + 16 data bytes
            return None
        return resp[1:17]

    def read_ndef_text(self):
        """Read NTAG memory from page 4, parse NDEF, extract Text Record.
        Uses pre-allocated buffer to avoid heap fragmentation.
        Returns key string or None.
        """
        buf = self._page_buf
        buf_len = 0

        for page in range(4, _MAX_READ_PAGE, 4):
            chunk = self._ntag_read_page(page)
            if not chunk:
                break
            cl = len(chunk)
            if buf_len + cl > len(buf):
                break
            buf[buf_len:buf_len+cl] = chunk
            buf_len += cl
            # Stop early at terminator TLV
            for b in chunk:
                if b == 0xFE:
                    return _parse_ndef_text(buf, buf_len)

        if buf_len < 4:
            return None
        return _parse_ndef_text(buf, buf_len)

    def poll(self):
        """Non-blocking poll for NFC tag. Returns (success: bool, key: str|None).
        Designed for use in asyncio loop with short blocking time.
        """
        if not self._initialized:
            self._record_error()
            return (False, None)

        try:
            uid = self.read_passive_target(timeout_ms=150)
        except Exception as e:
            print(f"PN532 poll error: {e}")
            self._record_error()
            return (False, None)

        if uid is None:
            # No tag — clear cached UID after cooldown
            if self._last_uid and time.ticks_diff(
                    time.ticks_ms(), self._last_uid_time) > self._uid_cooldown_ms:
                self._last_uid = None
            return (False, None)

        self._record_success()

        # Anti-repeat: skip if same tag still present
        now = time.ticks_ms()
        if self._last_uid == uid:
            self._last_uid_time = now
            return (False, None)

        self._last_uid = uid
        self._last_uid_time = now

        # New tag — read NDEF
        try:
            payload = self.read_ndef_text()
        except Exception as e:
            print(f"PN532 NDEF error: {e}")
            self._release_target()
            return (False, None)

        self._release_target()
        gc.collect()

        if payload:
            return (True, payload)
        return (False, None)


def _parse_ndef_text(data, data_len):
    """Parse NDEF TLV from buffer and extract Text Record payload.
    Handles both 1-byte and 3-byte TLV length formats.
    Returns text string or None.
    """
    i = 0
    while i < data_len:
        tlv_type = data[i]
        i += 1

        if tlv_type == 0x00:
            continue  # NULL TLV, no length field
        if tlv_type == 0xFE:
            return None  # Terminator TLV

        if i >= data_len:
            return None

        # TLV length: 1-byte or 3-byte format
        if data[i] == 0xFF:
            # 3-byte length: 0xFF, high, low
            if i + 2 >= data_len:
                return None
            tlv_len = (data[i+1] << 8) | data[i+2]
            i += 3
        else:
            tlv_len = data[i]
            i += 1

        if tlv_type == 0x03:
            # NDEF Message TLV
            if i + tlv_len > data_len:
                return None
            return _parse_ndef_record(data, i, tlv_len)

        # Skip unknown TLV
        i += tlv_len

    return None


def _parse_ndef_record(data, offset, rec_len):
    """Parse an NDEF record at data[offset:offset+rec_len].
    Validates TNF=0x01 (Well-Known) and Type='T' (Text).
    Returns text string or None.
    """
    end = offset + rec_len
    if offset + 3 > end:
        return None

    header = data[offset]
    tnf = header & 0x07
    sr = (header >> 4) & 0x01  # Short Record flag
    type_len = data[offset + 1]

    if sr:
        if offset + 3 > end:
            return None
        payload_len = data[offset + 2]
        pos = offset + 3
    else:
        if offset + 6 > end:
            return None
        payload_len = ((data[offset+2] << 24) | (data[offset+3] << 16) |
                       (data[offset+4] << 8) | data[offset+5])
        pos = offset + 6

    # Type field
    if pos + type_len > end:
        return None

    # Verify TNF=0x01 and Type='T'
    if tnf != 0x01:
        return None
    if type_len != 1 or data[pos] != 0x54:  # 'T'
        return None
    pos += type_len

    # Payload
    if pos + payload_len > end:
        return None
    if payload_len < 2:
        return None

    # Status byte: bit 7 = encoding (0=UTF-8), bits 5:0 = lang code length
    status = data[pos]
    lang_len = status & 0x3F

    text_start = pos + 1 + lang_len
    text_end = pos + payload_len

    if text_start >= text_end:
        return None

    # Extract text — use memoryview to avoid allocation
    return bytes(data[text_start:text_end]).decode('utf-8')
