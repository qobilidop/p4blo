#!/bin/sh
set -eu

multiarch=$(gcc -dumpmachine)
compile() {
clang-18 --target=bpfel -O2 -g -std=gnu2x -fno-stack-protector \
  -Wall -Werror -Wno-unused-value -Wno-pointer-sign \
  -Wno-compare-distinct-pointer-types -Wno-visibility \
  -I/opt/src/xdp-tools/headers -I/opt/bpf-headers \
  -I"/usr/include/$multiarch" \
  -ffile-prefix-map=/opt/src=/src -fdebug-prefix-map=/opt/src=/src \
  -MD -MF /opt/artifacts/xdpfilt_alw_eth.d \
  -c /opt/src/xdp-tools/xdp-filter/xdpfilt_alw_eth.c \
  -o "$1"
}
compile /opt/artifacts/xdpfilt_alw_eth.o
compile /opt/artifacts/xdpfilt_alw_eth.repeat.o
cmp /opt/artifacts/xdpfilt_alw_eth.o /opt/artifacts/xdpfilt_alw_eth.repeat.o
sha256sum /opt/artifacts/xdpfilt_alw_eth.o > /opt/artifacts/object.sha256
llvm-readelf-18 --all /opt/artifacts/xdpfilt_alw_eth.o > /opt/artifacts/readelf.txt
llvm-objdump-18 --disassemble /opt/artifacts/xdpfilt_alw_eth.o > /opt/artifacts/disassembly.txt
dpkg-query -W -f='${Package}=${Version}\n' > /opt/artifacts/build-packages.txt
clang-18 --version > /opt/artifacts/compiler.txt
printf '%s\n' "$multiarch" > /opt/artifacts/build-multiarch.txt
cp /opt/build.sh /opt/inspect.c /opt/artifacts/
make -C /opt/src/libbpf/src BUILD_STATIC_ONLY=1 OBJDIR=/opt/libbpf-build
gcc -std=c11 -Wall -Wextra -Werror -I/opt/src/libbpf/src \
  /opt/inspect.c /opt/libbpf-build/libbpf.a -lelf -lz -o /opt/inspect
/opt/inspect /opt/artifacts/xdpfilt_alw_eth.o
