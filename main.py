#!/usr/bin/env python3
"""
Main entry point for the TinyTuya MCP Server
Designed to work with uvx for easy execution
"""

import sys
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from tuya_mcp_server import main
import asyncio

if __name__ == "__main__":
    asyncio.run(main())
