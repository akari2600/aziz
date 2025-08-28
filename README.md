# TinyTuya MCP Server

An MCP (Model Context Protocol) server that provides AI control over Tuya smart home devices using the TinyTuya library. Control your smart lights, outlets, switches, and other Tuya devices through natural language with Claude or other MCP-compatible AI assistants.

## Quick Run with uvx

```bash
# Install and run in one command
uvx run tuya-mcp-server

# Or install first, then run
uvx install tuya-mcp-server
uvx run tuya-mcp-server
```

## Features

- 🏠 **Device Discovery** - Automatically scan your network for Tuya devices
- 💡 **Smart Lighting Control** - Turn lights on/off, adjust brightness, change colors
- 🔌 **Outlet Management** - Control smart plugs and outlets
- 🎛️ **Switch Control** - Manage smart switches and relays
- 🔍 **Status Monitoring** - Check device status and availability
- 🎯 **Batch Operations** - Control multiple devices simultaneously
- 🤖 **AI Integration** - Natural language control through MCP protocol

## Prerequisites

### 1. Install Dependencies

```bash
# Using uvx (recommended)
uvx install -r requirements.txt

# Or using pip
pip install -r requirements.txt
```

### 2. Set Up Your Tuya Devices

Follow the [Tuya Developer Setup Checklist](docs/tuya-setup-checklist.md) to:
- Set up devices in Smart Life app
- Create Tuya IoT Platform account
- Extract device credentials using TinyTuya wizard

### 3. Configure Devices

After running the TinyTuya wizard, you'll have a `devices.json` file with your device credentials. The server will automatically load this file on startup.

## Quick Start

### 1. Install and Set Up

```bash
# Install dependencies with uvx
uvx install -r requirements.txt

# Or install the package directly
uvx install tuya-mcp-server

# Run TinyTuya wizard to extract device credentials
python -m tinytuya wizard

# This will create devices.json with your device info
```

### 2. Run the Server

```bash
# Using uvx (recommended)
uvx run tuya-mcp-server

# Or run directly with Python
python main.py
```

### 3. Add to Claude Desktop

Add this configuration to your Claude Desktop config file:

**macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
**Windows**: `%APPDATA%/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "tuya-smart-home": {
      "command": "uvx",
      "args": ["run", "tuya-mcp-server"],
      "env": {}
    }
  }
}
```

## Available Tools

### `discover_devices`
Scan your network for Tuya devices.
```
Usage: "Scan for Tuya devices on my network"
```

### `list_devices` 
List all configured devices and their current status.
```
Usage: "Show me all my smart home devices"
```

### `get_device_status`
Get current status of a specific device.
```
Usage: "Check the status of my living room lamp"
Parameters: device_id
```

### `control_device`
Control a single device with various commands.
```
Usage: "Turn on the kitchen lights"
Parameters: device_id, command, value (optional)
Commands: turn_on, turn_off, toggle, set_brightness, set_colour, set_dps
```

### `control_multiple_devices`
Control multiple devices at once.
```
Usage: "Turn off all the bedroom lights and turn on the hallway lamp"
Parameters: operations (array of device operations)
```

## Device Commands

### Basic Control
- **Turn On**: `"Turn on the living room lamp"`
- **Turn Off**: `"Turn off all kitchen outlets"`  
- **Toggle**: `"Toggle the bedroom switch"`

### Advanced Control (for supported devices)
- **Set Brightness**: `"Set the living room lamp to 75% brightness"`
- **Change Color**: `"Make the bedroom light blue"`
- **Custom DPS**: `"Set device parameter 3 to value 250"`

### Batch Operations
- **Multiple Devices**: `"Turn on the living room lamp, turn off the kitchen outlet, and set the bedroom light to 50% brightness"`

## Example Usage

Once configured with Claude Desktop, you can use natural language:

```
User: "Turn on all my living room lights"
AI: I'll turn on the living room lights for you.
[Calls control_multiple_devices with appropriate operations]

User: "What's the status of my smart outlets?"
AI: Let me check your outlet status.
[Calls list_devices and filters for outlets]

User: "Dim the bedroom lights to 30%"
AI: I'll set your bedroom lights to 30% brightness.
[Calls control_device with set_brightness command]
```

## Configuration

### devices.json Format
The server expects a `devices.json` file (created by TinyTuya wizard) with this format:

```json
[
    {
        "id": "device_id_here",
        "name": "Living Room Lamp", 
        "ip": "192.168.1.100",
        "key": "local_key_here",
        "version": "3.3",
        "device_type": "bulb"
    }
]
```

### Device Types
- `bulb` - Smart light bulbs (supports brightness and color)
- `outlet` - Smart plugs and outlets  
- `switch` - Smart switches and relays
- `generic` - Other devices (basic on/off control)

## Troubleshooting

### "No devices.json found"
Run the TinyTuya wizard: `python -m tinytuya wizard`

### "Device not responding"  
- Check that device is on the same network
- Verify device IP address hasn't changed
- Try power cycling the device

### "Could not retrieve status"
- Device may be offline or IP changed
- Local key may have changed (re-run TinyTuya wizard)
- Check firewall settings

### Connection Issues
- Ensure devices are on same network subnet
- Check that UDP ports 6666, 6667, 7000 and TCP port 6668 are open
- Some devices only allow one connection at a time

## Development

### Project Structure
```
tuya-mcp-server/
├── src/
│   └── tuya_mcp_server.py    # Main server implementation
├── main.py                   # Entry point for uvx
├── pyproject.toml           # Project configuration
├── requirements.txt          # Python dependencies  
├── devices.json.example      # Example device configuration
└── README.md                 # This file
```

### Adding New Device Types
1. Extend `DeviceConfig` with new device type
2. Update `get_device_connection()` to handle new type
3. Add device-specific commands to `control_device()`

## Security Notes

- Device credentials contain sensitive local_key values
- Keep `devices.json` secure and don't commit to version control
- Consider network segmentation for IoT devices
- Local keys change when devices are re-paired

## License

MIT License - see LICENSE file for details.

## Contributing

Contributions welcome! Please open issues or pull requests.

## Credits

- Built with [TinyTuya](https://github.com/jasonacox/tinytuya)
- Uses [Model Context Protocol](https://modelcontextprotocol.io/)
- Inspired by the Tuya smart home ecosystem