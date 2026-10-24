#!/usr/bin/env bash
set -Eeuo pipefail

export DISPLAY="${DISPLAY:-:99}"
export XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/tmp/meeting-runtime}"

mkdir -p "$XDG_RUNTIME_DIR" /recordings
chmod 700 "$XDG_RUNTIME_DIR"

XVFB_PID=""
PULSE_PID=""
BROWSER_PID=""

cleanup() {
    trap - EXIT INT TERM

    for pid in "$BROWSER_PID" "$PULSE_PID" "$XVFB_PID"; do
        if [[ -n "$pid" ]]; then
            kill "$pid" 2>/dev/null || true
        fi
    done

    wait || true
}

trap cleanup EXIT
trap 'exit 143' TERM
trap 'exit 130' INT

echo "[meeting-browser] Starting Xvfb..."

Xvfb "$DISPLAY" \
    -screen 0 \
    "${BROWSER_SCREEN_WIDTH:-1920}x${BROWSER_SCREEN_HEIGHT:-1080}x${BROWSER_SCREEN_DEPTH:-24}" \
    -nolisten tcp \
    +extension RANDR &

XVFB_PID=$!

for i in {1..50}; do
    if xdpyinfo -display "$DISPLAY" >/dev/null 2>&1; then
        break
    fi
    sleep 0.2
done

xdpyinfo -display "$DISPLAY" >/dev/null

echo "[meeting-browser] Starting PulseAudio..."

pulseaudio \
    --daemonize=no \
    --exit-idle-time=-1 \
    --disallow-exit \
    --log-target=stderr \
    -n \
    -F /opt/meeting-browser/pulse.pa &

PULSE_PID=$!

for i in {1..50}; do
    if pactl info >/dev/null 2>&1; then
        break
    fi
    sleep 0.2
done

pactl info >/dev/null

pactl set-default-sink meeting_output
pactl set-default-source meeting_microphone.monitor

echo "[meeting-browser] Starting Playwright Server..."

node /opt/meeting-browser/server.mjs &

BROWSER_PID=$!

wait "$BROWSER_PID"
