#include <core.p4>
#include <v1model.p4>
header Data { bit<32> result; }
struct H { Data h; }
struct M { }
parser P(packet_in packet, out H hdr, inout M meta, inout standard_metadata_t sm) {
    state start {  transition accept; }
}
control V(inout H hdr, inout M meta) { apply { } }
control I(inout H hdr, inout M meta, inout standard_metadata_t sm) {
    apply { hdr.h.setValid(); hash(hdr.h.result, HashAlgorithm.crc32, 32w0, { 8w0x01 }, 64w4294967296); sm.egress_spec = 0; }
}
control E(inout H hdr, inout M meta, inout standard_metadata_t sm) { apply { } }
control C(inout H hdr, inout M meta) { apply { } }
control D(packet_out packet, in H hdr) { apply { packet.emit(hdr.h); } }
V1Switch(P(), V(), I(), E(), C(), D()) main;
