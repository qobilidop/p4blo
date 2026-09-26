# Authoring Python block libraries

The Python eDSL builds architecture-free IR. A library declares block bodies,
their types and extern interfaces; an architecture chooses which blocks to
call, supplies extern implementations and interprets the resulting metadata.
Start with the [router](../examples/router/program.py), then the
[firewall](../examples/firewall/program.py) or
[load balancer](../examples/load_balancer/program.py).

## Readable programs

Python executes a block method once while building IR. `self.assign` records
an assignment; `with self.if_(condition)` records a branch taken when the
program runs. Ordinary Python helpers can name or assemble those operations.
Python `if` cannot branch on an eDSL expression, and assigning a Python name
does not introduce a packet-time variable.

Use local names for domain concepts and exact widths:

```python
from p4blo import edsl as p4
from p4blo.arch.externs.declarations import Checksum16

ChecksumWords = p4.Bits[p4.L[144]]
checksum = Checksum16[ChecksumWords]("checksum")
```

The alias names a type without changing it. A helper like `checksum_data(ip)`
returns a symbolic expression; a name like `supported_header` holds a symbolic
predicate. Both are evaluated on packet data when the resulting IR executes.
The examples keep the checksum field list visible beside the application,
so each program can be read independently.

`.as_(T)` checks an expression's width while building and supplies the static
type Python cannot infer for concatenation; `.cast(T)` records a packet-time
conversion. They are different operations. Mutable temporaries remain
declared block locals or metadata fields with explicit `self.assign` calls.
Extern calls are effects: a returned value must be assigned directly, and
an `out` parameter must be a writable place.

## Blocks and libraries

A block class declares its own parameters and behavior. It needs no pipeline
role or architecture to be compiled. A `BlockLibrary` optionally collects
several block definitions and their shared declarations:

```python
blocks = p4.BlockLibrary(Parse, Route, Emit, externs=[checksum])
compiled = blocks.compile()
```

`compile()` returns a protobuf `p4blo.v0.BlockLibrary` with its name, errors,
types, extern declarations and instances, and blocks. It can be checked by the
core validator. It has no selected global headers/metadata roots, exports,
ports or packet-fate policy. The library may hold any number of parsers,
controls and deparsers; it does not choose a pipeline. A library containing a
single control with an explicit scalar
`InOut[bit8]` parameter also compiles; conventional `hdr`/`meta` parameters are
shorthands, not requirements of independent block compilation.

Architecture assembly selects the roles and the header/metadata values used
by the existing wire format. The supported v1model adapter is explicit:

```python
from p4blo.arch import v1model

assembly = v1model.assemble(
    blocks,
    name="router",
    headers=Headers,
    metadata=Metadata,
    parser=Parse,
    ingress=Route,
    deparser=Emit,
)
```

An alternative adapter uses `p4blo.arch.assemble` with an explicit export
mapping, then calls the blocks according to its own logic. The architectural
wire `p4blo.arch.v0.BlockAssembly` carries the selected H/M roots and exports
alongside the library declarations. Its exported entry points follow the
existing H/M calling convention. It does not define the architecture's
execution behavior. Arbitrary scalar block signatures remain valid inside a
library and as sub-blocks, but are not promised as assembly exports.

Assembly compiles the library definitions together in one context, so types,
sub-blocks and shared extern instances keep one identity. Independent
`.compile()` produces a core library that can be validated and used without an
assembly. Assembly does not link separately compiled protobuf fragments. The
loader checks the assembly and its selected roles. Optional
`verify_checksum`, `egress` and `compute_checksum` arguments select separate
Control blocks; omitted stages are empty. Explicit stage blocks must be
distinct and cannot also serve as internal callees. Standard metadata uses
`egress_spec` for requests and read-only `egress_port` for the selected output;
see the [stage contract](arch-supports.md#the-metadata-contract).

An architecture may bind a compiled library directly, including several
blocks of the same kind. For example, a host that runs two controls can name
both roles without changing the core library:

```python
from p4blo import arch, validator
from p4blo.arch.contract import Contract
from p4blo.arch.externs import Registry
from p4blo.arch.v0 import assembly_pb2 as apb
from p4blo.v0 import p4blo_pb2 as pb

library = p4.BlockLibrary(ChooseLeft, ChooseRight).compile()
validator.check(library)
bindings = apb.BlockBindings(
    headers="Headers",
    metadata="Metadata",
    exports=[
        apb.Export(role="left", block="ChooseLeft"),
        apb.Export(role="right", block="ChooseRight"),
    ],
)
loaded = arch.load(
    library,
    bindings=bindings,
    registry=Registry(),
    contract=Contract(()),
    roles={"left": pb.BLOCK_KIND_CONTROL, "right": pb.BLOCK_KIND_CONTROL},
)
```

The architecture supplies `Headers` and `Metadata` only when it binds blocks
to its H/M calling convention. The core library contains their type
declarations because the blocks use them, with neither type selected as a
global root. The [multiple-block witness](../tests/programs/test_block_libraries.py)
also binds two parsers and two deparsers and calls both paths.

## Declare, register, bind

These are three separate steps:

1. **Declare an interface.** Subclass `p4.Extern`; annotate constructor
   constants with `Const`, method parameters with `In`, `Out` or `InOut`,
   and any result with its value type. Instantiating it and listing it in
   `BlockLibrary(externs=[...])` writes declarations and call sites into IR.
   It neither executes nor registers an implementation.
2. **Register an implementation.** Construct a local
   `p4blo.arch.externs.Registry` and call `register(Implementation(...))`.
   An implementation provides its family name, accepted `Shape`, and factory.
   The shape independently checks method names, directions, argument and
   result widths against the program's declaration.
3. **Bind a loaded assembly.** Pass that registry to the loader. Binding
   checks declarations and constructor values, then calls the factory for
   every instance. Each factory must create fresh state. Reusing a loaded
   assembly preserves that state; loading again creates a new runtime.

Registration is local to the registry. Duplicate family registration fails;
an unregistered family or incompatible declaration fails at binding. A
family name is the segment before the first dot, preserving the wire
convention for width-specialized declarations such as `register.8`.

Concrete families are outside the generic eDSL:

| Public API | Responsibility |
|---|---|
| `p4blo.edsl.Extern` | Generic typed extern declarations and calls |
| `p4blo.arch.externs.declarations` | Supplied typed families and dynamic declaration helpers |
| `p4blo.arch.externs.Registry`, `Implementation`, `Shape` | Explicit runtime implementation registration and checked binding |
| `p4blo.arch.externs.supplied_registry()` | Fresh registry containing the supplied implementations |
| `p4blo.arch.load` | Load with an explicit registry, metadata contract and required role/kind mapping |
| `p4blo.arch.v1model.load` | Load the supported six-stage v1model profile with its supplied extern families |

The three demos explicitly select the v1model profile:

```python
from p4blo.arch import v1model

loaded = v1model.load(assembly)
pipeline = v1model.V1Model(ports=4)
```

A custom caller can select a smaller registry or register different families
through generic `arch.load`. That loader supplies no architecture defaults. The
[custom extern example](../examples/custom_extern.py) defines an extern,
registers its Python implementation and runs a control-only assembly without
modifying p4blo:

```sh
uv run python -m examples.custom_extern
```

A Python implementation does not confer Lean semantics, a proof, or a P4
printing translation. Each of those requires separate implementation and
evidence. The supplied families' contracts and known differences are in
[architecture support](arch-supports.md#extern-families). The `P4blo` package
used by the P4-SpecTec block oracle is a testing adapter, not an architecture
required by the authoring or execution APIs.

## Migrating older source

- Author independent `Parser`, `Control` and `Deparser` classes, optionally
  collected in `BlockLibrary`; keep pipeline selection in `v1model.assemble`.
- Replace `reference.assemble(..., control=...)` with
  `v1model.assemble(..., ingress=...)`; keep optional stages separate.
- Replace `arch.reference.load` and `arch.Switch` with `v1model.load` and
  `v1model.V1Model`. Filter and the custom Switch are no longer supplied.
- Replace requested-destination `egress_port` with `egress_spec`. Replace a
  drop assignment with `egress_spec = 511` at that point in the block; later
  writes may undo it. Remove `drop` and `flood` fields. The new `egress_port`
  is the actual destination snapshot available only after ingress.
- Keep concrete extern declarations in `p4blo.arch.externs.declarations`.
  Custom registries use explicit `arch.load` dependencies; they do not extend
  the supported v1model profile automatically.

Regenerate affected architecture goldens and check packet/state behavior.
The core BlockLibrary and arbitrary typed block signatures remain independent
of this migration; serialized architecture bindings and metadata do change.
