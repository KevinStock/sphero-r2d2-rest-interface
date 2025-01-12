from flask import Flask, request, render_template
import json
import pygatt
import time
import logging
import sys
from pygatt.backends import BLEAddressType, Characteristic, BLEBackend

app = Flask(__name__)

command = None
address = 'E2:7D:CA:55:E5:5F'
sendbytes = None
debuglogging = False
sleeponexit = True
sequences = []

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

# Wake-up and sleep packets
# 'usetheforce...band' tells the droid we're a controller, I guess.  Prevents disconnection.
use_the_force = [0x75, 0x73, 0x65, 0x74, 0x68, 0x65, 0x66, 0x6F, 0x72, 0x63, 0x65, 0x2E, 0x2E, 0x2E, 0x62, 0x61, 0x6E, 0x64]
# wake from sleep?  Droid is responsive and front led flashes blue/red
wake_up_packet = [0x8D, 0x0A, 0x13, 0x0D, 0x00, 0xD5, 0xD8]
# Turn on holoprojector led, 0xff (max) intensity
holoprojector_on = [0x8D, 0x0A, 0x1A, 0x0E, 0x1C, 0x00, 0x80, 0xFF, 0x32, 0xD8]
# Rotate top to -90 degrees
rotate_top_90 = [0x8D, 0x0A, 0x17, 0x0F, 0x1C, 0x42, 0xB4, 0x00, 0x00, 0xBD, 0xD8]
# Rotate top to 0 degrees
rotate_top_0 = [0x8D, 0x0A, 0x17, 0x0F, 0x1E, 0x00, 0x00, 0x00, 0x00, 0xB1, 0xD8]
# put the droid to sleep
sleep_packet = [0x8D, 0x0A, 0x13, 0x01, 0x17, 0xCA, 0xD8]

def BuildPacket(bytes):
    ret = [0x8D]
    for b in bytes:
        ret.append(b)
    ret.append(GenCrc(bytes))
    ret.append(0xD8)
    return ret

def GenCrc(bytes):
    ret = 0
    for b in bytes:
        ret += b
        ret = ret % 256
    return ~ret % 256

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/send_command', methods=['GET', 'POST'])
def send_command():
    command = request.args.get('command') if request.method == 'GET' else request.form.get('command')
    if command in commandmap:
        try:
            global address
            sequences = [commandmap[command]]

            adapter = pygatt.GATTToolBackend()
            adapter.start()
            device = adapter.connect(address=address, address_type=BLEAddressType.random)

            device.char_write_handle(0x15, use_the_force, True)
            device.char_write_handle(0x1c, wake_up_packet, True)
            device.char_write_handle(0x1c, holoprojector_on, True)

            for seq in sequences:
                device.char_write_handle(0x1c, BuildPacket(seq), True)
                time.sleep(6)

            # rotate top to -90 degrees
            #device.char_write_handle(0x1c, rotate_top_90, True)
            #time.sleep(1)

            # rotate top to 0 degrees
            #device.char_write_handle(0x1c, rotate_top_0, True)
            #time.sleep(1)
            
            if sleeponexit:
                # put the droid to sleep
                device.char_write_handle(0x1c, sleep_packet, True)
            adapter.stop()
            return json.dumps({"status": "success", "message": f"Command '{command}' sent successfully."}), 200
        except Exception as e:
            return json.dumps({"status": "error", "message": str(e)}), 500
    else:
        return json.dumps({"status": "error", "message": "Invalid command."})

@app.route('/put_to_sleep', methods=['POST'])
def put_to_sleep():
    try:
        global address
        adapter = pygatt.GATTToolBackend()
        adapter.start()
        device = adapter.connect(address=address, address_type=BLEAddressType.random)

        device.char_write_handle(0x15, sleep_packet, True)
        
        adapter.stop()
        return "Droid put to sleep successfully"
    except Exception as e:
        return str(e)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)