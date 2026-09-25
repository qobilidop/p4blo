import P4bloIR.Validity.StepLaws
import P4bloIR.Validity.InstallLaws
import P4bloIR.ScalarStatements

/-!
# Progress: a valid program never gets stuck

`Execution.step` has two kinds of fault: a parser error (`Fault.parse`),
which is an outcome the semantics defines, and an `InterpError`
(`Fault.interp`), which the step machine uses for "cannot happen": a name
that resolves to nothing, a value of the wrong kind, a missing packet.
This module proves that for a program `Validity.check` accepts, the second
kind cannot happen.

`progress`: from a well-formed machine (`MachineOk`), one step finishes
successfully, finishes with a parser error the program declares, or
reaches another well-formed machine. `MachineOk` itself only admits
declared parser errors as the fault being unwound, so by induction
(`Steps.machineOk`) no reachable machine carries an `InterpError`, and a
finite run (`finishes_documented`) ends in success or a declared parser
error. `initial_ok` gives the well-formed machines the entry points start.

What is assumed, by premise: the program is `Valid` (for instance,
`Validity.check` accepted it, `check_sound`); the architecture's extern
binding obeys `ExternContract`; the installed table entries obey
`InstalledOk`, which every successful `Installed.build` does
(`build_installedOk`); the initial run fits the block kind and its frame
holds a value of every declared type. Binding and installation errors
happen at load and installation, before any packet runs, and are outside
this theorem.

What is not established: termination. A finite trace is required for a
result; that every run of a valid program is finite (the acyclic call
graph with the parser's revisit rule) is the next obligation.
-/

namespace P4bloIR.Validity

open Execution
open ScalarTyping (run_bind run_pure run_map)

/-- The result of a finished run is success or a parser error the program
declares. -/
def ResultOk (G : Global) (result : Except Fault Unit) : Prop :=
  result = .ok () ∨ ∃ e, result = .error (.parse e) ∧ e ∈ G.p.errors

/-- One step of a well-formed machine never gets stuck.

Premise: `MachineOk G m`, which includes a valid program, the extern and
installation contracts, and a typed continuation stack.

Conclusion: `step m` either finishes with success or with a parser error
the program declares, or yields a machine that is again well formed; in
particular it never yields an `InterpError`.

It does not establish that the machine finishes. -/
theorem progress {G : Global} {m : Machine} (hm : MachineOk G m) :
    match step m with
    | .inl (result, _) => ResultOk G result
    | .inr m' => MachineOk G m' := by
  obtain ⟨work, run, fault⟩ := m
  obtain ⟨hr, hmode⟩ := hm
  simp only at hr hmode
  cases work with
  | nil =>
    simp only [step]
    cases fault with
    | none => exact .inl rfl
    | some f =>
      obtain ⟨⟨e, rfl, he⟩, -⟩ := hmode
      exact .inr ⟨e, rfl, he⟩
  | cons task rest =>
    simp only [step]
    cases fault with
    | none =>
      obtain ⟨c, hc, hf, hs⟩ := hmode
      have ht := dispatch_ok hc hf hr hs
      unfold Triple at ht
      simp only [Option.isSome_none, Bool.false_and, Bool.false_eq_true, ↓reduceIte]
      revert ht
      cases (dispatch task).run run with
      | mk res run' =>
        cases res with
        | ok next =>
          rintro ⟨hr', c', hc', hf', hs'⟩
          exact ⟨hr', c', hc', hf', hs'⟩
        | error f =>
          rintro ⟨hdoc, hr', c', hc', hf', hu⟩
          exact ⟨hr', hdoc, c', hc', hf', hu⟩
    | some f =>
      obtain ⟨hdoc, c, hc, hf, hu⟩ := hmode
      cases task with
      | blockReturn caller params args =>
        have ht := blockReturn_unwind hc hf hr hu
        unfold Triple at ht
        simp only [Option.isSome_some, Work.handlesFault, Bool.not_true, Bool.and_false,
          Bool.false_eq_true, ↓reduceIte]
        revert ht
        cases (dispatch (.blockReturn caller params args)).run run with
        | mk res run' =>
          cases res with
          | ok next =>
            rintro ⟨rfl, hr', c', hc', hf', hu'⟩
            exact ⟨hr', hdoc, c', hc', hf', hu'⟩
          | error f' =>
            rintro ⟨hdoc', hr', c', hc', hf', hu'⟩
            exact ⟨hr', hdoc', c', hc', hf', hu'⟩
      | _ =>
        simp only [Option.isSome_some, Work.handlesFault, Bool.not_false, Bool.and_self,
          ↓reduceIte]
        exact ⟨hr, hdoc, c, hc, hf, by simpa [UnwindOk] using hu⟩

/-- Every machine reachable from a well-formed one is well formed. -/
theorem Steps.machineOk {G : Global} {m m' : Machine} (h : Steps m m') (hm : MachineOk G m) :
    MachineOk G m' := by
  induction h with
  | refl => exact hm
  | next hstep _ ih =>
    have := progress hm
    rw [hstep] at this
    exact ih this

/-- A finite run of a well-formed machine ends in success or in a parser
error the program declares.

Premises: `MachineOk G m` and a finite trace of `step` from `m`.

It does not establish that the trace exists; that is termination. -/
theorem finishes_documented {G : Global} {m : Machine} {o : Outcome} (h : Finishes m o)
    (hm : MachineOk G m) : ResultOk G o.1 := by
  induction h with
  | done hstep =>
    have := progress hm
    rw [hstep] at this
    exact this
  | next hstep _ ih =>
    have := progress hm
    rw [hstep] at this
    exact ih this

/-- The same for the actual runner: when a well-formed machine has a
finite trace, `drive` returns success or a declared parser error. -/
theorem drive_documented {G : Global} {m : Machine} {o : Outcome} (h : Finishes m o)
    (hm : MachineOk G m) : drive m = o ∧ ResultOk G o.1 :=
  ⟨h.sound, finishes_documented h hm⟩

-- ---------------------------------------------------------------------------
-- Entry
-- ---------------------------------------------------------------------------

/-- The machine an entry point starts is well formed: a block of the
program, of the run's kind, run from a frame of its scope that holds a
value of every declared type, with no action layer.

Premises: the block is indexed and of the run's kind, `RunOk`, and the
frame is well formed for the block's scope (see `entryFrame_ok`).

Conclusion: `MachineOk` for `[.runBlock b]`, and for the direct forms the
entry points in `P4bloIR.Interp` use: `[.states b]` for a parser and
`[.statements b.body]` otherwise. -/
theorem initial_ok {G : Global} {n : String} {b : Block} {sc : BlockScope} {rn : Run}
    (hb : G.idx.blocks[n]? = some b) (hk : b.kind = G.kind) (hr : RunOk G rn)
    (hsc : G.idx.scopes[b.name]? = some sc)
    (hf : FrameOk { index := G.idx, scope := sc, kind := G.kind } rn.frame) :
    MachineOk G { work := [.runBlock b], run := rn } ∧
      (b.kind = .parser → MachineOk G { work := [.states b], run := rn }) ∧
      MachineOk G { work := [.statements b.body], run := rn } := by
  obtain ⟨sc', hsc', hscb, hc⟩ := G.blockCtx hb hk
  rw [hsc] at hsc'
  cases hsc'
  refine ⟨⟨hr, ⟨_, hc, hf, hscb, rfl, trivial⟩⟩, fun hp => ⟨hr, ⟨_, hc, hf, hscb, rfl, hp, trivial⟩⟩,
    ⟨hr, ⟨_, hc, hf, ?_, trivial⟩⟩⟩
  have := hc.typed.body
  rw [hscb] at this
  simp only [Ctx.ofBlock, hk] at this
  exact this

/-- The frame the entry points build is well formed: `Frame.forBlock`,
then each parameter set to a value of its type.

Premises: the block is indexed, and each value given for a parameter has
the parameter's type.

It does not cover a frame built any other way. -/
theorem entryFrame_ok {G : Global} {n : String} {b : Block} {vals : String → Option Value}
    (hb : G.idx.blocks[n]? = some b) (hk : b.kind = G.kind)
    (hvals : ∀ q ∈ b.params, ∀ v, vals q.name = some v → ValueHas G.idx v q.type) :
    ∃ sc f, G.idx.scopes[b.name]? = some sc ∧ Frame.forBlock G.idx b = .ok f ∧
      ∀ (names : List String), (∀ x ∈ names, ∃ q ∈ b.params, q.name = x) →
        FrameOk { index := G.idx, scope := sc, kind := G.kind }
          { f with vars := names.foldl (fun m x => match vals x with
              | some v => m.insert x v
              | none => m) f.vars } := by
  obtain ⟨sc, hsc, hscb, hc⟩ := G.blockCtx hb hk
  have hlaws : Build.ScopeLaws b sc := hscb ▸ hc.laws
  have hbt : BlockTyped G.idx sc b := hscb ▸ hc.typed
  have hvty : ∀ (x : String) (d : VarDecl), sc.vars[x]? = some d → TyOk G.idx d.type := by
    intro x d hd
    obtain ⟨_, hsrc⟩ := hlaws.varOrigin x d hd
    rcases hsrc with ⟨q, hq, rfl⟩ | ⟨v, hv, rfl⟩
    · exact (hbt.params q hq).2
    · exact hbt.locals v hv
  obtain ⟨f, hfb, hs, hav, hvars⟩ := forBlock_ok G.laws hsc hvty
  refine ⟨sc, f, hsc, hfb, fun names hnames => ⟨hs, ?_, by simp [LayerOk, hav]⟩⟩
  suffices key : ∀ (names : List String) (m0 : Std.HashMap String Value),
      (∀ x ∈ names, ∃ q ∈ b.params, q.name = x) → VarsOk G.idx sc m0 →
      VarsOk G.idx sc (names.foldl (fun m x => match vals x with
        | some v => m.insert x v
        | none => m) m0) from key names f.vars hnames hvars
  intro names
  induction names with
  | nil => intro m0 _ h; exact h
  | cons x xs ih =>
    intro m0 hn h0
    obtain ⟨q, hq, hqx⟩ := hn x (by simp)
    simp only [List.foldl_cons]
    apply ih _ (fun z hz => hn z (List.mem_cons_of_mem _ hz))
    subst hqx
    cases hv : vals q.name with
    | none => exact h0
    | some v =>
      intro y d hd
      by_cases hqy : q.name = y
      · subst hqy
        rw [hlaws.paramFound q hq] at hd
        cases hd
        exact ⟨v, by simp, hvals q hq v hv⟩
      · simpa [Std.HashMap.getElem?_insert, hqy] using h0 y d hd

end P4bloIR.Validity
