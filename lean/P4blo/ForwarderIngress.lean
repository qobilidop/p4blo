import P4blo.ForwarderApply

/-! Exact prefix of the original ingress body, stopping before its checksum
conditional. This is neither checksum execution nor whole-body completion. -/
namespace P4blo.ForwarderIngress

open P4bloIR P4bloIR.Execution P4bloIR.ScalarStatements Fields Forwarder
open ForwarderAction (Snapshot observe restore)
open ForwarderTables (Config)

def firstConditional : Stmt :=
  .conditional (.isValid (.member (.var "hdr") "ipv4")) [.apply "ipv4_lpm" none] []

private def ipField (name : String) : P4bloIR.Expr :=
  .member (.member (.var "hdr") "ipv4") name

def checksumConditional : Stmt :=
  .conditional Forwarder.ipv4.expr
    [.callExtern "csum" "compute" [.expr checksumInput] (some hdrChecksum.lvalue)] []

/-- Full pending syntax, independently spelled rather than projected from
the body under proof. The order and destination are part of the boundary. -/
theorem checksum_identity : checksumConditional =
  .conditional (.isValid (.member (.var "hdr") "ipv4"))
    [.callExtern "csum" "compute"
      [.expr (["ihl", "diffserv", "totalLen", "identification", "flags",
        "fragOffset", "ttl", "protocol", "srcAddr", "dstAddr"].map ipField |>.foldl
          (.binary .concat) (ipField "version"))]
      (some (.member (.member (.var "hdr") "ipv4") "hdrChecksum"))] [] := by cbv

theorem body_identity : ingress.body = [firstConditional, checksumConditional] := by rfl

def policy (c : Config) (s : Snapshot) : Snapshot :=
  if s.ipv4Valid then ForwarderApply.policy c s else s

def result (c : Config) (run : Run) (s : Snapshot) : Run :=
  if s.ipv4Valid then ForwarderApply.result c run s else run

/-- Concrete operational admissibility for the valid branch only. These are
state identities, not an assumed lookup or execution correctness callback. -/
def Ready (c : Config) (run : Run) : Prop :=
  run.frame.scope = Forwarder.scope ∧ BlockFrame run.frame ∧
    run.entries = some (ForwarderTables.installed c)

theorem guard_evaluate (run : Run) (store : Store roots)
    (hi : run.index = Forwarder.index) (hf : FrameMatches store run.frame) :
    (evaluate Forwarder.ipv4.expr).run run =
      (.ok (.bool (observe store).ipv4Valid), run) := by
  have h := Forwarder.ipv4.evaluate store run (hi ▸ roots_agree) hf
  have source : Forwarder.ipv4.get store = (observe store).ipv4Valid := by
    calc
      _ = Forwarder.ipv4.get (restore (observe store)) :=
        congrArg Forwarder.ipv4.get (ForwarderAction.restore_observe store).symm
      _ = _ := rfl
  simpa only [source] using h

private theorem conditional_of_guard (run : Run) (value : Bool)
    (guard : (evaluate Forwarder.ipv4.expr).run run = (.ok (.bool value), run)) :
    (dispatch (.statement firstConditional)).run run =
      (.ok [.statements (if value then [.apply "ipv4_lpm" none] else [])], run) := by
  change (dispatch (.statement (.conditional Forwarder.ipv4.expr
    [.apply "ipv4_lpm" none] []))).run run = _
  simp [dispatch, ScalarTyping.run_bind, guard, expectBool, Value.expectBool, P4bloIR.liftExcept]
  rfl

/-- The raw invalid boundary needs only the actual header read and index:
no metadata agreement, valid stored fields, entries, scope or action absence. -/
theorem invalid_steps_header (run : Run) (ethernet : Value) (ipv4Values : List Value)
    (continuation : List Work) (hi : run.index = Forwarder.index)
    (header : run.frame.read? "hdr" = some (Forwarder.invalidHeaders ethernet ipv4Values)) :
    Steps { work := .statements ingress.body :: continuation, run }
      { work := .statements [checksumConditional] :: continuation, run } := by
  have guard := conditional_of_guard run false
    (Forwarder.invalid_guard run ethernet ipv4Values hi header)
  simp only [Bool.false_eq_true, ↓reduceIte] at guard
  have selected : step
      { work := .statement firstConditional :: .statements [checksumConditional] :: continuation
        run } = .inr {
      work := .statements [] :: .statements [checksumConditional] :: continuation, run } := by
    simp [step, guard]
  rw [body_identity]
  exact .next rfl (.next selected (.next rfl .refl))

/-- The typed-store corollary derives its header witness, rather than adding
metadata or action-free-frame premises to the raw invalid theorem. -/
theorem invalid_steps (run : Run) (store : Store roots) (continuation : List Work)
    (hi : run.index = Forwarder.index) (hf : FrameMatches store run.frame)
    (invalid : (observe store).ipv4Valid = false) :
    Steps { work := .statements ingress.body :: continuation, run }
      { work := .statements [checksumConditional] :: continuation, run } := by
  have shape : ∃ ethernet fields, ((restore (observe store)).get .here).toValue =
      Forwarder.invalidHeaders ethernet fields := by
    simp only [restore, invalid, Forwarder.invalidHeaders]
    exact ⟨_, _, rfl⟩
  obtain ⟨ethernet, fields, shape⟩ := shape
  have header := hf (.here : Slot roots _)
  rw [← ForwarderAction.restore_observe store] at header
  exact invalid_steps_header run ethernet fields continuation hi
    (header.trans (congrArg some shape))

/-- Valid IPv4 composes the actual table application, then pops its real
empty branch list. Ethernet validity, TTL and prior drop do not gate it. -/
theorem valid_steps (c : Config) (run : Run) (store : Store roots)
    (continuation : List Work) (hi : run.index = Forwarder.index)
    (hf : FrameMatches store run.frame) (ready : Ready c run)
    (valid : (observe store).ipv4Valid = true) :
    Steps { work := .statements ingress.body :: continuation, run }
      { work := .statements [checksumConditional] :: continuation
        run := ForwarderApply.result c run (observe store) } := by
  have guard := conditional_of_guard run (observe store).ipv4Valid
    (guard_evaluate run store hi hf)
  simp only [valid, ↓reduceIte] at guard
  have selected : step
      { work := .statement firstConditional :: .statements [checksumConditional] :: continuation
        run } = .inr {
      work := .statements [.apply "ipv4_lpm" none] ::
        .statements [checksumConditional] :: continuation, run } := by
    simp [step, guard]
  have application := ForwarderApply.source_steps c run store
    (.statements [] :: .statements [checksumConditional] :: continuation)
    hi ready.1 ready.2.1 ready.2.2 hf
  rw [body_identity]
  exact .next rfl (.next selected (.next rfl (.next rfl
    (application.trans (.next rfl .refl)))))

/-- Exact prefix with arbitrary untouched continuation. Readiness is required
only if the stored IPv4 validity makes the actual branch execute. Steps is
unindexed; explicit chains/native boundaries have lengths18/12/10 or3. -/
theorem source_steps (c : Config) (run : Run) (store : Store roots)
    (continuation : List Work) (hi : run.index = Forwarder.index)
    (hf : FrameMatches store run.frame)
    (ready : (observe store).ipv4Valid = true → Ready c run) :
    Steps { work := .statements ingress.body :: continuation, run }
      { work := .statements [checksumConditional] :: continuation
        run := result c run (observe store) } := by
  cases validity : (observe store).ipv4Valid with
  | false => simpa [result, validity] using invalid_steps run store continuation hi hf validity
  | true => simpa [result, validity] using
      valid_steps c run store continuation hi hf (ready validity) validity

theorem result_matches (c : Config) (run : Run) (s : Snapshot)
    (hf : FrameMatches (restore s) run.frame)
    (hb : s.ipv4Valid = true → BlockFrame run.frame) :
    FrameMatches (restore (policy c s)) (result c run s).frame := by
  cases valid : s.ipv4Valid with
  | false => simp only [policy, result, valid, Bool.false_eq_true, ↓reduceIte]; exact hf
  | true =>
    simp only [policy, result, valid, ↓reduceIte]
    exact ForwarderApply.result_matches c run s (hb valid) hf

theorem changes_only_vars (c : Config) (run : Run) (s : Snapshot) :
    ChangesOnlyVars run (result c run s) := by
  cases valid : s.ipv4Valid with
  | false => simpa [result, valid] using ChangesOnlyVars.refl run
  | true => simpa [result, valid] using ForwarderApply.changes_only_vars c run s

theorem preserves_outside (c : Config) (run : Run) (s : Snapshot) :
    PreservesOutside ["hdr", "meta"] run (result c run s) := by
  cases valid : s.ipv4Valid with
  | false => intro name _; simp [result, valid]
  | true => simpa [result, valid] using ForwarderApply.preserves_outside c run s

/-- Constructive actual initialized scope and installed configuration for
every source store. The checksum conditional and K remain pending. -/
theorem populated_steps (c : Config) (store : Store roots) (continuation : List Work) :
    let run : Run := {
      index := Forwarder.index
      frame := ForwarderAction.populated store
      entries := some (ForwarderTables.installed c) }
    Steps { work := .statements ingress.body :: continuation, run }
      { work := .statements [checksumConditional] :: continuation
        run := result c run (observe store) } := by
  apply source_steps c _ store continuation rfl (ForwarderAction.populated_matches store)
  intro _
  exact ⟨ForwarderAction.initial_scope, frame_no_action, rfl⟩

end P4blo.ForwarderIngress
