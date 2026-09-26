# The image for p4blo's second oracle: p4c's BMv2 backend and BMv2's
# simple_switch in one Ubuntu noble image, with the simple_switch_CLI made
# runnable. Built by `docker build -t p4blo-bmv2 tests/oracles/bmv2` and driven by
# tests/oracles/bmv2/run.py; see tests/oracles/bmv2/README.md.
#
# Both sources are github.com/qobilidop/p4lang-builds images, pinned by the
# digest of their multi-architecture index (native amd64 and arm64 both
# work). The bmv2 image ships simple_switch and the simple_switch_CLI
# wrapper but no Python, so the CLI's modules (bm_runtime, sswitch_runtime,
# runtime_CLI, sswitch_CLI, bmpy_utils) are absent: they are generated here
# from the pinned BMv2 source tarball with Ubuntu's thrift compiler, whose
# 0.19.0 matches the libthrift the switch links against.

# ghcr.io/qobilidop/p4lang-builds/p4c:1.2.5.15-noble
FROM ghcr.io/qobilidop/p4lang-builds/p4c@sha256:794edb1682e286792fbf7b1ca5da2ed7be52ddbeab3659a3bbfb4e1906684e48

LABEL org.opencontainers.image.description="p4blo's BMv2 oracle: p4c-bm2-ss 1.2.5.15 with simple_switch 1.15.4" \
      p4blo.p4c.image="ghcr.io/qobilidop/p4lang-builds/p4c@sha256:794edb1682e286792fbf7b1ca5da2ed7be52ddbeab3659a3bbfb4e1906684e48" \
      p4blo.bmv2.image="ghcr.io/qobilidop/p4lang-builds/bmv2@sha256:3c70f7516440e36a217a7685364a1d1ffb766d0965ab3fbd549f8bbaf7c3cc9d" \
      p4blo.bmv2.source="https://github.com/p4lang/behavioral-model/archive/refs/tags/1.15.4.tar.gz"

ENV DEBIAN_FRONTEND=noninteractive

# The runtime libraries the bmv2 image's final stage installs (its
# bmv2/Dockerfile), plus the thrift compiler and Python bindings for the CLI.
RUN apt-get update && apt-get install -y --no-install-recommends \
      libgmp-dev libpcap-dev libjudy-dev libevent-dev libssl-dev \
      libxxhash-dev libjsoncpp-dev libthrift-dev \
      libboost-program-options-dev libboost-system-dev \
      libboost-filesystem-dev libboost-thread-dev \
      thrift-compiler python3-thrift \
 && rm -rf /var/lib/apt/lists/*

# ghcr.io/qobilidop/p4lang-builds/bmv2:1.15.4-noble
COPY --from=ghcr.io/qobilidop/p4lang-builds/bmv2@sha256:3c70f7516440e36a217a7685364a1d1ffb766d0965ab3fbd549f8bbaf7c3cc9d /usr/local /usr/local
RUN ldconfig

# The CLI's Python modules, generated from the pinned source. The tarball's
# checksum is the one recorded on 2026-09-22.
ADD --checksum=sha256:c6236ed842fbb5d2d31a2f49a2b2d6863e858c413178a59963f34b6a1cbe0bd7 \
    https://github.com/p4lang/behavioral-model/archive/refs/tags/1.15.4.tar.gz /tmp/bmv2.tar.gz
RUN set -eu; \
    site=/usr/local/lib/python3.12/dist-packages; \
    mkdir -p "$site" /tmp/bmv2; \
    tar -xzf /tmp/bmv2.tar.gz -C /tmp/bmv2 --strip-components=1; \
    cd /tmp/bmv2; \
    for idl in thrift_src/standard.thrift thrift_src/simple_pre.thrift \
               thrift_src/simple_pre_lag.thrift \
               targets/simple_switch/thrift/simple_switch.thrift; do \
      thrift -o /tmp/bmv2 --gen py "$idl"; \
    done; \
    cp -r gen-py/bm_runtime gen-py/sswitch_runtime "$site/"; \
    cp tools/runtime_CLI.py tools/bmpy_utils.py \
       targets/simple_switch/sswitch_CLI.py "$site/"; \
    rm -rf /tmp/bmv2 /tmp/bmv2.tar.gz

# The driver run.py talks to over stdin/stdout (see its docstring).
COPY driver.py /usr/local/lib/p4blo/driver.py
RUN printf '#!/bin/sh\nexec python3 /usr/local/lib/p4blo/driver.py "$@"\n' \
      > /usr/local/bin/p4blo-bmv2-driver \
 && chmod +x /usr/local/bin/p4blo-bmv2-driver

# Self-describing: every tool the oracle needs answers.
RUN p4c-bm2-ss --version && simple_switch --version \
 && simple_switch_CLI --help > /dev/null && p4blo-bmv2-driver --version
