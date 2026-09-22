// bare: printed by p4blo for v1model. Do not edit.
#include <core.p4>
#include <v1model.p4>

struct H {
}

struct M {
    bool seen;
}

parser P(packet_in packet, out H h, inout M m, inout standard_metadata_t standard_metadata) {
    state start {
        m.seen = true;
        transition accept;
    }
}

control MyIngress(inout H hdr, inout M meta, inout standard_metadata_t standard_metadata) {
    apply {
    }
}

control MyDeparser(packet_out packet, in H hdr) {
    apply {
    }
}

control MyVerifyChecksum(inout H hdr, inout M meta) {
    apply {
    }
}

control MyEgress(inout H hdr, inout M meta, inout standard_metadata_t standard_metadata) {
    apply {
    }
}

control MyComputeChecksum(inout H hdr, inout M meta) {
    apply {
    }
}

V1Switch(P(), MyVerifyChecksum(), MyIngress(), MyEgress(), MyComputeChecksum(), MyDeparser()) main;
