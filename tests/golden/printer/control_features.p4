// control_features: printed by p4blo for v1model. Do not edit.
#include <core.p4>
#include <v1model.p4>

enum Color { RED, GREEN, BLUE }

header ethernet_t {
    bit<48> dst;
    bit<48> src;
    bit<16> type;
}

header ipv4_t {
    bit<8> ttl;
    bit<32> src;
    bit<32> dst;
}

header tag_t {
    bit<8> v;
}

struct headers {
    ethernet_t eth;
    ipv4_t ipv4;
    tag_t[3] tags;
}

struct metadata {
    bit<9> ingress_port;
    error parser_error;
    bit<9> egress_port;
    bool drop;
    Color color;
    bool flag;
    bit<32> scratch;
}

parser EthParser(packet_in packet, out headers hdr, inout metadata meta, inout standard_metadata_t standard_metadata) {
    state start {
        meta.ingress_port = standard_metadata.ingress_port;
        packet.extract(hdr.eth);
        packet.extract(hdr.ipv4);
        transition accept;
    }
}

control Rewrite(inout ethernet_t eth, in bit<48> dst) {
    apply {
        eth.src = eth.dst;
        eth.dst = dst;
    }
}

control MainIngress(inout headers hdr, inout metadata meta, inout standard_metadata_t standard_metadata) {
    Rewrite() Rewrite_inst;
    bit<16> tmp = 16w0;
    bool matched = false;
    Color c = Color.RED;
    error e = error.NoError;
    tag_t spare;
    action drop() {
        meta.drop = true;
    }
    action forward(bit<48> dst, bit<9> port) {
        meta.egress_port = port;
        hdr.eth.dst = dst;
    }
    action set_ttl(in bit<8> ttl) {
        hdr.ipv4.ttl = ttl;
    }
    table ipv4_lpm {
        key = {
            hdr.ipv4.dst: lpm @name("dst");
            hdr.eth.type: exact;
        }
        actions = {
            forward;
            drop;
            NoAction;
        }
        default_action = drop();
        const entries = {
            (32w167772160 &&& 32w4278190080, 16w2048) : forward(48w1, 9w1);
            (32w0 &&& 32w0, 16w2048) : drop();
        }
        size = 1024;
    }
    table acl {
        key = {
            hdr.ipv4.src: ternary;
            meta.ingress_port: exact;
        }
        actions = {
            drop;
            NoAction;
        }
        const default_action = NoAction();
        entries = {
            priority = 20: (32w167772161 &&& 32w4294967295, 9w1) : NoAction();
            priority = 10: (32w167772160 &&& 32w4278190080, 9w1) : drop();
        }
        largest_priority_wins = true;
    }
    table by_port {
        key = {
            meta.ingress_port: exact @name("port");
        }
        actions = {
            drop;
            NoAction;
        }
        default_action = NoAction();
    }
    apply {
        meta.ingress_port = standard_metadata.ingress_port;
        meta.parser_error = standard_metadata.parser_error;
        matched = ipv4_lpm.apply().hit;
        if (matched) {
            acl.apply();
        } else {
            drop();
        }
        by_port.apply();
        set_ttl(8w64);
        Rewrite_inst.apply(hdr.eth, 48w1);
        hdr.tags.push_front(1);
        hdr.tags.pop_front(2);
        hdr.tags[32w0].setValid();
        hdr.tags[32w1].setInvalid();
        spare.setValid();
        hdr.tags[32w2] = spare;
        meta.scratch = (((bit<32>) hdr.ipv4.ttl) + 32w1) * (32w2 |+| 32w3);
        tmp = (hdr.eth.type[7:0]) ++ (hdr.eth.type[15:8]);
        tmp = (tmp << 8w2) >> 8w1;
        tmp = (~(tmp & 16w255)) | (tmp ^ 16w1);
        tmp = (-tmp) |-| (tmp - 16w1);
        meta.flag = ((tmp < 16w5) || (tmp >= 16w9)) && ((!(tmp == 16w0)) && ((tmp != 16w1) && ((tmp <= 16w7) && (tmp > 16w2))));
        meta.color = meta.flag ? Color.GREEN : Color.BLUE;
        c = meta.color;
        e = meta.parser_error;
        meta.scratch = (bit<32>) ((bit<1>) meta.flag);
        meta.flag = (bool) (meta.scratch[0:0]);
        if (hdr.ipv4.isValid() && (c == Color.RED)) {
            forward(48w2, 9w2);
        }
        standard_metadata.egress_spec = meta.egress_port;
        if (meta.drop) { mark_to_drop(standard_metadata); }
    }
}

control Summarize(packet_out packet, in tag_t[3] tags, out bit<8> first) {
    apply {
        first = tags[32w0].v;
    }
}

control MainDeparser(packet_out packet, in headers hdr) {
    Summarize() Summarize_inst;
    bit<8> first = 8w0;
    apply {
        packet.emit(hdr.eth);
        Summarize_inst.apply(packet, hdr.tags, first);
        packet.emit(hdr.tags);
        if (first != 8w0) {
            packet.emit(hdr.ipv4);
        }
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

V1Switch(EthParser(), MyVerifyChecksum(), MainIngress(), MyEgress(), MyComputeChecksum(), MainDeparser()) main;
