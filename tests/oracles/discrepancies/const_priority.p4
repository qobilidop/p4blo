// SPDX-License-Identifier: Apache-2.0
// Priority rows reduced from p4c table-entries-priority-bmv2.p4.
// Copyright 2013-present Barefoot Networks, Inc.
#include <core.p4>
#include <v1model.p4>
header Data { bit<16> key; }
struct H { Data h; }
struct M { }
parser P(packet_in packet, out H hdr, inout M meta, inout standard_metadata_t sm) {
    state start { packet.extract(hdr.h); transition accept; }
}
control V(inout H hdr, inout M meta) { apply { } }
control I(inout H hdr, inout M meta, inout standard_metadata_t sm) {
    action forward(bit<9> port) { sm.egress_spec = port; }
    table routes {
        key = { hdr.h.key : ternary; }
        actions = { forward; }
        default_action = forward(0);
        const entries = {
            0x1111 &&& 0x000f : forward(1) @priority(3);
            0x1181 : forward(2);
            0x1181 &&& 0xf00f : forward(3) @priority(1);
        }
    }
    apply { routes.apply(); }
}
control E(inout H hdr, inout M meta, inout standard_metadata_t sm) { apply { } }
control C(inout H hdr, inout M meta) { apply { } }
control D(packet_out packet, in H hdr) { apply { packet.emit(hdr.h); } }
V1Switch(P(), V(), I(), E(), C(), D()) main;
