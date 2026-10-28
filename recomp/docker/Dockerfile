# Linux build and headless run environment for the Soulcalibur III recompilation (see
# recomp/README.md, "Linux (Docker) and Windows (llvm-mingw) builds"). Build it with
# --platform linux/arm64 on an Apple-silicon Mac. The repository is mounted at /src (read-only),
# the work directory at /work; build.sh finds the disc image in /src.
FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential clang cmake ninja-build pkg-config python3 git ca-certificates \
        p7zip-full rsync ccache \
        libx11-dev libxrandr-dev libxinerama-dev libxcursor-dev libxi-dev libxkbcommon-dev \
        libgl1-mesa-dev libegl1-mesa-dev libwayland-dev libvulkan-dev \
        libavcodec-dev libavformat-dev libavutil-dev libswresample-dev libswscale-dev \
    && rm -rf /var/lib/apt/lists/*

# Headless run: xvfb and Mesa's software Vulkan (lavapipe) and GL (llvmpipe); x11-apps and
# imagemagick take screenshots of the virtual display (xwd, convert).
RUN apt-get update && apt-get install -y --no-install-recommends \
        xvfb xauth x11-utils x11-apps imagemagick mesa-vulkan-drivers libgl1-mesa-dri libvulkan1 \
        vulkan-tools procps \
    && rm -rf /var/lib/apt/lists/*

ENV CC=clang CXX=clang++ CCACHE_DIR=/work/.ccache
WORKDIR /src
