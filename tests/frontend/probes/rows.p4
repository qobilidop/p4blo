// The elaborated rows no corpus program exercises: unary +, hs.size, +:,
// named arguments and _, a parenthesized lvalue, the empty statement,
// compound assignment and switch on a value.
// The vector's expectations are P4-SpecTec's output.
#include <core.p4>
#include <v1model.p4>
header h_t { bit<8> f; bit<8> g; bit<8> k; bit<8> n; bit<8> s; bit<8> t; bit<8> u; bit<8> w; }
struct H { h_t h; h_t[3] st; }
struct M { }
void setp(in bit<8> a, out bit<8> b, inout bit<8> c) { b = a + c; c = c + 1; }
parser P(packet_in pkt, out H hdr, inout M meta, inout standard_metadata_t sm) {
    state start { pkt.extract(hdr.h); transition accept; }
}
control V(inout H hdr, inout M meta) { apply { } }
control I(inout H hdr, inout M meta, inout standard_metadata_t sm) {
    action act(bit<8> x) { ; hdr.h.w = x; }
    table t { key = { hdr.h.f : exact; } actions = { act; NoAction; } default_action = NoAction; }
    apply {
        hdr.h.g = +hdr.h.f;
        hdr.h.k = (bit<8>) hdr.st.size;
        hdr.h.n = hdr.h.f[2 +: 4] ++ 4w0;
        setp(c = hdr.h.t, b = hdr.h.s, a = hdr.h.f);
        setp(hdr.h.f, _, hdr.h.u);
        (hdr.h.u) = hdr.h.u + 2;
        hdr.h.f += 1;
        hdr.h.f |= 8w0x40;
        switch (hdr.h.g) {
            1: 
            2: { hdr.h.t = 0xaa; }
            3: { hdr.h.t = 0xbb; }
            default: { hdr.h.t = hdr.h.t ^ 0xff; }
        }
        {
            ;
        }
        t.apply();
        sm.egress_spec = 1;
    }
}
control E(inout H hdr, inout M meta, inout standard_metadata_t sm) { apply { } }
control C(inout H hdr, inout M meta) { apply { } }
control D(packet_out pkt, in H hdr) { apply { pkt.emit(hdr.h); } }
V1Switch(P(), V(), I(), E(), C(), D()) main;
