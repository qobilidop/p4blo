// Portable BMv2 staged witness; VerifyChecksum intentionally empty.
#include <core.p4>
#include <v1model.p4>
header H_t { bit<32> trace; bit<8> mode; bit<8> port; bit<8> e; bit<16> checksum; }
header Trailer { bit<8> value; }
struct H { H_t h; Trailer trailer; }
struct M { }
register<bit<8>>(1) egress_count;
parser P(packet_in pkt, out H hdr, inout M meta, inout standard_metadata_t sm) {
    state start { pkt.extract(hdr.h); hdr.h.trace = 1; transition accept; }
}
control V(inout H hdr, inout M meta) { apply { } }
control I(inout H hdr, inout M meta, inout standard_metadata_t sm) {
    apply {
        hdr.h.trace = (hdr.h.trace << 4) | 3;
        hdr.trailer.setValid(); hdr.trailer.value = 6;
        sm.egress_spec = 2;
        if (hdr.h.mode == 1) { mark_to_drop(sm); }
        if (hdr.h.mode == 3) { mark_to_drop(sm); sm.egress_spec = 2; }
    }
}
control E(inout H hdr, inout M meta, inout standard_metadata_t sm) {
    bit<8> n;
    apply {
        hdr.h.trace = (hdr.h.trace << 4) | 4;
        hdr.h.port = (bit<8>) sm.egress_port;
        egress_count.read(hdr.h.e, 0);
        egress_count.read(n, 0); egress_count.write(0, n + 1);
        if (hdr.h.mode == 2) { mark_to_drop(sm); }
    }
}
control C(inout H hdr, inout M meta) {
    apply { update_checksum(true, { hdr.h.trace }, hdr.h.checksum, HashAlgorithm.csum16); }
}
control D(packet_out pkt, in H hdr) {
    apply { pkt.emit(hdr.h); pkt.emit(hdr.trailer); }
}
V1Switch(P(), V(), I(), E(), C(), D()) main;
