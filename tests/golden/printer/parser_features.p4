// parser_features: printed by p4blo for v1model. Do not edit.
#include <core.p4>
#include <v1model.p4>

error { BadVersion }

header ethernet_t {
    bit<48> dst;
    bit<48> src;
    bit<16> type;
}

header vlan_t {
    bit<3> pcp;
    bit<1> cfi;
    bit<12> vid;
    bit<16> type;
}

header ipv4_t {
    bit<4> version;
    bit<4> ihl;
    bit<8> ttl;
    bool flag;
}

struct headers {
    ethernet_t eth;
    vlan_t[2] vlans;
    ipv4_t ipv4;
}

struct metadata {
    bit<9> ingress_port;
    error parser_error;
    bit<8> note;
}

parser Ipv4Parser(packet_in packet, out ipv4_t ip, inout bit<8> note) {
    state start {
        packet.extract(ip);
        verify(ip.version == 4w4, error.BadVersion);
        note = ip.ttl;
        transition accept;
    }
}

parser TopParser(packet_in packet, out headers hdr, inout metadata meta, inout standard_metadata_t standard_metadata) {
    Ipv4Parser() Ipv4Parser_inst;
    bit<16> peek = 16w0;
    state start {
        meta.ingress_port = standard_metadata.ingress_port;
        transition begin;
    }
    state begin {
        packet.extract(hdr.eth);
        peek = packet.lookahead<bit<16>>();
        transition select(hdr.eth.type, hdr.eth.dst[47:40]) {
            (16w33024, _): vlan;
            (16w2048..16w2049, 8w1 &&& 8w255): ipv4;
            (16w34525, 8w0): skip;
            default: accept;
        }
    }
    state vlan {
        packet.extract(hdr.vlans.next);
        meta.note = (bit<8>) hdr.vlans.lastIndex;
        transition select(hdr.vlans[32w0].type) {
            16w33024: vlan;
            16w2048: ipv4;
            default: accept;
        }
    }
    state ipv4 {
        Ipv4Parser_inst.apply(packet, hdr.ipv4, meta.note);
        packet.advance((((bit<32>) hdr.ipv4.ihl) - 32w5) * 32w32);
        if (hdr.ipv4.ttl == 8w0) {
            meta.note = 8w255;
        }
        transition select(meta.note) {
            8w255: reject;
            default: accept;
        }
    }
    state skip {
        packet.advance(32w16);
        transition reject;
    }
}

control TopIngress(inout headers hdr, inout metadata meta, inout standard_metadata_t standard_metadata) {
    apply {
        meta.ingress_port = standard_metadata.ingress_port;
        meta.parser_error = standard_metadata.parser_error;
        if (meta.parser_error != error.NoError) {
            meta.note = 8w1;
        }
    }
}

control TopDeparser(packet_out packet, in headers hdr) {
    apply {
        packet.emit(hdr.eth);
        packet.emit(hdr.vlans);
        packet.emit(hdr.ipv4);
    }
}

control MyVerifyChecksum(inout headers hdr, inout metadata meta) {
    apply {
    }
}

control MyEgress(inout headers hdr, inout metadata meta, inout standard_metadata_t standard_metadata) {
    apply {
        meta.ingress_port = standard_metadata.ingress_port;
        meta.parser_error = standard_metadata.parser_error;
        standard_metadata.egress_spec = standard_metadata.egress_port;
    }
}

control MyComputeChecksum(inout headers hdr, inout metadata meta) {
    apply {
    }
}

V1Switch(TopParser(), MyVerifyChecksum(), TopIngress(), MyEgress(), MyComputeChecksum(), TopDeparser()) main;
