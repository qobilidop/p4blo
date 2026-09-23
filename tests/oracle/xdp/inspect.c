/* SPDX-License-Identifier: Apache-2.0 */
/* Open ELF/BTF metadata only. No load, attach, pin, map or test-run syscall. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "libbpf.h"
#include "btf.h"

static void require(int condition, const char *message)
{
    if (!condition) {
        fprintf(stderr, "profile: %s\n", message);
        exit(1);
    }
}

static const struct btf_type *type(const struct btf *btf, unsigned id)
{
    const struct btf_type *result = btf__type_by_id(btf, id);
    require(result != NULL, "missing BTF type");
    return result;
}

static unsigned uint_member(const struct btf *btf, const struct btf_member *member)
{
    const struct btf_type *pointer = type(btf, member->type);
    require(btf_is_ptr(pointer), "configuration member is not a pointer");
    const struct btf_type *array = type(btf, pointer->type);
    require(btf_is_array(array), "configuration member is not an array");
    return btf_array(array)->nelems;
}

int main(int argc, char **argv)
{
    require(argc == 2, "expected one object path");
    struct bpf_object *object = bpf_object__open_file(argv[1], NULL);
    require(libbpf_get_error(object) == 0 && object != NULL, "cannot open object");
    require(bpf_object__btf_fd(object) < 0, "BTF was loaded");

    struct bpf_program *program;
    unsigned programs = 0;
    bpf_object__for_each_program(program, object) {
        programs++;
        require(strcmp(bpf_program__name(program), "xdpfilt_alw_eth") == 0,
                "wrong program name");
        require(strcmp(bpf_program__section_name(program), "xdp") == 0,
                "wrong program section");
        require(bpf_program__type(program) == BPF_PROG_TYPE_XDP, "wrong program type");
        require(bpf_program__fd(program) < 0, "program was loaded");
    }
    require(programs == 1, "expected exactly one program");

    unsigned maps = 0, seen = 0, stats_type = 0;
    struct bpf_map *map;
    bpf_object__for_each_map(map, object) {
        const char *name = bpf_map__name(map);
        int ethernet = strcmp(name, "filter_ethernet") == 0;
        require(ethernet || strcmp(name, "xdp_stats_map") == 0, "unexpected map");
        unsigned bit = ethernet ? 1u : 2u;
        require(!(seen & bit), "duplicate map");
        seen |= bit;
        if (!ethernet)
            stats_type = bpf_map__btf_value_type_id(map);
        maps++;
        require(bpf_map__type(map) == (ethernet ? BPF_MAP_TYPE_PERCPU_HASH : BPF_MAP_TYPE_PERCPU_ARRAY),
                "wrong map type");
        require(bpf_map__key_size(map) == (ethernet ? 6u : 4u), "wrong key size");
        require(bpf_map__value_size(map) == (ethernet ? 8u : 16u), "wrong value size");
        require(bpf_map__max_entries(map) == (ethernet ? 10000u : 5u), "wrong capacity");
        require(bpf_map__map_flags(map) == 0, "unexpected map flags");
        require(bpf_map__fd(map) < 0 && !bpf_map__is_pinned(map), "map was loaded or pinned");
        require(bpf_map__pin_path(map) != NULL, "missing original pin-by-name metadata");
    }
    require(maps == 2 && seen == 3, "expected exactly two maps");

    const struct btf *btf = bpf_object__btf(object);
    require(btf != NULL, "missing BTF");
    int record_id = btf__find_by_name_kind(btf, "xdp_stats_record", BTF_KIND_STRUCT);
    require(record_id > 0, "missing statistics record");
    require(btf__resolve_type(btf, stats_type) == record_id, "wrong statistics map value type");
    const struct btf_type *record = type(btf, record_id);
    require(record->size == 16 && btf_vlen(record) == 2, "wrong statistics layout");
    const struct btf_member *fields = btf_members(record);
    const char *field_names[2][2] = {{"packets", "rx_packets"}, {"bytes", "rx_bytes"}};
    for (unsigned i = 0; i < 2; i++) {
        require(fields[i].name_off == 0 && fields[i].offset == i * 64,
                "wrong statistics member layout");
        const struct btf_type *alias = type(btf, fields[i].type);
        require(btf_is_union(alias) && alias->size == 8 && btf_vlen(alias) == 2,
                "wrong statistics aliases");
        const struct btf_member *names = btf_members(alias);
        for (unsigned j = 0; j < 2; j++) {
            require(strcmp(btf__name_by_offset(btf, names[j].name_off), field_names[i][j]) == 0 &&
                    names[j].offset == 0, "wrong statistics alias");
            int scalar_id = btf__resolve_type(btf, names[j].type);
            require(scalar_id > 0, "invalid statistics scalar");
            const struct btf_type *scalar = type(btf, scalar_id);
            require(btf_is_int(scalar) && scalar->size == 8 && btf_int_bits(scalar) == 64 &&
                    btf_int_offset(scalar) == 0 && btf_int_encoding(scalar) == 0,
                    "statistics scalar is not unsigned 64-bit");
        }
    }

    int config_id = btf__find_by_name_kind(btf, "_xdpfilt_alw_eth", BTF_KIND_VAR);
    require(config_id > 0, "missing run configuration");
    const struct btf_type *config = type(btf, type(btf, config_id)->type);
    require(btf_is_struct(config) && btf_vlen(config) == 2, "wrong run configuration");
    const struct btf_member *settings = btf_members(config);
    require(strcmp(btf__name_by_offset(btf, settings[0].name_off), "priority") == 0 &&
            strcmp(btf__name_by_offset(btf, settings[1].name_off), "XDP_PASS") == 0,
            "wrong configuration keys");
    unsigned priority = uint_member(btf, &settings[0]);
    unsigned chain_pass = uint_member(btf, &settings[1]);
    require(priority == 10 && chain_pass == 1, "wrong configuration values");
    printf("{\"programs\":%u,\"maps\":%u,\"priority\":%u,\"chain_pass\":%u,\"loaded\":false}\n",
           programs, maps, priority, chain_pass);
    bpf_object__close(object);
    return 0;
}
