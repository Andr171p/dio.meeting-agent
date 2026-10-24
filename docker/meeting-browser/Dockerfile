ARG PLAYWRIGHT_VERSION=1.64.0

FROM mcr.microsoft.com/playwright:v${PLAYWRIGHT_VERSION}-noble

ARG PLAYWRIGHT_VERSION

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        xvfb \
        x11-utils \
        pulseaudio \
        pulseaudio-utils \
        libasound2-plugins \
        ffmpeg \
        fonts-noto-core \
        fonts-noto-color-emoji \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /opt/meeting-browser

RUN npm install \
        --prefix /opt/meeting-browser \
        --omit=dev \
        --no-audit \
        --no-fund \
        "playwright@${PLAYWRIGHT_VERSION}" \
    && mkdir -p /recordings \
    && chown -R pwuser:pwuser \
        /opt/meeting-browser \
        /recordings

COPY --chown=pwuser:pwuser \
    docker/meeting-browser/ \
    /opt/meeting-browser/

RUN chmod +x \
    /opt/meeting-browser/entrypoint.sh \
    /opt/meeting-browser/healthcheck.sh

USER pwuser

ENV XDG_RUNTIME_DIR=/tmp/meeting-runtime \
    PULSE_SERVER=unix:/tmp/meeting-runtime/pulse/native

ENTRYPOINT ["/opt/meeting-browser/entrypoint.sh"]
