// mark_to_drop writes 511 to egress_spec, which a later read sees; a later
// write of a port undoes the drop.
// The vector's expectations are P4-SpecTec's output.
#include <core.p4>
#include <v1model.p4>
header h_t { bit<8> f; bit<8> g; }
struct H { h_t h; }
struct M {  }
parser P(packet_in pkt, out H hdr, inout M meta, inout standard_metadata_t sm) {
    state start { pkt.extract(hdr.h); transition accept; }
}
control V(inout H hdr, inout M meta) { apply { } }
control I(inout H hdr, inout M meta, inout standard_metadata_t sm) { apply { mark_to_drop(sm); hdr.h.f = (bit<8>)(sm.egress_spec >> 1); sm.egress_spec = 1; } }
control E(inout H hdr, inout M meta, inout standard_metadata_t sm) {  apply {  } }
control C(inout H hdr, inout M meta) { apply { } }
control D(packet_out pkt, in H hdr) { apply { pkt.emit(hdr.h); } }
V1Switch(P(), V(), I(), E(), C(), D()) main;
