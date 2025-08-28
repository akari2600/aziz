#!/usr/bin/env python3
"""
TinyTuya MCP Server

An MCP server that provides AI control over Tuya smart home devices using TinyTuya.
Supports lights, outlets, switches, and other compatible Tuya devices.
"""

import asyncio
import json
import logging
import os
import sys
from typing import Any, Dict, List, Optional, Union
from pathlib import Path
import colorsys

import tinytuya
from mcp.server.models import InitializationOptions
from mcp.server import NotificationOptions, Server
from mcp.types import (
    CallToolRequest,
    CallToolResult,
    ListToolsRequest,
    ListToolsResult,
    Tool,
    TextContent,
)
from pydantic import BaseModel, Field

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DeviceConfig(BaseModel):
    """Configuration for a Tuya device"""
    device_id: str
    name: str
    ip: str
    local_key: str
    version: str = "3.3"
    device_type: str = "generic"  # outlet, bulb, switch, etc.

class TuyaDeviceManager:
    """Manages Tuya device connections and operations"""
    
    def __init__(self):
        self.devices: Dict[str, DeviceConfig] = {}
        self.device_connections: Dict[str, tinytuya.Device] = {}
        # Use absolute path to ensure we find devices.json regardless of working directory
        project_dir = Path(__file__).parent.parent  # Go up from src/ to project root
        self.config_file = project_dir / "devices.json"
        
    def rgb_to_hsv_hex(self, r: int, g: int, b: int) -> str:
        """Convert RGB (0-255) to HSV hex format for Tuya bulbs"""
        # Convert to 0-1 range
        r_norm, g_norm, b_norm = r/255.0, g/255.0, b/255.0
        
        # Convert to HSV
        h, s, v = colorsys.rgb_to_hsv(r_norm, g_norm, b_norm)
        
        # Convert to Tuya format:
        # Hue: 0-360 -> 0-1000 (scaled)
        # Saturation: 0-1 -> 0-1000 
        # Value: 0-1 -> 0-1000
        h_tuya = int(h * 360 * 1000 / 360)  # 0-1000
        s_tuya = int(s * 1000)              # 0-1000  
        v_tuya = int(v * 1000)              # 0-1000
        
        # Format as 6-byte hex: HHHHSSSSBBBB
        return f"{h_tuya:04x}{s_tuya:04x}{v_tuya:04x}"
        
    def rgb_to_workbench_hex(self, r: int, g: int, b: int) -> str:
        """Convert RGB to workbench light hex format"""
        # For workbench lights, try simple RGB hex format
        return f"ff{r:02x}{g:02x}{b:02x}00ffff"
        
    async def load_devices(self) -> None:
        """Load device configurations from devices.json"""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r') as f:
                    data = json.load(f)
                    
                # Handle TinyTuya wizard format
                for device_data in data:
                    device_config = DeviceConfig(
                        device_id=device_data["id"],
                        name=device_data.get("name", device_data["id"]),
                        ip=device_data["ip"],
                        local_key=device_data["key"],
                        version=str(device_data.get("version", "3.3"))
                    )
                    self.devices[device_config.device_id] = device_config
                    
                logger.info(f"Loaded {len(self.devices)} devices from configuration")
            else:
                logger.warning("No devices.json found. Run 'python -m tinytuya wizard' to set up devices.")
                
        except Exception as e:
            logger.error(f"Error loading device configuration: {e}")
            
    def get_device_connection(self, device_id: str) -> Optional[tinytuya.Device]:
        """Get or create a device connection"""
        if device_id not in self.devices:
            return None
            
        if device_id not in self.device_connections:
            config = self.devices[device_id]
            
            # Create appropriate device type
            if config.device_type == "bulb":
                device = tinytuya.BulbDevice(
                    config.device_id,
                    config.ip,
                    config.local_key,
                    version=float(config.version)
                )
            elif config.device_type == "outlet":
                device = tinytuya.OutletDevice(
                    config.device_id,
                    config.ip,
                    config.local_key,
                    version=float(config.version)
                )
            else:
                # Generic device for switches and other devices
                device = tinytuya.Device(
                    config.device_id,
                    config.ip,
                    config.local_key,
                    version=float(config.version)
                )
            
            # Set connection timeout
            device.set_socketTimeout(10)
            self.device_connections[device_id] = device
            
        return self.device_connections[device_id]
        
    async def discover_devices(self) -> List[Dict[str, Any]]:
        """Discover devices on the network"""
        try:
            logger.info("Scanning network for Tuya devices...")
            devices = tinytuya.deviceScan(False, 20)  # No verbose, 20 second timeout
            
            discovered = []
            for device_id, device_info in devices.items():
                discovered.append({
                    "id": device_id,
                    "ip": device_info.get("ip", "unknown"),
                    "name": device_info.get("name", f"Device_{device_id}"),
                    "version": device_info.get("version", "3.3")
                })
                
            return discovered
        except Exception as e:
            logger.error(f"Error during device discovery: {e}")
            return []
            
    async def get_device_status(self, device_id: str) -> Dict[str, Any]:
        """Get current status of a device"""
        device = self.get_device_connection(device_id)
        if not device:
            return {"error": f"Device {device_id} not found"}
            
        try:
            status = device.status()
            if status and 'dps' in status:
                return {
                    "device_id": device_id,
                    "name": self.devices[device_id].name,
                    "online": True,
                    "status": status['dps']
                }
            else:
                return {
                    "device_id": device_id,
                    "name": self.devices[device_id].name,
                    "online": False,
                    "error": "Could not retrieve status"
                }
        except Exception as e:
            return {
                "device_id": device_id,
                "name": self.devices[device_id].name,
                "online": False,
                "error": str(e)
            }
            
    async def control_device(self, device_id: str, command: str, value: Any = None) -> Dict[str, Any]:
        """Control a device with various commands"""
        device = self.get_device_connection(device_id)
        if not device:
            return {"error": f"Device {device_id} not found"}
            
        try:
            # First get current status to determine the correct DPS numbers
            status = device.status()
            if not status or 'dps' not in status:
                return {"error": "Could not get device status"}
            
            dps = status['dps']
            
            # Determine power DPS number (usually 1 or 20)
            power_dps = None
            if '1' in dps:
                power_dps = '1'
            elif '20' in dps:
                power_dps = '20'
            else:
                return {"error": "Could not determine power control DPS"}
            
            result = None
            
            if command == "turn_on":
                result = device.set_value(power_dps, True)
            elif command == "turn_off":
                result = device.set_value(power_dps, False)
            elif command == "toggle":
                current_state = dps.get(power_dps, False)
                result = device.set_value(power_dps, not current_state)
            elif command == "set_brightness":
                if value is not None:
                    # Try common brightness DPS numbers
                    brightness_dps = None
                    if '3' in dps:  # Common for some lights
                        brightness_dps = '3'
                    elif '22' in dps:  # Common for other lights
                        brightness_dps = '22'
                    elif '23' in dps:  # Another common one
                        brightness_dps = '23'
                    
                    if brightness_dps:
                        brightness_val = max(10, min(1000, int(value)))  # Scale to device range
                        result = device.set_value(brightness_dps, brightness_val)
                    else:
                        return {"error": "Device does not support brightness control"}
                else:
                    return {"error": "Brightness value required"}
            elif command == "set_color":
                if value is not None and isinstance(value, dict) and "r" in value and "g" in value and "b" in value:
                    r, g, b = int(value["r"]), int(value["g"]), int(value["b"])
                    
                    # Determine device type based on DPS structure
                    if '24' in dps:  # Merkury/Genii bulbs
                        color_hex = self.rgb_to_hsv_hex(r, g, b)
                        # Set color mode first, then color
                        device.set_value('21', 'colour')
                        result = device.set_value('24', color_hex)
                    elif '5' in dps:  # Workbench lights  
                        color_hex = self.rgb_to_workbench_hex(r, g, b)
                        result = device.set_value('5', color_hex)
                    else:
                        return {"error": "Device does not support color control"}
                else:
                    return {"error": "Color RGB values required: {'r': 255, 'g': 0, 'b': 255}"}
            elif command == "set_magenta":
                # Use the exact values from the app
                if '24' in dps:  # Merkury/Genii bulbs
                    # Set to color mode first
                    device.set_value('21', 'colour')
                    # Use Mercury magenta value (works for both brands)
                    result = device.set_value('24', '013803e803e8')
                elif '5' in dps:  # Workbench lights - need to test this
                    result = device.set_value('5', 'ff00ff0000ffff')
                else:
                    return {"error": "Device does not support color control"}
            elif command == "set_dps":
                if value is not None and isinstance(value, dict) and "dp" in value and "value" in value:
                    result = device.set_value(str(value["dp"]), value["value"])
                else:
                    return {"error": "DPS number and value required in format: {'dp': number, 'value': data}"}
            else:
                return {"error": f"Unknown command: {command}"}
                
            # Check if the command actually worked by getting new status
            new_status = device.status()
            success = new_status and 'dps' in new_status
                
            return {
                "device_id": device_id,
                "command": command,
                "result": result,
                "old_status": dps,
                "new_status": new_status.get('dps', {}) if new_status else {},
                "success": success
            }
            
        except Exception as e:
            return {
                "device_id": device_id,
                "command": command,
                "error": str(e),
                "success": False
            }

# Initialize device manager
device_manager = TuyaDeviceManager()

# Create MCP server
app = Server("tuya-mcp-server")

@app.list_tools()
async def handle_list_tools() -> list[Tool]:
    """List available tools"""
    return [
        Tool(
            name="discover_devices",
            description="Scan the network to discover Tuya devices",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            },
        ),
        Tool(
            name="list_devices",
            description="List all configured devices and their current status",
            inputSchema={
                "type": "object", 
                "properties": {},
                "required": []
            },
        ),
        Tool(
            name="get_device_status", 
            description="Get current status of a specific device",
            inputSchema={
                "type": "object",
                "properties": {
                    "device_id": {
                        "type": "string",
                        "description": "The device ID to check status for"
                    }
                },
                "required": ["device_id"]
            },
        ),
        Tool(
            name="control_device",
            description="Control a device (turn on/off, set brightness, set colors for Merkury/Genii bulbs)",
            inputSchema={
                "type": "object",
                "properties": {
                    "device_id": {
                        "type": "string", 
                        "description": "The device ID to control"
                    },
                    "command": {
                        "type": "string",
                        "description": "Command to execute",
                        "enum": ["turn_on", "turn_off", "toggle", "set_brightness", "set_color", "set_magenta", "set_dps"]
                    },
                    "value": {
                        "description": "Value for the command (brightness level, RGB color object, or DPS object)"
                    }
                },
                "required": ["device_id", "command"]
            },
        ),
        Tool(
            name="control_multiple_devices",
            description="Control multiple devices at once",
            inputSchema={
                "type": "object",
                "properties": {
                    "operations": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "device_id": {"type": "string"},
                                "command": {"type": "string"}, 
                                "value": {"type": ["number", "object", "null"]}
                            },
                            "required": ["device_id", "command"]
                        },
                        "description": "Array of device operations to perform"
                    }
                },
                "required": ["operations"]
            },
        ),
    ]

@app.call_tool()
async def handle_call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Handle tool calls"""
    
    if name == "discover_devices":
        devices = await device_manager.discover_devices()
        return [
            TextContent(
                type="text", 
                text=f"Found {len(devices)} devices on network:\n{json.dumps(devices, indent=2)}"
            )
        ]
        
    elif name == "list_devices":
        if not device_manager.devices:
            return [TextContent(
                type="text",
                text="No devices configured. Run discover_devices or set up devices.json file."
            )]
            
        device_list = []
        for device_id, config in device_manager.devices.items():
            status = await device_manager.get_device_status(device_id)
            device_list.append({
                "device_id": device_id,
                "name": config.name,
                "ip": config.ip,
                "type": config.device_type,
                "status": status
            })
            
        return [
            TextContent(
                type="text",
                text=f"Found {len(device_list)} configured devices:\n{json.dumps(device_list, indent=2)}"
            )
        ]
        
    elif name == "get_device_status":
        device_id = arguments.get("device_id")
        if not device_id:
            return [TextContent(type="text", text="Device ID is required")]
            
        status = await device_manager.get_device_status(device_id)
        return [TextContent(type="text", text=json.dumps(status, indent=2))]
        
    elif name == "control_device":
        device_id = arguments.get("device_id")
        command = arguments.get("command")
        value = arguments.get("value")
        
        if not device_id or not command:
            return [TextContent(type="text", text="Device ID and command are required")]
            
        result = await device_manager.control_device(device_id, command, value)
        return [TextContent(type="text", text=json.dumps(result, indent=2))]
        
    elif name == "control_multiple_devices":
        operations = arguments.get("operations", [])
        results = []
        
        for op in operations:
            device_id = op.get("device_id")
            command = op.get("command")
            value = op.get("value")
            
            if device_id and command:
                result = await device_manager.control_device(device_id, command, value)
                results.append(result)
                
        return [
            TextContent(
                type="text",
                text=f"Executed {len(results)} operations:\n{json.dumps(results, indent=2)}"
            )
        ]
        
    else:
        return [TextContent(type="text", text=f"Unknown tool: {name}")]

async def main():
    """Main server entry point"""
    # Load device configurations
    await device_manager.load_devices()
    
    # Run the server using stdin/stdout
    from mcp.server.stdio import stdio_server
    
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="tuya-mcp-server",
                server_version="0.1.0",
                capabilities=app.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )

def cli_main():
    """Synchronous entry point for CLI/uvx usage"""
    import asyncio
    asyncio.run(main())

if __name__ == "__main__":
    cli_main()
