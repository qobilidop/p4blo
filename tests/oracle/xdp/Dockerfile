# Compile and inspect the pinned original program; never load it into a kernel.
FROM ubuntu:24.04@sha256:008173c23f95b170204355c12626cb5a965d779a7e1283b09e9cffbb1bf33ca3 AS base

# Bootstrap authenticated HTTPS without a floating package installation.
ADD --chmod=0644 --checksum=sha256:f66dff1bdf8f96060b8177976f8b7d9254bc89bc4db933d769f7384d28480bc9 \
    https://curl.se/ca/cacert-2026-08-13.pem /etc/ssl/certs/ca-certificates.crt
COPY ubuntu.sources /etc/apt/sources.list.d/ubuntu.sources
# Remote ADD also applies its mode to newly created parents. The unprivileged
# apt downloader must be able to traverse these public certificate directories.
RUN chmod 0755 /etc/ssl /etc/ssl/certs
# Every package operation uses the same immutable archive view, not latest apt.
FROM base AS build
RUN apt-get -o Acquire::https::CaInfo=/etc/ssl/certs/ca-certificates.crt update --error-on=any && \
    DEBIAN_FRONTEND=noninteractive apt-get -o Acquire::https::CaInfo=/etc/ssl/certs/ca-certificates.crt install \
      --no-install-recommends -y ca-certificates clang-18 llvm-18 \
      linux-libc-dev gcc make libelf-dev zlib1g-dev pkg-config

ADD --checksum=sha256:b83d1a74deacf2ba48ee50798bb38a389ddda402967413c6c2ad1389daed3c16 \
    https://codeload.github.com/xdp-project/xdp-tools/tar.gz/f27ea2a83fd4fcce8968f627b25493950aaf5c44 /opt/archives/xdp-tools.tar.gz
ADD --checksum=sha256:f94a66ab80e79aa11e15409479d8bc2572649f0ef25dbd2daf503ea5b05067ad \
    https://codeload.github.com/libbpf/libbpf/tar.gz/09b9e83102eb8ab9e540d36b4559c55f3bcdb95d /opt/archives/libbpf.tar.gz
RUN mkdir -p /opt/src/xdp-tools /opt/src/libbpf /opt/bpf-headers/bpf /opt/artifacts && \
    tar -xzf /opt/archives/xdp-tools.tar.gz --strip-components=1 -C /opt/src/xdp-tools && \
    tar -xzf /opt/archives/libbpf.tar.gz --strip-components=1 -C /opt/src/libbpf && \
    cp /opt/src/libbpf/src/bpf_helpers.h /opt/src/libbpf/src/bpf_helper_defs.h \
      /opt/src/libbpf/src/bpf_endian.h /opt/bpf-headers/bpf/
COPY build.sh inspect.c /opt/
RUN sh /opt/build.sh

FROM base AS runtime
RUN apt-get -o Acquire::https::CaInfo=/etc/ssl/certs/ca-certificates.crt update --error-on=any && \
    DEBIAN_FRONTEND=noninteractive apt-get -o Acquire::https::CaInfo=/etc/ssl/certs/ca-certificates.crt install \
      --no-install-recommends -y ca-certificates python3 llvm-18 strace libelf1t64 && \
    apt-get clean && find /var/lib/apt/lists -type f -delete
# Preserve unchanged upstream sources and license notices with the object.
COPY --from=build /opt/src /opt/src
COPY --from=build /opt/archives /opt/archives
COPY --from=build /opt/artifacts /opt/artifacts
COPY --from=build /opt/inspect /opt/inspect
COPY check.py check_tests.py /opt/
USER 65534:65534
CMD ["python3", "/opt/check.py"]
