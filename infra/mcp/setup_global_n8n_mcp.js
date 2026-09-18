const fs = require('fs');
const path = require('path');

const targetPath = 'C:\\Users\\Lenovo\\.gemini\\antigravity-ide\\mcp\\n8n\\n8n_proxy.js';
const dir = path.dirname(targetPath);
if (!fs.existsSync(dir)) {
  fs.mkdirSync(dir, { recursive: true });
}

const proxyContent = `#!/usr/bin/env node
const readline = require('readline');

const ENDPOINT = process.env.N8N_MCP_URL || 'https://n8n-production-0277a.up.railway.app/mcp-server/http';
const TOKEN = process.env.N8N_MCP_TOKEN || '';

const rl = readline.createInterface({
  input: process.stdin,
  output: process.stdout,
  terminal: false
});

rl.on('line', async (line) => {
  line = line.trim();
  if (!line) return;
  
  let msg;
  try {
    msg = JSON.parse(line);
  } catch (err) {
    return;
  }

  if (msg.id === undefined && msg.method !== 'notifications/initialized') return;

  try {
    const headers = {
      'Content-Type': 'application/json',
      'Accept': 'application/json, text/event-stream'
    };
    if (TOKEN) {
      headers['Authorization'] = 'Bearer ' + TOKEN;
    }

    const res = await fetch(ENDPOINT, {
      method: 'POST',
      headers,
      body: JSON.stringify(msg)
    });

    const text = await res.text();
    let responseJson = null;
    const lines = text.split('\\n');
    for (const l of lines) {
      if (l.startsWith('data: ')) {
        try {
          responseJson = JSON.parse(l.slice(6));
          break;
        } catch (e) {}
      }
    }

    if (!responseJson) {
      try {
        responseJson = JSON.parse(text);
      } catch (e) {
        responseJson = {
          jsonrpc: '2.0',
          id: msg.id,
          error: { code: -32603, message: text || 'Invalid response' }
        };
      }
    }

    if (responseJson && responseJson.id === undefined) responseJson.id = msg.id;
    if (responseJson && !responseJson.jsonrpc) responseJson.jsonrpc = '2.0';

    process.stdout.write(JSON.stringify(responseJson) + '\\n');
  } catch (error) {
    process.stdout.write(JSON.stringify({
      jsonrpc: '2.0',
      id: msg.id,
      error: { code: -32603, message: error.message }
    }) + '\\n');
  }
});
`;

fs.writeFileSync(targetPath, proxyContent, 'utf8');
console.log('n8n_proxy.js criado com sucesso em:', targetPath);

// 1. Atualizar C:\Users\Lenovo\.gemini\config\mcp_config.json (Antigravity Global)
const mcpConfigPath = 'C:\\Users\\Lenovo\\.gemini\\config\\mcp_config.json';
if (fs.existsSync(mcpConfigPath)) {
  const mcpConfig = JSON.parse(fs.readFileSync(mcpConfigPath, 'utf8'));
  mcpConfig.mcpServers = mcpConfig.mcpServers || {};
  mcpConfig.mcpServers.n8n = {
    command: 'node',
    args: [targetPath],
    env: {
      N8N_MCP_URL: 'https://n8n-production-0277a.up.railway.app/mcp-server/http',
      N8N_MCP_TOKEN: process.env.N8N_MCP_TOKEN || ''
    }
  };
  fs.writeFileSync(mcpConfigPath, JSON.stringify(mcpConfig, null, 2), 'utf8');
  console.log('Antigravity global (mcp_config.json) atualizado!');
}

// 2. Atualizar C:\Users\Lenovo\.claude.json (Claude Code Global)
const claudePath = 'C:\\Users\\Lenovo\\.claude.json';
if (fs.existsSync(claudePath)) {
  const claudeConfig = JSON.parse(fs.readFileSync(claudePath, 'utf8'));
  claudeConfig.mcpServers = claudeConfig.mcpServers || {};
  claudeConfig.mcpServers.n8n = {
    type: 'http',
    url: 'https://n8n-production-0277a.up.railway.app/mcp-server/http'
  };
  if (process.env.N8N_MCP_TOKEN) {
    claudeConfig.mcpServers.n8n.headers = {
      Authorization: 'Bearer ' + process.env.N8N_MCP_TOKEN
    };
  }
  fs.writeFileSync(claudePath, JSON.stringify(claudeConfig, null, 2), 'utf8');
  console.log('Claude Code (.claude.json) atualizado!');
}

// 3. Atualizar C:\Users\Lenovo\.codex\config.toml (Codex Global)
const codexPath = 'C:\\Users\\Lenovo\\.codex\\config.toml';
if (fs.existsSync(codexPath)) {
  let toml = fs.readFileSync(codexPath, 'utf8');
  const escapedProxy = targetPath.replace(/\\/g, '\\\\');
  if (!toml.includes('[mcp_servers.n8n]')) {
    toml += `\n[mcp_servers.n8n]\ncommand = "node"\nargs = ["${escapedProxy}"]\n`;
    fs.writeFileSync(codexPath, toml, 'utf8');
    console.log('Codex (config.toml) atualizado!');
  } else {
    console.log('Codex config.toml já possui [mcp_servers.n8n]');
  }
}
