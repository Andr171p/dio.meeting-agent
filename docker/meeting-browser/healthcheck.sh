#!/usr/bin/env bash
set -Eeuo pipefail

xdpyinfo -display "$DISPLAY" >/dev/null 2>&1

pactl info >/dev/null 2>&1

pactl list short sinks | grep -q 'meeting_output'

node -e '
const net = require("node:net");

const socket = net.createConnection({
  host: "127.0.0.1",
  port: 3000,
});

socket.on("connect", () => {
  socket.end();
  process.exit(0);
});

socket.on("error", () => process.exit(1));

socket.setTimeout(2000, () => {
  socket.destroy();
  process.exit(1);
});
'
