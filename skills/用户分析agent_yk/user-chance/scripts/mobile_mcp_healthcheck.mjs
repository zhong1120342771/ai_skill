#!/usr/bin/env node
import path from 'node:path';
import os from 'node:os';
import fs from 'node:fs';
import { pathToFileURL } from 'node:url';

const args = process.argv.slice(2);

function readArg(name, fallback = undefined) {
  const index = args.indexOf(name);
  if (index === -1) return fallback;
  return args[index + 1];
}

function hasArg(name) {
  return args.includes(name);
}

function usage() {
  console.log(`Usage:
  node mobile_mcp_healthcheck.mjs --device <adb-serial> [--save-to <png>] [--click x,y]

Examples:
  node mobile_mcp_healthcheck.mjs --device emulator-5554 --save-to /tmp/preflight.png
  node mobile_mcp_healthcheck.mjs --device emulator-5554 --click 430,150
`);
}

if (hasArg('--help') || hasArg('-h')) {
  usage();
  process.exit(0);
}

const device = readArg('--device', process.env.ANDROID_SERIAL);
if (!device) {
  console.error('Missing --device <adb-serial> or ANDROID_SERIAL.');
  process.exit(2);
}

const saveTo = readArg(
  '--save-to',
  path.join(os.tmpdir(), `user-chance-mcp-${Date.now()}.png`),
);
const clickArg = readArg('--click');

const home = os.homedir();
const mcpRoot = process.env.MOBILE_MCP_ROOT || path.join(home, '.codex', 'mobile-mcp');
const serverPath =
  process.env.MOBILE_MCP_SERVER ||
  path.join(mcpRoot, 'node_modules', '@mobilenext', 'mobile-mcp', 'lib', 'index.js');
const sdkClientPath = path.join(
  mcpRoot,
  'node_modules',
  '@modelcontextprotocol',
  'sdk',
  'dist',
  'esm',
  'client',
  'index.js',
);
const sdkStdioPath = path.join(
  mcpRoot,
  'node_modules',
  '@modelcontextprotocol',
  'sdk',
  'dist',
  'esm',
  'client',
  'stdio.js',
);

const { Client } = await import(pathToFileURL(sdkClientPath).href);
const { StdioClientTransport } = await import(pathToFileURL(sdkStdioPath).href);

const transport = new StdioClientTransport({
  command: process.execPath,
  args: [serverPath, '--stdio'],
  env: { ...process.env, MOBILEMCP_DISABLE_TELEMETRY: '1' },
});

const client = new Client(
  { name: 'user-chance-mobile-mcp-healthcheck', version: '1.0.0' },
  { capabilities: {} },
);

function textOf(result) {
  return result?.content?.map((item) => item.text || '').join('\n') || '';
}

function parseClick(value) {
  if (!value) return null;
  const [xRaw, yRaw] = value.split(',');
  const x = Number(xRaw);
  const y = Number(yRaw);
  if (!Number.isFinite(x) || !Number.isFinite(y)) {
    throw new Error(`Invalid --click value: ${value}. Expected x,y.`);
  }
  return { x, y };
}

function assertToolOk(toolName, text) {
  if (/not found|please fix the issue|error|failed/i.test(text)) {
    throw new Error(`${toolName} failed: ${text.slice(0, 500)}`);
  }
}

let summary;
try {
  await client.connect(transport);

  const tools = await client.listTools();
  const toolNames = tools.tools.map((tool) => tool.name);
  const required = [
    'mobile_list_available_devices',
    'mobile_get_screen_size',
    'mobile_save_screenshot',
    'mobile_list_elements_on_screen',
    'mobile_click_on_screen_at_coordinates',
  ];
  const missing = required.filter((name) => !toolNames.includes(name));
  if (missing.length > 0) {
    throw new Error(`Missing mobile-mcp tools: ${missing.join(', ')}`);
  }

  const devices = await client.callTool({
    name: 'mobile_list_available_devices',
    arguments: {},
  });
  const devicesText = textOf(devices);
  if (!devicesText.includes(device)) {
    throw new Error(`Device "${device}" not found in mobile-mcp device list: ${devicesText.slice(0, 800)}`);
  }

  const screenSize = await client.callTool({
    name: 'mobile_get_screen_size',
    arguments: { device },
  });
  const screenSizeText = textOf(screenSize);
  assertToolOk('mobile_get_screen_size', screenSizeText);

  const screenshot = await client.callTool({
    name: 'mobile_save_screenshot',
    arguments: { device, saveTo },
  });
  const screenshotText = textOf(screenshot);
  assertToolOk('mobile_save_screenshot', screenshotText);
  if (!fs.existsSync(saveTo) || fs.statSync(saveTo).size === 0) {
    throw new Error(`Screenshot was not created or is empty: ${saveTo}`);
  }

  const elements = await client.callTool({
    name: 'mobile_list_elements_on_screen',
    arguments: { device },
  });
  const elementText = textOf(elements);
  assertToolOk('mobile_list_elements_on_screen', elementText);

  const click = parseClick(clickArg);
  let clickResult = null;
  if (click) {
    clickResult = await client.callTool({
      name: 'mobile_click_on_screen_at_coordinates',
      arguments: { device, x: click.x, y: click.y },
    });
    assertToolOk('mobile_click_on_screen_at_coordinates', textOf(clickResult));
  }

  summary = {
    ok: true,
    device,
    saveTo,
    tools_checked: required,
    devices_text: devicesText.slice(0, 1200),
    screen_size_text: screenSizeText.slice(0, 500),
    screenshot_text: screenshotText.slice(0, 500),
    element_count_hint: (elementText.match(/\{"type"/g) || []).length,
    click_text: clickResult ? textOf(clickResult).slice(0, 500) : null,
  };
} catch (error) {
  summary = {
    ok: false,
    device,
    saveTo,
    error: error instanceof Error ? error.message : String(error),
  };
  process.exitCode = 1;
} finally {
  try {
    await client.close();
  } catch {
    // Ignore close errors; the summary above is the useful output.
  }
}

console.log(JSON.stringify(summary, null, 2));
