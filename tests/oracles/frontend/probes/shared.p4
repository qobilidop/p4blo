// Two instances of a control that owns a register only through a sub-control
// keep two registers.
// The vector's expectations are P4-SpecTec's output.
#include <core.p4>
#include <v1model.p4>
header h_t { bit<8> f; bit<8> g; }
struct H { h_t h; }
struct M { }
parser P(packet_in pkt, out H hdr, inout M meta, inout standard_metadata_t sm) {
    state start { pkt.extract(hdr.h); transition accept; }
}
control B(inout bit<8> x) {
    register<bit<8>>(1) r;
    apply { bit<8> v; r.read(v, 0); v = v + 1; r.write(0, v); x = v; }
}
control A(inout bit<8> x) {
    B() b;
    apply { b.apply(x); }
}
control V(inout H hdr, inout M meta) { apply { } }
control I(inout H hdr, inout M meta, inout standard_metadata_t sm) {
    A() a1;
    A() a2;
    apply { a1.apply(hdr.h.f); a2.apply(hdr.h.g); sm.egress_spec = 1; }
}
control E(inout H hdr, inout M meta, inout standard_metadata_t sm) { apply { } }
control C(inout H hdr, inout M meta) { apply { } }
control D(packet_out pkt, in H hdr) { apply { pkt.emit(hdr.h); } }
V1Switch(P(), V(), I(), E(), C(), D()) main;
