# Model Context Protocol (MCP) Server Development Primer

## Introduction

The Model Context Protocol (MCP) is an open standard created by Anthropic that provides a universal communication layer between AI models and external services. Think of it as "USB-C for AI" - a standardized way for Large Language Models (LLMs) to interact with tools, data sources, and APIs without requiring custom integrations for each AI-service pair.

## Core Concepts

### Architecture Overview

MCP follows a client-server architecture with three key layers:

1. **Host Applications** - The AI interface (Claude Desktop, VS Code, custom apps)
2. **MCP Clients** - Built into host applications, maintain 1:1 connections with servers
3. **MCP Servers** - Lightweight services that expose capabilities to AI models

### The Three Primitives

MCP servers expose functionality through three core primitives:

#### 1. Tools
- **Purpose**: Executable functions that AI models can invoke
- **Control**: Model-controlled (the AI decides when to call them)
- **Use Cases**: API calls, calculations, data processing, system operations
- **Example**: A tool to convert a document, check weather, or query a database

#### 2. Resources
- **Purpose**: Structured data sources accessible via URIs
- **Control**: Application-controlled (defined by the server)
- **Access**: Read-only by design
- **Use Cases**: File contents, database records, API responses, document data
- **Example**: `myapp://documents/123` returning document metadata

#### 3. Prompts
- **Purpose**: Reusable message templates with parameters
- **Control**: User-controlled (selected/triggered by users)
- **Use Cases**: Complex workflows, multi-step operations, standardized queries
- **Example**: "Analyze document and extract key insights" template

### Communication Protocol

MCP uses JSON-RPC 2.0 for all communications:

- **Transport Options**:
  - **stdio** (local servers) - Communication via standard input/output
  - **HTTP + SSE** (remote servers) - HTTP for requests, Server-Sent Events for server-initiated messages

- **Message Flow**:
  1. **Initialization** - Client and server negotiate capabilities
  2. **Operation** - Actual work (tool calls, resource access, prompt execution)  
  3. **Shutdown** - Graceful connection closure

## TypeScript SDK Fundamentals

### Installation

```bash
npm install @modelcontextprotocol/sdk
npm install zod  # For schema validation
```

### Basic Server Structure

```typescript
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { z } from "zod";

// Create server instance
const server = new McpServer({
  name: "my-mcp-server",
  version: "1.0.0"
});

// Register a tool
server.registerTool(
  "my-tool",
  {
    title: "My Tool",
    description: "Does something useful",
    inputSchema: z.object({
      input: z.string()
    }).strict()
  },
  async ({ input }) => {
    // Tool implementation
    return {
      content: [{
        type: "text",
        text: `Processed: ${input}`
      }]
    };
  }
);

// Start the server
async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
}

main().catch(console.error);
```

### Key Patterns

#### Error Handling
```typescript
server.onerror = (error) => {
  console.error("Server error:", error);
  // Don't exit - let MCP handle reconnection
};
```

#### Session Management
MCP servers can be stateless or stateful. For stateful operations:
```typescript
const sessions = new Map();

server.registerTool("start-session", {
  // ... schema
}, async ({ sessionId }) => {
  sessions.set(sessionId, { 
    created: Date.now(),
    data: {} 
  });
  // ...
});
```

## Resource Implementation

Resources provide structured data access:

```typescript
import { ResourceTemplate } from "@modelcontextprotocol/sdk";

server.registerResource(
  "document-data",
  new ResourceTemplate("myapp://doc/{docId}", {
    list: undefined  // For listing support
  }),
  {
    title: "Document Data",
    description: "Access document information"
  },
  async (uri, { docId }) => {
    const data = await fetchDocumentData(docId);
    return {
      contents: [{
        uri: uri.href,
        mimeType: "application/json",
        text: JSON.stringify(data, null, 2)
      }]
    };
  }
);
```

## Testing and Development

### MCP Inspector

The primary development tool for testing MCP servers:

```bash
npm install -g @modelcontextprotocol/inspector
npx @modelcontextprotocol/inspector build/index.js
```

Features:
- Interactive web UI for testing all capabilities
- Real-time protocol message viewing
- Tool invocation with parameter validation
- Resource browsing with URI exploration

### Claude Desktop Integration

Configure your server in Claude Desktop settings:

```json
{
  "mcpServers": {
    "my-server": {
      "command": "node",
      "args": ["/path/to/build/index.js"],
      "env": {
        "API_KEY": "your_api_key"
      }
    }
  }
}
```

### Debugging Best Practices

1. **Structured Logging**:
```typescript
const logger = {
  info: (msg: string, data?: any) => 
    console.error(`[INFO] ${msg}`, data ? JSON.stringify(data) : ''),
  error: (msg: string, error?: Error) => 
    console.error(`[ERROR] ${msg}`, error?.stack || '')
};
```

2. **Environment-based Debugging**:
```typescript
const DEBUG = process.env.NODE_ENV === 'development';
if (DEBUG) {
  console.error('[DEBUG]', data);
}
```

## Advanced Patterns

### Long-Running Operations

For operations that take time (like file conversions):

```typescript
const tasks = new Map();

server.registerTool("start-task", {
  // ... schema
}, async ({ input }) => {
  const taskId = generateId();
  tasks.set(taskId, { 
    status: "running",
    progress: 0 
  });
  
  // Start async operation
  processAsync(taskId, input);
  
  return {
    content: [{
      type: "text",
      text: `Task started: ${taskId}`
    }]
  };
});

server.registerTool("check-status", {
  // ... schema
}, async ({ taskId }) => {
  const task = tasks.get(taskId);
  return {
    content: [{
      type: "text",
      text: JSON.stringify(task)
    }]
  };
});
```

### Rate Limiting and Retries

Implement exponential backoff for external API calls:

```typescript
async function callWithRetry(fn, maxRetries = 3) {
  for (let i = 0; i < maxRetries; i++) {
    try {
      return await fn();
    } catch (error) {
      if (i === maxRetries - 1) throw error;
      const delay = Math.min(1000 * Math.pow(2, i), 10000);
      await new Promise(r => setTimeout(r, delay));
    }
  }
}
```

## Production Considerations

### Security
- Always validate input with Zod schemas
- Sanitize data before external API calls
- Use environment variables for sensitive configuration
- Implement proper authentication for HTTP transport

### Performance
- Cache frequently accessed data
- Implement connection pooling for databases
- Use streaming for large data transfers
- Monitor memory usage in long-running servers

### Error Recovery
- Graceful degradation when external services fail
- Clear error messages for debugging
- Automatic reconnection handling
- State persistence for critical data

## Best Practices

1. **Single Responsibility**: Each tool should do one thing well
2. **Clear Naming**: Use descriptive names for tools and resources
3. **Comprehensive Descriptions**: Help AI models understand capabilities
4. **Consistent Schemas**: Use TypeScript types and Zod for validation
5. **Idempotent Operations**: Design tools to be safely retryable
6. **Progressive Disclosure**: Start simple, add complexity as needed

## Common Pitfalls

1. **Not handling rate limits** - Always implement retry logic
2. **Blocking operations** - Use async/await properly
3. **Missing error boundaries** - Wrap operations in try-catch
4. **State management issues** - Be careful with shared state
5. **Inadequate logging** - Log enough to debug production issues

## Further Reading

- **Official Documentation**: https://modelcontextprotocol.io/docs/getting-started/intro
- **TypeScript SDK**: https://github.com/modelcontextprotocol/typescript-sdk
- **MCP Specification**: https://modelcontextprotocol.io/specification
- **Example Servers**: https://github.com/modelcontextprotocol/servers
- **Community Resources**: https://github.com/punkpeye/awesome-mcp-servers

## Quick Reference

### Package.json Setup
```json
{
  "name": "my-mcp-server",
  "type": "module",
  "scripts": {
    "build": "tsc",
    "dev": "tsx src/index.ts",
    "inspector": "npx @modelcontextprotocol/inspector dist/index.js"
  },
  "dependencies": {
    "@modelcontextprotocol/sdk": "^1.0.0",
    "zod": "^3.0.0"
  }
}
```

### TypeScript Config
```json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "NodeNext",
    "moduleResolution": "NodeNext",
    "strict": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "forceConsistentCasingInFileNames": true
  }
}
```

This primer provides the foundation for building MCP servers. The protocol's simplicity and standardization make it straightforward to expose any capability to AI models in a consistent, reusable way.