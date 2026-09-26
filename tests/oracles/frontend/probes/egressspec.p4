// In egress, egress_spec reads as the port until mark_to_drop, and as 511
// after it.
// The vector's expectations are P4-SpecTec's output.
#include <core.p4>
#include <v1model.p4>
header h_t { bit<8> f; bit<8> g; }
struct H { h_t h; }
struct M { }
parser P(packet_in pkt, out H hdr, inout M meta, inout standard_metadata_t sm) {
    state start { pkt.extract(hdr.h); transition accept; }
}
control V(inout H hdr, inout M meta) { apply { } }
control I(inout H hdr, inout M meta, inout standard_metadata_t sm) { apply { sm.egress_spec = 3; } }
control E(inout H hdr, inout M meta, inout standard_metadata_t sm) {
    register<bit<8>>(1) r;
    apply {
        bit<8> v;
        if (hdr.h.f == 1) { mark_to_drop(sm); }
        r.read(v, 0);
        hdr.h.g = v;
        r.write(0, sm.egress_spec[8:1]);
    }
}
control C(inout H hdr, inout M meta) { apply { } }
control D(packet_out pkt, in H hdr) { apply { pkt.emit(hdr.h); } }
V1Switch(P(), V(), I(), E(), C(), D()) main;
