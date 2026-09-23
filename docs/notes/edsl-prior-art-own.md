# Prior art from Bili's own repos: p4py and pakeles, read against p4blo's eDSL

Clones: `/private/tmp/claude-501/-Users-qobilidop-my-work-p4blo/07cfdaea-e2c5-4c99-819f-19a428efb35b/scratchpad/{p4py,pakeles}` (abbreviated `$S/p4py`, `$S/pakeles` below). p4blo's current eDSL is `/Users/qobilidop/my/work/p4blo/python/p4blo/edsl/{types,expr,blocks,program,externs}.py`, used by `corpus/forwarder/forwarder.py` and `corpus/acl/acl.py`.

## 0. The one-paragraph verdict

The two repos sit at opposite corners of the design space and p4blo today sits at a third:

| | p4py (2026-03/04) | pakeles (2026-07/08) | p4blo now |
|---|---|---|---|
| Mechanism | Decorators capture **source**, compiler pattern-matches the **AST** | **Direct construction**: class bodies + operator trees + fluent chains, run at assembly | Direct construction via builder methods and `with` blocks |
| Headers | `class ethernet_t(p4.header): dstAddr: p4.bit(48)` (annotations) | `class Ethernet(Header): dst = bits(48, ...)` (class attributes) | `p.header("ethernet_t", dstAddr=bit(48))` (kwargs) |
| Field reference | `hdr.ethernet.dstAddr` (AST path; never a Python object) | `Ethernet.ethertype` (a real class attribute, a `FieldSpec`) | `c.hdr.ethernet.dstAddr` (`Expr.__getattr__`, checked at runtime against a `TypeTable`) |
| Widths | Data on `BitType(width)`; **nothing checked in Python**, p4c decides | Data on `FieldSpec.width_bits`; ints are widthless constants; only select-arm range is checked | Every `Expr` carries a `pb.Type`; int literals get width from context; mismatch is an `EdslError` |
| Control flow | Real `if/elif/else`, `match` | `select({arm: target})` only; no if | `with b.if_()/elif_()/else_()`, `select({...})` |
| State/action refs | Bare names read from AST (strings in effect) | Bound methods `self.parse_ipv4` (pyright-checked) or strings | Strings or builder objects (`StateBody`, `ActionBody`) |
| pyright | Fails on every header (call in type expression) | Strict, clean, enforced in CI | Not exercised by the two repos; p4blo's `__getattr__`-based paths type as `Expr` with no field checking |

pakeles is the repo to learn *declarations and references* from; p4blo already does *width typing* better than either. p4py is mostly a cautionary tale, but its parser/control bodies read better than anything else here, which matters when comparing "how much ceremony per statement".

---

## 1. p4py

### 1.1 What it is, status

- "A Python eDSL for P4 network programming" that compiles Python to P4-16 source for v1model/eBPF and also simulates it. `$S/p4py/README.md` is three lines; the real doc is `$S/p4py/docs/architecture.md`.
- Git: 185 commits, **2026-03-27 to 2026-04-04** (nine days), nothing since. Co-authored by Claude Opus 4.6 throughout.
- Size: package `src/p4py` is ~3.6k lines (`lang.py` 388, `compiler.py` 1029, `ir.py` 413, `emitter/p4.py` 511, `sim/engine.py` 711, `arch/{base,v1model,ebpf_model}.py`); 12.5k Python lines total including tests.
- Tests: absltest unit tests per layer (`tests/unit/{lang,ir,compiler,emitter,sim,arch}`), golden `.p4` tests, STF tests run on its **own simulator** (BMv2 was removed: `fa7aef2 Remove BMv2 code from stf_runner`, `6177bf7 Revert "Add design spec for BMv2 to p4testgen test migration"`), and p4testgen tests. Corpus: `examples/basic_forward.py`, six p4c samples, and a large SAI-P4 transcription (`tests/e2e/sai_p4/`, `wbb.py` + `tor.py` with a `fixed/` layer).
- Docs: Sphinx; `docs/p4-spec-coverage.md` is **stale** (says casts, slicing, ternary, comparisons are "No"; the code supports all four by the last commits).
- Lint: ruff only. `tools/lint.sh` runs `ruff check src/ tests/`; **no pyright or mypy anywhere** in the repo.

### 1.2 N-bit typed values

`$S/p4py/src/p4py/lang.py:16-31`:

```python
@lru_cache(maxsize=256)
def bit(width: int) -> BitType:
    """Create a bit<W> type. Cached so that bit(8) is bit(8)."""
    ...
@dataclass(frozen=True)
class BitType:
    width: int
```

Plus `_NamedType(underlying, name, kind)` for `typedef`/`newtype` (`lang.py:37-57`), `enum(underlying)` returning a base class whose `__init_subclass__` harvests int class attributes (`lang.py:68-90`), `_Const`, and `BoolType` singleton `p4.bool`.

Widths do **not** flow through operators, because expressions are never Python objects: block bodies are captured as source and re-parsed.

```python
# lang.py:305-313
def _make_decorator(kind: str):
    def decorator(func):
        source = textwrap.dedent(inspect.getsource(func))
        annotations = {k: v for k, v in func.__annotations__.items() if k != "return"}
        return _Spec(kind=kind, name=func.__name__, source=source, annotations=annotations)
```

The IR literal is `IntLiteral(value, width: int | None = None, hex: bool = False)` (`ir.py`); `p4.literal(v, width=N)` emits `Nw v`, a bare int emits a bare int and **p4c infers the width**. The helpers are identity functions at runtime, present only so the AST has a recognizable shape:

```python
# lang.py:268-286
def literal(value: int, *, width: int) -> int: return value
def hex(value: int) -> int: return value
def mask(value: int, mask: int) -> int: return value
def cast(type_ref, value): return value
```

Width mismatch: nothing in Python notices. The simulator stores unmasked ints (`sim/engine.py:672-684 _set_field`) and evaluates `ArithOp` as plain `left - right` (`engine.py:587-596`), so `ttl - 1` at 0 becomes -1 in simulation; only p4c on the emitted text reports a real width error.

### 1.3 Declarations and references

Headers/structs are classes with **annotations**, harvested by `__init_subclass__`; the P4 name is the class name:

```python
# lang.py:126-150
class header:
    def __init_subclass__(cls, **kwargs: object) -> None:
        for name, ann in cls.__annotations__.items():
            if not _is_bit_like(ann):
                raise TypeError(f"Header field '{name}' must be annotated with bit(W), got {ann!r}")
        cls._p4_name = cls.__name__
        cls._p4_fields = tuple(fields)
```

Usage (`$S/p4py/examples/basic_forward.py`):

```python
class ethernet_t(p4.header):
    dstAddr: p4.bit(48)
    srcAddr: p4.bit(48)
    etherType: p4.bit(16)

class headers_t(p4.struct):
    ethernet: ethernet_t

@p4.parser
def MyParser(pkt, hdr: headers_t, meta: metadata_t, std_meta):
    def start():
        pkt.extract(hdr.ethernet)
        return p4.ACCEPT

@p4.control
def MyIngress(hdr, meta, std_meta):
    @p4.action
    def forward(port: p4.bit(9)):
        std_meta.egress_spec = port
    mac_table = p4.table(
        key={hdr.ethernet.dstAddr: p4.exact},
        actions=[forward, drop],
        default_action=drop,
    )
    mac_table.apply()
```

- Blocks are functions; **parameters are the block params**, directions via `p4.in_(headers_t)` / `p4.inout(...)` in the annotation (`lang.py:353-381`; `in_` is also reachable as `getattr(p4, "in")` through a module `__getattr__`, `lang.py:385`).
- Field access `hdr.ethernet.dstAddr` becomes `ir.FieldAccess(path=("hdr","ethernet","dstAddr"))` by walking `ast.Attribute` (`compiler.py:202-213`). It is never type-checked; a misspelled field reaches p4c.
- Actions are nested `@p4.action` defs; tables are `name = p4.table(...)` assignments; `actions=[forward, drop]` looks like object references but the compiler only reads the identifier (`compiler.py:872-877: action_names.append(elt.id)`), so **every reference is by name**. Partial application `set_nexthop_id(local_metadata)` in an action list is turned into the string `"set_nexthop_id(local_metadata)"` (`compiler.py:878-898`).
- Parser states are nested defs; the first def is `start`; `return parse_ipv4` is a transition and the target is the bare name (`compiler.py:536-545`). Forward references are free since nothing is executed.
- Local variables are declared by assigning a type: `ttl = p4.bit(8)` (`_is_local_var_decl`, `compiler.py:750-755`), and later `ttl = headers.ipv4.ttl` is an assignment. The same syntax means two things depending on the RHS shape.
- Externs are module-qualified calls (`v1model.mark_to_drop(std_meta)`); the compiler strips any attribute base that is not a block param (`compiler.py:441-466`). `direct_counter`, `direct_meter`, `action_selector` are recognized by `func.attr` name only.
- Sub-controls: `acl_ingress.apply(headers, local_metadata, standard_metadata)`, and the package must be told about everything explicitly: `tor.py:344-415` lists `sub_controls=(...)`, `file_scope_actions=(...)`, and **71 lines of `declarations=(...)`** naming every typedef, newtype, enum and const, because there is no program-level registry.

### 1.4 Control flow

Real Python, compiled from AST:

- `if/elif/else` → `ir.IfElse` (`compiler.py:367-383`); an `elif` nests as an `If` in `orelse`.
- `match table.apply(): case "action_name": ...` → `SwitchAction` (`compiler.py:385-406`).
- Parser select is a `match` on one subject; case values are ints or dotted constant names (`ConstRef`); `case _:` is default; each case body must be exactly one `return` (`compiler.py:548-577`):

```python
# tor.py:115-123
match headers.ethernet.ether_type:
    case _c.ETHERTYPE_IPV4: return parse_ipv4
    case _: return p4.ACCEPT
```

- `table.apply().hit` is matched structurally (`compiler.py:300-309`).
- `docs/architecture.md` argues for AST over tracing: "tracing (executing with proxy objects) would only see one execution path per run, making it unsuited for capturing parser state machines. The restriction on Python features inside decorated functions is a feature, not a bug."

### 1.5 Static type safety

None, and it cannot be retrofitted on this design. Verified with `pyright --strict` on `examples/basic_forward.py` (p4blo's venv pyright):

```
basic_forward.py:12:14 - error: Call expression not allowed in type expression (reportInvalidTypeForm)   # dstAddr: p4.bit(48)
basic_forward.py:34:6  - error: Untyped function decorator obscures type of function; ignoring decorator
basic_forward.py:43:14 - error: Type of "dstAddr" is unknown (reportUnknownMemberType)                 # hdr.ethernet.dstAddr
```

`x: p4.bit(48)` is illegal as a type expression; `hdr` in a control has no annotation; `pkt`, `std_meta` are untyped; `p4.table` returns a sentinel with no `.apply`. The whole point of the design is that the code is never executed, so it is also never type-checked.

### 1.6 Worth adopting / what did not work

Adopt (surface ideas, not mechanism):

- **Bodies that read like P4.** `acl_ingress.py` holds an entire SAI ACL control (15 actions, 3 tables, an if-ladder) in 280 lines with no `with` nesting and no `a.assign(x, y)`; the equivalent in p4blo's builder would be `with c.action(...) as a: a.assign(...)` per statement. p4blo cannot take the AST route (see pakeles's argument below), but the *density* target is worth keeping in view.
- Table keys as `{expr: match_kind}` with an optional `("name", expr)` tuple key for `@name` (`compiler.py:943-965`); action lists holding the action objects.
- The `fixed/` + `instantiations/` module layout: headers, metadata and sub-controls in importable Python modules composed by a top-level program. p4blo's single `Program` object would need declarations to be program-independent for this to work (pakeles shows how).
- `p4.literal(v, width=N)` as the explicit-width literal spelling. p4blo has `p.literal(value, type)`.

Did not work / scars:

- **AST pattern matching does not scale**: `compiler.py` is 1029 lines of `isinstance(node, ast.Call) and node.func.attr == "bit"` chains, each new construct a new special case; `_compile_local_var` distinguishes a declaration from an assignment by the RHS shape.
- Everything is stringly: `FieldAccess.path`, action names, `type_name: str` in `ActionParam`, `StructMember.type: BitType | BoolType | str`. No type information exists in Python, so widths, unknown fields and bad casts surface only from p4c, and the simulator is silently wrong on wraparound.
- The explicit `declarations=(...)` list in `tor.py` (70 lines) is the cost of having no registry.
- The module split `lang/_types.py` + `lang/_blocks.py` (`4f5beac`) was flattened back into one `lang.py` a day later (`35eabe9 Flatten modules and rename backend to emitter`).
- BMv2-in-the-loop STF was dropped for an in-Python simulator (`fa7aef2`), which then needed its own coverage docs and drifted from the real target.
- The coverage doc was not kept in sync with the code in the final sprint.
- The project stopped after nine days at the point where SAI-P4 `tor.p4` compiled, i.e. right when the AST compiler was at its most special-cased.

---

## 2. pakeles

### 2.1 What it is, status

- A Rust toolchain around a serializable **packet-parser IR** (proto3 `pakeles.ir.v1alpha1`) with a Python eDSL as the authoring surface; the Rust CLI validates/canonicalizes and derives interpreter, symbolic testgen, Wireshark Lua, C99, eBPF and P4-16 backends. Domain is **parsers only**: extract, lookahead, select, accept/reject, metadata assigns, sized regions. No controls, tables, actions, arithmetic beyond `+ - * << >> & |`, no comparisons.
- Git: 316 commits, **2026-07-18 to 2026-08-03**; README says "Work in progress, iterating fast, don't use this yet." Co-authored by Claude Fable 5.
- Python package `$S/pakeles/python/src/pakeles`: ~1.4k lines (`_states.py` 517, `_build.py` 279, `_header.py` 207, `_expr.py` 211, `_parser.py` 211, `_metadata.py` 78, `_labels.py` 57, `fmt.py`), vendored `_pb/ir_pb2.py(i)`, `py.typed`. 16 pytest modules under `python/tests`.
- Gallery: 15 parsers authored in the eDSL (7 industry incl. Linux flow dissector, Katran, DPDK ptype, DASH, QUIC; 8 academic incl. the full switch.p4 parser, 63 states). Every one is proto-equality-tested against its committed `ir.json` (`python/tests/test_conformance.py`), the same acceptance pattern as p4blo's `test_forwarder_equals_the_golden`.
- Docs: design spec `docs/superpowers/specs/2026-07-19-python-edsl-design.md`, review notes `docs/plans/2026-08-01-edsl-ir-review-followups.md`, normative `docs/reference/ir-semantics.md`.
- CI: `ruff` + **`pyright` strict** + pytest, gallery included (`pyrightconfig.json`: `"typeCheckingMode": "strict"`, include `python/src, python/tests, examples`; note `benchmarks/` is not in the include list after the 2026-07-31 layout move, a small drift from what `python/README.md` claims).

### 2.2 N-bit typed values

Width is **data on a field spec**, not a type parameter:

```python
# _expr.py:158-177
@dataclass
class FieldSpec(Operand):
    width_bits: int | None = None
    bit_len_expr: Expr | None = None
    display_name: str = ""
    ...
    name: str = ""      # assigned by Header.__init_subclass__
    header: str = ""
```

```python
# _header.py:35-55
def bits(width: int, display: str = "", format: ir_pb2.DisplayFormat = ..., *, doc="", labels=None, tshark=None) -> FieldSpec:
    if not 1 <= width <= 64:
        raise ValueError(f"bits width must be 1..64, got {width}")
```

Operators build an eager tree via a mixin, and **ints are widthless unsigned constants**:

```python
# _expr.py:32-43
class Operand:
    def as_expr(self) -> Expr: raise NotImplementedError
    def _bin(self, op: str, other: object, swap: bool = False) -> Expr:
        rhs = coerce_expr(other); lhs = self.as_expr()
        ...
        return Expr(op=_OPS[op], lhs=lhs, rhs=rhs)

# _expr.py:206-211
def coerce_expr(v: object) -> Expr:
    if isinstance(v, int): return const(v)
    if isinstance(v, Operand): return v.as_expr()
    raise TypeError(f"cannot use {v!r} in a field expression")
```

There is **no width checking on operators** in Python; the IR value domain is Z_2^64 by decision ("the value domain is Z_2^64 by design; wider fields are opaque byte runs", review notes, Idea 4), and the Rust validator is the sole authority. The Python-side width checks that do exist are select-arm values against the key width and metadata init values:

```python
# _build.py:107-112
if bound >= 1 << key_spec.width_bits:
    raise ValueError(f"state {sname!r}: arm value {bound:#x} does not fit "
                     f"{key_spec.header}.{key_spec.name} ({key_spec.width_bits} bits){here}")
```

Fields over 64 bits are opaque `fixed_bytes`/`var_bytes(len_expr)` runs ("wide bytes may be matched, never computed"). This is less than what p4blo already has (`Expr._same` refuses `bit<16>` vs `bit<8>`, `literal()` refuses ints that do not fit).

### 2.3 Declarations and references

**Headers**: class bodies where the attribute name is the field name and the IR name is a snake-cased class name unless overridden with a class keyword:

```python
# _header.py:118-144
class Header:
    _fields: ClassVar[list[FieldSpec]] = []
    def __init_subclass__(cls, name: str | None = None, **kwargs: object) -> None:
        cls._name = name if name is not None else snake(cls.__name__)
        for attr, value in vars(cls).items():
            if isinstance(value, FieldSpec):
                value.name = attr
                value.header = cls._name
                fields.append(value)
        cls._fields = fields
    def __init__(self) -> None:
        raise TypeError("Header classes are declarations; do not instantiate")
```

Earlier fields are in scope for later ones, and references hold the **object**, resolving names lazily:

```python
# examples/eth_ipvx_l4/eth_ipvx_l4.py:40-54
class IPv4(Header):
    version = bits(4, "Version", DEC, tshark="ip.version")
    ihl     = bits(4, "Header Length", DEC, doc="in 32-bit words")
    ...
    options = var_bytes(ihl * 4 - 20)
```

"Field references hold the `FieldSpec` *object* and resolve to (header, field) names lazily at serialization: inside a Header class body the spec's name/header are not yet assigned ... but the object identity is already stable." (`_expr.py` module doc.)

**Header instances** (repeated extraction of one type) use class subscript and module-level binding:

```python
# _header.py:149-155
def __class_getitem__(cls, name: str) -> Instance:
    """`VLAN["vlan_q"]`: a named extraction of this header type."""
# katran_parser.py:133
icmp = ICMP["icmp"]  # one shared instance for both families
```

`Instance.__getattr__` returns a `BoundField(spec, instance)` presenting the same `(name, header, width_bits)` surface as `FieldSpec`.

**Families** of near-identical headers via a factory that goes through the same `__init_subclass__`:

```python
# _header.py:102-115
def header(name: str, /, **fields: FieldSpec) -> type[Header]:
    """... Reference the family's fields through the `FieldSpec` objects you passed
    (here `t`), not as class attributes — the type checker cannot see manufactured
    attributes, and the whole point is keeping every reference a name it can check."""
    return types.new_class(name, (Header,), exec_body=lambda ns: ns.update(fields))
```

**Metadata**: the same pattern (`class QuicMeta(Metadata): kind = metadata_bits(3, ...)`, `_metadata.py`).

**Parsers**: a class; each state is a method; the def name is the state name; targets are bound-method references:

```python
# examples/eth_ipvx_l4/eth_ipvx_l4.py:89-117
class EthIpvxL4(Parser):
    max_depth = 4
    def parse_ethernet(self) -> State:
        return extract(Ethernet).select(
            Ethernet.ethertype,
            {EtherType.IPV4: self.parse_ipv4, EtherType.IPV6: self.parse_ipv6},
            default=reject("unsupported ethertype", info=True),
        )
    def parse_tcp(self) -> State:
        return extract(TCP).accept()
```

Assembly instantiates the class and calls every non-underscore method once, then swaps method references for name strings (`_parser.py:157-193 _assemble`, `_parser.py:85-125 _resolve_all`). "Bodies run only at assembly time ... so forward references, back edges, and self-loops cost nothing." The first-defined method is the start unless `start = parse_ethernet` is set; `_RESERVED = {"name","max_depth","metadata","start","check","to_pb","to_json","save"}` are not states; subclasses/mixins add and override states (`python/tests/test_parser_machinery.py`: `class Rung0(L4Tail, Parser)`, `class Rung1(Rung0)`).

Targets are a typed union; strings stay valid as the P4-convention forward reference:

```python
# _states.py:475-477
Target = str | StateRef | Accept | Reject | State
```

An inline `State` chain as a target is hoisted into a real state named `<parent>__<arm label>` (`.named()` overrides), so one-line continuations need no method (`48c2a5e`).

**One vocabulary for dispatch and display**:

```python
# _labels.py:18-39
class LabeledEnum(IntEnum):
    def __new__(cls, value: int, label: str | None = None) -> Self: ...
# eth_ipvx_l4.py:18-24
class EtherType(LabeledEnum):
    IPV4 = 0x0800, "IPv4"
    ARP = 0x0806
```

Members are ints, so they are select keys directly and also feed `bits(labels=EtherType)`; "a mistyped member name fails at import time instead of silently dispatching a wrong wire value."

**Docstrings** of the parser class and each state method become IR `annotations["doc"]` (`_parser.py:176-185`), rendered by docgen and as SVG tooltips.

**Source locations** for assembly-time errors: every `State` records the nearest stack frame outside the package (`_states.py:126-136 _caller_src`), and errors append `(defined at file:line)`; deliberately never emitted into the IR so goldens stay machine-independent (`199a839`).

### 2.4 Control flow

Only `select`; there is no `if`. Arm keys are ints, `oneof(...)`, Python `range`, `masked(v, m)`, or tuples of those for multi-key selects, expanded at `select()` time with duplicate/overlap detection and a size budget (`_states.py:403-452`). `default=` may be omitted when arms provably cover the key's whole value space; a gap is an error listing the smallest missing values with their labels (`_states.py:182-223 _exhaustive_default`).

The design spec is explicit that this is a domain decision, not a limitation to fix, and it names the criterion (`2026-07-19-python-edsl-design.md`, "Mechanism"):

> The criterion that predicts which mechanism wins in ML is **op granularity × control-flow freedom** ... Coarse-grained ops with restricted control flow (`nn.Sequential`, `tf.data` pipelines, Beam) are authored by direct construction — as are parsers ... Additionally, our select is deliberately impoverished; a Python `if`-based surface would syntactically overpromise and the compiler would become a rejection machine (the almost-Python trap at miniature scale).

> **Honest Python**: no tracing, no AST reading, no staged control flow. ... Build-time metaprogramming (a `for` loop emitting fields/states) is ordinary and encouraged.

Re-affirmed after a design review: "Imperative/AST-rewritten eDSL surface: rejected permanently" (`docs/plans/2026-08-01-edsl-ir-review-followups.md`, Non-goals). The escape-hatch ladder is "(1) build-time metaprogramming; (2) new coarse combinators; (3) only if the IR ever grew kernel-like op density ... a Triton-style scoped micro-language."

For p4blo the criterion cuts partly the other way: its IR has `if/else`, `mux`, saturating arithmetic and extern calls, i.e. finer ops with real control flow. That argues against pakeles's *no-if* stance for controls but not against direct construction; it argues for keeping p4blo's explicit `if_`/`else_` builders rather than reading Python `if`.

### 2.5 Static type safety

Verified: pyright strict on `examples/eth_ipvx_l4/eth_ipvx_l4.py` and `python/src/pakeles/_parser.py` with the repo's own config gives `0 errors`. What the checker sees (via `reveal_type`):

```
Type of "Ethernet.ethertype"        is "FieldSpec"
Type of "IPv4.ihl * 4 - 20"         is "Expr"
Type of "EthIpvxL4.parse_ipv4"      is "(self: EthIpvxL4) -> State"
Type of "Ethernet["inner"].ethertype" is "FieldSpec"      # statically the class, at runtime a BoundField
```

So a misspelled field (`Ethernet.ethertyp`) or state (`self.parse_ipv`) is an editor error; a target dict is `dict[ArmKey, Target]` with `Target = str | StateRef | Accept | Reject | State`. The tricks that make this work:

- Fields are ordinary class attributes (no `__getattr__`), so completion, rename and jump-to-def work. The `header()` factory docstring spells out the rule: keep every checked name a real name.
- `StateRef` and `StateFunc` are `Protocol`s with `__name__: str` and a zero-arg `__call__` (`_states.py:66-74`, `_parser.py:61-67`), so a bound method satisfies the target type without the class knowing its subclasses.
- `Parser` attributes are `ClassVar`s (`name`, `max_depth`, `metadata`, `start: ClassVar[StateFunc | None]`).
- `ArmKey`/`ArmValue`/`SelectKey` are plain union aliases (`_states.py:116-120`).
- The four `# type: ignore[attr-defined]` in `_build.py`/`_header.py` are all `cls._fields` ClassVar reads on `type[Header]`.

What pyright does **not** see: widths. `FieldSpec` is not generic; `bits(16)` and `bits(8)` have the same static type. `Header["x"]` is typed as the class itself (pyright treats a class subscript as a generic alias), so `BoundField` vs `FieldSpec` is invisible statically; harmless because both present the same surface. No `Literal[N]` generics or overloads were attempted anywhere in the repo.

### 2.6 Worth adopting / what was tried and dropped

Adopt:

1. **Declarative header/struct classes** with attribute name = field name and an `__init_subclass__(cls, name=...)` override for the IR name. This directly removes p4blo's `Expr.__getattr__` opacity and the documented shadowing rule ("`hdr.eth.type` is the expression's `pb.Type`, not the member; `hdr.eth.field("type")` always means the field", `expr.py`), and p4blo's `Key.__post_init__` hint about it. p4blo can keep its typed `Expr` while making fields real attributes (a descriptor per field that yields a typed `Expr` when accessed through a typed path is the natural bridge).
2. **Blocks as classes, states/actions as methods, targets as `self.<method>`**, assembled by running each method once. p4blo's `Parser.state("name")`/`transition("parse_ipv4")` strings and `Control.action("name")`/`actions=["drop"]` strings become checked names; forward references stop needing declaration order (p4blo's `Parser.build` checks unknown targets only at build).
3. **`LabeledEnum`** for the constants that feed both select arms and table entries (p4blo's `TYPE_IPV4 = 0x800` in `forwarder.py` is a bare int).
4. **Source-location provenance** in build-time errors (p4blo's `EdslError` names the block and field but not the file:line of the offending call).
5. **Exhaustive-select default synthesis** and overlap detection on select arms (p4blo's `select` accepts anything and defers to the validator).
6. `check()`/`to_pb()`/`save()` as classmethods on the program class; docstrings lifted into IR annotations if p4blo's IR gains them.
7. The **"keep every checked name a real name"** rule for families: a `header()` factory plus helper functions returning inline chains, never dynamic method generation.
8. Module-level binding of instances/aliases (`icmp = ICMP["icmp"]`) as the house idiom for repeated names; and typed `dict[ArmKey, Target]` helpers (`_ethertype_arms()` in `p4lang_switch_parser.py:593`) as the replacement for P4's CPP macros.

Tried and dropped, or explicitly rejected:

- The **initial dict-of-states design** in the spec (`parser("eth_ipv4_tcp", start="ethernet", states={"ethernet": extract(...).select(..., {0x0800: "ipv4"})})`, string forward refs) shipped 2026-07-19 and was replaced on 2026-07-31 by classes-with-methods (`ccf1878`): "typos are unknown-attribute errors at edit time, and lazy bodies make forward references, back edges, and self-loops free." String targets survive only as the internal representation.
- Names `ParserDef`/`StateChain`/`Meta`/`meta_bits` were renamed the same day to P4-16's nouns `Parser`/`State`/`Metadata` (`78b92a8`): "Django trained readers to parse 'Meta' as model options."
- A `const()` helper was dropped because `coerce_expr` lifts bare ints (`78b92a8`).
- **Header stacks as an eDSL/IR feature were designed and withdrawn** (`80ed6cf` then `a1076ef`): repeated extraction under one instance plus `max_depth` already gave the observables; exact-count caps became a "specified, build on trigger" per-instance cap. Not transferable as-is (p4blo's IR has stacks for match-action reasons the note itself names), but the decomposition method is.
- **Emulating lookahead** by splitting headers into nibble types was replaced by an IR primitive because "distortion reaches observable output (dissector/docs), not just authoring."
- Byte-denominated lengths were re-denominated to bits in the IR, while the **frontend stayed unit-explicit** (`var_bytes` and `var_bits`, `push_region(bytes=|bits=)`): "P4-16's bit-uniform surface has a known forgot-the-×8 papercut class."
- Source locations are deliberately not emitted into the IR until there is a path-canonicalization story.
- An `assume` name for lookahead was rejected for colliding with verification vocabulary; the P4 term won.

---

## 3. What this means for p4blo's redesign

- **Keep** p4blo's typed `Expr` (width from context, `_same` mismatch errors, explicit casts only). Neither prior repo checks widths in Python; pakeles delegates to Rust, p4py to p4c. p4blo's `literal()`/`_shift` rules are strictly more than either offers and should survive any surface change.
- **Replace** kwargs-and-strings declarations with pakeles-style classes: `class ethernet_t(Header): dstAddr = bit(48)`; `class MyParser(Parser)` with state methods; `class MyIngress(Control)` with action methods and tables as class attributes; targets and action lists holding the methods. This is the change that makes pyright useful and removes the `__getattr__` name-shadowing trap.
- **Do not** go the p4py way of reading Python `if`/`match` from source. Both the pakeles spec and the p4py code base itself show why: the compiler becomes a 1000-line special-case matcher with no static typing possible. p4blo's IR has richer control flow than pakeles's, so its explicit `if_`/`elif_`/`else_` builders stay, but they can live on a body object obtained from a method rather than nested `with` blocks, and p4blo's `select({...}, default=)` is already the pakeles shape.
- **Width-carrying static types** (`Bits[Literal[8]]`-style generics) are untried in both repos; pakeles consciously settled for "names are checked, widths are not" and got a clean strict-pyright surface out of it. If p4blo wants widths visible to pyright, that is new ground relative to both.
- Small things to copy verbatim: `LabeledEnum`, `_caller_src` provenance, exhaustiveness/overlap checks on select, `name=` class keyword for IR names, the "real names only" rule for generated families, and the conformance test as the acceptance gate (already in place).
