import Lean.Data.Json

/-!
Structural bounds for actual Lean JSON children. No map well-formedness or
cached-size invariant is assumed. Keep pinned TreeMap representation details
behind these lemmas; decoder recursion should depend only on `object_lookup_lt`.
-/
namespace P4bloIR.JsonBounds

open Lean

private theorem lookup_lt [Ord α] [SizeOf α] [SizeOf β]
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

theorem empty_object_le (fields : Std.TreeMap.Raw String Json) :
    sizeOf (Json.mkObj []) ≤ sizeOf (Json.obj fields) := by
  cases fields with | mk fields =>
    cases fields with | mk tree =>
      have empty : sizeOf (Json.mkObj []) = 4 := by decide
      rw [empty]
      cases tree <;> simp <;> omega

/-- Genuine array membership supplies a strict structural child bound. -/
theorem array_mem_lt (xs : Array Json) (child : Json) (h : child ∈ xs) :
    sizeOf child < sizeOf (Json.arr xs) := by
  have bound := Array.sizeOf_lt_of_mem h
  simp only [Json.arr.sizeOf_spec]
  omega

end P4bloIR.JsonBounds
