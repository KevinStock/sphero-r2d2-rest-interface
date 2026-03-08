# Sphero R2D2 REST Interface

A Flask web application that provides a RESTful interface to send commands to a Sphero R2D2 droid via Bluetooth Low Energy (BLE).

Two platform-specific entry points are provided:

| File | Platform | BLE library |
|------|----------|-------------|
| `src/app.py` | **Linux** (BlueZ / gatttool) | [pygatt](https://github.com/peplin/pygatt) |
| `src/app_windows.py` | **Windows** (WinRT) | [bleak](https://github.com/hbldh/bleak) |

## Project Structure

```
sphero-r2d2-rest-interface
├── src
│   ├── app.py                # Flask app – Linux (pygatt / BlueZ)
│   ├── app_windows.py        # Flask app – Windows (bleak / WinRT)
│   └── templates
│       └── index.html        # Shared HTML template for the web interface
├── requirements.txt           # Linux dependencies
├── requirements_windows.txt   # Windows dependencies
└── README.md                  # This file
```

## Setup Instructions

### Linux

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd sphero-r2d2-rest-interface
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the application:**
   ```bash
   python src/app.py
   ```

### Windows

1. **Clone the repository:**
   ```powershell
   git clone <repository-url>
   cd sphero-r2d2-rest-interface
   ```

2. **Install dependencies:**
   ```powershell
   pip install -r requirements_windows.txt
   ```

3. **Run the application:**
   ```powershell
   python src/app_windows.py
   ```

### Access the web interface

Open your browser and go to `http://127.0.0.1:5000`.

## Configuration

The droid address and sleep-on-exit behaviour can be set via **environment variables** instead of editing source code:

| Variable | Default | Description |
|----------|---------|-------------|
| `DROID_BLE_ADDRESS` | `E2:7D:CA:55:E5:5F` | Bluetooth address of your R2-D2 droid |
| `DROID_SLEEP_ON_EXIT` | `true` | Put the droid to sleep after each command (`true`/`false`) |

Example (Linux):
```bash
DROID_BLE_ADDRESS="E3:61:5F:C0:FF:EE" python src/app.py
```

Example (Windows PowerShell):
```powershell
$env:DROID_BLE_ADDRESS = "E3:61:5F:C0:FF:EE"
python src/app_windows.py
```

## Obtaining the Bluetooth Identifier Address

### Linux (BlueZ)

1. **Install BlueZ** – ensure the BlueZ package is installed.

2. **Scan for BLE devices:**
   ```bash
   sudo hcitool lescan
   ```
   Look for an entry like:
   ```
   E3:61:5F:C0:FF:EE D2-FFEE
   ```
   `E3:61:5F:C0:FF:EE` is the address; `D2-FFEE` is the name (the last four hex digits match the address).

3. **Verify the connection (optional):**
   ```bash
   sudo gatttool -b E3:61:5F:C0:FF:EE --interactive
   ```

### Windows

Open **Settings → Bluetooth & devices**, pair the droid, then find its address
in **Device Manager → Bluetooth** properties, or use a BLE scanner app.

## Usage

- Use the web interface buttons to trigger animations, sounds, leg actions, and head rotations.
- The **Put to Sleep** button sends the droid back to sleep without waking it first.
- The **Sound Tester** section lets you cycle through animation/sound IDs 0–255.
- Available commands can also be retrieved programmatically via `GET /commands`.

## API Endpoints

### `GET /`

Renders the main web interface.

### `GET /commands`

Returns the list of available command names as JSON.

### `GET|POST /send_command`

Sends a command to the droid.

**Parameters:**
- `command` – one of the command names from `COMMAND_MAP` (query string for GET, form body for POST).

**Response (JSON):**
- `status`: `"success"` or `"error"`
- `message`: Human-readable result.

### `GET /put_to_sleep`

Puts the droid to sleep.

### `GET /test_sound?id=<0–255>`

Plays a specific animation/sound by numeric ID.

## License

This project is licensed under the MIT License.

## Credits

Credit to Rob Braun via [http://www.synack.net/~bbraun/spherodroid/](http://www.synack.net/~bbraun/spherodroid/)