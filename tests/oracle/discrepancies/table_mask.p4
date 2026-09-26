#include <core.p4>
#include <v1model.p4>
header Data { bit<8> key; }
struct H { Data h; }
struct M { }
parser P(packet_in packet, out H hdr, inout M meta, inout standard_metadata_t sm) {
    state start { packet.extract(hdr.h); transition accept; }
}
control V(inout H hdr, inout M meta) { apply { } }
control I(inout H hdr, inout M meta, inout standard_metadata_t sm) {
    action hit() { sm.egress_spec = 1; }
    action miss() { sm.egress_spec = 2; }
    table route {
        key = { hdr.h.key : ternary; }
        actions = { hit; miss; }
        default_action = miss;
    }
    apply { route.apply(); }
}
control E(inout H hdr, inout M meta, inout standard_metadata_t sm) { apply { } }
control C(inout H hdr, inout M meta) { apply { } }
control D(packet_out packet, in H hdr) { apply { packet.emit(hdr.h); } }
V1Switch(P(), V(), I(), E(), C(), D()) main;
