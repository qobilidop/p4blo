// A parser state's locals take their default on every entry: `cnt` is 1 and
// `tmp` invalid each time the loop state runs.
// The vector's expectations are P4-SpecTec's output.
#include <core.p4>
#include <v1model.p4>
header h_t { bit<8> f; }
header o_t { bit<8> a; bit<8> b; bit<8> c; }
struct H { h_t[3] s; o_t o; }
struct M { }
parser P(packet_in pkt, out H hdr, inout M meta, inout standard_metadata_t sm) {
    state start { hdr.o.setValid(); transition loop; }
    state loop {
        bit<8> cnt;
        h_t tmp;
        if (tmp.isValid()) { hdr.o.b = hdr.o.b + 1; }
        tmp.setValid();
        cnt = cnt + 1;
        hdr.o.a = cnt;
        pkt.extract(hdr.s.next);
        transition select(hdr.s.last.f) { 0: accept; default: loop; }
    }
}
control V(inout H hdr, inout M meta) { apply { } }
control I(inout H hdr, inout M meta, inout standard_metadata_t sm) { apply { sm.egress_spec = 1; } }
control E(inout H hdr, inout M meta, inout standard_metadata_t sm) { apply { } }
control C(inout H hdr, inout M meta) { apply { } }
control D(packet_out pkt, in H hdr) { apply { pkt.emit(hdr.o); } }
V1Switch(P(), V(), I(), E(), C(), D()) main;
