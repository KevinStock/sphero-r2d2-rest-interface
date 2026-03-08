import os
import asyncio
import logging

from flask import Flask, request, render_template, jsonify
from bleak import BleakClient

# ---------------------------------------------------------------------------
# Configuration (override via environment variables)
# ---------------------------------------------------------------------------
ADDRESS = os.environ.get("DROID_BLE_ADDRESS", "E2:7D:CA:55:E5:5F")
SLEEP_ON_EXIT = os.environ.get("DROID_SLEEP_ON_EXIT", "true").lower() in ("1", "true", "yes")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# BLE characteristic UUIDs for Sphero droids
# (bleak uses UUIDs, not integer ATT handles like pygatt)
FORCE_UUID = "00020005-574f-4f20-5370-6865726f2121"     # Anti-DOS
COMMAND_UUID = "00010002-574f-4f20-5370-6865726f2121"    # Command write
RESPONSE_UUID = "00010003-574f-4f20-5370-6865726f2121"   # Response / notify

# Command mapping from droid.py
# Animation IDs from spherov2.py R2D2.Animations enum
# Sequence byte (3rd data byte) is arbitrary; animation ID is the last 2 bytes (big-endian)
COMMAND_MAP = {
    # --- Emote animations (sounds + movement) ---
    "laugh": [0x0A, 0x17, 0x05, 0x01, 0x00, 0x0F],       # 15 = EMOTE_LAUGH
    "yes": [0x0A, 0x17, 0x05, 0x02, 0x00, 0x15],          # 21 = EMOTE_YES
    "no": [0x0A, 0x17, 0x05, 0x03, 0x00, 0x10],           # 16 = EMOTE_NO
    "alarm": [0x0A, 0x17, 0x05, 0x04, 0x00, 0x07],        # 7  = EMOTE_ALARM
    "angry": [0x0A, 0x17, 0x05, 0x05, 0x00, 0x08],        # 8  = EMOTE_ANGRY
    "annoyed": [0x0A, 0x17, 0x05, 0x06, 0x00, 0x0A],      # 10 = EMOTE_FRUSTRATED
    "ionblast": [0x0A, 0x17, 0x05, 0x07, 0x00, 0x0E],     # 14 = EMOTE_SHORT_CIRCUIT
    "excited": [0x0A, 0x17, 0x05, 0x08, 0x00, 0x0C],      # 12 = EMOTE_EXCITED
    "surprise": [0x0A, 0x17, 0x05, 0x09, 0x00, 0x18],     # 24 = EMOTE_SURPRISED
    # --- WWM (Watch With Me) animations ---
    "sad": [0x0A, 0x17, 0x05, 0x0A, 0x00, 0x2F],          # 47 = WWM_SAD
    "scared": [0x0A, 0x17, 0x05, 0x0B, 0x00, 0x30],       # 48 = WWM_SCARED
    "chatty": [0x0A, 0x17, 0x05, 0x0C, 0x00, 0x36],       # 54 = WWM_YOOHOO
    "confident": [0x0A, 0x17, 0x05, 0x0D, 0x00, 0x21],    # 33 = WWM_BOW
    "happy": [0x0A, 0x17, 0x05, 0x0E, 0x00, 0x28],        # 40 = WWM_HAPPY
    # --- Movement animations ---
    "bow": [0x0A, 0x17, 0x05, 0x10, 0x00, 0x21],          # 33 = WWM_BOW
    "doubletake": [0x0A, 0x17, 0x05, 0x11, 0x00, 0x24],   # 36 = WWM_DOUBLE_TAKE
    "shake": [0x0A, 0x17, 0x05, 0x12, 0x00, 0x31],        # 49 = WWM_SHAKE
    "longshake": [0x0A, 0x17, 0x05, 0x13, 0x00, 0x2B],    # 43 = WWM_LONG_SHAKE
    "jittery": [0x0A, 0x17, 0x05, 0x14, 0x00, 0x29],      # 41 = WWM_JITTERY
    "drive": [0x0A, 0x17, 0x05, 0x15, 0x00, 0x0B],        # 11 = EMOTE_DRIVE
    "taunting": [0x0A, 0x17, 0x05, 0x16, 0x00, 0x33],     # 51 = WWM_TAUNTING
    "whisper": [0x0A, 0x17, 0x05, 0x17, 0x00, 0x34],      # 52 = WWM_WHISPER
    "yelling": [0x0A, 0x17, 0x05, 0x18, 0x00, 0x35],      # 53 = WWM_YELLING
    "curious": [0x0A, 0x17, 0x05, 0x19, 0x00, 0x23],      # 35 = WWM_CURIOUS
    # --- Leg actions (device 0x17, command 0x0D) ---
    "tripod": [0x0A, 0x17, 0x0D, 0x1D, 0x01],             # THREE_LEGS
    "bipod": [0x0A, 0x17, 0x0D, 0x1C, 0x02],              # TWO_LEGS
    "waddle": [0x0A, 0x17, 0x0D, 0x1E, 0x03],             # WADDLE
    "stopwaddle": [0x0A, 0x17, 0x0D, 0x1F, 0x00],         # STOP
    # --- Head rotation (device 0x17, command 0x0F, float angle big-endian) ---
    "headleft": [0x0A, 0x17, 0x0F, 0x20, 0xC2, 0xB4, 0x00, 0x00],   # -90.0 degrees
    "headright": [0x0A, 0x17, 0x0F, 0x21, 0x42, 0xB4, 0x00, 0x00],  #  90.0 degrees
    "headcenter": [0x0A, 0x17, 0x0F, 0x22, 0x00, 0x00, 0x00, 0x00], #   0.0 degrees
}

# ---------------------------------------------------------------------------
# Available command names (used by /commands endpoint)
# ---------------------------------------------------------------------------
COMMAND_NAMES = sorted(COMMAND_MAP.keys())

# ---------------------------------------------------------------------------
# BLE packets
# ---------------------------------------------------------------------------
# 'use_the_force' tells the droid we're a controller. Prevents disconnection.
USE_THE_FORCE = bytes([0x75, 0x73, 0x65, 0x74, 0x68, 0x65, 0x66, 0x6F,
                       0x72, 0x63, 0x65, 0x2E, 0x2E, 0x2E, 0x62, 0x61, 0x6E, 0x64])
# Wake from sleep — droid becomes responsive; front LED flashes blue/red.
WAKE_UP_PACKET = bytes([0x8D, 0x0A, 0x13, 0x0D, 0x00, 0xD5, 0xD8])
# Turn on holoprojector LED at max (0xFF) intensity.
HOLOPROJECTOR_ON = bytes([0x8D, 0x0A, 0x1A, 0x0E, 0x1C, 0x00, 0x80, 0xFF, 0x32, 0xD8])
# Put the droid to sleep.
SLEEP_PACKET = bytes([0x8D, 0x0A, 0x13, 0x01, 0x17, 0xCA, 0xD8])

def build_packet(data):
    """Wrap *data* in the Sphero packet framing (0x8D … CRC … 0xD8)."""
    ret = [0x8D]
    for b in data:
        ret.append(b)
    ret.append(_gen_crc(data))
    ret.append(0xD8)
    return bytes(ret)


def _gen_crc(data):
    """Compute the Sphero checksum (one's complement of the sum mod 256)."""
    return ~sum(data) % 256


def _notification_handler(sender, data):
    """Handle BLE notifications from the droid (required to activate full command processing)."""
    pass


# ---------------------------------------------------------------------------
# BLE helpers — centralised async connect → command → disconnect logic
# ---------------------------------------------------------------------------
async def _send_sequences(sequences, *, wake=True, sleep=SLEEP_ON_EXIT):
    """Connect to the droid over BLE (bleak/WinRT) and send *sequences*,
    optionally waking the droid first and putting it to sleep afterwards.
    """
    async with BleakClient(ADDRESS) as client:
        if not client.is_connected:
            raise ConnectionError(f"Failed to connect to {ADDRESS}")

        # Authenticate as a controller
        await client.write_gatt_char(FORCE_UUID, USE_THE_FORCE, response=True)

        # Subscribe to notifications — required before the droid will fully
        # process audio/animation commands.
        await client.start_notify(RESPONSE_UUID, _notification_handler)

        if wake:
            await client.write_gatt_char(COMMAND_UUID, WAKE_UP_PACKET, response=True)
            # Give the droid time to wake up and initialise its audio subsystem
            await asyncio.sleep(2)
            await client.write_gatt_char(COMMAND_UUID, HOLOPROJECTOR_ON, response=True)

        for seq in sequences:
            await client.write_gatt_char(COMMAND_UUID, build_packet(seq), response=True)
            await asyncio.sleep(6)

        if sleep:
            await client.write_gatt_char(COMMAND_UUID, SLEEP_PACKET, response=True)

        await client.stop_notify(RESPONSE_UUID)


async def _put_droid_to_sleep():
    """Connect and send only the sleep packet."""
    async with BleakClient(ADDRESS) as client:
        if not client.is_connected:
            raise ConnectionError(f"Failed to connect to {ADDRESS}")
        await client.write_gatt_char(FORCE_UUID, USE_THE_FORCE, response=True)
        await client.start_notify(RESPONSE_UUID, _notification_handler)
        await client.write_gatt_char(COMMAND_UUID, SLEEP_PACKET, response=True)
        await client.stop_notify(RESPONSE_UUID)

# ---------------------------------------------------------------------------
# Flask routes
# ---------------------------------------------------------------------------
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/commands", methods=["GET"])
def list_commands():
    """Return the list of available command names."""
    return jsonify({"commands": COMMAND_NAMES})


@app.route("/send_command", methods=["GET", "POST"])
def send_command():
    command = (
        request.args.get("command") if request.method == "GET"
        else request.form.get("command")
    )
    if command not in COMMAND_MAP:
        return jsonify({"status": "error", "message": "Invalid command."}), 400

    try:
        logger.info("Sending command: %s", command)
        asyncio.run(_send_sequences([COMMAND_MAP[command]]))
        return jsonify({"status": "success", "message": f"Command '{command}' sent successfully."})
    except Exception as e:
        logger.exception("Failed to send command '%s'", command)
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/put_to_sleep", methods=["GET"])
def put_to_sleep():
    """Send only the sleep packet (no wake / holoprojector)."""
    try:
        asyncio.run(_put_droid_to_sleep())
        return jsonify({"status": "success", "message": "Droid put to sleep successfully."})
    except Exception as e:
        logger.exception("Failed to put droid to sleep")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/test_sound", methods=["GET"])
def test_sound():
    """Test different animation/sound IDs. Usage: /test_sound?id=11"""
    sound_id = request.args.get("id", type=int)
    if sound_id is None or not 0 <= sound_id <= 255:
        return jsonify({"status": "error", "message": "Provide ?id=0 through ?id=255"}), 400

    try:
        seq = [0x0A, 0x17, 0x05, 0x18, 0x00, sound_id]
        logger.info("Testing sound id=%d (0x%02X)", sound_id, sound_id)
        asyncio.run(_send_sequences([seq]))
        return jsonify({"status": "success", "message": f"Played sound id={sound_id} (0x{sound_id:02X})"})
    except Exception as e:
        logger.exception("Failed to play sound id=%s", sound_id)
        return jsonify({"status": "error", "message": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
