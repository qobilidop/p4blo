// forwarder: printed by p4blo for v1model. Do not edit.
#include <core.p4>
#include <v1model.p4>

header ethernet_t {
    bit<48> dstAddr;
    bit<48> srcAddr;
    bit<16> etherType;
}

header ipv4_t {
    bit<4> version;
    bit<4> ihl;
    bit<8> diffserv;
    bit<16> totalLen;
    bit<16> identification;
    bit<3> flags;
    bit<13> fragOffset;
    bit<8> ttl;
    bit<8> protocol;
    bit<16> hdrChecksum;
    bit<32> srcAddr;
    bit<32> dstAddr;
}

struct headers {
    ethernet_t ethernet;
    ipv4_t ipv4;
}

struct metadata {
    bit<9> ingress_port;
    bit<9> egress_port;
    bool drop;
}

parser MyParser(packet_in packet, out headers hdr, inout metadata meta, inout standard_metadata_t standard_metadata) {
    state start {
        transition parse_ethernet;
    }
    state parse_ethernet {
        packet.extract(hdr.ethernet);
        transition select(hdr.ethernet.etherType) {
            16w2048: parse_ipv4;
            default: accept;
        }
    }
    state parse_ipv4 {
        packet.extract(hdr.ipv4);
        transition accept;
    }
}

control MyIngress(inout headers hdr, inout metadata meta, inout standard_metadata_t standard_metadata) {
    action drop() {
        meta.drop = true;
    }
    action ipv4_forward(bit<48> dstAddr, bit<9> port) {
        meta.egress_port = port;
        hdr.ethernet.srcAddr = hdr.ethernet.dstAddr;
        hdr.ethernet.dstAddr = dstAddr;
        hdr.ipv4.ttl = hdr.ipv4.ttl - 8w1;
    }
    table ipv4_lpm {
        key = {
            hdr.ipv4.dstAddr: lpm;
        }
        actions = {
            ipv4_forward;
            drop;
            NoAction;
        }
        default_action = drop();
        size = 1024;
    }
    apply {
        meta.ingress_port = standard_metadata.ingress_port;
        if (hdr.ipv4.isValid()) {
            ipv4_lpm.apply();
        }
        if (hdr.ipv4.isValid()) {
            hash(hdr.ipv4.hdrChecksum, HashAlgorithm.csum16, 16w0, { (((((((((hdr.ipv4.version ++ hdr.ipv4.ihl) ++ hdr.ipv4.diffserv) ++ hdr.ipv4.totalLen) ++ hdr.ipv4.identification) ++ hdr.ipv4.flags) ++ hdr.ipv4.fragOffset) ++ hdr.ipv4.ttl) ++ hdr.ipv4.protocol) ++ hdr.ipv4.srcAddr) ++ hdr.ipv4.dstAddr }, 32w65536);
        }
        standard_metadata.egress_spec = meta.egress_port;
        if (meta.drop) { mark_to_drop(standard_metadata); }
    }
}

control MyDeparser(packet_out packet, in headers hdr) {
    apply {
        packet.emit(hdr.ethernet);
        packet.emit(hdr.ipv4);
    }
}

control MyVerifyChecksum(inout headers hdr, inout metadata meta) {
    apply {
    }
}

control MyEgress(inout headers hdr, inout metadata meta, inout standard_metadata_t standard_metadata) {
    apply {
    }
}

control MyComputeChecksum(inout headers hdr, inout metadata meta) {
    apply {
    }
}

V1Switch(MyParser(), MyVerifyChecksum(), MyIngress(), MyEgress(), MyComputeChecksum(), MyDeparser()) main;
