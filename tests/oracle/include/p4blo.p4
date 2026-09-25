/* p4blo.p4: the block architecture P4-SpecTec runs p4blo's blocks on.
 *
 * Not an architecture in the usual sense: the simulator's `block` command
 * (tests/oracle/patches/, backend-sim/p4blo/) calls exactly one of the
 * three blocks per request, on the headers, metadata, table entries and
 * extern state the request supplies, and returns what the block left.
 * The block signatures are p4blo's calling convention with the packet
 * added (docs/design.md, "Blocks and the P4NAH rule"); there is no
 * standard_metadata and no metadata contract, because nothing runs
 * between blocks.
 *
 * The extern declarations are the families p4blo's printer uses, with
 * V1Model's signatures (p4c/p4include/v1model.p4 at V1MODEL_VERSION
 * 20180101), because the plugin implements them with the V1Model
 * simulator's own code and the printer prints them as it does for v1model.
 */

#ifndef _P4BLO_P4_
#define _P4BLO_P4_

#include <core.p4>

enum CounterType {
    packets,
    bytes,
    packets_and_bytes
}

extern counter {
    counter(bit<32> size, CounterType type);
    void count(in bit<32> index);
}

extern register<T> {
    register(bit<32> size);
    void read(out T result, in bit<32> index);
    void write(in bit<32> index, in T value);
}

enum HashAlgorithm {
    crc32,
    crc32_custom,
    crc16,
    crc16_custom,
    random,
    identity,
    csum16,
    xor16
}

extern void hash<O, T, D, M>(out O result, in HashAlgorithm algo, in T base, in D data, in M max);

parser P4bloParser<H, M>(packet_in packet, out H hdr, inout M meta);
control P4bloControl<H, M>(inout H hdr, inout M meta);
control P4bloDeparser<H>(packet_out packet, in H hdr);

package P4blo<H, M>(P4bloParser<H, M> p, P4bloControl<H, M> c, P4bloDeparser<H> d);

#endif  /* _P4BLO_P4_ */
