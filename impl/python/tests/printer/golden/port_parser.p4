// port_parser: printed by p4blo for v1model. Do not edit.
#include <core.p4>
#include <v1model.p4>

header h_t {
    bit<8> f;
}

struct H {
    h_t h;
}

struct M {
    bit<9> ingress_port;
    bit<9> egress_spec;
    bool drop_requested;
}

parser P(packet_in packet, out H hdr, inout M meta, inout standard_metadata_t standard_metadata) {
    state start {
        meta.ingress_port = standard_metadata.ingress_port;
        packet.extract(hdr.h);
        transition select(meta.ingress_port) {
            9w1: from_one;
            default: accept;
        }
    }
    state from_one {
        meta.drop_requested = true;
        transition accept;
    }
}

control C(inout H hdr, inout M meta, inout standard_metadata_t standard_metadata) {
    apply {
        meta.ingress_port = standard_metadata.ingress_port;
        meta.egress_spec = standard_metadata.egress_spec;
        meta.egress_spec = 9w2;
        if (meta.drop_requested) {
            meta.egress_spec = 9w511;
        }
        standard_metadata.egress_spec = meta.egress_spec;
    }
}

control D(packet_out packet, in H hdr) {
    apply {
        packet.emit(hdr.h);
    }
}

control MyVerifyChecksum(inout H hdr, inout M meta) {
    apply {
    }
}

control MyEgress(inout H hdr, inout M meta, inout standard_metadata_t standard_metadata) {
    apply {
        meta.ingress_port = standard_metadata.ingress_port;
        meta.egress_spec = 0;
        standard_metadata.egress_spec = (meta.egress_spec == 9w511 ? 9w511 : standard_metadata.egress_port);
    }
}

control MyComputeChecksum(inout H hdr, inout M meta) {
    apply {
    }
}

V1Switch(P(), MyVerifyChecksum(), C(), MyEgress(), MyComputeChecksum(), D()) main;
