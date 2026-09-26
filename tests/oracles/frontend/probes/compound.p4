// Compound assignment: with a side-effecting call, into a slice, and shifts
// by an unsized amount, including one at least the width.
// The vector's expectations are P4-SpecTec's output.
#include <core.p4>
#include <v1model.p4>
header h_t { bit<8> f; bit<8> g; bit<8> k; bit<8> s; bit<4> n; bit<4> m; }
struct H { h_t h; }
struct M { }
bit<8> bump(inout bit<8> v) { v = v + 10; return 1; }
parser P(packet_in pkt, out H hdr, inout M meta, inout standard_metadata_t sm) {
    state start { pkt.extract(hdr.h); transition accept; }
}
control V(inout H hdr, inout M meta) { apply { } }
control I(inout H hdr, inout M meta, inout standard_metadata_t sm) {
    apply {
        hdr.h.f += bump(hdr.h.f);
        hdr.h.g |= 8w0x40;
        hdr.h.k[3:0] += (bit<4>) bump(hdr.h.k);
        hdr.h.s <<= 2;
        hdr.h.s >>= 1;
        hdr.h.n <<= 20;
        hdr.h.m >>= 1;
        hdr.h.s[7:4] <<= 1;
        sm.egress_spec = 1;
    }
}
control E(inout H hdr, inout M meta, inout standard_metadata_t sm) { apply { } }
control C(inout H hdr, inout M meta) { apply { } }
control D(packet_out pkt, in H hdr) { apply { pkt.emit(hdr.h); } }
V1Switch(P(), V(), I(), E(), C(), D()) main;
