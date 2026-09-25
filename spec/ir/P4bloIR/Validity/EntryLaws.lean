import P4bloIR.Interp
import P4bloIR.Validity.KindLaws

/-!
# Progress at the entry points

`progress` and `finishes_kind` speak about the step machine. This module
states their consequence for the three functions an architecture calls,
`runParser`, `runControl` and `runDeparser` of `P4bloIR.Interp`: given a
valid program, typed arguments, a contract-satisfying extern state and, for
a control, entries `Installed.build` accepted, the machine inside never
fails. A parser returns an outcome that accepts with `NoError` or rejects
with an error the program declares; a control fails only if the final
frame's headers or metadata variable is not a struct; a deparser always
returns its bytes.

The entry points use private helpers, so this module restates them
publicly, word for word, and proves each equal to its original by `rfl`,
as `Build.index` restates `Index.build`.

What is assumed, by premise: termination, as every run of the block
finishing (`Finishes`), which is still open. What is not established: that
a control's final headers and metadata are structs. That needs the frame
the machine ends in to be the entry block's, which the invariant does not
track; `structVar` is the check that remains.
-/

namespace P4bloIR.Validity.Entry

/-- `P4bloIR.blockOf`, restated. -/
def blockOf (index : Index) (name : String) (kind : BlockKind) (arity : Nat) (what : String) :
    Except String Block := do
  let some decl := index.blocks[name]? | throw s!"unknown block '{name}'"
  if decl.kind != kind || decl.params.length != arity then throw s!"block '{name}' is not a {what}"
  pure decl

/-- `P4bloIR.structVar`, restated. -/
def structVar (run : Run) (name : String) : Except String Value := do
  let some v := run.frame.vars[name]? | throw s!"unknown variable '{name}'"
  let _ ← v.expectStruct
  pure v

/-- `P4bloIR.finished`, restated. -/
def finished (result : Except Fault Unit) : Except String Unit :=
  match result with
  | .ok () => pure ()
  | .error (.interp msg) => throw msg
  | .error (.parse e) => throw s!"parse error '{e}' outside a parser"

/-- `P4bloIR.runParser`, restated. -/
def runParser (index : Index) (block : String) (packet : ByteArray) (metadata : Value)
    (externs : Externs) : Except String ParseOutcome := do
  let decl ← blockOf index block .parser 2 "parser of (out H, inout M)"
  let [headersParam, metadataParam] := decl.params | throw "unreachable"
  let frame ← Frame.forBlock index decl
  let frame := { frame with vars := frame.vars.insert metadataParam.name metadata }
  let run : Run := { index, externs, frame, packet := some (Packet.ofBytes packet) }
  let (result, run) := (runStates decl).run run
  let (accepted, error) ← match result with
    | .ok () => pure (true, "NoError")
    | .error (.parse e) => pure (false, e)
    | .error (.interp msg) => throw msg
  let some packet := run.packet | throw "the parser lost its packet"
  pure { headers := ← structVar run headersParam.name,
         metadata := ← structVar run metadataParam.name,
         consumedBits := packet.cursor, accepted, error, externs := run.externs }

/-- `P4bloIR.runControl`, restated. -/
def runControl (index : Index) (block : String) (headers metadata : Value)
    (entries : Installed) (externs : Externs) : Except String (Value × Value × Externs) := do
  let decl ← blockOf index block .control 2 "control of (inout H, inout M)"
  let [headersParam, metadataParam] := decl.params | throw "unreachable"
  let frame ← Frame.forBlock index decl
  let frame := { frame with vars := (frame.vars.insert headersParam.name headers).insert metadataParam.name metadata }
  let run : Run := { index, entries := some entries, externs, frame }
  let (result, run) := (execute decl.body).run run
  finished result
  pure (← structVar run headersParam.name, ← structVar run metadataParam.name, run.externs)

/-- `P4bloIR.runDeparser`, restated. -/
def runDeparser (index : Index) (block : String) (headers : Value) (externs : Externs) :
    Except String (ByteArray × Externs) := do
  let decl ← blockOf index block .deparser 1 "deparser of (in H)"
  let [headersParam] := decl.params | throw "unreachable"
  let frame ← Frame.forBlock index decl
  let frame := { frame with vars := frame.vars.insert headersParam.name headers }
  let run : Run := { index, externs, frame, emitter := some {} }
  let (result, run) := (execute decl.body).run run
  finished result
  let some emitter := run.emitter | throw "the deparser lost its buffer"
  pure (emitter.toBytes, run.externs)

theorem runParser_eq : P4bloIR.runParser = runParser := rfl
theorem runControl_eq : P4bloIR.runControl = runControl := rfl
theorem runDeparser_eq : P4bloIR.runDeparser = runDeparser := rfl

open Execution

/-- The run a finished trace ends with is well formed.

Premises: a finite trace from a `MachineOk` machine. -/
theorem finishes_runOk {G : Global} {m : Machine} {o : Outcome} (h : Finishes m o)
    (hm : MachineOk G m) : RunOk G o.2 := by
  induction h with
  | done hstep =>
    rename_i machine result
    obtain ⟨work, run, fault⟩ := machine
    cases work with
    | nil =>
      simp only [step] at hstep
      cases hstep
      cases fault <;> exact hm.run
    | cons task rest =>
      simp only [step] at hstep
      split at hstep
      · cases hstep
      · split at hstep <;> cases hstep
  | next hstep _ ih =>
    have := progress hm
    rw [hstep] at this
    exact ih this

/-- A control of a valid program, run on typed headers and metadata with
installed entries and bound externs, never fails inside the machine: its
result is the final run's headers, metadata and externs.

Premises: a `Global` of kind control, the control block indexed under `n`
with parameters `[hp, mp]`, values of their types, entries from
`Installed.build`, externs satisfying the extern contract, and every run of
the body finishing.

It does not establish that `structVar` succeeds on the final frame, or
termination. -/
theorem runControl_documented {G : Global} {n : String} {b : Block} {hp mp : Param}
    {hv mv : Value} {inst : Installed} {e : Externs} {host : Option Entries}
    (hG : G.kind = .control) (hb : G.idx.blocks[n]? = some b) (hk : b.kind = .control)
    (hps : b.params = [hp, mp]) (hhv : ValueHas G.idx hv hp.type) (hmv : ValueHas G.idx mv mp.type)
    (hinst : Installed.build G.idx host = .ok inst) (he : G.externs.inv e)
    (hterm : ∀ m : Machine, m.work = [.statements b.body] → ∃ o, Finishes m o) :
    ∃ run : Run, RunOk G run ∧
      P4bloIR.runControl G.idx n hv mv inst e =
        (do pure (← structVar run hp.name, ← structVar run mp.name, run.externs)) := by
  have hkG : b.kind = G.kind := hk.trans hG.symm
  obtain ⟨sc, f, hsc, hfb, hok⟩ := entryFrame_ok (G := G) (vals := fun _ => none) hb hkG
    (by intro q _ v h; cases h)
  have hf0 := hok [] (by simp)
  simp only [List.foldl_nil] at hf0
  obtain ⟨sc', hsc', hscb, hcb⟩ := G.blockCtx hb hkG
  rw [hsc] at hsc'
  cases hsc'
  have hlaws : Build.ScopeLaws b sc := hscb ▸ hcb.laws
  let fr : Frame := { f with vars := (f.vars.insert hp.name hv).insert mp.name mv }
  have hfr : FrameOk { index := G.idx, scope := sc, kind := G.kind } fr := by
    refine ⟨hf0.scope, fun x d hd => ?_, hf0.layer⟩
    simp only [fr, Std.HashMap.getElem?_insert]
    by_cases hxm : mp.name = x
    · subst hxm
      rw [hlaws.paramFound mp (by simp [hps])] at hd
      cases hd
      exact ⟨mv, by simp, hmv⟩
    · by_cases hxh : hp.name = x
      · subst hxh
        rw [hlaws.paramFound hp (by simp [hps])] at hd
        cases hd
        exact ⟨hv, by simp [hxm], hhv⟩
      · simpa [hxm, hxh] using hf0.vars x d hd
  let run0 : Run := { index := G.idx, entries := some inst, externs := e, frame := fr }
  have hr0 : RunOk G run0 :=
    { index := rfl
      packet := fun h => by rw [hG] at h; cases h
      emitter := fun h => by rw [hG] at h; cases h
      entries := fun _ => ⟨inst, rfl, build_installedOk G hinst⟩
      externs := he }
  have hm0 := (initial_ok hb hkG hr0 hsc hfr).2.2
  obtain ⟨o, hfin⟩ := hterm { work := [.statements b.body], run := run0 } rfl
  have hres := finishes_outside_parser hfin ⟨hm0, rfl, by simp [parserFree]⟩ (by rw [hG]; decide)
  have hrun := finishes_runOk hfin hm0
  obtain ⟨res, run⟩ := o
  simp only at hres hrun
  subst hres
  refine ⟨run, hrun, ?_⟩
  rw [runControl_eq]
  unfold runControl blockOf
  have hdrive := hfin.sound
  simp only [run0, fr] at hdrive
  simp only [hb, hk, hps, bne_self_eq_false, List.length_cons, List.length_nil,
    Bool.false_or, Nat.reduceAdd, Bool.false_eq_true, ↓reduceIte, execute, run_eq]
  simp only [pure_bind, hps, hfb, finished]
  rw [show (Except.ok f : Except String Frame) = pure f from rfl, pure_bind]
  simp only [hdrive, pure_bind]

/-- A deparser of a valid program, run on typed headers with bound externs,
returns the bytes it emitted.

Premises: a `Global` of kind deparser, the deparser indexed under `n` with
the one parameter `hp`, a value of its type, externs satisfying the extern
contract, and every run of the body finishing.

It does not establish termination, or anything about which bytes. -/
theorem runDeparser_ok {G : Global} {n : String} {b : Block} {hp : Param} {hv : Value}
    {e : Externs} (hG : G.kind = .deparser) (hb : G.idx.blocks[n]? = some b)
    (hk : b.kind = .deparser) (hps : b.params = [hp]) (hhv : ValueHas G.idx hv hp.type)
    (he : G.externs.inv e)
    (hterm : ∀ m : Machine, m.work = [.statements b.body] → ∃ o, Finishes m o) :
    ∃ (run : Run) (em : Emitter), RunOk G run ∧ run.emitter = some em ∧
      P4bloIR.runDeparser G.idx n hv e = .ok (em.toBytes, run.externs) := by
  have hkG : b.kind = G.kind := hk.trans hG.symm
  obtain ⟨sc, f, hsc, hfb, hok⟩ := entryFrame_ok (G := G) (vals := fun _ => none) hb hkG
    (by intro q _ v h; cases h)
  have hf0 := hok [] (by simp)
  simp only [List.foldl_nil] at hf0
  obtain ⟨sc', hsc', hscb, hcb⟩ := G.blockCtx hb hkG
  rw [hsc] at hsc'
  cases hsc'
  have hlaws : Build.ScopeLaws b sc := hscb ▸ hcb.laws
  let fr : Frame := { f with vars := f.vars.insert hp.name hv }
  have hfr : FrameOk { index := G.idx, scope := sc, kind := G.kind } fr := by
    refine ⟨hf0.scope, fun x d hd => ?_, hf0.layer⟩
    simp only [fr, Std.HashMap.getElem?_insert]
    by_cases hxh : hp.name = x
    · subst hxh
      rw [hlaws.paramFound hp (by simp [hps])] at hd
      cases hd
      exact ⟨hv, by simp, hhv⟩
    · simpa [hxh] using hf0.vars x d hd
  let run0 : Run := { index := G.idx, externs := e, frame := fr, emitter := some {} }
  have hr0 : RunOk G run0 :=
    { index := rfl
      packet := fun h => by rw [hG] at h; cases h
      emitter := fun _ => rfl
      entries := fun h => by rw [hG] at h; cases h
      externs := he }
  have hm0 := (initial_ok hb hkG hr0 hsc hfr).2.2
  obtain ⟨o, hfin⟩ := hterm { work := [.statements b.body], run := run0 } rfl
  have hres := finishes_outside_parser hfin ⟨hm0, rfl, by simp [parserFree]⟩ (by rw [hG]; decide)
  have hrun := finishes_runOk hfin hm0
  obtain ⟨res, run⟩ := o
  simp only at hres hrun
  subst hres
  obtain ⟨em, hem⟩ := Option.isSome_iff_exists.mp (hrun.emitter hG)
  refine ⟨run, em, hrun, hem, ?_⟩
  rw [runDeparser_eq]
  unfold runDeparser blockOf
  have hdrive := hfin.sound
  simp only [run0, fr] at hdrive
  simp only [hb, hk, hps, bne_self_eq_false, List.length_cons, List.length_nil,
    Bool.false_or, Nat.reduceAdd, Bool.false_eq_true, ↓reduceIte, execute, run_eq]
  simp only [pure_bind, hps, hfb, finished]
  rw [show (Except.ok f : Except String Frame) = pure f from rfl, pure_bind]
  simp only [hdrive, pure_bind, hem]
  rfl

/-- A parser of a valid program, run on a packet with typed metadata and
bound externs, returns an outcome that accepts with `NoError` or rejects
with an error the program declares, read from the final run.

Premises: a `Global` of kind parser, the parser indexed under `n` with
parameters `[hp, mp]`, metadata of `mp`'s type, externs satisfying the
extern contract, and every run from its start state finishing.

It does not establish that `structVar` succeeds on the final frame, or
termination. -/
theorem runParser_documented {G : Global} {n : String} {b : Block} {hp mp : Param}
    {bytes : ByteArray} {mv : Value} {e : Externs} (hG : G.kind = .parser)
    (hb : G.idx.blocks[n]? = some b) (hk : b.kind = .parser) (hps : b.params = [hp, mp])
    (hmv : ValueHas G.idx mv mp.type) (he : G.externs.inv e)
    (hterm : ∀ m : Machine, m.work = [.states b] → ∃ o, Finishes m o) :
    ∃ (run : Run) (p : Packet) (accepted : Bool) (error : String), RunOk G run ∧
      run.packet = some p ∧
      (accepted = true ∧ error = "NoError" ∨ accepted = false ∧ error ∈ G.p.errors) ∧
      P4bloIR.runParser G.idx n bytes mv e =
        (do pure { headers := ← structVar run hp.name, metadata := ← structVar run mp.name,
                   consumedBits := p.cursor, accepted, error, externs := run.externs }) := by
  have hkG : b.kind = G.kind := hk.trans hG.symm
  obtain ⟨sc, f, hsc, hfb, hok⟩ := entryFrame_ok (G := G) (vals := fun _ => none) hb hkG
    (by intro q _ v h; cases h)
  have hf0 := hok [] (by simp)
  simp only [List.foldl_nil] at hf0
  obtain ⟨sc', hsc', hscb, hcb⟩ := G.blockCtx hb hkG
  rw [hsc] at hsc'
  cases hsc'
  have hlaws : Build.ScopeLaws b sc := hscb ▸ hcb.laws
  let fr : Frame := { f with vars := f.vars.insert mp.name mv }
  have hfr : FrameOk { index := G.idx, scope := sc, kind := G.kind } fr := by
    refine ⟨hf0.scope, fun x d hd => ?_, hf0.layer⟩
    simp only [fr, Std.HashMap.getElem?_insert]
    by_cases hxm : mp.name = x
    · subst hxm
      rw [hlaws.paramFound mp (by simp [hps])] at hd
      cases hd
      exact ⟨mv, by simp, hmv⟩
    · simpa [hxm] using hf0.vars x d hd
  let run0 : Run := { index := G.idx, externs := e, frame := fr,
                      packet := some (Packet.ofBytes bytes) }
  have hr0 : RunOk G run0 :=
    { index := rfl
      packet := fun _ => rfl
      emitter := fun h => by rw [hG] at h; cases h
      entries := fun h => by rw [hG] at h; cases h
      externs := he }
  have hm0 := (initial_ok hb hkG hr0 hsc hfr).2.1 hk
  obtain ⟨o, hfin⟩ := hterm { work := [.states b], run := run0 } rfl
  have hres := finishes_documented hfin hm0
  have hrun := finishes_runOk hfin hm0
  obtain ⟨res, run⟩ := o
  simp only at hres hrun
  obtain ⟨p, hp'⟩ := Option.isSome_iff_exists.mp (hrun.packet hG)
  have hdrive := hfin.sound
  simp only [run0, fr] at hdrive
  rw [runParser_eq]
  unfold runParser blockOf
  simp only [hb, hk, hps, bne_self_eq_false, List.length_cons, List.length_nil,
    Bool.false_or, Nat.reduceAdd, Bool.false_eq_true, ↓reduceIte, runStates, run_eq]
  simp only [pure_bind, hps, hfb]
  rw [show (Except.ok f : Except String Frame) = pure f from rfl, pure_bind]
  simp only [hdrive]
  rcases hres with rfl | ⟨err, rfl, herr⟩
  · exact ⟨run, p, true, "NoError", hrun, hp', .inl ⟨rfl, rfl⟩, by simp [hp']⟩
  · exact ⟨run, p, false, err, hrun, hp', .inr ⟨rfl, herr⟩, by simp [hp']⟩

end P4bloIR.Validity.Entry
