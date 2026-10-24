import { chromium } from 'playwright';

const wsPath = process.env.BROWSER_WS_PATH;

if (!wsPath?.startsWith('/ws/') || wsPath.length < 32) {
  throw new Error('BROWSER_WS_PATH must be a long /ws/... path');
}

const browserServer = await chromium.launchServer({
  headless: false,

  host: '0.0.0.0',
  port: 3000,
  wsPath,

  chromiumSandbox: false,

  ignoreDefaultArgs: [
    '--mute-audio',
  ],

  args: [
    `--autoplay-policy=${
      process.env.BROWSER_AUTOPLAY_POLICY ??
      'no-user-gesture-required'
    }`,
  ],
});

console.log('Meeting Browser Server is ready');

let stopping = false;

async function shutdown() {
  if (stopping) return;

  stopping = true;

  try {
    await browserServer.close();
  } finally {
    process.exit(0);
  }
}

process.once('SIGINT', shutdown);
process.once('SIGTERM', shutdown);
