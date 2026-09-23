# eDSL v2: type-safe by construction

| | |
|---|---|
| Status | Proposed, 2026-09-22; awaiting Bili's review before any code |
| Inputs | [edsl-prior-art-own.md](edsl-prior-art-own.md) (pakeles, p4py), [edsl-prior-art-survey.md](edsl-prior-art-survey.md) (HDL and compiler eDSLs), the pyright probes under [probes/](probes/) |

## The problem

The current eDSL builds correct IR, but nothing about it is visible to
a type checker, and three of its habits rely on typing the right
string: table action lists (`actions=["ipv4_forward", "drop"]`), state
targets (`{0x800: "parse_ipv4"}`, `s.transition("parse_ethernet")`) and
exports (`p.export("parser", "MyParser")`). Field access goes through
`__getattr__`, so `hdr.ipv4.tt1` is a run-time error and `hdr.eth.type`
returns the wrong thing. Widths are checked, but only at run time.

Bili's requirement: as type safe as possible; define and refer to
variables, never strings.

## What the prior art says

- **pakeles** settled the declaration model: headers as classes whose
  fields are real attributes, parsers as classes whose states are
  methods, targets holding the methods, assembled by running each
  method once. Its own history is the argument: it started with a
  dict of states and string forward references and replaced it with
  classes because "typos are unknown-attribute errors at edit time".
  Strict pyright is a headline feature there. It does not type widths.
- **p4py** is the counter-example: decorators read Python source, every
  reference is a name in effect, pyright fails on every header, and the
  AST matcher stopped scaling after nine days.
- **Amaranth, Magma, PyRTL, PyCDE** agree on builder-style control flow
  (`with m.If(...)`), on `__bool__` refusing with a message that names
  the cause, and on class-body field declarations. None makes widths
  visible to a type checker; the pyright maintainers say numeric widths
  are outside the type system.
- **MLIR's Python bindings and xDSL** show the object-first pattern for
  forward references (create the block, fill it under an insertion
  point) and the trick that lets a descriptor read as its value type
  for the checker (`cast(T, descriptor)`).
- **The probes** show that widths *are* checkable in practice: with
  `class Bits[W: int]` and `Literal` widths, pyright rejects an 8-bit
  plus 16-bit add, a wrong cast width and a misspelled field, and with
  actions as decorated methods it rejects a missing or extra action
  argument in a table default and a misspelled table name. This is new
  ground relative to every surveyed project.

## Principles

1. **Every reference is a Python object**: a field, a state method, an
   action method, a table attribute, a block class, an extern instance.
   Strings survive only as IR names, which the objects carry.
2. **Widths are types.** `Bits[Literal[8]]` at the type level, checked
   by pyright where it can be, and always checked at run time by the
   existing `EdslError` rules, which stay authoritative.
3. **No source reading.** Bodies are Python functions that are *called*
   once with a recording context; control flow is explicit `with`
   builders, as today. `__bool__` on an expression raises and names the
   cause. (This is the design doc's rule; pakeles and the survey both
   confirm it.)
4. **Goldens do not change.** v2 emits exactly the IR v1 emits for every
   corpus program; `tests/test_corpus.py` is the acceptance test, as it
   was for v1.
5. **Errors carry provenance**: the file and line of the declaration or
   statement, as pakeles does, never the IR.

## The surface, on the forwarder

```python
from p4blo.edsl import (Bits, Bool, L, Header, Struct, Parser, Control,
                        Deparser, Program, Table, action, state, lpm)
from p4blo.edsl.externs import Checksum16

bit8, bit9, bit16, bit32, bit48 = Bits[L[8]], Bits[L[9]], Bits[L[16]], Bits[L[32]], Bits[L[48]]

class ethernet_t(Header):
    dstAddr: bit48
    srcAddr: bit48
    etherType: bit16

class ipv4_t(Header):
    version: Bits[L[4]]
    ihl: Bits[L[4]]
    diffserv: bit8
    totalLen: bit16
    identification: bit16
    flags: Bits[L[3]]
    fragOffset: Bits[L[13]]
    ttl: bit8
    protocol: bit8
    hdrChecksum: bit16
    srcAddr: bit32
    dstAddr: bit32

class headers(Struct):
    ethernet: ethernet_t
    ipv4: ipv4_t

class metadata(Struct):
    ingress_port: bit9
    egress_port: bit9
    drop: Bool

class EtherType(IntEnum):
    IPV4 = 0x800

class MyParser(Parser[headers, metadata]):
    @state(start=True)
    def start(self) -> Transition:
        return self.goto(self.parse_ethernet)

    @state
    def parse_ethernet(self) -> Transition:
        self.extract(self.hdr.ethernet)
        return self.select(self.hdr.ethernet.etherType,
                           {EtherType.IPV4: self.parse_ipv4}, default=self.accept)

    @state
    def parse_ipv4(self) -> Transition:
        self.extract(self.hdr.ipv4)
        return self.accept

csum = Checksum16[Bits[L[144]]]("csum")

class MyIngress(Control[headers, metadata]):
    @action
    def NoAction(self) -> None:
        pass

    @action
    def drop(self) -> None:
        self.assign(self.meta.drop, True)

    @action
    def ipv4_forward(self, dstAddr: bit48, port: bit9) -> None:
        self.assign(self.meta.egress_port, port)
        self.assign(self.hdr.ethernet.srcAddr, self.hdr.ethernet.dstAddr)
        self.assign(self.hdr.ethernet.dstAddr, dstAddr)
        self.assign(self.hdr.ipv4.ttl, self.hdr.ipv4.ttl - 1)

    ipv4_lpm = Table(keys=[lpm(headers.ipv4.dstAddr)],
                     actions=[ipv4_forward, drop, NoAction],
                     default=drop(), size=1024)

    def apply(self) -> None:
        with self.if_(self.hdr.ipv4.is_valid()):
            self.apply_table(self.ipv4_lpm)
        with self.if_(self.hdr.ipv4.is_valid()):
            ipv4 = self.hdr.ipv4
            data = concat(ipv4.version, ipv4.ihl, ipv4.diffserv, ipv4.totalLen,
                          ipv4.identification, ipv4.flags, ipv4.fragOffset,
                          ipv4.ttl, ipv4.protocol, ipv4.srcAddr, ipv4.dstAddr)
            self.assign(ipv4.hdrChecksum, csum.compute(data.as_(Bits[L[144]])))

class MyDeparser(Deparser[headers]):
    def apply(self) -> None:
        self.emit(self.hdr.ethernet)
        self.emit(self.hdr.ipv4)

program = Program("forwarder", headers=headers, metadata=metadata,
                  parser=MyParser, control=MyIngress, deparser=MyDeparser,
                  externs=[csum])
```

Every name a reader could mistype is now an attribute pyright resolves:
`self.parse_ipv4`, `ipv4_forward`, `self.ipv4_lpm`, `headers.ipv4.dstAddr`,
`MyParser`. Every width is in the type of the thing.

## How it works

**Values.** `class Bits[W: int]` is the expression type for `bit<N>`;
`Bool` for `bool`; enum and error values keep their own classes.
Operators are typed `(self: Bits[W], other: Bits[W] | int) -> Bits[W]`,
which is exactly the run-time rule (an `int` takes the other operand's
width and must fit). Comparisons return `Bool`. Casts are
`x.cast(Bits[L[16]])` and typed `-> Bits[V]`. `concat`, slices and
`lookahead` cannot be typed exactly (the type system has no width
arithmetic), so they return `Bits[Any]`; `x.as_(Bits[L[16]])` asserts
a width at run time and narrows it for the checker. Widths are spelled
`Bits[L[8]]` with `L = Literal`; the package exports aliases
`bit1`..`bit64`. A `bit(n)` function keeps the dynamic form for
generated programs, typed `Bits[Any]`.

**Headers and structs.** Class-body annotations declare fields;
`__init_subclass__` reads them with `get_type_hints`, recovers each
width from the `Literal`, and builds the `pb.HeaderType`. The IR name is
the class name unless `name=` is given as a class keyword. A view bound
to an lvalue path sets one real attribute per field in `__init__`, so
there is no `__getattr__`, typos are static errors, and `hdr.eth.type`
means the field. Reserved names (the view's own methods) are refused at
class definition with a "did you mean" message and an escape hatch
`view.field("type")` is kept for generated code.

**Blocks.** `Parser[H, M]`, `Control[H, M]`, `Deparser[H]` are generic
in the program's types, so `self.hdr` and `self.meta` are statically
typed. A block class is assembled once: `@state` methods are called
with a recording `self` and must return a `Transition` (`self.goto(m)`,
`self.select(...)`, `self.accept`, `self.reject`); the first `@state`
or the one marked `start=True` is the start state. `@action` wraps a
method into an `Action[P]` whose `ParamSpec` is the method's
parameters after `self`; calling it inside a body records a
`call_action`, calling it in a class body (a table's `default=` or
const entries) produces an `ActionCall` literal; both are checked by
pyright against the declared parameters. Actions with directional
parameters use `In[...]`/`Out[...]`/`InOut[...]` annotations. `Table`
is a class attribute holding action objects, keys as typed
expressions, and typed const entries. The control's `apply` and the
deparser's `apply` are called once to record the body.

**Sub-blocks.** A parser or control class with extra parameters
declares them as annotated attributes with `In`/`Out`/`InOut`; a call
is `self.call(SubParser, self.hdr.ipv4, self.meta.x)`, typed by a
`Callable` protocol generated from the annotations.

**Externs.** An extern family is a class with typed method signatures
whose parameters carry directions: `class Register[W: int](Extern):
def read(self, result: Out[Bits[W]], index: In[bit32]) -> None`. The
IR `ExternType` is derived from the signatures; the instance
`Register[bit8]("r", size=4)` binds `W`; a call `r.read(self.meta.x,
idx)` is checked against the signature. A returning method used in
expression position (`csum.compute(data)`) records a `call_extern`
with the assignment target as `result`, the elaboration the coverage
table already names.

**Control flow.** Unchanged: `with self.if_(c):`, `elif_`, `else_`,
`mux(c, a, b)`, `select` with typed key sets. Literal rules unchanged:
an `int` takes the width of the other operand and must fit; a literal
with no context is written `bit8(1)`, which types as `Bits[L[8]]`.
Constants are `IntEnum`s (pakeles's `LabeledEnum` if labels are
wanted), never bare ints.

**Errors.** Every `EdslError` ends with `(defined at file:line)` taken
from the nearest frame outside the package.

**Program.** `Program(name, headers=..., metadata=..., parser=...,
control=..., deparser=..., externs=[...])` takes classes and instances,
never names; roles are keyword arguments, so `p.export("parser", ...)`
disappears. The current builder becomes the implementation layer
(`p4blo.edsl.core`), untouched, so v2 is a typed front on top of the
code that produces today's goldens.

## What pyright checks, and what it cannot

| Checked statically | Run time only |
|---|---|
| field names, state, action, table, block names | width of concat, slices, lookahead (`Bits[Any]`, narrowed by `as_`) |
| equal widths in arithmetic, comparison, assignment | that an `int` literal fits its width |
| cast target widths | select key-set values against the key type |
| action argument count and widths in calls, defaults, entries | table key match-kind rules, everything the validator owns |
| extern method names, argument directions and widths | |

The run-time checks are the same ones v1 has today; nothing gets
weaker. Static checking is a second, earlier line.

## Migration

1. Build v2 in `python/p4blo/edsl/` beside the current modules, with
   the current builder as its implementation layer.
2. Rewrite each corpus source in v2; the acceptance test is equality
   with the committed golden, exactly as for v1. Goldens do not change.
3. Add pyright-based tests: files that must type-check and files that
   must fail with specific diagnostics (pyright's `--outputjson`), so
   the static guarantees are tested, not assumed.
4. Retire the v1 surface (keep `bit(n)`, `p.header(name, **fields)`
   and friends as the documented dynamic API for generated programs).
5. Update `docs/design.md`'s eDSL section and the coverage table's
   elaboration names that mention eDSL forms.

## Open questions for Bili

- **Spelling of widths.** `Bits[L[8]]` everywhere, or the generated
  aliases `bit8`, `bit16`, ... as the house style? The probes used both.
- **Statements.** `self.assign(target, value)` as today, or operator
  sugar such as `target @= value` (Magma) / `target <<= value` (PyRTL)?
  Explicit reads better and types better; sugar reads shorter.
- **Directional annotations.** `Out[Bits[W]]` as a typing alias that
  pyright sees through (`Annotated`), or distinct wrapper types that
  the checker enforces at call sites? The second is stricter and
  noisier.
- **Const entries.** `entry((masked(1, 0xFF), 2), ipv4_forward(3, 1))`
  typed against the key types is possible with one more generic on
  `Table`; worth it in v2, or later?
- **Scope.** Do this before or after a p4c backend? It is orthogonal to
  the four claims and touches only the eDSL and corpus sources.
