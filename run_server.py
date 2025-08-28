#!/usr/bin/env python3
"""
Convenience script to run the Tuya MCP server
"""

import sys
import os
from pathlib import Path

# Add src directory to Python path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from tuya_mcp_server import main
import asyncio

if __name__ == "__main__":
    asyncio.run(main())
