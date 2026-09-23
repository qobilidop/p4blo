# Python eDSL prior art for redesigning p4blo's eDSL

Survey date: 2026-09-22. Sources are the primary docs and source files
linked inline; short quotes are verbatim. Pyright claims were checked
locally with pyright 1.1.411; the experiment files are under
`/private/tmp/claude-501/-Users-qobilidop-my-work-p4blo/07cfdaea-e2c5-4c99-819f-19a428efb35b/scratchpad/pyright-exp/`
(`exp1`..`exp8`), and the relevant output is quoted in section 3.

## 0. What p4blo has today (the baseline being redesigned)

From `/Users/qobilidop/my/work/p4blo/python/p4blo/edsl/{types,expr,blocks,program}.py`
and `/Users/qobilidop/my/work/p4blo/corpus/forwarder/forwarder.py`:

- Types are `pb.Type` values: `bit(48)` returns `pb.Type(bits=48)`;
  headers/structs are `p.header("ipv4_t", ttl=bit(8), ...)` keyword
  constructors returning `HeaderType`/`StructType` declaration objects.
- `Expr` wraps `pb.Expr` + `pb.Type` (+ `pb.LValue`); every operator checks
  equal widths at build time (`EdslError`), an `int` operand takes the
  other operand's width (`hdr.ipv4.ttl - 1` makes `1` a `bit<8>`), no cast
  is ever inserted. `Expr.__bool__` raises with a hint to use `b.if_`/`mux`.
- Field access is `Expr.__getattr__` → `self.field(name)` consulting a
  `TypeTable`; so `hdr.ipv4.ttl` is typed at *runtime* only, and field
  names that collide with `Expr`'s own attributes (`type`, `next`, `last`,
  `cast`, ...) must be reached as `.field("type")` (documented wart).
- Control flow is `with b.if_(cond): ... with b.elif_(c): ... with b.else_():`
  on a `Stmts` builder with an explicit target stack; nothing reads source.
- References to states, actions, tables and blocks are *strings* or the
  builder objects (`Target = str | StateBody | Accept | Reject`;
  `actions=["ipv4_forward", "drop", "NoAction"]`); forward references to
  states are strings checked at `Parser.build()`.
- Action params: `c.action("ipv4_forward", dstAddr=bit(48), port=bit(9))`,
  reached as `a.port` through `__getattr__`.
- Nothing is visible to pyright: `hdr.ipv4.ttl` is `Expr`, `bit(8)` is
  `pb.Type`, `a.port` is `Expr`.
- Design constraint (docs/design.md: "A decorator-based eDSL that reads
  Python source. Rejected because it hides the IR, and the IR is the
  product"; docs/writeup.md: "There is no decorator that reads Python
  source ... the eDSL should teach it by use, not hide it").

---

## 1. HDL eDSLs

### 1.1 Amaranth

Docs: https://amaranth-lang.org/docs/amaranth/latest/guide.html ,
https://amaranth-lang.org/docs/amaranth/latest/stdlib/data.html ,
https://amaranth-lang.org/docs/amaranth/latest/reference.html ,
source https://github.com/amaranth-lang/amaranth/blob/main/amaranth/lib/data.py

**What.** A pure builder: `Module` objects collect statements; nothing
reads Python source. Values are `Signal`/`Const`/operator trees.

**Typed values.** `Signal(8)`, `Signal(signed(8))`, `Signal(range(-8, 7))`
→ `signed(4)`. `Shape.cast`: "an `int`, where the result is
`unsigned(obj)`", ranges and enums also cast. Literal ints become `Const`
with the *minimal* width ("`5` → `unsigned(3)`"). Arithmetic never errors on
width mismatch: "arithmetics on Amaranth values never overflows because
the width of the arithmetic expression is always sufficient to represent
all possible results"; "unsigned values are always zero-extended and
signed values are always sign-extended regardless of the operation".
Comparisons are "1-bit unsigned". `a[i:j]` needs constant subscripts,
LSB at index 0; `Cat(a, b)` puts `a` in the low bits; `a.bit_select(b, w)`
/ `a.word_select(b, w)` for variable offsets. Assignment `.eq()` truncates
or extends to the target ("the number's binary representation will be
truncated or extended to fit the shape").

**Declarations / references.** `ValueCastable` requires `shape()` and
`as_value()` (an `__init_subclass__` check raises `TypeError` if missing),
and the invariant `Shape.cast(self.shape()) == Value.cast(self).shape()`.
`ShapeCastable` requires `as_shape()`, `const(obj)`, `from_bits(raw)`,
`__call__(obj)`. `amaranth.lib.data`:

```python
class IEEE754Single(data.Struct):
    fraction: 23
    exponent:  8 = 0x7f
    sign:      1
flt = Signal(IEEE754Single)
flt.fraction   # (slice (sig flt) 0:23)
```

The metaclass loops over `__annotations__`: `Shape.cast(annotations[field_name])`,
skipping annotations that are not shape-castable; class attributes with
the same name become field defaults (`init`). `View.__getattr__` calls
`self[name]` and raises `AttributeError(f"View with layout {layout!r} does
not have a field {name!r}; did you mean one of: ...")`; names starting
with `_` are reserved: "has a reserved name and may only be accessed by
indexing". FSM states are **strings**: `with m.State("Idle"): m.next =
"Running"`, `fsm.ongoing("Idle")`, with the caveat "If a non-string object
is provided as a state name to `with m.State(...):`, it is cast to a
string first, which may lead to surprising behavior."

**Control flow.**

```python
with m.If(cond1):   m.d.comb += a.eq(1)
with m.Elif(cond2): m.d.sync += b.eq(2)
with m.Else():      m.d.sync += c.eq(3)
with m.Switch(value):
    with m.Case(0, 2, 4): ...
    with m.Default():     ...
```

Rationale for not using Python `if`: "Because the value of `a`, and
therefore `a == 0`, is not known at the time when the `if` statement is
executed, there is no way to decide whether the body of the statement
should be executed—in fact, if the design is synthesized, by the time `a`
has any concrete value, the Python program has long finished!"

**Static typing.** None. `View.__getattr__` is untyped; widths are runtime
`Shape` objects; no `py.typed`.

**Steal.** Class-body annotations as struct layout with an
`__init_subclass__`/metaclass that reads `__annotations__`; the "did you
mean one of" error; the reserved-name rule (`_`-prefixed only via
indexing) as a cleaner version of p4blo's `.field("type")` escape hatch;
`Switch/Case/Default` naming if p4blo ever adds a switch.
**Avoid.** Silent width extension (P4 requires equal widths, and p4blo's
"no inserted casts" rule is right); string-named states.

### 1.2 Magma

Docs: https://raw.githubusercontent.com/phanrahan/magma/master/docs/syntaxes.md ,
https://raw.githubusercontent.com/phanrahan/magma/master/docs/types_and_values.md ,
https://raw.githubusercontent.com/phanrahan/magma/master/docs/when/internals.md ,
https://raw.githubusercontent.com/phanrahan/magma/master/docs/smart_bits.md ;
source https://github.com/phanrahan/magma/blob/master/magma/bits.py ,
https://github.com/phanrahan/magma/blob/master/magma/array.py

**What.** "Magma is a hardware design language embedded in python";
circuits are classes: "Circuits are defined by subclassing `m.Circuit` and
assigning an interface definition to the variable named `io`":

```python
class Accum(m.Circuit):
    io = m.IO(I=m.In(m.UInt[8]), O=m.Out(m.UInt[8]))
    io += m.ClockIO()
```

**Typed values.** `Bits[N]` is a real class made by a metaclass:
`class Bits(Array, AbstractBitVector, metaclass=BitsMeta)`; `BitsMeta.__getitem__`
maps `Bits[8]` to `Array[(8, Bit)]`, and `ArrayMeta.__getitem__` caches
in `mcs._class_cache[cls, index]` and builds `mcs(class_name, bases, {...},
info=(cls,)+index)`, storing `type_._info_ = type_, N, T`. Operations by
type: "`Bits[n]`" supports `&, |, ^, ~, ==, <<, >>`; `UInt[n]`/`SInt[n]`
add `+, -, *, /, <, ...`. Width mismatch is an error: `bvadd` goes through
`@bits_cast` → `_coerce` → `_check_size`: `if len(val) != len(T): raise
InconsistentSizeError('Inconsistent size')`. Python ints coerce to the
other operand's type; too big is an error: `if arg.bit_length() > cls.N:
raise ValueError(f"Cannot construct {cls.orig_name}[{cls.N}] with integer
{arg} (requires truncation)")`. This is p4blo's rule exactly.
`SmartBits` is the opposite design (Verilog-style inference: "the result
of addition has bit-width equal to the maximum of all of its operand
bit-widths", concat width `sum(operands)`, comparison width 1).

**Declarations / references.** Structs are `Product` classes with fields as
class-body attributes (`class Foo(m.Product): x = m.Bits[8]`), collected by
hwtypes' `ProductMeta` into `_field_table_`; field access on values goes
through `__getattr__` that "looks up the field in `self.keys()` and lazily
constructs the child via `self[key]`". Instances reference circuit
*classes* by Python object (`mux2 = Mux2()`), wiring is `@=`.

**Control flow.** Two families. (1) Builder: `with m.when(cond): out @=
a` / `with m.elsewhen(cond2):` / `with m.otherwise():`, recorded via a
block stack (`_curr_block`, `_prev_block`), `ConditionalWire(drivee,
driver)` objects and a `WhenBuilder` per context; "the value must be
defined in all branches. Failure to define all possible cases will lead to
an inferred latch error." (2) Source-reading: `@m.combinational2`,
`@m.sequential2`, `@m.coroutine` "read Python source via AST rewriting"
(ast_tools), turning Python `if/else` into muxes.

**Static typing.** None, and worse than none: `Bits[8]` is a class created
at runtime, so pyright sees only `Bits`. Locally (exp4): a class with
`__class_getitem__` lets pyright *accept* `x: Bits[8]` as an annotation
without complaint, and `reveal_type(x + y)` is just `Bits` — the width
is silently discarded, so `Bits[8] + Bits[16]` is not caught.

**Steal.** The equal-width-or-error rule with int coercion (already
p4blo's); `when/elsewhen/otherwise` as a naming option; class-body field
declarations. **Avoid.** Metaclass-made `Bits[N]` types (invisible to
pyright); AST-rewriting decorators.

### 1.3 PyRTL

Docs: https://pyrtl.readthedocs.io/en/latest/basic.html ; source
https://github.com/UCSBarchlab/PyRTL/blob/development/pyrtl/wire.py ,
https://github.com/UCSBarchlab/PyRTL/blob/development/pyrtl/conditional.py

**What.** Builder over a global working block; `WireVector(bitwidth=8,
name=...)`, `Input`, `Output`, `Register`, `Const`. Connection is `<<=`
("`a <<= b` does not overwrite `a`, but simply wires the two together").

**Typed values / widths.** Unsigned arithmetic; "If the inputs do not have
the same bitwidth, the shorter input will be zero_extended to the longer
input's bitwidth"; `+`/`-` result is "the longer of the two input
WireVectors, plus one", `*` twice the longer, bitwise ops the longer,
comparisons 1 bit. Const: "int will be coerced to an unsigned Const
WireVector with the minimum bitwidth required for the integer"; an
explicit bitwidth too short raises. `__bool__` raises `PyrtlError("cannot
convert WireVector to compile-time boolean. This error often happens when
you attempt to use WireVectors with '==' or something that calls
'__eq__'...")` — same device as p4blo's `Expr.__bool__`.

**Control flow.**

```python
with pyrtl.conditional_assignment:
    with cond:            wire |= value
    with pyrtl.otherwise: wire |= other_value
```

`|=` is only valid under a condition ('conditional assignment "|=" only
valid under a condition'); nesting the outer context is refused ("no
nesting of conditional assignments allowed"); assignments are stored by
`_build` "until finalize is called" on a `_conditions_list_stack`.

**Static typing.** None.

**Steal.** The `__bool__` error text that names the likely cause.
**Avoid.** Implicit extension and grow-by-one arithmetic.

### 1.4 PyMTL3 (why p4blo rejects it)

Source: https://github.com/pymtl/pymtl3/blob/master/pymtl3/dsl/ComponentLevel2.py ,
https://github.com/pymtl/pymtl3/blob/master/pymtl3/passes/rtlir/behavioral/BehavioralRTLIRGenL1Pass.py

**What.** `class Foo(Component): def construct(s): s.in_ = InPort(Bits8)`
and `@update def up(): s.out @= s.in_ + 1`. The `update` decorator only
registers the function (`s._dsl.name_upblk[name] = blk`), but elaboration
then reads its source — `ComponentLevel2.py` lines 103–105:

```python
_src, _line = inspect.getsourcelines( func )
_src = "".join( _src )
_ast = ast.parse( compiled_re.sub( r'\2', _src ) )
```

and `AstHelper.extract_reads_writes_calls(s, func, _ast, ...)` walks the
AST to find signal reads/writes for scheduling — so even *simulation*
depends on source availability. The RTLIR pass is an `ast.NodeVisitor`
that rejects Python outside its subset (`PyMTLSyntaxError(... 'Temporary
variable is not supported at L1!')`, `'Update blocks should not have
arguments!'`).

**Why rejected for p4blo.** (1) Two semantics for one text: Python runs
the block for simulation, a separate visitor re-interprets the same text
for translation, and the two can drift. (2) Source must be retrievable
(`inspect.getsource` fails for code built with `exec`, in a REPL, or
generated) — an eDSL meant to be *driven programmatically* (p4blo's
corpus generators, future fuzzers) cannot depend on that. (3) It hides the
IR: the author writes `if`, never sees `pb.If`, which contradicts the
design rule that the eDSL teaches the IR by use. Same verdict applies to
MyHDL, TVMScript, Taichi, Triton, Exo and Magma's `@m.combinational2`.

### 1.5 MyHDL

Docs: https://docs.myhdl.org/en/stable/manual/intro.html ,
https://docs.myhdl.org/en/stable/manual/conversion.html ; source
https://github.com/myhdl/myhdl/blob/master/myhdl/_util.py

**What.** Generators as hardware: "Generators are the basic building blocks
of MyHDL models"; `@block`, `@always_comb`, `@always_seq`, `@instance`;
`Signal(intbv(0)[8:])`; "A new value of a signal is specified by
assigning to its `next` attribute". `intbv` carries runtime bounds
(`intbv(0, min=MIN, max=MAX)`), and "intbv objects must be constructed so
that a bit width can be inferred".

**Conversion reads source.** `_makeAST(f)`: `s = inspect.getsource(f)`,
dedent, `compile(s, ..., flags=ast.PyCF_ONLY_AST | ...)`; the docs say
"The converter uses the Python profiler to track the interpreter's
operation ... [and] selectively compiles pieces of source code for
additional analysis and for conversion." `_FirstPassVisitor` "Prune[s]
unsupported constructs" (dicts, lambdas, try/except, list literals,
chained comparisons, ...). Same rejection as PyMTL3.

**Steal.** Runtime bound-checking of literals against the target
(p4blo already refuses a literal that does not fit).

### 1.6 CIRCT PyCDE (and PyRTG)

Docs: https://circt.llvm.org/docs/PyCDE/basics/ ; source
https://github.com/llvm/circt/blob/main/frontends/PyCDE/src/pycde/types.py ,
`.../signals.py`, `.../constructs.py`, `.../fsm.py`,
https://github.com/llvm/circt/blob/main/frontends/PyRTG/src/pyrtg/control_flow.py

**What.** Modules with typed ports as class attributes and a generator
that is *called*, not parsed:

```python
class OrInts(Module):
    a = Input(Bits(32))
    b = Input(Bits(32))
    c = Output(Bits(32))
    @generator
    def construct(self):
        self.c = self.a | self.b
```

Instantiation by keyword: `or_ints = OrInts(a=self.a, b=self.b); self.c =
or_ints.c`. `@modparams` makes parameterized module classes from Python
functions.

**Typed values.** `Bits(w)`, `UInt(w)`, `SInt(w)` are *instances* of
`Type`, interned: `Type.__new__` caches in `Type._cache[(cls, circt_type)]`
so `Bits(8) is Bits(8)`. `Bits(8) * 4` is an array. Constants:
`Bits(16)(value)`, with `_from_obj_check` raising `ValueError(f"{x}
overflows type {self}")`; the docs note "explicit typing via
`Bits(16)(value)` may be necessary when width is ambiguous". Signless
`BitsSignal` arithmetic refuses mismatches: `raise TypeError(f"Operator
'{op_symbol}' requires both operands to be the same width.")`.
`UIntSignal`/`SIntSignal` accept Python ints and size them by
`bit_length()` (then `hwarith` widens results). Struct types:
`StructType({"a": Bits(8), ...})`; `StructType.__getattr__` returns the
field *type*; `StructSignal.__getattr__` emits `hw.StructExtractOp` and
raises `AttributeError` otherwise. Casts are explicit: `.as_bits(width)`,
`.as_uint(width)`.

**Declarations / references.** FSM states are objects declared first,
wired later:

```python
class MyFSM(Machine):
    initial_state = State(initial=True)
    other_state = State()
# later: state.set_transitions((target_state, condition_function), ...)
```

Forward references are free because every `State()` exists before any
transition is set.

**Control flow.** PyCDE itself has none: `constructs.py` has `Wire()`
("Declare a wire. Used to create backedges. Must assign exactly once."),
`Reg()`, `Mux()` ("Create a single mux from a list of values"),
`ControlReg`. The sibling frontend PyRTG has `with If(cond): v =
Integer(1) / with Else(): v = Integer(0) / EndIf(); use(v)`, implemented
by capturing `inspect.stack()[...].f_locals`, diffing them on `__exit__`,
and writing merged values back with `ctypes.pythonapi.PyFrame_LocalsToFast`
— frame hacking, not source reading, but equally fragile.

**Static typing.** No `py.typed`; `Bits(8)` is a value, so pyright sees
`Bits`/`BitsSignal` with no width.

**Steal.** Ports/fields as class attributes; interned types; the exact
wording of the width `TypeError`; states-as-objects-then-transitions;
the generator-is-called (never parsed) model. **Avoid.** Frame hacking.

---

## 2. Compiler / array eDSLs

### 2.1 JAX (`lax.cond` / `lax.switch` / `lax.scan`)

Docs: https://docs.jax.dev/en/latest/control-flow.html ,
https://docs.jax.dev/en/latest/_autosummary/jax.lax.cond.html ,
https://docs.jax.dev/en/latest/_autosummary/jax.lax.switch.html

**Why explicit control flow.** Under `jit` values are abstract: "when we
hit a line like `if x < 3`, the expression `x < 3` evaluates to an
abstract `ShapedArray((), jnp.bool_)` that represents the set `{True,
False}`. When Python attempts to coerce that to a concrete `True` or
`False`, we get an error" — `TracerBoolConversionError: Attempted boolean
conversion of traced array with shape bool[]`. Tracing *executes* the
Python function once with tracers; no source is read (the same model as
MLIR's `from_py_func` and p4blo's builders).

**Constructs.** `lax.cond(pred, true_fun, false_fun, *operands)` ("pred
... Boolean scalar type"), `lax.switch(index, branches, *operands)` with
`index = clamp(0, index, len(branches) - 1)`, `lax.select`/`jnp.where`
(a mux), `lax.scan`, `lax.fori_loop`, `lax.while_loop`. Invariant: "all
branches must return the same output structure"; both branches are
traced. Static values are opted in with `jit(f, static_argnames='x')`.

**Steal.** Branches as callables is the right shape for *expression*
constructs (`mux`) and could serve `select` cases; the clamped
`switch(index, branches)` is a model for a keyed dispatch with default.
The tracer-error message style. **Avoid.** Nothing structural; JAX's
typing (jaxtyping) is non-standard and shape-only.

### 2.2 TVMScript

Docs: https://tvm.apache.org/docs/deep_dive/tensor_ir/learning.html ;
source https://github.com/apache/tvm/blob/main/python/tvm/script/parser/core/entry.py

```python
@tvm.script.ir_module
class MyModule:
    @T.prim_func
    def mm_relu(A: T.Buffer((128, 128), "float32"), ...):
        for i, j, k in T.grid(128, 128, 128):
            with T.block("Y"):
                vi = T.axis.spatial(128, i)
```

`parse(program)` builds `source = Source(program)` (wrapping
`inspect.getsource`), collects `func.__annotations__`, then `Parser(source,
ann)` visits the AST inside `with IRBuilder() as builder:` — the parser
*drives a `with`-based builder* (`tvm.script.ir_builder`), which is the
part worth noting: TVM's own substrate is a p4blo-style builder; TVMScript
is a source-reading skin over it. `T.int32` etc. are annotations the
parser interprets. Rejected for p4blo as with PyMTL3.

### 2.3 Halide (Python bindings)

Docs: https://github.com/halide/Halide/blob/main/doc/Python.md

The closest cousin to p4blo's approach: pure operator-overloading builder.

```python
x, y, c = hl.Var("x"), hl.Var("y"), hl.Var("c")
f = hl.Func("f")
f[x, y, c] = hl.cast(hl.UInt(8), hl.sin(x * k) * 255.0)
```

Explicit `hl.select(cond, a, b)` and `hl.cast(type, e)`; Python's
`and/or/not` and ternary cannot be overloaded, so "Instead use `&`, `|`,
and `logical_not()`". "Native type aliases are supported: `bool` for
`hl.Bool()`, `int` for `hl.Int(32)`, and `float` for `hl.Float(32)`" —
i.e. bare Python ints are `Int(32)` constants and then follow Halide's
C++ coercion rules, not the other operand's width. Generators declare
I/O as class attributes and are *called*:

```python
@hl.generator(name="my_gen")
class MyGenerator:
    input  = hl.InputBuffer(hl.UInt(8), 2)
    output = hl.OutputBuffer(hl.UInt(8), 2)
    def generate(g):
        g.output[x, y] = g.input[x, y]
```

**Steal.** `select` as the mux name; typed class-attribute declarations
consumed by a called `generate`. **Avoid.** `int → Int(32)` literal rule
(P4 literals are context-typed, which p4blo already does).

### 2.4 Taichi

Docs: https://docs.taichi-lang.org/docs/kernel_function ,
https://docs.taichi-lang.org/docs/compilation ,
https://docs.taichi-lang.org/docs/meta

`@ti.kernel`/`@ti.func` bodies are "Taichi scope"; "Taichi mandates that
the arguments and return value of a kernel are type hinted". Pipeline:
"the Taichi frontend compiler (i.e., the `ASTTransformer` Python class)
will transform the kernel body AST into a Python script, which, when
executed, emits a Taichi frontend AST" — source-reading, rejected. One
idea transfers: `ti.static` — "a hint for the compiler to evaluate the
argument at compile time" (`if ti.static(cond):`, `for i in
ti.static(range(4)):`). p4blo already has this split implicitly (Python
`if` = elaboration time, `b.if_` = program time); naming it in the docs
("two clocks") helps users.

### 2.5 Triton

Docs: https://triton-lang.org/main/getting-started/tutorials/01-vector-add.html ;
source https://github.com/triton-lang/triton/blob/main/python/triton/runtime/jit.py ,
`.../language/core.py`

`def add_kernel(x_ptr, ..., BLOCK_SIZE: tl.constexpr)`; `constexpr` "is
used to store a value that is known at compile-time"; the JIT reads
source: `self.raw_src, self.starting_line_number =
inspect.getsourcelines(fn)`, `ast.parse(self._src)`, and constexpr
arguments enter the cache key (`specialization.append(f'("constexpr",
{name})')`). Rejected as a whole; the transferable idea is *marking
compile-time-ness in the annotation* — for p4blo, `Annotated`/marker types
on action parameters or table attributes could carry "this is a constant"
for pyright, but there is no current need.

### 2.6 MLIR Python bindings

Docs: https://mlir.llvm.org/docs/Bindings/Python/ ; source
https://github.com/llvm/llvm-project/blob/main/mlir/python/mlir/dialects/scf.py ,
`.../dialects/func.py`

**What.** Context managers for ambient state: `with Context(), Location.unknown():`,
`module = Module.create()`, `with InsertionPoint(module.body), Location.file("f.mlir",
line=42, col=1): Operation(<...>)`. Generic creation: `Operation.create("func.func",
results=[], operands=[], attributes={...}, regions=1)`; ODS generates
`_{DIALECT}_ops_gen.py` `OpView` subclasses with typed accessors
(`.result`, `.operands`). Types are interned via `get`: `IntegerType.get_signless(32)`;
every `Value` has `.type`.

**Function bodies are called, not parsed.** `FuncOp.from_py_func` reads
`inspect.signature(f)` only, then:

```python
func_op = FuncOp(name=symbol_name, type=function_type)
with InsertionPoint(func_op.add_entry_block()):
    func_args = func_op.entry_block.arguments
    return_values = f(*func_args, **func_kwargs)
```

**Control flow.** `IfOp(cond, results_, has_else=True)` exposes
`then_block` / `else_block`, and the body is filled by `with
InsertionPoint(if_op.then_block): ...`; `for_()` is a generator that does
`with InsertionPoint(for_op.body): yield iv`. Blocks and ops are Python
objects; successors reference `Block` objects, so a forward branch is
"create the block first, fill it later".

**Static typing.** The native module ships nanobind stubs (`ir.pyi`), so
`Value.type`, `OpView.results` etc. are visible to pyright; but there is
no width-level typing (an `i8` and an `i16` are both `IntegerType`).

**Steal.** Insertion point as a context manager (p4blo's `Stmts._nested`
is this); `from_py_func`: run the user's Python function once with typed
placeholder arguments — the source-free way to give action bodies named,
typed parameters; forward references by creating the target object
(state/block) before its body.

### 2.7 xDSL

Source: https://github.com/xdslproject/xdsl/blob/main/xdsl/irdl/operations.py ,
https://github.com/xdslproject/xdsl/blob/main/xdsl/dialects/arith.py ,
https://github.com/xdslproject/xdsl/blob/main/xdsl/builder.py

**Declarations as typed class-body fields.**

```python
class SignlessIntegerBinaryOperation(IRDLOperation, ...):
    T: ClassVar = VarConstraint("T", signlessIntegerLike)
    lhs = operand_def(T)
    rhs = operand_def(T)
    result = result_def(T)
    def __init__(self, operand1, operand2, result_type=None):
        if result_type is None:
            result_type = SSAValue.get(operand1).type
        super().__init__(operands=[operand1, operand2], result_types=[result_type])

@irdl_op_definition
class AddiOp(SignlessIntegerBinaryOperationWithOverflow):
    name = "arith.addi"
```

The trick that makes this statically typed: `def operand_def(constraint=...)
-> Operand: return cast(Operand, _OperandFieldDef(OperandDef, constraint))`
where `Operand: TypeAlias = SSAValue`, and `result_def(...) ->
OpResult[AttributeInvT]`. Pyright sees `op.lhs: SSAValue`; at runtime the
value is a descriptor placeholder that `irdl_op_definition` replaces with
generated accessors (`get_accessors_from_op_def`). `VarConstraint("T", ...)`
ties operand/result types ("same T") and is verified at `verify()` time —
the dynamic analogue of p4blo's equal-width rule. The older
`lhs: Annotated[Operand, ...]` syntax is gone; it is all function-based
now.

**Builders.** `with ImplicitBuilder(block): arith.Constant(...)` inserts
automatically by hooking `Operation.__post_init__` with a thread-local
`_current_builder`; `@Builder.implicit_region(input_types)` calls a Python
function with block arguments (again: called, not parsed). xDSL is
type-checked with pyright in CI.

**Steal.** `field_def(...) -> T` returning `cast(T, descriptor)` so class
bodies are simultaneously runtime declarations and pyright-visible
attribute types; implicit insertion via a context stack.

### 2.8 Exo

Source: https://github.com/exo-lang/exo/blob/main/src/exo/API.py ,
https://github.com/exo-lang/exo/blob/main/src/exo/frontend/pyparser.py

`@proc` never executes the function: `body, src_info = get_ast_from_python(f)`
(`inspect.getsource` → `textwrap.dedent` → `pyast.parse`) then
`Parser(body, ...)`; loops are `for i in seq(lo, hi)`; unsupported
argument syntax is refused with a list ("position-only arguments ...
default argument values"). Rejected for p4blo like the others; the
notable separation is that *scheduling* (the metalanguage) is ordinary
Python operating on `Procedure` objects by reference, i.e. object
references between procs, not names.

---

## 3. Typing tricks: what a type checker can actually see

### 3.1 Local pyright results (1.1.411)

All files in `.../scratchpad/pyright-exp/`. Definitions used:

```python
class Bits[W: int]:
    def __add__(self, other: Bits[W] | int) -> Bits[W]: ...
```

| Spelling | pyright result |
|---|---|
| `a8: Bits[Literal[8]]; b16: Bits[Literal[16]]; a8 + b16` | **error**: `Operator "+" not supported for types "Bits[Literal[8]]" and "Bits[Literal[16]]"` (exp1, exp6) |
| `a8 + 1`, `a8 + a8` | `Bits[Literal[8]]` |
| `def bit[W: int](w: W) -> Bits[W]; bit(8)` | `Bits[int]` — pyright widens the literal when solving `W`; `Final` ints do not help (exp1, exp6, exp7) |
| `bit(8) + bit(16)` with the generic `bit` | **no error** (both `Bits[int]`) |
| `x: Bits[8]` on a PEP 695 generic | error: `Expected class but received "Literal[8]"` (exp7) |
| `L = Literal; y: Bits[L[8]]` | `Bits[Literal[8]]` — the alias works (exp7) |
| `type bit8 = Bits[Literal[8]]` | works (exp7) |
| per-width overloads `@overload def bit(w: Literal[8]) -> Bits[Literal[8]]` ... catch-all `-> Bits[Any]` | `bit(8)` → `Bits[Literal[8]]`, `bit(48)` → `Bits[Literal[48]]`, `bit(9)` (no overload) → `Bits[Any]`; `bit(8) + bit(16)` **error** (exp8). If the catch-all returns `Bits[int]` instead, pyright rejects the overload set (`reportOverlappingOverload`, `reportInconsistentOverload`, "Type parameter W@Bits is invariant") (exp7) |
| `Literal[8] + Literal[16]` on plain ints | `Literal[24]` ("literal math", https://github.com/microsoft/pyright/blob/main/docs/type-concepts-advanced.md: "pyright computes the result of operations on the literal values, producing a new literal type"; "limits the number of subtypes in the resulting union to 64"; "disabled within loops and lambda expressions") (exp2) |
| `def add2[A: int, B: int](a: A, b: B): a + b` | `int` — no arithmetic on TypeVars, so `concat` cannot be typed `Bits[A + B]` (exp2) |
| `class ipv4_t(Header): ttl: Bits[Literal[8]]; hdr.ipv4.ttl` | `Bits[Literal[8]]`; `hdr.ipv4.ttl + hdr.ipv4.dstAddr` **error** 8 vs 32 (exp3, exp8) |
| same, with `Header.__getattr__` defined | typo `hdr.ipv4.nosuch` is `Any`, no error (exp3) |
| same, **without** `__getattr__` | typo is an **error**: `Cannot access attribute "tll" for class "ipv4_t"` (exp8) |
| descriptor `class Field[T]` with overloaded `__get__(obj: None) -> Field[T]` / `(obj: object) -> T`; `ttl = Field(bit(8))` | `hdr.ipv4.ttl` is `T` (works), but `T` is only as precise as the argument: `Bits[int]` with the generic `bit`, `Bits[Literal[8]]` with the overloaded `bit` (exp5) |
| Magma-style `__class_getitem__` returning a cached subclass; `x: Bits[8]` | accepted silently; `x + y` is `Bits` — width invisible (exp4) |
| `concat(a, b) -> Bits[Any]`; `x[3:0] -> Bits[Any]` | `Bits[Any]` mixes with anything, no false errors (exp8) |

No mypy on this machine; nothing above is pyright-specific in principle
(PEP 695, `Literal`, overloads, invariance are all in the typing spec),
but mypy's overload-overlap and literal-retention rules may differ and
should be checked before committing to a design.

### 3.2 Do real projects catch `Bits[8] + Bits[16]` statically?

- **hwtypes** (`BitVector[8]`, https://github.com/leonardt/hwtypes/blob/master/hwtypes/bit_vector_abc.py ):
  `AbstractBitVectorMeta.__getitem__` builds `mcs(class_name, bases, {},
  info=(cls, idx))` cached in a `WeakValueDictionary`; "No `typing.Generic`
  or `TypeVar` usage". Mismatch is a runtime `InconsistentSizeError`.
  **Not static.**
- **Magma**, **PyCDE**, **Amaranth**, **PyRTL**, **PyMTL3**: none expose
  widths to a type checker (sections 1.x). **Not static.**
- **phantom-tensors** ( https://github.com/rsokl/phantom-tensors ): shapes
  as `Tensor[L[1], L[3]]` / `NDArray[A, B]`; "pyright can tell the
  difference between `Tensor[Batch, Channel]` and `Tensor[Batch, Feature]`";
  runtime side via beartype. **Static for equality of dims; no arithmetic.**
- **Shape typing numpy with pyright and variadic generics**
  ( https://taoa.io/posts/Shape-typing-numpy-with-pyright-and-variadic-generics/ ):
  `NDArray[Shape[Literal[3], Literal[4]], dtype]` with PEP 646; matmul via
  overloads yields errors like "Argument of type NDArray[Shape2D[SLICES,
  COLS]] cannot be assigned to parameter x2"; limitation: "No dimension
  arithmetic ... requires manually defining multiplication lookup tables
  via Literal". **Same conclusion.**
- **pyright #1872** (fixed-width ints, https://github.com/microsoft/pyright/issues/1872 ),
  Eric Traut: "The Python type system has no way of representing numeric
  widths or ranges. Pyright supports the typing standards spelled out in
  various PEPs. ... We don't currently have any plans to pursue such
  extensions given that this is a very niche use case in Python."
- **mypy #3345** "Integer generics" ( https://github.com/python/mypy/issues/3345 ),
  open since 2017: proposes `class Vector(Generic[N]): def __add__(self,
  other: Vector[N]) -> Vector[N]`, and notes `Vector[N+M]` "may be taking it
  too far".
- **PEP 695** ( https://peps.python.org/pep-0695/ ): `class ClassA[T: str]:`
  (bound), "type checkers will infer the variance of type parameters based
  on their usage"; with `__add__(self, other: Bits[W]) -> Bits[W]` pyright
  infers `W` invariant, which is what makes the mismatch an error.

**Bottom line.** No surveyed HDL catches `Bits[8] + Bits[16]` with a type
checker. It is nonetheless achievable today with `Bits[W: int]` plus
`Literal` widths (verified above), at the cost of (i) spelling widths as
`Literal[8]`/`L[8]`/`bit8` in annotations, (ii) per-width overloads for a
`bit(n)` constructor (or accepting `Bits[Any]` from it), and (iii) losing
the width statically through `concat` and slices (`Bits[Any]`), where the
runtime check remains the authority.

### 3.3 Other mechanisms, briefly

- `typing.Annotated[Bits, 8]`: pyright ignores metadata, so the width is
  invisible; only useful as a runtime carrier.
- `__class_getitem__` (Magma/hwtypes): worst of both worlds — pyright
  accepts the spelling and discards it (exp4).
- Descriptors with typed `__get__`: work (exp5) and give a place to hold
  the `pb.Type` at runtime, but class-body *annotations* achieve the same
  static result with less machinery, and `get_type_hints(cls)` recovers
  `Literal[8]` at runtime (`typing.get_args(Bits[Literal[8]])[0]` →
  `Literal[8]`, `get_args(...)[0]` → `8`).
- `dataclass_transform`: would let pyright synthesize `__init__` for header
  classes (`ipv4_t(ttl=..., dstAddr=...)`) if constant header values are
  ever needed; not required now.
- The xDSL `cast(T, descriptor)` trick (3.1 of section 2.7) is the general
  recipe when a declaration must return one thing at runtime and be seen
  as another by pyright.

---

## 4. Patterns for p4blo (ranked)

### (a) N-bit values whose widths pyright can see

1. **`Bits[W: int]` as the expression class, widths as `Literal` type
   arguments** (verified: exp1/3/6/8). Merge today's `Expr` and `pb.Type`
   carrier into one generic value class parameterized by its P4 type:
   `Bits[Literal[8]]`, plus a separate `Bool` value class (comparisons
   return `Bool`, `&`/`|`/`~` are overloaded on both). Operators typed
   `def __add__(self, other: Bits[W] | int) -> Bits[W]` — this matches the
   runtime rule "an int takes the other operand's width" exactly, so what
   pyright infers is what the IR gets. Keep the runtime `EdslError`
   checks unchanged; the static layer is advisory.
2. **Constructor spelling.** Provide `L = Literal` re-export or, better,
   a generated set of aliases `bit1 ... bit64` (`type bit8 =
   Bits[Literal[8]]`) and an overloaded `bit(n)` for the same widths whose
   catch-all returns `Bits[Any]` (exp8). Unusual widths (`bit(144)` in the
   forwarder's checksum) degrade to `Bits[Any]`, which never produces a
   false error. Do not use `__class_getitem__`; `x: Bits[8]` must stay a
   pyright error rather than a silently untyped success (exp4 vs exp7).
3. **Accept the static holes:** `concat`, slices, `cast`, `lookahead(type)`
   return `Bits[Any]` unless given an explicit target type argument
   (`x.cast(bit16)` can return `Bits[Literal[16]]` if `cast` is typed
   `def cast[V: int](self, to: type[Bits[V]] | Bits[V]) -> Bits[V]`). No
   type-level arithmetic exists (exp2, mypy #3345).
4. Prior art to cite in the design note: PyCDE's `TypeError("Operator '+'
   requires both operands to be the same width.")` and Magma/hwtypes'
   `InconsistentSizeError` as the runtime rule; phantom-tensors/taoa.io as
   the static `Literal`-dims precedent; pyright #1872 for why there is no
   built-in width type.

### (b) Headers/structs as Python classes with annotated fields

1. **Class-body annotations, Amaranth `data.Struct` style, with no
   `__getattr__`** (exp8):

   ```python
   class ipv4_t(Header):
       ttl: bit8
       dstAddr: bit32
   class headers(Struct):
       ethernet: ethernet_t
       ipv4: ipv4_t
   ```

   `__init_subclass__` reads `get_type_hints(cls)` to build the
   `pb.HeaderType` (Amaranth: loop over `__annotations__` with
   `Shape.cast`; xDSL: `OpDef.from_pyrdl` walks the class dict). Field
   access `hdr.ipv4.ttl` is then statically `Bits[Literal[8]]`, typos are
   pyright errors, and nested headers type as the header class itself.
   At runtime an instance is a *view* bound to an lvalue path (Amaranth
   `View`: `as_value()`, per-field slices; PyCDE `StructSignal.__getattr__`
   emitting `StructExtractOp`) — the instance must set real attributes
   (one `Bits`/`Bool`/view per field) in `__init__` rather than rely on
   `__getattr__`, or the static typo check is lost (exp3 vs exp8).
2. **Reserved names.** Fields that collide with view methods (`is_valid`,
   `cast`, `next`, `last`, `type`) are the remaining wart; Amaranth's rule
   ("has a reserved name and may only be accessed by indexing") and its
   "did you mean one of: ..." error are the model. Keep `view["type"]` /
   `.field("type")` as the escape hatch and keep the method surface on
   views tiny (move `is_valid`, `set_valid`, stack ops to functions or to
   a `hdr.ipv4.h` namespace) so collisions are rare.
3. **Program registration.** Header classes should be program-independent
   declarations (Amaranth layouts are), registered on first use or via
   `p.declare(ipv4_t)`; today's `p.header("ipv4_t", ...)` keyword form can
   remain as the dynamic path for generated programs.
4. Alternative if annotations are unwanted: xDSL's `field_def(...)
   -> T` implemented as `cast(T, descriptor)`, or a `Field[T]` descriptor
   with overloaded `__get__` (exp5). Both work; annotations are simpler.

### (c) References by Python object, with forward references

1. **Declare-then-define, PyCDE FSM / MLIR block style.** `State()` objects
   exist before transitions are set (`state.set_transitions((target,
   cond), ...)`); MLIR creates the block, then `cf.br(block)`, then fills
   it under `InsertionPoint`. For p4blo: `parse_ipv4 = ps.state("parse_ipv4")`
   returns the handle immediately; the body is filled later (`with
   parse_ipv4:` or `@parse_ipv4.body`), so `s.select(..., {0x800:
   parse_ipv4}, default=ps.accept)` references the object. Make `Target =
   StateBody | Accept | Reject` (drop `str`), and likewise
   `actions=[ipv4_forward, drop, NoAction]`, `default=drop`,
   `b.apply(ipv4_lpm)`, `p.export("parser", MyParser)`. The `build()`-time
   "unknown state" check becomes a "state declared but never defined"
   check.
2. **Call-the-function pattern for bodies** (MLIR `from_py_func`, xDSL
   `Builder.implicit_region`, PyCDE `@generator`, Halide `generate`): an
   action becomes

   ```python
   @c.action
   def ipv4_forward(b: ActionBody, dstAddr: bit48, port: bit9) -> None:
       b.assign(meta.egress_port, port)
   ```

   The eDSL reads only `inspect.signature`/`get_type_hints` (never
   source), creates typed placeholder `Bits` for the parameters, calls the
   function once, and the decorator returns the `ActionBody` handle. This
   removes `a.port` `__getattr__`, gives pyright the parameter widths, and
   is precisely the line MLIR draws: signature yes, AST no. The same works
   for parser states (`@ps.state def parse_ipv4(s: StateBody): ...`), with
   forward references solved by two-phase declaration (1) or by ordinary
   Python late binding (a body referencing `parse_ipv4` defined later in
   the same function is fine as long as the body runs after all
   decorators — which argues for collecting bodies and running them at
   the end of the `with p.parser(...)` block).
3. Contrast to cite: Amaranth's string FSM states and its "cast to a
   string first, which may lead to surprising behavior" caveat.

### (d) Control-flow constructs without source reading

1. **Keep the `with` builders** (`if_`/`elif_`/`else_`), which are the
   Amaranth `m.If/Elif/Else`, Magma `when/elsewhen/otherwise`, PyRTL
   `conditional_assignment` and MLIR `InsertionPoint` family; p4blo's
   `_nested` target stack is already the MLIR insertion-point model.
2. **Keep `__bool__` raising**, and adopt the JAX/PyRTL habit of naming the
   likely mistake in the message (PyRTL: "This error often happens when
   you attempt to use WireVectors with '==' ..."; JAX:
   `TracerBoolConversionError`).
3. **Expression-level branching stays functional**: `mux(cond, a, b)`
   (Halide `select`, JAX `lax.select`); if p4blo ever adds `switch` on a
   table's action run, JAX's `switch(index, branches)` / Amaranth's
   `Switch/Case/Default` are the two shapes.
4. **Document the two clocks** (Taichi `ti.static`, Triton `constexpr`,
   JAX `static_argnames`): a Python `if` runs at elaboration time and
   never appears in the IR; `b.if_` is the program's `if`. This is what
   makes source-free control flow teachable.
5. **Avoid** PyRTG's frame-locals capture (`PyFrame_LocalsToFast`) and every
   AST-reading decorator (PyMTL3, MyHDL, TVMScript, Taichi, Triton, Exo,
   Magma `@combinational2`).

### (e) Literal width inference rules

Survey of the rules:

| Project | bare `int` operand | mismatch |
|---|---|---|
| P4 / p4blo today | takes the other operand's width; must fit; no context → error; shift amount free | `EdslError` |
| Magma `Bits`/hwtypes | coerced to the other operand's type; `bit_length() > N` → `ValueError(... requires truncation)` | `InconsistentSizeError` |
| PyCDE `Bits` | explicit `Bits(16)(v)`; `UInt`/`SInt` size ints by `bit_length()` | `TypeError(... same width.)` |
| Amaranth | `Const` of minimal width, then zero/sign-extend | never errors; result widened |
| PyRTL | `Const` of minimal width, zero-extend | never errors; `+` grows by one bit |
| Halide | `int` → `Int(32)`, then Halide coercion | C++ rules |

Recommendation: **keep p4blo's rule** — it is P4's own, it is what Magma
and hwtypes chose for the non-"smart" types, and it is the only one of
the above that a static type (`__add__(self, other: Bits[W] | int) ->
Bits[W]`) can describe faithfully. Two refinements from the survey:
(1) keep the shift-amount exception and the `mux` "one Expr branch"
rule exactly as `expr.py` documents them, and add an equally explicit
docstring rule for `select` keysets and table entries (context = key
type; already the behaviour); (2) when a literal has no context
(`concat(1, x)`, `mux(c, 1, 2)`), continue to refuse rather than adopt
Amaranth/PyRTL minimal-width inference — the IR wants every width to be
one the author wrote, and `p.literal(1, bit8)` / `bit8(1)` (Halide
`hl.cast`, PyCDE `Bits(8)(1)`) is the explicit spelling; with (a) it also
types as `Bits[Literal[8]]`.

### Summary ranking

1. Class-body-annotated headers/structs with typed views and no
   `__getattr__` (b1) — biggest usability and static-typing win, verified.
2. `Bits[W]` with `Literal` widths, overloaded `bit()` and `Bits[Any]`
   holes (a1–a3) — verified; requires the spelling compromise.
3. Object references with declare-then-define and decorator-called bodies
   (c1–c2) — MLIR/xDSL/PyCDE precedent; removes strings and `a.port`.
4. Keep `with`-builders and the two-clocks doc (d) — already right.
5. Keep the literal rule (e) — already right; make the no-context cases
   spell an explicit typed literal.
