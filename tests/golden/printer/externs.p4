// externs: printed by p4blo for v1model. Do not edit.
#include <core.p4>
#include <v1model.p4>

header ethernet_t {
    bit<48> dst;
    bit<48> src;
    bit<16> type;
}

struct headers {
    ethernet_t eth;
}

struct metadata {
    bit<9> egress_spec;
    bit<32> idx;
    bit<16> sum;
}

counter(32w4, CounterType.packets) pkts;

parser EthParser(packet_in packet, out headers hdr, inout metadata meta, inout standard_metadata_t standard_metadata) {
    state start {
        packet.extract(hdr.eth);
        transition accept;
    }
}

control Count(in bit<32> i) {
    apply {
        pkts.count(i);
    }
}

control MainIngress(inout headers hdr, inout metadata meta, inout standard_metadata_t standard_metadata) {
    register<bit<16>>(32w16) last_seen;
    Count() Count_inst;
    apply {
        meta.egress_spec = standard_metadata.egress_spec;
        last_seen.read(meta.sum, meta.idx);
        meta.sum = meta.sum + 16w1;
        last_seen.write(meta.idx, meta.sum);
        pkts.count(32w0);
        Count_inst.apply(meta.idx);
        hash(meta.sum, HashAlgorithm.csum16, 16w0, { hdr.eth.dst ++ hdr.eth.src }, 32w65536);
        meta.egress_spec = 9w1;
        standard_metadata.egress_spec = meta.egress_spec;
    }
}

control MainDeparser(packet_out packet, in headers hdr) {
    apply {
        packet.emit(hdr.eth);
    }
}

control MyVerifyChecksum(inout headers hdr, inout metadata meta) {
    apply {
    }
}

control MyEgress(inout headers hdr, inout metadata meta, inout standard_metadata_t standard_metadata) {
    apply {
        meta.egress_spec = 0;
        standard_metadata.egress_spec = (meta.egress_spec == 9w511 ? 9w511 : standard_metadata.egress_port);
    }
}

control MyComputeChecksum(inout headers hdr, inout metadata meta) {
    apply {
    }
}

V1Switch(EthParser(), MyVerifyChecksum(), MainIngress(), MyEgress(), MyComputeChecksum(), MainDeparser()) main;
