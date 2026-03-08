from flask import Flask, request, render_template
import json
import asyncio
import time
import logging
from bleak import BleakClient, BleakScanner

app = Flask(__name__)

address = 'E2:7D:CA:55:E5:5F'
sleeponexit = True

# BLE characteristic handles (same as original)
FORCE_HANDLE = 0x15
COMMAND_HANDLE = 0x1c

# Command mapping from droid.py
commandmap = {
    "laugh": [0x0A,0x18,0x00,0x1F,0x00,0x32,0x00,0x00,0x00,0x00,0x00],
    "yes": [0x0A, 0x17, 0x05, 0x41, 0x00, 0x0F],
    "no": [0x0A, 0x17, 0x05, 0x3F, 0x00, 0x10],
    "alarm": [0x0A, 0x17, 0x05, 0x17, 0x00, 0x07],
    "angry": [0x0A, 0x17, 0x05, 0x18, 0x00, 0x08],
    "annoyed": [0x0A, 0x17, 0x05, 0x19, 0x00, 0x09],
    "ionblast": [0x0A, 0x17, 0x05, 0x1A, 0x00, 0x0E],
    "sad": [0x0A, 0x17, 0x05, 0x1C, 0x00, 0x11],
    "scared": [0x0A, 0x17, 0x05, 0x1D, 0x00, 0x13],
    "chatty": [0x0A, 0x17, 0x05, 0x17, 0x00, 0x0A],
    "confident": [0x0A, 0x17, 0x05, 0x18, 0x00, 0x12],
    "excited": [0x0A, 0x17, 0x05, 0x19, 0x00, 0x0C],
    "happy": [0x0A, 0x17, 0x05, 0x1A, 0x00, 0x0D],
    "surprise": [0x0A, 0x17, 0x05, 0x1C, 0x00, 0x18],
    "tripod": [0x0A, 0x17, 0x0D, 0x1D, 0x01],
    "bipod": [0x0A, 0x17, 0x0D, 0x1C, 0x02]
}

# 'use_the_force' tells the droid we're a controller. Prevents disconnection.
use_the_force = bytes([0x75, 0x73, 0x65, 0x74, 0x68, 0x65, 0x66, 0x6F, 0x72, 0x63, 0x65, 0x2E, 0x2E, 0x2E, 0x62, 0x61, 0x6E, 0x64])
# Wake from sleep. Droid is responsive and front led flashes blue/red
wake_up_packet = bytes([0x8D, 0x0A, 0x13, 0x0D, 0x00, 0xD5, 0xD8])
# Turn on holoprojector led, 0xff (max) intensity
holoprojector_on = bytes([0x8D, 0x0A, 0x1A, 0x0E, 0x1C, 0x00, 0x80, 0xFF, 0x32, 0xD8])
# Put the droid to sleep
sleep_packet = bytes([0x8D, 0x0A, 0x13, 0x01, 0x17, 0xCA, 0xD8])

def BuildPacket(data):
    ret = [0x8D]
    for b in data:
        ret.append(b)
    ret.append(GenCrc(data))
    ret.append(0xD8)
    return bytes(ret)

def GenCrc(data):
    ret = 0
    for b in data:
        ret += b
        ret = ret % 256
    return ~ret % 256

async def send_ble_command(sequences):
    """Connect to the droid over BLE and send a list of command sequences."""
    # On Windows, bleak uses WinRT and handles random address type automatically.
    # The 'winrt' keyword argument can be used to pass platform-specific options.
    async with BleakClient(address) as client:
        if not client.is_connected:
            raise ConnectionError(f"Failed to connect to {address}")

        # Authenticate as a controller
        await client.write_gatt_char(FORCE_HANDLE, use_the_force, response=True)
        await client.write_gatt_char(COMMAND_HANDLE, wake_up_packet, response=True)
        await client.write_gatt_char(COMMAND_HANDLE, holoprojector_on, response=True)

        for seq in sequences:
            await client.write_gatt_char(COMMAND_HANDLE, BuildPacket(seq), response=True)
            await asyncio.sleep(6)

        if sleeponexit:
            await client.write_gatt_char(COMMAND_HANDLE, sleep_packet, response=True)

async def put_droid_to_sleep():
    """Connect and send only the sleep packet."""
    async with BleakClient(address) as client:
        if not client.is_connected:
            raise ConnectionError(f"Failed to connect to {address}")
        await client.write_gatt_char(COMMAND_HANDLE, sleep_packet, response=True)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/send_command', methods=['GET', 'POST'])
def send_command():
    command = request.args.get('command') if request.method == 'GET' else request.form.get('command')
    if command in commandmap:
        try:
            sequences = [commandmap[command]]
            asyncio.run(send_ble_command(sequences))
            return json.dumps({"status": "success", "message": f"Command '{command}' sent successfully."}), 200
        except Exception as e:
            return json.dumps({"status": "error", "message": str(e)}), 500
    else:
        return json.dumps({"status": "error", "message": "Invalid command."})

@app.route('/put_to_sleep', methods=['GET'])
def put_to_sleep():
    try:
        asyncio.run(put_droid_to_sleep())
        return json.dumps({"status": "success", "message": "Droid put to sleep successfully."}), 200
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
