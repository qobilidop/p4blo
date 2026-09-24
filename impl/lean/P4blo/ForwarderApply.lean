import P4blo.ForwarderTables

/-! Actual application of the unchanged forwarder's table. This boundary
does not execute its surrounding validity guards or checksum continuation. -/
namespace P4blo.ForwarderApply

open P4bloIR P4bloIR.Execution P4bloIR.ScalarStatements Fields Forwarder
open ForwarderAction (Snapshot restore observe)
open ForwarderTables (Config RouteData Decision)

inductive Effect where
  | forward (data : RouteData)
  | drop
  | noAction
  deriving Repr, DecidableEq

def effect (c : Config) : Decision → Effect
  | .network => .forward c.network
  | .host => .forward c.host
  | .drop => .drop
  | .noAction => .noAction
  | .forwardDefault => match c.otherwise with
    | .drop => .drop
    | .noAction => .noAction
    | .forward d => .forward d

def Effect.call : Effect → ActionCall
  | .forward d => d.call
  | .drop => ⟨"drop", []⟩
  | .noAction => ⟨"NoAction", []⟩

def hit : Decision → Bool
  | .network | .host => true
  | _ => false

theorem decision_result (c : Config) (d : Decision) :
    d.result c = ⟨some (effect c d).call, hit d⟩ := by
  cases d <;> cases hc : c.otherwise <;>
    simp [Decision.result, effect, Effect.call, hit, hc, ForwarderTables.Default.call]

/-- Full independent stored-field policy. Validity does not gate application;
the surrounding real control, not this operation, supplies its IPv4 guard. -/
def Effect.policy (e : Effect) (s : Snapshot) : Snapshot := match e with
  | .forward d => ForwarderAction.policy s d.dst d.port
  | .drop => { s with drop := true }
  | .noAction => s

def selected (c : Config) (s : Snapshot) : Effect :=
  effect c (ForwarderTables.select c s.ipDst)

def policy (c : Config) (s : Snapshot) : Snapshot := (selected c s).policy s

def dropped (run : Run) (s : Snapshot) : Run :=
  let vars := run.frame.vars.insert "meta"
    ((restore { s with drop := true }).get (.there .here)).toValue
  { run with frame := { run.frame with vars } }

def Effect.result (e : Effect) (run : Run) (s : Snapshot) : Run := match e with
  | .forward d => ForwarderAction.result run s d.dst d.port
  | .drop => dropped run s
  | .noAction => run

def result (c : Config) (run : Run) (s : Snapshot) : Run :=
  (selected c s).result run s

private theorem run_get (run : Run) : (get : M Run).run run = (.ok run, run) := rfl
private theorem run_modify (f : Run → Run) (run : Run) :
    (modify f : M Unit).run run = (.ok (), f run) := rfl

theorem table_lookup : Forwarder.scope.tables["ipv4_lpm"]? = some ipv4Table := by cbv
theorem drop_lookup : Forwarder.scope.actions["drop"]? = some dropAction := by cbv
theorem no_action_lookup : Forwarder.scope.actions["NoAction"]? = some noAction := by cbv

/-- Literal complete key identity, not a projected name or assumed key read. -/
theorem key_identity : ipv4Table.keys =
    [⟨.member (.member (.var "hdr") "ipv4") "dstAddr", .lpm, ""⟩] := by cbv

private theorem ip_dst_ref : Forwarder.ipDst =
    Ref.mk .here (.field (.there .here)
      (.field (.there (.there (.there (.there (.there (.there
        (.there (.there (.there (.there (.there .here))))))))))) .scalar)) := by
  cbv

theorem key_evaluate (run : Run) (s : Snapshot)
    (hi : run.index = Forwarder.index) (hf : FrameMatches (restore s) run.frame) :
    (evaluate Forwarder.ipDst.expr).run run =
      (.ok (.bits (ForwarderTables.query s.ipDst)), run) := by
  have h := Forwarder.ipDst.evaluate (restore s) run (hi ▸ roots_agree) hf
  have source : Forwarder.ipDst.get (restore s) = s.ipDst := by rw [ip_dst_ref]; rfl
  simpa only [source, Scalar.toValue, ForwarderTables.query] using h

/-- Actual table dispatch reads the key and installed lookup, leaving the
selected action and success-only hit administrative step pending. -/
theorem dispatch_table (c : Config) (run : Run) (s : Snapshot) (target : Option LValue)
    (hi : run.index = Forwarder.index) (hs : run.frame.scope = Forwarder.scope)
    (he : run.entries = some (ForwarderTables.installed c))
    (hf : FrameMatches (restore s) run.frame) :
    (dispatch (.table "ipv4_lpm" target)).run run =
      (.ok [.tableAction (selected c s).call,
        .writeHit target (hit (ForwarderTables.select c s.ipDst))], run) := by
  have key := key_evaluate run s hi hf
  have lookup := ForwarderTables.lookup_correct c s.ipDst
  rw [decision_result] at lookup
  simp only [ForwarderTables.ref] at lookup
  have block : run.frame.block.name = "MyIngress" := by
    simp [Frame.block, hs, Forwarder.scope_block, ingress]
  have bitsRun (b : Bits) (r : Run) : (expectBits (.bits b)).run r = (.ok b, r) := rfl
  simp [dispatch, ScalarTyping.run_bind, run_get, getFrame,
    hs, table_lookup, ipv4Table, key, bitsRun, P4bloIR.liftExcept,
    requireEntries, he, block, lookup, selected]

private def activeEmpty (run : Run) (name : String) : Run :=
  { run with frame := { run.frame with action := some name, actionVars := some {} } }

private theorem active_matches (run : Run) (s : Snapshot) (name : String)
    (hb : BlockFrame run.frame) (hf : FrameMatches (restore s) run.frame) :
    FrameMatches (restore s) (activeEmpty run name).frame := by
  intro shape root
  have h := hf root
  simpa [activeEmpty, Frame.read?, hb.2] using h

private theorem drop_ref : Forwarder.dropFlag =
    Ref.mk (.there .here) (.field (.there (.there .here)) .scalar) := by cbv

private theorem drop_write (run : Run) (s : Snapshot)
    (hi : run.index = Forwarder.index) (hf : FrameMatches (restore s) run.frame)
    (hu : run.frame.actionVars.bind (·["meta"]?) = none) :
    (writeLValue Forwarder.dropFlag.lvalue (.bool true)).run run =
      (.ok (), dropped run s) := by
  rw [drop_ref]
  exact Ref.write_unshadowed (.there .here) (.field (.there (.there .here)) .scalar)
    (restore s) true run (hi ▸ roots_agree) hf hu

theorem drop_steps (run : Run) (s : Snapshot) (continuation : List Work)
    (hi : run.index = Forwarder.index) (hs : run.frame.scope = Forwarder.scope)
    (hb : BlockFrame run.frame) (hf : FrameMatches (restore s) run.frame) :
    Steps { work := .tableAction ⟨"drop", []⟩ :: continuation, run }
      { work := continuation, run := dropped run s } := by
  let r0 := activeEmpty run "drop"
  have enter : (dispatch (.tableAction ⟨"drop", []⟩)).run run =
      (.ok [.statements dropAction.body, .actionReturn run.frame none], r0) := by
    simp [dispatch, ScalarTyping.run_bind, ScalarTyping.run_map, run_get, run_modify,
      getFrame, setFrame, hs, drop_lookup, dropAction, activeEmpty, r0]
  have write := drop_write r0 s hi (active_matches run s "drop" hb hf)
    (by simp [r0, activeEmpty])
  have assignment : (dispatch (.statement (.assign Forwarder.dropFlag.lvalue
      (.literal (.boolean true))))).run r0 = (.ok [], dropped r0 s) := by
    simp [dispatch, evaluate, literalValue, Literal.toValue, ScalarTyping.run_map, write]
  have returnStep : step
      { work := .actionReturn run.frame none :: continuation, run := dropped r0 s } =
      .inr { work := continuation, run := dropped run s } := by
    simp [step, dispatch, ScalarTyping.run_bind, ScalarTyping.run_map,
      getFrame, setFrame, run_get, run_modify, r0, activeEmpty, dropped]
  have entered : step { work := .tableAction ⟨"drop", []⟩ :: continuation, run } =
      .inr {
        work := .statements dropAction.body :: .actionReturn run.frame none :: continuation
        run := r0 } := by simp [step, enter]
  have assigned : step
      { work := .statement (.assign Forwarder.dropFlag.lvalue (.literal (.boolean true))) ::
          .statements [] :: .actionReturn run.frame none :: continuation
        run := r0 } =
      .inr {
        work := .statements [] :: .actionReturn run.frame none :: continuation
        run := dropped r0 s } := by simp [step, assignment]
  exact .next entered (.next rfl (.next assigned (.next rfl (.next returnStep .refl))))

theorem no_action_steps (run : Run) (continuation : List Work)
    (hs : run.frame.scope = Forwarder.scope) :
    Steps { work := .tableAction ⟨"NoAction", []⟩ :: continuation, run }
      { work := continuation, run } := by
  have enter : (dispatch (.tableAction ⟨"NoAction", []⟩)).run run =
      (.ok [.statements [], .actionReturn run.frame none], activeEmpty run "NoAction") := by
    simp [dispatch, ScalarTyping.run_bind, ScalarTyping.run_map, run_get, run_modify,
      getFrame, setFrame, hs, no_action_lookup, noAction, activeEmpty]
  have returned : step
      { work := .actionReturn run.frame none :: continuation, run := activeEmpty run "NoAction" } =
      .inr { work := continuation, run } := by
    simp [step, dispatch, ScalarTyping.run_bind, ScalarTyping.run_map,
      getFrame, setFrame, run_get, run_modify, activeEmpty]
  have entered : step { work := .tableAction ⟨"NoAction", []⟩ :: continuation, run } =
      .inr {
        work := .statements [] :: .actionReturn run.frame none :: continuation
        run := activeEmpty run "NoAction" } := by simp [step, enter]
  exact .next entered (.next rfl (.next returned .refl))

theorem Effect.source_steps (e : Effect) (run : Run) (s : Snapshot)
    (continuation : List Work) (hi : run.index = Forwarder.index)
    (hs : run.frame.scope = Forwarder.scope) (hb : BlockFrame run.frame)
    (hf : FrameMatches (restore s) run.frame) :
    Steps { work := .tableAction e.call :: continuation, run }
      { work := continuation, run := e.result run s } := by
  cases e with
  | forward d =>
    simpa [Effect.call, Effect.result, ForwarderAction.observe_restore,
      ForwarderTables.RouteData.call, ForwarderAction.call] using
      ForwarderAction.source_steps run (restore s) d.dst d.port continuation hi hs hb hf
  | drop => exact drop_steps run s continuation hi hs hb hf
  | noAction => exact no_action_steps run continuation hs

/-- Stop before writeHit. Even a missing hit target retains this real
administrative step; an arbitrary continuation has not executed. -/
theorem before_hit (c : Config) (run : Run) (store : Store roots)
    (target : Option LValue) (continuation : List Work)
    (hi : run.index = Forwarder.index) (hs : run.frame.scope = Forwarder.scope)
    (hb : BlockFrame run.frame) (he : run.entries = some (ForwarderTables.installed c))
    (hf : FrameMatches store run.frame) :
    Steps { work := .table "ipv4_lpm" target :: continuation, run }
      { work := .writeHit target (hit (ForwarderTables.select c (observe store).ipDst)) ::
          continuation, run := result c run (observe store) } := by
  have frameAgreement : FrameMatches (restore (observe store)) run.frame := by
    rw [ForwarderAction.restore_observe]; exact hf
  have enter := dispatch_table c run (observe store) target hi hs he frameAgreement
  exact .next (by simp [step, enter])
    ((selected c (observe store)).source_steps run (observe store) _ hi hs hb frameAgreement)

/-- Actual table application for the unchanged no-hit-target operation.
The explicit finite chain contains 13/7/5 transitions for forward/drop/no-op;
Steps itself is unindexed and leaves arbitrary continuation work untouched. -/
theorem source_steps (c : Config) (run : Run) (store : Store roots)
    (continuation : List Work) (hi : run.index = Forwarder.index)
    (hs : run.frame.scope = Forwarder.scope) (hb : BlockFrame run.frame)
    (he : run.entries = some (ForwarderTables.installed c))
    (hf : FrameMatches store run.frame) :
    Steps { work := .table "ipv4_lpm" none :: continuation, run }
      { work := continuation, run := result c run (observe store) } := by
  apply (before_hit c run store none continuation hi hs hb he hf).trans
  exact .next rfl .refl

theorem run_correct (c : Config) (run : Run) (store : Store roots)
    (hi : run.index = Forwarder.index) (hs : run.frame.scope = Forwarder.scope)
    (hb : BlockFrame run.frame) (he : run.entries = some (ForwarderTables.installed c))
    (hf : FrameMatches store run.frame) :
    (applyTable "ipv4_lpm" none).run run = (.ok (), result c run (observe store)) :=
  ((source_steps c run store [] hi hs hb he hf).finishes (.done rfl)).sound

theorem Effect.result_matches (e : Effect) (run : Run) (s : Snapshot)
    (hb : BlockFrame run.frame) (hf : FrameMatches (restore s) run.frame) :
    FrameMatches (restore (e.policy s)) (e.result run s).frame := by
  cases e with
  | forward d => exact ForwarderAction.result_matches run s d.dst d.port hb
  | noAction => exact hf
  | drop =>
    have unchanged : ((restore { s with drop := true }).get .here).toValue =
        ((restore s).get .here).toValue := rfl
    intro shape root
    cases root with
    | here => simpa [Effect.result, Effect.policy, dropped, Frame.read?, hb.2,
        Slot.name, Std.HashMap.getElem?_insert, unchanged] using hf .here
    | there root => cases root with
      | here => simp [Effect.result, Effect.policy, dropped, Frame.read?, hb.2, Slot.name]
      | there root => cases root

theorem result_matches (c : Config) (run : Run) (s : Snapshot)
    (hb : BlockFrame run.frame) (hf : FrameMatches (restore s) run.frame) :
    FrameMatches (restore (policy c s)) (result c run s).frame :=
  (selected c s).result_matches run s hb hf

theorem changes_only_vars (c : Config) (run : Run) (s : Snapshot) :
    ChangesOnlyVars run (result c run s) := by
  unfold result
  cases selected c s with
  | forward d => exact ForwarderAction.changes_only_vars run s d.dst d.port
  | noAction => exact .refl run
  | drop => exact ⟨_, rfl⟩

theorem preserves_outside (c : Config) (run : Run) (s : Snapshot) :
    PreservesOutside ["hdr", "meta"] run (result c run s) := by
  unfold result
  cases selected c s with
  | forward d => exact ForwarderAction.preserves_outside run s d.dst d.port
  | noAction => intro name _; rfl
  | drop =>
    intro name hn
    simp only [List.mem_cons, List.not_mem_nil, or_false, not_or] at hn
    simp [Effect.result, dropped, Std.HashMap.getElem?_insert, Ne.symm hn.2]

/-- Constructive instance: real Program/Index, initialized control scope,
arbitrary source values, and the proved actual installer, not fabricated maps. -/
theorem populated_correct (c : Config) (store : Store roots) :
    let run : Run := {
      index := Forwarder.index, frame := ForwarderAction.populated store
      entries := some (ForwarderTables.installed c) }
    (applyTable "ipv4_lpm" none).run run = (.ok (), result c run (observe store)) := by
  exact run_correct c _ store rfl ForwarderAction.initial_scope frame_no_action rfl
    (ForwarderAction.populated_matches store)

end P4blo.ForwarderApply
