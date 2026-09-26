// Egress observes a fresh drop request and the selected destination.
// BMv2 resets egress_spec to 0; P4-SpecTec retains ingress value 2.
// The vector records the selected BMv2 target behavior.
#include <core.p4>
#include <v1model.p4>
header h_t { bit<8> f; bit<8> g; }
struct H { h_t h; }
struct M {  }
parser P(packet_in pkt, out H hdr, inout M meta, inout standard_metadata_t sm) {
    state start { pkt.extract(hdr.h); transition accept; }
}
control V(inout H hdr, inout M meta) { apply { } }
control I(inout H hdr, inout M meta, inout standard_metadata_t sm) { apply { mark_to_drop(sm); sm.egress_spec = 2; } }
control E(inout H hdr, inout M meta, inout standard_metadata_t sm) { apply { hdr.h.f = (bit<8>) sm.egress_spec; hdr.h.g = (bit<8>) sm.egress_port; } }
control C(inout H hdr, inout M meta) { apply { } }
control D(packet_out pkt, in H hdr) { apply { pkt.emit(hdr.h); } }
V1Switch(P(), V(), I(), E(), C(), D()) main;
