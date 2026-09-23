import P4bloIR.Json

/- Isolated feasibility probes, not a second codec or a package target. -/
namespace CodecRecursionProbe

open Lean

theorem lookup_lt [Ord α] [SizeOf α] [SizeOf β]
    (t : Std.DTreeMap.Internal.Impl α (fun _ => β)) (k : α) (v : β)
    (h : Std.DTreeMap.Internal.Impl.Const.get? t k = some v) :
    sizeOf v < sizeOf t := by
  induction t with
  | leaf => simp [Std.DTreeMap.Internal.Impl.Const.get?] at h
  | inner n key value left right ihl ihr =>
    simp only [Std.DTreeMap.Internal.Impl.Const.get?] at h
    split at h
    · have := ihl h
      simp_all only [Std.DTreeMap.Internal.Impl.inner.sizeOf_spec]
      omega
    · have := ihr h
      simp_all only [Std.DTreeMap.Internal.Impl.inner.sizeOf_spec]
      omega
    · cases h
      simp only [Std.DTreeMap.Internal.Impl.inner.sizeOf_spec]
      omega

theorem object_lookup_lt (fields : Std.TreeMap.Raw String Json) (key : String)
    (v : Json) (h : fields.get? key = some v) :
    sizeOf v < sizeOf (Json.obj fields) := by
  cases fields with | mk fields =>
    cases fields with | mk tree =>
      have bound := lookup_lt tree key v h
      simp only [Json.obj.sizeOf_spec, Std.TreeMap.Raw.mk.sizeOf_spec,
        Std.DTreeMap.Raw.mk.sizeOf_spec]
      omega

theorem array_get_lt (xs : Array Json) (i : Nat) (h : i < xs.size) :
    sizeOf xs[i] < sizeOf (Json.arr xs) := by
  have := Array.sizeOf_get xs i h
  simp only [Json.arr.sizeOf_spec]
  omega

theorem empty_object_le (fields : Std.TreeMap.Raw String Json) :
    sizeOf (Json.mkObj []) ≤ sizeOf (Json.obj fields) := by
  cases fields with | mk fields =>
    cases fields with | mk tree =>
      have empty : sizeOf (Json.mkObj []) = 4 := by decide
      rw [empty]
      cases tree <;> simp <;> omega

theorem get_some_lt (path : String) (j : Json) (key : String) (v : Json)
    (h : P4bloIR.Decode.get? path j key = .ok (some v)) :
    sizeOf v < sizeOf j := by
  cases j with
  | obj fields =>
    cases found : fields.get? key with
    | none => simp [P4bloIR.Decode.get?, found, pure, Except.pure] at h
    | some value =>
      cases value <;> simp [P4bloIR.Decode.get?, found, pure, Except.pure] at h
      all_goals subst v; exact object_lookup_lt fields key _ found
  | _ => cases h

theorem message_target_le (path : String) (j : Json) (key : String)
    (value : Option Json) (h : P4bloIR.Decode.get? path j key = .ok value) :
    sizeOf (value.getD (Json.mkObj [])) ≤ sizeOf j := by
  cases value with
  | some v => exact Nat.le_of_lt (get_some_lt path j key v h)
  | none =>
    cases j with
    | obj fields => exact empty_object_le fields
    | _ => cases h

/-- A candidate proof-carrying adapter for the actual `msgField`, not a codec.
It threads a bound to callbacks without altering missing/null semantics. -/
def boundedMsgField (outer : Json) (path : String) (j : Json)
    (smaller : sizeOf j < sizeOf outer) (key : String)
    (dec : String → (child : Json) → sizeOf child < sizeOf outer →
      P4bloIR.Decode.Dec α) : P4bloIR.Decode.Dec α :=
  match h : P4bloIR.Decode.get? path j key with
  | .error error => .error error
  | .ok value =>
    dec (P4bloIR.Decode.sub path key) (value.getD (Json.mkObj []))
      (Nat.lt_of_le_of_lt (message_target_le path j key value h) smaller)

theorem boundedMsgField_erasure (outer : Json) (path : String) (j : Json)
    (smaller : sizeOf j < sizeOf outer) (key : String)
    (dec : String → Json → P4bloIR.Decode.Dec α) :
    boundedMsgField outer path j smaller key (fun p v _ => dec p v) =
      P4bloIR.Decode.msgField path j key dec := by
  unfold boundedMsgField P4bloIR.Decode.msgField
  split <;> simp_all [bind, Except.bind] <;> rfl

/-- Array callback shape with genuine membership, unlike `mapFinIdxM`'s
unrelated value argument. Its erasure theorem is a production prerequisite. -/
def boundedArray (path : String) (j : Json)
    (dec : String → (child : Json) → sizeOf child < sizeOf j →
      P4bloIR.Decode.Dec α) : P4bloIR.Decode.Dec (List α) :=
  match j with
  | .arr xs => (·.toList) <$> xs.attach.mapIdxM fun i x =>
      dec (P4bloIR.Decode.at_ path i) x.val (by
        have bound := Array.sizeOf_lt_of_mem x.property
        simp only [Json.arr.sizeOf_spec]
        omega)
  | _ => P4bloIR.Decode.fail path "expected an array"

example : boundedArray (α := String) "items" (Json.arr #[Json.str "a", Json.str "b"])
    (fun p _ _ => .error p) = .error "items[0]" := rfl

example : boundedArray "items" (Json.arr #[Json.str "a", Json.str "b"])
    (fun p _ _ => .ok p) = .ok ["items[0]", "items[1]"] := rfl

example : ¬ sizeOf (Json.mkObj []) < sizeOf (Json.mkObj []) := Nat.lt_irrefl _

#print axioms lookup_lt
#print axioms object_lookup_lt
#print axioms array_get_lt
#print axioms empty_object_le
#print axioms get_some_lt
#print axioms message_target_le
#print axioms boundedMsgField_erasure
end CodecRecursionProbe
