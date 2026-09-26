// A user M whose contract-named fields the source copies to and from
// standard_metadata exactly as p4blo's printer does: they are the contract
// fields (tests/external/test_frontend_spectec.py checks the translation's M too).
// The vector's expectations are P4-SpecTec's output.
#include <core.p4>
#include <v1model.p4>
header h_t { bit<8> f; bit<8> g; }
struct H { h_t h; }
struct M { bit<9> ingress_port; error parser_error; bit<9> egress_port; bool drop; }
parser P(packet_in pkt, out H hdr, inout M meta, inout standard_metadata_t sm) {
    state start {
        meta.ingress_port = sm.ingress_port;
        pkt.extract(hdr.h);
        transition accept;
    }
}
control V(inout H hdr, inout M meta) { apply { } }
control I(inout H hdr, inout M meta, inout standard_metadata_t sm) {
    apply {
        meta.ingress_port = sm.ingress_port;
        meta.parser_error = sm.parser_error;
        hdr.h.g = (bit<8>) meta.ingress_port;
        if (meta.parser_error == error.NoError) { hdr.h.g = hdr.h.g + 0x10; }
        meta.egress_port = 2;
        if (hdr.h.f == 1) { meta.drop = true; }
        sm.egress_spec = meta.egress_port;
        if (meta.drop) { mark_to_drop(sm); }
    }
}
control E(inout H hdr, inout M meta, inout standard_metadata_t sm) { apply { } }
control C(inout H hdr, inout M meta) { apply { } }
control D(packet_out pkt, in H hdr) { apply { pkt.emit(hdr.h); } }
V1Switch(P(), V(), I(), E(), C(), D()) main;
