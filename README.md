# Sphero R2D2 REST Interface

This project is a Flask web application that provides a RESTful interface to send commands to a Sphero R2D2 droid via Bluetooth.

## Project Structure

```
sphero-r2d2-rest-interface
├── src
│   ├── app.py            # Main entry point of the Flask application
│   └── templates
│       └── index.html    # HTML template for the web interface
├── requirements.txt       # Lists project dependencies
└── README.md              # Project documentation
```

## Setup Instructions

1. **Clone the repository:**
   ```
   git clone <repository-url>
   cd sphero-r2d2-rest-interface
   ```

2. **Install dependencies:**
   Make sure you have Python installed, then run:
   ```
   pip install -r requirements.txt
   ```

3. **Run the application:**
   ```
   python src/app.py
   ```

4. **Access the web interface:**
   Open your web browser and go to `http://127.0.0.1:5000`.

## Obtaining the Bluetooth Identifier Address

To communicate with the droid, you need to obtain its Bluetooth identifier address. Follow these steps:

1. **Install BlueZ:**
   Ensure you have the BlueZ package installed on your Linux machine. BlueZ includes tools for interacting with Bluetooth devices.

2. **Scan for BLE Devices:**
   Use `hcitool` to scan for BLE devices:
   ```
   sudo hcitool lescan
   ```
   This will list all the BLE devices the machine can see, including something like:
   ```
   E3:61:5F:C0:FF:EE D2-FFEE
   ```
   In this example, `E3:61:5F:C0:FF:EE` is the address of the droid, and `D2-FFEE` is the name of the droid. The last four digits of the name (`FFEE`) match the last four digits of the address, which helps distinguish between multiple droids of the same model.

3. **Verify the Address:**
   Once you have the address, you can use `gatttool` to interact with the droid and verify the connection:
   ```
   sudo gatttool -b E3:61:5F:C0:FF:EE --interactive
   ```
   Replace `E3:61:5F:C0:FF:EE` with the actual address of your droid.

4. **Update the Address in `app.py`:**
   Open `src/app.py` and replace the `address` variable with the Bluetooth address obtained for your droid:
   ```python
   address = 'E3:61:5F:C0:FF:EE'  # Replace with your droid's Bluetooth address
   ```

## Usage

- Use the web interface to input commands that you want to send to the droid.
- The available commands can be found in the `commandmap` dictionary within `app.py`.
- The web interface provides buttons for each command, making it easy to send commands to the droid.

## API Endpoints

### `GET /`

Renders the main web interface.

### `POST /send_command`

Sends a command to the droid. The command should be provided in the request body.

**Request Parameters:**
- `command`: The command to send to the droid. Must be one of the commands defined in the `commandmap` dictionary.

**Response:**
- `status`: "success" or "error"
- `message`: A message describing the result of the operation.

### `POST /put_to_sleep`

Puts the droid to sleep.

**Response:**
- A message indicating whether the droid was successfully put to sleep or an error message.

## License

This project is licensed under the MIT License.

## Credits

Credit to Rob Braun via [http://www.synack.net/~bbraun/spherodroid/](http://www.synack.net/~bbraun/spherodroid/)