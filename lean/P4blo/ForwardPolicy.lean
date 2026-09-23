import P4blo.FieldCommandExamples

/-! An application-intent contract for the already-parsed, route-selected
rewrite. The independent observation covers the entire source store and
uses data constructors, not the authored field accessors. No parser, route
lookup, checksum maintenance or architecture packet-fate claim follows. -/

namespace P4blo.ForwardPolicy

open Fields
open FieldCommandExamples (roots modes forward)

/-- Complete named state, including invalid-header contents and read-only
inputs. Fin bounds are representability, not valid-packet assumptions. -/
structure Snapshot where
  dst : Fin (2 ^ 48)
  src : Fin (2 ^ 48)
  etherType : Fin (2 ^ 16)
  ethernetValid : Bool
  ttl : Fin 256
  protocol : Fin 256
  checksum : Fin (2 ^ 16)
  ipv4Valid : Bool
  port : Fin 512
  drop : Bool
  sentinel : Fin (2 ^ 16)
  routeHit : Bool
  routeDst : Fin (2 ^ 48)
  routeSrc : Fin (2 ^ 48)
  routePort : Fin 512
  scratch : Fin 256
  deriving DecidableEq, Repr

def restore (s : Snapshot) : Store roots :=
  .cons (.aggregate () (.cons (.aggregate s.ethernetValid
    (.cons (.scalar s.dst) (.cons (.scalar s.src) (.cons (.scalar s.etherType) .nil))))
    (.cons (.aggregate s.ipv4Valid
      (.cons (.scalar s.ttl) (.cons (.scalar s.protocol) (.cons (.scalar s.checksum) .nil)))) .nil)))
  (.cons (.aggregate () (.cons (.scalar s.port) (.cons (.scalar s.drop) (.cons (.scalar s.sentinel) .nil))))
  (.cons (.aggregate () (.cons (.scalar s.routeHit) (.cons (.scalar s.routeDst)
    (.cons (.scalar s.routeSrc) (.cons (.scalar s.routePort) .nil)))))
  (.cons (.scalar s.scratch) .nil)))

def observe : Store roots → Snapshot
  | .cons (.aggregate () (.cons (.aggregate ev
      (.cons (.scalar dst) (.cons (.scalar src) (.cons (.scalar et) .nil))))
      (.cons (.aggregate iv
        (.cons (.scalar ttl) (.cons (.scalar protocol) (.cons (.scalar checksum) .nil)))) .nil)))
    (.cons (.aggregate () (.cons (.scalar port) (.cons (.scalar drop) (.cons (.scalar sentinel) .nil))))
    (.cons (.aggregate () (.cons (.scalar hit) (.cons (.scalar rd)
      (.cons (.scalar rs) (.cons (.scalar rp) .nil)))))
    (.cons (.scalar scratch) .nil))) =>
      ⟨dst, src, et, ev, ttl, protocol, checksum, iv, port, drop, sentinel, hit, rd, rs, rp, scratch⟩

theorem observe_restore (s : Snapshot) : observe (restore s) = s := by
  cases s
  rfl

theorem restore_observe : (store : Store roots) → restore (observe store) = store
  | .cons (.aggregate () (.cons (.aggregate _
      (.cons (.scalar _) (.cons (.scalar _) (.cons (.scalar _) .nil))))
      (.cons (.aggregate _
        (.cons (.scalar _) (.cons (.scalar _) (.cons (.scalar _) .nil)))) .nil)))
    (.cons (.aggregate () (.cons (.scalar _) (.cons (.scalar _) (.cons (.scalar _) .nil))))
    (.cons (.aggregate () (.cons (.scalar _) (.cons (.scalar _)
      (.cons (.scalar _) (.cons (.scalar _) .nil)))))
    (.cons (.scalar _) .nil))) => rfl

/-- Policy uses ordinary natural comparison and predecessor, not the
authored equality guards, modular addition, paths or command denotation. -/
def policy (s : Snapshot) : Snapshot :=
  if s.routeHit && decide (1 < s.ttl.val) then
    { s with
      dst := s.routeDst, src := s.routeSrc,
      ttl := ⟨s.ttl.val - 1, Nat.lt_of_le_of_lt (Nat.sub_le _ _) s.ttl.isLt⟩,
      port := s.routePort, drop := false }
  else { s with drop := true }

-- Permit equation matching through the dependent layout/type aliases.
-- These elaboration settings do not change the resulting kernel proof.
set_option maxRecDepth 4096 in
set_option backward.isDefEq.respectTransparency false in
theorem authored_policy (s : Snapshot) :
    observe (forward.denote (restore s)) = policy s := by
  cases s with
  | mk dst src etherType ev ttl protocol checksum iv port drop sentinel hit rd rs rp scratch =>
    dsimp [forward, Cmd.ite, Cmd.assign, Cmd.seq, Cmd.denote,
      Scalar.CmdWith.ite, Scalar.CmdWith.assign, Scalar.CmdWith.seq,
      Scalar.CmdWith.denoteWith, Scalar.denoteWith, Scalar.bitsWith, Place.read,
      FieldCommandExamples.dst, FieldCommandExamples.src, FieldCommandExamples.ttl,
      FieldCommandExamples.port, FieldCommandExamples.drop, FieldCommandExamples.routeHit,
      FieldCommandExamples.routeDst, FieldCommandExamples.routeSrc, FieldCommandExamples.routePort,
      restore, observe, Ref.get, Ref.set, Record.get, Record.set, Path.get, Path.set, policy,
      FieldCommandExamples.roots, FieldCommandExamples.headers, FieldCommandExamples.headerFields,
      FieldCommandExamples.ethernet, FieldCommandExamples.ethernetFields,
      FieldCommandExamples.ipv4, FieldCommandExamples.ipv4Fields,
      FieldCommandExamples.metadata, FieldCommandExamples.metaFields,
      FieldCommandExamples.route, FieldCommandExamples.routeFields]
    simp only [Record.get.eq_1, Record.get.eq_2, Record.set.eq_1, Record.set.eq_2,
      Path.get.eq_1, Path.get.eq_2, Path.set.eq_1, Path.set.eq_2]
    cases hit with
    | false => rfl
    | true =>
      by_cases hz : ttl.val = 0
      · simp [hz]
      · by_cases ho : ttl.val = 1
        · simp [ho]
        · have hg : 1 < ttl.val := by omega
          have arithmetic : (ttl.val + 255) % 256 = ttl.val - 1 := by
            have bound := ttl.isLt
            omega
          simp [hz, ho, hg]
          exact arithmetic

/-- Every source store, not just the fixed conformance initializer. -/
theorem source_policy (store : Store roots) :
    forward.denote store = restore (policy (observe store)) := by
  have h := congrArg restore (authored_policy (observe store))
  simpa only [restore_observe] using h

/-- Actual reference execution realizes the independent application policy
under the reviewed body theorem's concrete declaration/frame premises. -/
theorem execute_policy (store : Store roots) (initial : P4bloIR.Run)
    (hi : roots.IndexAgrees initial.index)
    (hd : modes.Agrees initial.frame.scope)
    (hf : FrameMatches store initial.frame)
    (hb : P4bloIR.ScalarStatements.BlockFrame initial.frame) :
    P4bloIR.FieldTyping.BodyTyped initial.index initial.frame.scope forward.lower ∧
    ∃ final, (P4bloIR.execute forward.lower).run initial = (.ok (), final) ∧
      FrameMatches (restore (policy (observe store))) final.frame ∧
      modes.Agrees final.frame.scope ∧
      P4bloIR.ScalarStatements.ChangesOnlyVars initial final ∧
      P4bloIR.ScalarStatements.PreservesOutside forward.targets initial final := by
  obtain ⟨typed, final, executed, hm, declarations, _, changes, outside⟩ :=
    forward.execute_correct store initial FieldCommandExamples.rootWF hi hd hf hb
  exact ⟨typed, final, executed, source_policy store ▸ hm, declarations, changes, outside⟩

end P4blo.ForwardPolicy
