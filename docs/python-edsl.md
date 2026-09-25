# Authoring Python programs

The Python eDSL builds architecture-free IR. A program declares headers,
metadata, blocks and extern interfaces; an architecture chooses which blocks
to call, supplies extern implementations and interprets the resulting metadata.
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

The compiled library contains block bodies and their dependencies. It has no
selected global headers/metadata roots, exports, ports or packet-fate policy.
It is a fragment, not a complete runnable program or a whole-program validity
certificate. A library containing a single control with an explicit scalar
`InOut[bit8]` parameter also compiles; conventional `hdr`/`meta` parameters are
shorthands, not requirements of independent block compilation.

Architecture assembly selects the roles and the header/metadata values used
by the existing wire format. The supplied switch adapter is explicit:

```python
from p4blo.arch import reference

program = reference.assemble(
    blocks,
    name="router",
    headers=Headers,
    metadata=Metadata,
    parser=Parse,
    control=Route,
    deparser=Emit,
)
```

An alternative adapter uses `p4blo.arch.assemble` with an explicit export
mapping, then calls the blocks according to its own logic. The current wire
`Program` is an assembly envelope; its exported entry points follow the
existing H/M calling convention. It does not define the architecture's
execution behavior. Arbitrary scalar block signatures remain valid inside a
library and as sub-blocks, but are not newly promised as wire exports.

Assembly compiles the library definitions together in one context, so types,
sub-blocks and shared extern instances keep one identity. Independent
`.compile()` is for inspection; assembly does not link separately compiled
protobuf fragments. Whole-program validation happens at loading or through
an explicit `validator.check`.

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
3. **Bind a loaded program.** Pass that registry to the loader. Binding
   checks declarations and constructor values, then calls the factory for
   every instance. Each factory must create fresh state. Reusing a loaded
   program preserves that state; loading again creates a new runtime.

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
| `p4blo.arch.reference.load` | Convenience loader selecting the supplied switch/filter contract and defaults |

The three demos explicitly select the reference environment and supplied
registry:

```python
from p4blo.arch import reference
from p4blo.arch.externs import supplied_registry

loaded = reference.load(program, registry=supplied_registry())
```

An architecture can select a smaller registry or register different custom
families. The generic loader supplies no switch defaults. The
[custom extern example](../examples/custom_extern.py) defines an extern,
registers its Python implementation and runs a control-only program without
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

- Replace typed `p4.Program(...)` authoring with `p4.BlockLibrary(P, C, D,
  externs=[...])`. Choose pipeline roles and H/M roots separately with
  `reference.assemble(...)` or a custom architecture adapter.
- Import concrete extern classes and dynamic declaration helpers from
  `p4blo.arch.externs.declarations`, rather than `p4blo.edsl.externs`,
  `p4blo.edsl.core.externs` or the eDSL's top-level CRC exports.
- Replace the old implicit `arch.load(program)` with
  `arch.reference.load(program)` when selecting the supplied environment;
  use explicit `arch.load` dependencies for a custom architecture.
- Replace `default_registry()` with `supplied_registry()`.

These changes affect authoring and runtime assembly. They do not change the
wire schema, interpreter semantics or the supplied applications' behavior.
