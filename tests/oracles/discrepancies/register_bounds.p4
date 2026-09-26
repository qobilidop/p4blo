#include <core.p4>
#include <v1model.p4>
header Data { bit<8> index; bit<8> result; }
struct H { Data h; }
struct M { }
parser P(packet_in packet, out H hdr, inout M meta, inout standard_metadata_t sm) {
    state start { packet.extract(hdr.h); transition accept; }
}
control V(inout H hdr, inout M meta) { apply { } }
control I(inout H hdr, inout M meta, inout standard_metadata_t sm) {
    register<bit<8>>(1) cells;
    apply { cells.read(hdr.h.result, (bit<32>) hdr.h.index); sm.egress_spec = 0; }
}
control E(inout H hdr, inout M meta, inout standard_metadata_t sm) { apply { } }
control C(inout H hdr, inout M meta) { apply { } }
control D(packet_out packet, in H hdr) { apply { packet.emit(hdr.h); } }
V1Switch(P(), V(), I(), E(), C(), D()) main;
