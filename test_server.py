#!/usr/bin/env python3
"""
Test script for the Tuya MCP server

This script helps verify that the server is working correctly by testing
basic functionality without requiring a full MCP client.
"""

import asyncio
import sys
from pathlib import Path

# Add src directory to Python path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from tuya_mcp_server import TuyaDeviceManager

async def test_device_manager():
    """Test the TuyaDeviceManager functionality"""
    print("🧪 Testing TinyTuya MCP Server")
    print("=" * 40)
    
    # Initialize device manager
    manager = TuyaDeviceManager()
    
    # Test 1: Load devices
    print("\n📂 Test 1: Loading device configuration...")
    await manager.load_devices()
    
    if manager.devices:
        print(f"✅ Found {len(manager.devices)} configured devices:")
        for device_id, config in manager.devices.items():
            print(f"   - {config.name} ({device_id}) at {config.ip}")
    else:
        print("⚠️  No devices found in configuration.")
        print("   Run 'python -m tinytuya wizard' to set up devices.json")
        
    # Test 2: Device discovery (optional, can be slow)
    print("\n🔍 Test 2: Network device discovery (optional)...")
    print("   This may take 20+ seconds. Press Ctrl+C to skip.")
    
    try:
        discovered = await manager.discover_devices()
        if discovered:
            print(f"✅ Discovered {len(discovered)} devices on network:")
            for device in discovered[:3]:  # Show first 3
                print(f"   - {device['name']} ({device['id']}) at {device['ip']}")
            if len(discovered) > 3:
                print(f"   ... and {len(discovered) - 3} more")
        else:
            print("⚠️  No devices discovered on network.")
            print("   Make sure devices are powered on and connected to WiFi.")
    except KeyboardInterrupt:
        print("⏭️  Discovery skipped by user.")
    except Exception as e:
        print(f"❌ Discovery failed: {e}")
        
    # Test 3: Device status check (if we have devices)
    if manager.devices:
        print(f"\n📊 Test 3: Checking status of configured devices...")
        for device_id, config in list(manager.devices.items())[:2]:  # Test first 2 devices
            print(f"   Checking {config.name}...")
            status = await manager.get_device_status(device_id)
            
            if status.get('online'):
                print(f"   ✅ {config.name} is online")
                if 'status' in status:
                    dps = status['status']
                    print(f"      Status: {dps}")
            else:
                print(f"   ❌ {config.name} is offline or unreachable")
                if 'error' in status:
                    print(f"      Error: {status['error']}")
    
    print("\n🎉 Testing complete!")
    print("\nNext steps:")
    print("1. If no devices found, run: python -m tinytuya wizard")
    print("2. Install dependencies: pip install -r requirements.txt")
    print("3. Test MCP server: python run_server.py")
    print("4. Add to Claude Desktop config as shown in README.md")

if __name__ == "__main__":
    try:
        asyncio.run(test_device_manager())
    except KeyboardInterrupt:
        print("\n\n⏹️  Testing interrupted by user.")
    except Exception as e:
        print(f"\n\n❌ Testing failed: {e}")
        sys.exit(1)
