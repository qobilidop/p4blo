import P4bloArch.Assembly
import P4bloArch.ContractLaws
import P4bloIR.Progress
import P4bloArchTest.Check

/-!
# A well-formed machine for a real program

The premises of `P4bloIR.Validity.progress` discharged together, by the
kernel, for the corpus program `csum16` (`tests/corpus/csum16/`): the
smallest corpus program with an extern. `Validity.check` accepts it, the
reference extern binding succeeds and meets the contract
(`P4bloArch.Contract.bind_contract`), the program's table entries install,
and the machine `runControl` starts for its control is well formed.

The concrete facts are discharged by `simp` unfolding the checker, the
index builder and the binder over the literal program: the index is a
chain of `HashMap.insert`s, and `simp` decides each lookup by the insert
lemmas and string literal equality. `decide` and `rfl` cannot evaluate
them, because `String.hash` is opaque to the kernel. No `native_decide`.

`program` is the corpus golden written as a Lean term. `tests` checks it
against `P4bloArchTest/fixtures/csum16.json`, the protobuf JSON of that golden,
which `tests/lean/test_lean_agrees_validity.py` keeps equal to the golden.
-/

namespace ArchTests.Csum16

open P4bloArch P4bloIR P4bloIR.Validity

/-- The `parserI` block of `csum16`. -/
def parserI : Block :=
  { name := "parserI", kind := .parser,
    params := [⟨"hdr", .struct "Parsed_packet", .out⟩, ⟨"meta", .struct "Metadata", .inout⟩],
    locals := [], actions := [], tables := [],
    states := [⟨"start", [.extract (.member (.var "hdr") "h")], .direct .accept⟩],
    startState := "start", body := [] }

/-- The `cIngress` block of `csum16`. -/
def cIngress : Block :=
  { name := "cIngress", kind := .control,
    params := [⟨"hdr", .struct "Parsed_packet", .inout⟩, ⟨"meta", .struct "Metadata", .inout⟩],
    locals := [], actions := [], tables := [], states := [], startState := "",
    body := [
      .assign (.member (.member (.var "hdr") "h") "d")
        (.binary .add (.member (.member (.var "hdr") "h") "d") (.literal (.bits 16 1))),
      .callExtern "csum" "compute" [.expr (.member (.member (.var "hdr") "h") "d")]
        (some (.member (.member (.var "hdr") "h") "c"))] }

/-- The `deparserI` block of `csum16`. -/
def deparserI : Block :=
  { name := "DeparserI", kind := .deparser,
    params := [⟨"hdr", .struct "Parsed_packet", .in⟩],
    locals := [], actions := [], tables := [], states := [], startState := "",
    body := [.emit (.member (.var "hdr") "h")] }

/-- `tests/corpus/csum16/csum16.txtpb`, as a Lean term. -/
def program : BlockAssembly where
  name := "csum16"
  errors := ["NoError", "PacketTooShort", "NoMatch", "StackOutOfBounds", "HeaderTooShort",
    "ParserTimeout", "ParserInvalidArgument"]
  headerTypes := [⟨"H", [⟨"d", .bits 16⟩, ⟨"c", .bits 16⟩]⟩]
  structTypes := [⟨"Parsed_packet", [⟨"h", .header "H"⟩]⟩, ⟨"Metadata", []⟩]
  enumTypes := []
  externTypes := [⟨"checksum16", [], [⟨"compute", [⟨"data", .bits 16, .in⟩], some (.bits 16)⟩]⟩]
  externInstances := [⟨"csum", "checksum16", []⟩]
  blocks := [parserI, cIngress, deparserI]
  headers := "Parsed_packet"
  metadata := "Metadata"
  exports := [⟨"parser", "parserI"⟩, ⟨"control", "cIngress"⟩, ⟨"deparser", "DeparserI"⟩]

/-- The checker accepts `csum16`; `simp` evaluates it over the literal. -/
theorem check_ok : ∃ idx, Validity.check program = .ok idx := by
  simp [Validity.check, Build.index_eq, Build.index, Build.addAll, Build.add, program,
    Build.errorStep, Build.scopeStep, Build.scope, Bind.bind, Except.bind, pure, Except.pure,
    VarDecl.name, parserI, cIngress, deparserI, Except.mapError, ensure, each, need, resolve, checkNames, checkTypeRefs,
    checkType, checkParams, checkExternType, checkLiteralArgs, checkBlock, checkShape,
    checkStmts, checkStmt, checkExpr, checkLValue, checkArgs, checkResult, checkExtractTarget,
    checkState, checkTarget, checkField, expect, tyDeep, fuel, scalarField,
    coreErrors, acyclic, blockCallees, allowed, Ctx.ofBlock, each.go,
    checkNames.go, ends, blockCalls, resolveVar, Ctx.var?, resolveLocal,
    Std.HashMap.getElem_insert, Std.HashMap.getElem?_insert, Std.HashMap.size_insert,
    Std.HashMap.contains_insert, writable, VarDecl.type, fieldType?, isHeader, binaryType,
    emittable, checkLiteral, isOut, noAlias, noAlias.go]

/-- The family segment of the extern type's name, by unfolding
`String.splitOnAux` step by step; the kernel does not reduce its
well-founded recursion directly. -/
theorem family : ("checksum16".splitOn ".").head! = "checksum16" := by
  simp only [String.splitOn]
  repeat (rw [String.splitOnAux]; simp (config := { decide := true }) only [↓reduceIte])

/-- The machine `runControl` starts for `csum16`'s control is well formed,
with every premise of progress discharged for the reference architecture.

Premises: none; everything is computed from the literal program.

Conclusion: a `Global` for `csum16` whose extern contract is the reference
architecture's (`P4bloArch.Contract.contract`), the control block
`cIngress`, the frame `Frame.forBlock` builds for it, the externs
`P4bloArch.bind` returns and the entries `Installed.build` returns, and
`MachineOk` for `[.statements body]` on the run `runControl` builds from
them with the zero headers and metadata `Frame.forBlock` leaves.

It does not establish that the run finishes, or anything about packet
values: that is what `progress` and its corollaries then give. -/
theorem control_start_ok : ∃ (G : Global) (b : Block) (f : Frame) (e : Externs) (inst : Installed),
    G.p = program ∧ G.kind = .control ∧ G.externs = P4bloArch.Contract.contract G.idx ∧
    G.idx.blocks["cIngress"]? = some b ∧ Frame.forBlock G.idx b = .ok f ∧
    P4bloArch.bind G.idx = .ok e ∧ Installed.build G.idx none = .ok inst ∧
    MachineOk G { work := [.statements b.body],
                  run := { index := G.idx, entries := some inst, externs := e, frame := f } } := by
  obtain ⟨idx, hc⟩ := check_ok
  have hv := check_sound hc
  let G : Global := ⟨program, idx, .control, hv, P4bloArch.Contract.contract idx⟩
  have hidx := hv.index
  simp [Build.index_eq, Build.index, Build.addAll, Build.add, program, Build.errorStep,
    Build.scopeStep, Build.scope, Bind.bind, Except.bind, pure, Except.pure, VarDecl.name,
    parserI, cIngress, deparserI] at hidx
  subst hidx
  have hb : G.idx.blocks["cIngress"]? = some cIngress := by
    simp [G, cIngress, Std.HashMap.getElem_insert]
  obtain ⟨sc, f, hsc, hf, hok⟩ := entryFrame_ok (G := G) (vals := fun _ => none) hb rfl
    (by intro q _ v h; cases h)
  have hfr := hok [] (by simp)
  simp only [List.foldl_nil] at hfr
  have hbind : P4bloArch.bind G.idx = .ok (P4bloArch.externs
      (({} : Std.HashMap String ExternState).insert "csum" .checksum16)) := by
    simp [G, P4bloArch.bind, Externs.bind, P4bloArch.registry, P4bloArch.externs, family,
      P4bloArch.shapeOf, P4bloArch.checksum16Shape, matchShape, P4bloArch.make,
      Bindings.unify]
    rfl
  let inst : Installed := { index := G.idx }
  have hinst : Installed.build G.idx none = .ok inst := by
    simp [G, inst, Installed.build]
    rfl
  have hr : RunOk G { index := G.idx
                      entries := some inst
                      externs := P4bloArch.externs
                        (({} : Std.HashMap String ExternState).insert "csum" .checksum16)
                      frame := f } :=
    { index := rfl
      packet := fun h => by cases h
      emitter := fun h => by cases h
      entries := fun _ => ⟨_, rfl, build_installedOk G hinst⟩
      externs := P4bloArch.Contract.bind_contract hv hbind }
  exact ⟨G, cIngress, f, _, _, rfl, rfl, rfl, hb, hf, hbind, hinst,
    (initial_ok hb rfl hr hsc hfr).2.2⟩

/-- The literal is the corpus program: the fixture decodes to it. -/
def tests (path : String) : T Unit := do
  match BlockAssembly.fromJsonString (← IO.FS.readFile path) with
  | .ok p => check "csum16 literal is the corpus golden" (p == program)
  | .error e =>
    IO.println s!"     got: {e}"
    check "csum16 fixture decodes" false

end ArchTests.Csum16
