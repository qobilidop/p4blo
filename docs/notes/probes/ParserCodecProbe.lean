import P4bloIR.CodecLaws

/-! Unregistered feasibility only. Actual codecs; no production coverage claim. -/
namespace ParserCodecProbe
open P4bloIR Lean

def KeySetRepresentable : KeySet → Prop
  | .exact v => CodecLaws.LiteralRepresentable v
  | .masked v m | .range v m =>
      CodecLaws.LiteralRepresentable v ∧ CodecLaws.LiteralRepresentable m
  | .dontCare => True
def CaseRepresentable (c : SelectCase) : Prop := ∀ s ∈ c.sets, KeySetRepresentable s
def TransitionRepresentable : Transition → Prop
  | .direct _ => True
  | .select keys cases => (∀ k ∈ keys, CodecLaws.ExprRepresentable k) ∧
      (∀ c ∈ cases, CaseRepresentable c)
def StateRepresentable (s : State) : Prop :=
  (∀ t ∈ s.body, CodecLaws.StmtRepresentable t) ∧ TransitionRepresentable s.transition

theorem target_roundtrip (path : String) (t : Target) :
    Target.decode path t.toJson = .ok t := by cases t <;> rfl

private theorem literal_object (v : Literal) : ∃ f, v.toJson = Json.obj f := by
  cases v <;> exact ⟨_, rfl⟩

theorem keySet_roundtrip (path : String) (k : KeySet) (h : KeySetRepresentable k) :
    KeySet.decode path k.toJson = .ok k := by
  cases k with
  | dontCare => rfl
  | exact v =>
    obtain ⟨f, obj⟩ := literal_object v
    have body : KeySet.decode path (KeySet.exact v).toJson =
        (KeySet.exact <$> Literal.decode (Decode.sub path "exact") v.toJson) := by
      simp only [KeySet.toJson, obj]
      rfl
    rw [body, CodecLaws.literal_roundtrip _ _ h]
    rfl
  | masked v m | range v m =>
    obtain ⟨vf, vo⟩ := literal_object v
    obtain ⟨mf, mo⟩ := literal_object m
    simp only [KeySet.toJson, vo, mo]
    change (do
      let a ← Literal.decode _ (Json.obj vf)
      let b ← Literal.decode _ (Json.obj mf)
      pure ((_ : Literal → Literal → KeySet) a b)) = _
    rw [← vo, ← mo, CodecLaws.literal_roundtrip _ _ h.1,
      CodecLaws.literal_roundtrip _ _ h.2]
    rfl

theorem case_roundtrip (path : String) (c : SelectCase) (h : CaseRepresentable c) :
    SelectCase.decode path c.toJson = .ok c := by
  cases c with | mk sets target =>
    have body : SelectCase.decode path (SelectCase.mk sets target).toJson = (do
        let ss ← Decode.array (Decode.sub path "sets")
          (.arr (sets.map KeySet.toJson).toArray) KeySet.decode
        let t ← Target.decode (Decode.sub path "target") target.toJson
        pure (SelectCase.mk ss t)) := by
      cases sets <;> cases target <;> rfl
    rw [body, CodecLaws.array_encoded_roundtrip _ _ _ _
      (fun s hs p => keySet_roundtrip p s (h s hs)), target_roundtrip]
    rfl

theorem transition_roundtrip (path : String) (t : Transition)
    (h : TransitionRepresentable t) : Transition.decode path t.toJson = .ok t := by
  cases t with
  | direct target =>
    have body : Transition.decode path (Transition.direct target).toJson =
        (Transition.direct <$> Target.decode (Decode.sub path "direct") target.toJson) := by
      cases target <;> rfl
    rw [body, target_roundtrip]
    rfl
  | select keys cases =>
    have body : Transition.decode path (Transition.select keys cases).toJson = (do
        let ks ← Decode.array (Decode.sub (Decode.sub path "select") "keys")
          (.arr (keys.map Expr.toJson).toArray) Expr.decode
        let cs ← Decode.array (Decode.sub (Decode.sub path "select") "cases")
          (.arr (cases.map SelectCase.toJson).toArray) SelectCase.decode
        pure (Transition.select ks cs)) := by
      cases keys <;> cases cases <;> rfl
    rw [body, CodecLaws.array_encoded_roundtrip _ _ _ _
      (fun k hk p => CodecLaws.expr_roundtrip p k (h.1 k hk)),
      CodecLaws.array_encoded_roundtrip _ _ _ _ (fun c hc p => case_roundtrip p c (h.2 c hc))]
    rfl

theorem state_roundtrip (path : String) (s : State) (h : StateRepresentable s) :
    State.decode path s.toJson = .ok s := by
  cases s with | mk name statements transition =>
    have obj : ∃ f, transition.toJson = Json.obj f := by
      cases transition <;> exact ⟨_, rfl⟩
    obtain ⟨f, obj⟩ := obj
    have body : State.decode path (State.mk name statements transition).toJson = (do
        let ts ← Decode.array (Decode.sub path "body")
          (.arr (statements.map Stmt.toJson).toArray) Stmt.decode
        let tr ← Transition.decode (Decode.sub path "transition") transition.toJson
        pure (State.mk name ts tr)) := by
      by_cases empty : name.isEmpty = true
      · have zero : name = "" := String.isEmpty_iff.mp empty
        subst name
        cases statements <;> simp only [State.toJson, obj] <;> rfl
      · cases statements <;> simp only [State.toJson, Encode.ofStr, empty, obj] <;> rfl
    rw [body, CodecLaws.array_encoded_roundtrip _ _ _ _
      (fun t ht p => CodecLaws.stmt_roundtrip p t (h.1 t ht)),
      transition_roundtrip _ _ h.2]
    rfl

def unusual : State := ⟨"", [.conditional (.literal (.boolean false))
  [.push (.var "missing") (2 ^ 32 - 1)] [.emit (.var "")]],
  .select [.lookahead (.stack "Missing" 0), .literal (.bits 0 (10 ^ 100))]
    [⟨[.exact (.boolean false), .masked (.bits 0 99) (.error ""),
       .range (.bits 0 77) (.bits 0 2), .dontCare], .state ""⟩,
     ⟨[], .accept⟩, ⟨[.dontCare], .reject⟩]⟩

theorem unusual_roundtrip (path : String) : State.decode path unusual.toJson = .ok unusual := by
  apply state_roundtrip
  simp [unusual, StateRepresentable, TransitionRepresentable, CaseRepresentable,
    KeySetRepresentable, CodecLaws.StmtRepresentable, CodecLaws.ExprRepresentable,
    CodecLaws.LValueRepresentable, CodecLaws.TypeRepresentable,
    CodecLaws.LiteralRepresentable, CodecLaws.UInt32]

example : ¬ KeySetRepresentable (.range (.bits 0 0) (.bits (2 ^ 32) 1)) := by
  simp [KeySetRepresentable, CodecLaws.LiteralRepresentable, CodecLaws.UInt32]
example : Target.decode "p" (Json.mkObj [("state", .str "")]) = .ok (.state "") := by rfl
example : Target.decode "p" (Json.mkObj [("accept", .null)]) = .error "p: no kind set" := by rfl
example : Transition.decode "p" (Json.mkObj [("select", Json.mkObj [])]) =
    .ok (.select [] []) := by rfl
example : Transition.decode "p" (Json.mkObj [("direct", Json.mkObj [])]) =
    .error "p.direct: no kind set" := by rfl
example : SelectCase.decode "p" (Json.mkObj []) = .error "p.target: no kind set" := by rfl
example : State.decode "p" (Json.mkObj []) = .error "p.transition: no kind set" := by rfl
-- Other remaining assembly defaults, not universal assembly proofs.
example : Action.decode "p" (Json.mkObj []) = .ok ⟨"", [], []⟩ := by rfl
example : Block.decode "p" (Json.mkObj []) = .error "p.kind: unspecified" := by rfl
example : Export.decode "p" (Json.mkObj []) = .ok ⟨"", ""⟩ := by rfl
example : Program.decode "p" (Json.mkObj []) =
    .ok ⟨"", [], [], [], [], [], [], [], "", "", []⟩ := by rfl
example : TableEntries.decode "p" (Json.mkObj []) = .ok ⟨"", "", [], none⟩ := by rfl
example : Entries.decode "p" (Json.mkObj []) = .ok ⟨[]⟩ := by rfl

#print axioms target_roundtrip
#print axioms keySet_roundtrip
#print axioms case_roundtrip
#print axioms transition_roundtrip
#print axioms state_roundtrip
#print axioms unusual_roundtrip
end ParserCodecProbe
