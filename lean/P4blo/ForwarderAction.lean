import P4blo.ForwarderProof
import P4blo.FieldActionWrites

/-! The actual selected `ipv4_forward` table action. This boundary neither
selects a route nor proves the surrounding parser, checksum or pipeline. -/

namespace P4blo.ForwarderAction

open P4bloIR P4bloIR.Execution P4bloIR.ScalarStatements Fields Forwarder

set_option maxRecDepth 8192

/-- Every stored field, including invalid-header contents. These observations
are independent of the authored paths and the IR evaluator. -/
structure Snapshot where
  dst : Fin (2 ^ 48)
  src : Fin (2 ^ 48)
  etherType : Fin (2 ^ 16)
  ethernetValid : Bool
  version : Fin 16
  ihl : Fin 16
  diffserv : Fin 256
  totalLen : Fin 65536
  identification : Fin 65536
  flags : Fin 8
  fragOffset : Fin 8192
  ttl : Fin 256
  protocol : Fin 256
  checksum : Fin 65536
  ipSrc : Fin (2 ^ 32)
  ipDst : Fin (2 ^ 32)
  ipv4Valid : Bool
  ingress : Fin 512
  egress : Fin 512
  drop : Bool
  deriving DecidableEq, Repr

def restore (s : Snapshot) : Store roots :=
  .cons (.aggregate () (.cons (.aggregate s.ethernetValid
    (.cons (.scalar s.dst) (.cons (.scalar s.src) (.cons (.scalar s.etherType) .nil))))
    (.cons (.aggregate s.ipv4Valid
      (.cons (.scalar s.version) (.cons (.scalar s.ihl) (.cons (.scalar s.diffserv)
      (.cons (.scalar s.totalLen) (.cons (.scalar s.identification) (.cons (.scalar s.flags)
      (.cons (.scalar s.fragOffset) (.cons (.scalar s.ttl) (.cons (.scalar s.protocol)
      (.cons (.scalar s.checksum) (.cons (.scalar s.ipSrc) (.cons (.scalar s.ipDst) .nil))))))))))))) .nil)))
  (.cons (.aggregate () (.cons (.scalar s.ingress) (.cons (.scalar s.egress)
    (.cons (.scalar s.drop) .nil)))) .nil)

def observe : Store roots → Snapshot
  | .cons (.aggregate () (.cons (.aggregate ev
      (.cons (.scalar dst) (.cons (.scalar src) (.cons (.scalar et) .nil))))
      (.cons (.aggregate iv
        (.cons (.scalar version) (.cons (.scalar ihl) (.cons (.scalar ds)
        (.cons (.scalar len) (.cons (.scalar id) (.cons (.scalar flags)
        (.cons (.scalar frag) (.cons (.scalar ttl) (.cons (.scalar proto)
        (.cons (.scalar checksum) (.cons (.scalar ips) (.cons (.scalar ipd) .nil))))))))))))) .nil)))
    (.cons (.aggregate () (.cons (.scalar ingress) (.cons (.scalar egress)
      (.cons (.scalar drop) .nil)))) .nil) =>
      ⟨dst, src, et, ev, version, ihl, ds, len, id, flags, frag, ttl, proto,
        checksum, ips, ipd, iv, ingress, egress, drop⟩

theorem observe_restore (s : Snapshot) : observe (restore s) = s := by cases s; rfl

theorem restore_observe : (store : Store roots) → restore (observe store) = store
  | .cons (.aggregate () (.cons (.aggregate _
      (.cons (.scalar _) (.cons (.scalar _) (.cons (.scalar _) .nil))))
      (.cons (.aggregate _
        (.cons (.scalar _) (.cons (.scalar _) (.cons (.scalar _)
        (.cons (.scalar _) (.cons (.scalar _) (.cons (.scalar _)
        (.cons (.scalar _) (.cons (.scalar _) (.cons (.scalar _)
        (.cons (.scalar _) (.cons (.scalar _) (.cons (.scalar _) .nil))))))))))))) .nil)))
    (.cons (.aggregate () (.cons (.scalar _) (.cons (.scalar _)
      (.cons (.scalar _) .nil)))) .nil) => rfl

/-- Mathematical policy: decrement wraps, independently of the emitted SUB.
All omitted record fields, including checksum and prior drop, are unchanged. -/
def policy (s : Snapshot) (dst : Fin (2 ^ 48)) (port : Fin 512) : Snapshot :=
  { s with
    dst := dst, src := s.dst, egress := port,
    ttl := ⟨(s.ttl.val + 255) % 256, Nat.mod_lt _ (by decide)⟩ }

private def portStage (s : Snapshot) (port : Fin 512) : Snapshot := { s with egress := port }
private def srcStage (s : Snapshot) (port : Fin 512) : Snapshot :=
  { portStage s port with src := s.dst }
private def dstStage (s : Snapshot) (dst : Fin (2 ^ 48)) (port : Fin 512) : Snapshot :=
  { srcStage s port with dst }

private theorem source_port (s : Snapshot) (port : Fin 512) :
    Forwarder.egress.set (restore s) port = restore (portStage s port) := by cbv
private theorem source_src (s : Snapshot) (port : Fin 512) :
    Forwarder.ethSrc.set (restore (portStage s port)) s.dst = restore (srcStage s port) := by cbv
private theorem source_dst (s : Snapshot) (dst : Fin (2 ^ 48)) (port : Fin 512) :
    Forwarder.ethDst.set (restore (srcStage s port)) dst = restore (dstStage s dst port) := by cbv
private theorem source_ttl (s : Snapshot) (dst : Fin (2 ^ 48)) (port : Fin 512) :
    Forwarder.ttl.set (restore (dstStage s dst port)) (policy s dst port).ttl =
      restore (policy s dst port) := by cbv

def call (dst : Fin (2 ^ 48)) (port : Fin 512) : ActionCall :=
  ⟨"ipv4_forward", [.bits 48 dst.val, .bits 9 port.val]⟩

theorem action_lookup : Forwarder.scope.actions["ipv4_forward"]? = some forwardAction := by cbv

/-- This anchor states the actual complete order, not a projected operation set. -/
theorem body_identity : forwardAction.body = [
    .assign (.member (.var "meta") "egress_port") (.var "port"),
    .assign (.member (.member (.var "hdr") "ethernet") "srcAddr")
      (.member (.member (.var "hdr") "ethernet") "dstAddr"),
    .assign (.member (.member (.var "hdr") "ethernet") "dstAddr") (.var "dstAddr"),
    .assign (.member (.member (.var "hdr") "ipv4") "ttl")
      (.binary .sub (.member (.member (.var "hdr") "ipv4") "ttl") (.literal (.bits 8 1))) ] := by cbv

def parameters (dst : Fin (2 ^ 48)) (port : Fin 512) : Std.HashMap String Value :=
  (({} : Std.HashMap String Value).insert "dstAddr" (Scalar.toValue (t := .bits 48) dst)).insert
    "port" (Scalar.toValue (t := .bits 9) port)

def active (run : Run) (dst : Fin (2 ^ 48)) (port : Fin 512) : Run :=
  { run with frame := { run.frame with
    action := some "ipv4_forward", actionVars := some (parameters dst port) } }

private def put (run : Run) (name : String) (value : Value) : Run :=
  { run with frame := { run.frame with vars := run.frame.vars.insert name value } }

/-- Exact ordered block-map updates, derived from independent record values.
No assumption identifies separately rebuilt hash maps extensionally. -/
def result (run : Run) (s : Snapshot) (dst : Fin (2 ^ 48)) (port : Fin 512) : Run :=
  put (put (put (put run "meta" ((restore (portStage s port)).get (.there .here)).toValue)
    "hdr" ((restore (srcStage s port)).get .here).toValue)
    "hdr" ((restore (dstStage s dst port)).get .here).toValue)
    "hdr" ((restore (policy s dst port)).get .here).toValue

private theorem run_get (run : Run) : (get : M Run).run run = (.ok run, run) := rfl
private theorem run_modify (f : Run → Run) (run : Run) :
    (modify f : M Unit).run run = (.ok (), f run) := rfl

theorem entry (run : Run) (dst : Fin (2 ^ 48)) (port : Fin 512)
    (hs : run.frame.scope = Forwarder.scope) :
    (dispatch (.tableAction (call dst port))).run run =
      (.ok [.statements forwardAction.body, .actionReturn run.frame none], active run dst port) := by
  have hd : literalValue (.bits 48 dst.val) = Scalar.toValue (t := .bits 48) dst := by
    simp [literalValue, Literal.toValue, Scalar.toValue, Bits.wrap, Nat.mod_eq_of_lt dst.isLt]
  have hp : literalValue (.bits 9 port.val) = Scalar.toValue (t := .bits 9) port := by
    simp [literalValue, Literal.toValue, Scalar.toValue, Bits.wrap, Nat.mod_eq_of_lt port.isLt]
  simp [dispatch, ScalarTyping.run_bind, ScalarTyping.run_map, run_get, run_modify,
    getFrame, setFrame, call, hs, action_lookup, forwardAction, active, parameters, hd, hp]

private theorem active_matches (s : Snapshot) (run : Run) (dst : Fin (2 ^ 48)) (port : Fin 512)
    (hf : FrameMatches (restore s) run.frame) (hb : BlockFrame run.frame) :
    FrameMatches (restore s) (active run dst port).frame := by
  intro shape root
  have h := hf root
  cases root with
  | here => simpa [active, Frame.read?, parameters, Slot.name, hb.2] using h
  | there root => cases root with
    | here => simpa [active, Frame.read?, parameters, Slot.name, hb.2] using h
    | there root => cases root

private theorem egress_ref : Forwarder.egress =
    Ref.mk (.there .here) (.field (.there .here) .scalar) := by cbv
private theorem src_ref : Forwarder.ethSrc =
    Ref.mk .here (.field .here (.field (.there .here) .scalar)) := by cbv
private theorem dst_ref : Forwarder.ethDst =
    Ref.mk .here (.field .here (.field .here .scalar)) := by cbv
private theorem ttl_ref : Forwarder.ttl =
    Ref.mk .here (.field (.there .here)
      (.field (.there (.there (.there (.there (.there (.there (.there .here))))))) .scalar)) := by cbv

private theorem port_write (s : Snapshot) (run : Run) (port : Fin 512)
    (hi : roots.IndexAgrees run.index) (hf : FrameMatches (restore s) run.frame)
    (hu : run.frame.actionVars.bind (·["meta"]?) = none) :
    let final := put run "meta" ((restore (portStage s port)).get (.there .here)).toValue
    (writeLValue Forwarder.egress.lvalue (Scalar.toValue (t := .bits 9) port)).run run =
      (.ok (), final) ∧ FrameMatches (restore (portStage s port)) final.frame := by
  rw [egress_ref]
  exact ⟨Ref.write_unshadowed (.there .here) (.field (.there .here) .scalar)
    (restore s) port run hi hf hu,
    hf.set_unshadowed (by decide) (.there .here) _ hu⟩

private theorem src_write (s : Snapshot) (run : Run) (port : Fin 512)
    (hi : roots.IndexAgrees run.index) (hf : FrameMatches (restore (portStage s port)) run.frame)
    (hu : run.frame.actionVars.bind (·["hdr"]?) = none) :
    let final := put run "hdr" ((restore (srcStage s port)).get .here).toValue
    (writeLValue Forwarder.ethSrc.lvalue (Scalar.toValue (t := .bits 48) s.dst)).run run =
      (.ok (), final) ∧ FrameMatches (restore (srcStage s port)) final.frame := by
  rw [src_ref]
  exact ⟨Ref.write_unshadowed .here (.field .here (.field (.there .here) .scalar))
    (restore (portStage s port)) s.dst run hi hf hu,
    hf.set_unshadowed (by decide) .here _ hu⟩

private theorem dst_write (s : Snapshot) (run : Run) (dst : Fin (2 ^ 48)) (port : Fin 512)
    (hi : roots.IndexAgrees run.index) (hf : FrameMatches (restore (srcStage s port)) run.frame)
    (hu : run.frame.actionVars.bind (·["hdr"]?) = none) :
    let final := put run "hdr" ((restore (dstStage s dst port)).get .here).toValue
    (writeLValue Forwarder.ethDst.lvalue (Scalar.toValue (t := .bits 48) dst)).run run =
      (.ok (), final) ∧ FrameMatches (restore (dstStage s dst port)) final.frame := by
  rw [dst_ref]
  exact ⟨Ref.write_unshadowed .here (.field .here (.field .here .scalar))
    (restore (srcStage s port)) dst run hi hf hu,
    hf.set_unshadowed (by decide) .here _ hu⟩

private theorem ttl_write (s : Snapshot) (run : Run) (dst : Fin (2 ^ 48)) (port : Fin 512)
    (hi : roots.IndexAgrees run.index) (hf : FrameMatches (restore (dstStage s dst port)) run.frame)
    (hu : run.frame.actionVars.bind (·["hdr"]?) = none) :
    let final := put run "hdr" ((restore (policy s dst port)).get .here).toValue
    (writeLValue Forwarder.ttl.lvalue (Scalar.toValue (t := .bits 8) (policy s dst port).ttl)).run run =
      (.ok (), final) ∧ FrameMatches (restore (policy s dst port)) final.frame := by
  rw [ttl_ref]
  exact ⟨Ref.write_unshadowed .here (.field (.there .here)
    (.field (.there (.there (.there (.there (.there (.there (.there .here))))))) .scalar))
    (restore (dstStage s dst port)) (policy s dst port).ttl run hi hf hu,
    hf.set_unshadowed (by decide) .here _ hu⟩

private theorem assignment (run final : Run) (target : LValue) (expr : P4bloIR.Expr) (value : Value)
    (he : (evaluate expr).run run = (.ok value, run))
    (hw : (writeLValue target value).run run = (.ok (), final)) :
    (dispatch (.statement (.assign target expr))).run run = (.ok [], final) := by
  simp [dispatch, ScalarTyping.run_bind, ScalarTyping.run_map, he, hw]

private theorem subtract_ttl (s : Snapshot) (run : Run) (dst : Fin (2 ^ 48)) (port : Fin 512)
    (hi : roots.IndexAgrees run.index) (hf : FrameMatches (restore (dstStage s dst port)) run.frame) :
    (evaluate (.binary .sub Forwarder.ttl.expr (.literal (.bits 8 1)))).run run =
      (.ok (Scalar.toValue (t := .bits 8) (policy s dst port).ttl), run) := by
  have hr := Forwarder.ttl.evaluate (restore (dstStage s dst port)) run hi hf
  have source : Forwarder.ttl.get (restore (dstStage s dst port)) = s.ttl := by
    rw [ttl_ref]; rfl
  rw [source] at hr
  have arithmetic : s.ttl.val + 256 - 1 = s.ttl.val + 255 := by omega
  have hb (b : Bits) : expectBits (.bits b) = pure b := rfl
  simp [evaluate, ScalarTyping.run_bind, ScalarTyping.run_pure, hr,
    literalValue, Literal.toValue, hb, Scalar.toValue, bitsBinary, Bits.wrap, policy, arithmetic]

private theorem assignment_step (run final : Run) (target : LValue) (expr : P4bloIR.Expr)
    (rest : List Work)
    (h : (dispatch (.statement (.assign target expr))).run run = (.ok [], final)) :
    step { work := .statement (.assign target expr) :: rest, run } =
      .inr { work := rest, run := final } := by simp [step, h]

/-- Ten actual transitions stop with normal actionReturn still pending.
The installed action layer remains; no continuation work has executed. -/
theorem before_return (run : Run) (s : Snapshot) (dst : Fin (2 ^ 48)) (port : Fin 512)
    (continuation : List Work) (hi : run.index = Forwarder.index)
    (hs : run.frame.scope = Forwarder.scope) (hb : BlockFrame run.frame)
    (hf : FrameMatches (restore s) run.frame) :
    Steps { work := .tableAction (call dst port) :: continuation, run }
      { work := .actionReturn run.frame none :: continuation,
        run := result (active run dst port) s dst port } := by
  let r0 := active run dst port
  let r1 := put r0 "meta" ((restore (portStage s port)).get (.there .here)).toValue
  let r2 := put r1 "hdr" ((restore (srcStage s port)).get .here).toValue
  let r3 := put r2 "hdr" ((restore (dstStage s dst port)).get .here).toValue
  let r4 := put r3 "hdr" ((restore (policy s dst port)).get .here).toValue
  have h0 : FrameMatches (restore s) r0.frame := active_matches s run dst port hf hb
  have unshadowed : (some (parameters dst port)).bind (·["hdr"]?) = none ∧
      (some (parameters dst port)).bind (·["meta"]?) = none := by simp [parameters]
  have indexAgreement : roots.IndexAgrees run.index := hi ▸ roots_agree
  have hp := port_write s r0 port indexAgreement h0 unshadowed.2
  have hsrc := src_write s r1 port indexAgreement hp.2 unshadowed.1
  have hdst := dst_write s r2 dst port indexAgreement hsrc.2 unshadowed.1
  have httl := ttl_write s r3 dst port indexAgreement hdst.2 unshadowed.1
  have readPort : (evaluate (.var "port")).run r0 =
      (.ok (Scalar.toValue (t := .bits 9) port), r0) := by
    apply readVar_action r0 (avs := parameters dst port) rfl
    simp [parameters]
  have readDst : (evaluate (.var "dstAddr")).run r2 =
      (.ok (Scalar.toValue (t := .bits 48) dst), r2) := by
    apply readVar_action r2 (avs := parameters dst port) rfl
    simp [parameters, Std.HashMap.getElem_insert]
  have readOldDst : (evaluate Forwarder.ethDst.expr).run r1 =
      (.ok (Scalar.toValue (t := .bits 48) s.dst), r1) := by
    have h := Forwarder.ethDst.evaluate (restore (portStage s port)) r1 indexAgreement hp.2
    have source : Forwarder.ethDst.get (restore (portStage s port)) = s.dst := by rw [dst_ref]; rfl
    simpa only [source] using h
  have ap := assignment r0 r1 _ _ _ readPort hp.1
  have asrc := assignment r1 r2 _ _ _ readOldDst hsrc.1
  have adst := assignment r2 r3 _ _ _ readDst hdst.1
  have attl := assignment r3 r4 _ _ _ (subtract_ttl s r3 dst port indexAgreement hdst.2) httl.1
  have entered : step { work := .tableAction (call dst port) :: continuation, run } =
      .inr {
        work := .statements forwardAction.body :: .actionReturn run.frame none :: continuation,
        run := r0 } := by simp [step, entry run dst port hs, r0]
  exact .next entered (.next rfl (.next (assignment_step _ _ _ _ _ ap)
    (.next rfl (.next (assignment_step _ _ _ _ _ asrc)
    (.next rfl (.next (assignment_step _ _ _ _ _ adst)
    (.next rfl (.next (assignment_step _ _ _ _ _ attl) (.next rfl .refl)))))))))

/-- The eleventh transition restores only action layers, retaining all four
block updates. The exact result does not rebuild any unrelated Run field. -/
theorem source_steps (run : Run) (store : Store roots) (dst : Fin (2 ^ 48)) (port : Fin 512)
    (continuation : List Work) (hi : run.index = Forwarder.index)
    (hs : run.frame.scope = Forwarder.scope) (hb : BlockFrame run.frame)
    (hf : FrameMatches store run.frame) :
    Steps { work := .tableAction (call dst port) :: continuation, run }
      { work := continuation, run := result run (observe store) dst port } := by
  have prior := before_return run (observe store) dst port continuation hi hs hb
    (by rw [restore_observe]; exact hf)
  apply prior.trans
  apply Steps.next ?_ .refl
  simp [step, dispatch, ScalarTyping.run_bind, ScalarTyping.run_map,
    getFrame, setFrame, run_get, run_modify, result, put, active]

/-- Actual normal runActionCall completion, not a direct callAction proxy. -/
theorem run_correct (run : Run) (store : Store roots) (dst : Fin (2 ^ 48)) (port : Fin 512)
    (hi : run.index = Forwarder.index) (hs : run.frame.scope = Forwarder.scope)
    (hb : BlockFrame run.frame) (hf : FrameMatches store run.frame) :
    (runActionCall (call dst port)).run run = (.ok (), result run (observe store) dst port) :=
  ((source_steps run store dst port [] hi hs hb hf).finishes (.done rfl)).sound

theorem result_matches (run : Run) (s : Snapshot) (dst : Fin (2 ^ 48)) (port : Fin 512)
    (hb : BlockFrame run.frame) :
    FrameMatches (restore (policy s dst port)) (result run s dst port).frame := by
  intro shape root
  cases root with
  | here => simp [result, put, Frame.read?, hb.2, Slot.name]
  | there root => cases root with
    | here => simp [result, put, Frame.read?, hb.2, Slot.name, Std.HashMap.getElem_insert]; rfl
    | there root => cases root

theorem changes_only_vars (run : Run) (s : Snapshot) (dst : Fin (2 ^ 48)) (port : Fin 512) :
    ChangesOnlyVars run (result run s dst port) := ⟨_, rfl⟩

theorem preserves_outside (run : Run) (s : Snapshot) (dst : Fin (2 ^ 48)) (port : Fin 512) :
    PreservesOutside ["hdr", "meta"] run (result run s dst port) := by
  intro name hn
  simp only [List.mem_cons, List.not_mem_nil, or_false, not_or] at hn
  simp [result, put, Std.HashMap.getElem?_insert, Ne.symm hn.1, Ne.symm hn.2]

private theorem initialized_scope (scope : BlockScope) (frame : Frame)
    (vars : Except String (Std.HashMap String Value))
    (h : (do let values ← vars; pure ({ scope, vars := values } : Frame)) = .ok frame) :
    frame.scope = scope := by cases vars <;> cases h <;> rfl

/-- Scope identity is derived from the same successful initialization used by
the corpus proof, not a separately fabricated declaration map. -/
theorem initial_scope : initialFrame.scope = Forwarder.scope := by
  have h := frame_built
  simp only [Frame.forBlock, scope_lookup] at h
  exact initialized_scope _ _ _ h

def populated (store : Store roots) : Frame :=
  { initialFrame with vars := ((initialFrame.vars.insert "hdr" (store.get .here).toValue).insert
    "meta" (store.get (.there .here)).toValue) }

theorem populated_matches (store : Store roots) : FrameMatches store (populated store) := by
  intro shape root
  cases root with
  | here => simp [populated, Frame.read?, frame_no_action.2, Slot.name, Std.HashMap.getElem_insert]
  | there root => cases root with
    | here => simp [populated, Frame.read?, frame_no_action.2, Slot.name]
    | there root => cases root

/-- A constructive instance for every source store, starting from the actual
Frame.forBlock activation and installing the real hdr/meta argument values. -/
theorem populated_correct (store : Store roots) (dst : Fin (2 ^ 48)) (port : Fin 512) :
    let run : Run := { index := Forwarder.index, frame := populated store }
    (runActionCall (call dst port)).run run = (.ok (), result run (observe store) dst port) := by
  exact run_correct _ store dst port rfl initial_scope frame_no_action (populated_matches store)

end P4blo.ForwarderAction
