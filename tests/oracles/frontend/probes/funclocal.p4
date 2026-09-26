// An inlined function's locals and `out` parameter start at their default on
// every call, here from an action that runs twice.
// The vector's expectations are P4-SpecTec's output.
#include <core.p4>
#include <v1model.p4>
header h_t { bit<8> f; bit<8> g; }
struct H { h_t h; }
struct M { }
bit<8> count(out bit<8> o) {
    h_t tmp;
    bit<8> c;
    bit<8> seen = 0;
    if (tmp.isValid()) { seen = 0x10; }
    tmp.setValid();
    c = c + 1;
    o = o + 1;
    return seen + c;
}
parser P(packet_in pkt, out H hdr, inout M meta, inout standard_metadata_t sm) {
    state start { pkt.extract(hdr.h); transition accept; }
}
control V(inout H hdr, inout M meta) { apply { } }
control I(inout H hdr, inout M meta, inout standard_metadata_t sm) {
    bit<8> o;
    action twice() {
        hdr.h.f = hdr.h.f + count(o);
        hdr.h.g = hdr.h.g + o;
    }
    apply {
        twice();
        twice();
        sm.egress_spec = 1;
    }
}
control E(inout H hdr, inout M meta, inout standard_metadata_t sm) { apply { } }
control C(inout H hdr, inout M meta) { apply { } }
control D(packet_out pkt, in H hdr) { apply { pkt.emit(hdr.h); } }
V1Switch(P(), V(), I(), E(), C(), D()) main;
