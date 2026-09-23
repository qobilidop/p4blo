import P4bloIR.CodecLaws
import Init.Data.Array.MapIdx
import Init.Data.Array.Attach

/- Isolated, unregistered planning probe. No Stmt decoder is replaced. -/
namespace StmtCodecProbe
open Lean P4bloIR P4bloIR.Decode

theorem mapIdxM_map (f : Nat → β → Except String γ) (g : α → β) (xs : List α) :
    (xs.map g).mapIdxM f = xs.mapIdxM (fun i x => f i (g x)) := by
  have go (ys : List α) (acc : Array γ) :
      List.mapIdxM.go f (ys.map g) acc =
        List.mapIdxM.go (fun i x => f i (g x)) ys acc := by
    induction ys generalizing acc with
    | nil => rfl
    | cons head tail ih => simp only [List.map_cons, List.mapIdxM.go, ih]
  exact go xs #[]

theorem array_attach_erasure (xs : Array α) (f : Nat → α → Except String β) :
    Array.toList <$> xs.attach.mapIdxM (fun i x => f i x.val) =
      Array.toList <$> xs.mapIdxM f := by
  rw [Array.toList_mapIdxM, Array.toList_mapIdxM]
  rw [← mapIdxM_map f Subtype.val xs.attach.toList]
  rw [← Array.toList_map, Array.attach_map_subtype_val]

theorem array_mem_lt (xs : Array Json) (child : Json) (h : child ∈ xs) :
    sizeOf child < sizeOf (Json.arr xs) := by
  have bound := Array.sizeOf_lt_of_mem h
  simp only [Json.arr.sizeOf_spec]
  omega

def arrayBounded (outer : Json) (path : String) (j : Json)
    (smaller : sizeOf j < sizeOf outer)
    (dec : String → (child : Json) → sizeOf child < sizeOf outer → Dec α) : Dec (List α) :=
  match j with
  | .arr xs => Array.toList <$> xs.attach.mapIdxM fun i x =>
      dec (at_ path i) x.val (Nat.lt_trans (array_mem_lt xs x.val x.property) smaller)
  | _ => fail path "expected an array"

theorem arrayBounded_erasure (outer : Json) (path : String) (j : Json)
    (smaller : sizeOf j < sizeOf outer) (dec : String → Json → Dec α) :
    arrayBounded outer path j smaller (fun p v _ => dec p v) = array path j dec := by
  cases j <;> try rfl
  exact array_attach_erasure _ _

def listFieldBounded (outer : Json) (path : String) (j : Json)
    (smaller : sizeOf j < sizeOf outer) (key : String)
    (dec : String → (child : Json) → sizeOf child < sizeOf outer → Dec α) : Dec (List α) :=
  match h : get? path j key with
  | .error error => .error error
  | .ok none => .ok []
  | .ok (some v) => arrayBounded outer (sub path key) v
      (Nat.lt_trans (get_some_lt path j key v h) smaller) dec

theorem listFieldBounded_erasure (outer : Json) (path : String) (j : Json)
    (smaller : sizeOf j < sizeOf outer) (key : String) (dec : String → Json → Dec α) :
    listFieldBounded outer path j smaller key (fun p v _ => dec p v) =
      listField path j key dec := by
  unfold listFieldBounded listField
  split <;> simp_all [arrayBounded_erasure, bind, Except.bind, pure, Except.pure]

theorem array_encoded_roundtrip (path : String) (xs : List α)
    (encode : α → Json) (decode : String → Json → Dec α)
    (h : ∀ x ∈ xs, ∀ p, decode p (encode x) = .ok x) :
    array path (.arr (xs.map encode).toArray) decode = .ok xs := by
  have go (ys : List α) (acc : Array α)
      (hy : ∀ x ∈ ys, ∀ p, decode p (encode x) = .ok x) :
      List.mapIdxM.go (fun i x => decode (at_ path i) x) (ys.map encode) acc =
        .ok (acc.toList ++ ys) := by
    induction ys generalizing acc with
    | nil => simp [List.mapIdxM.go, pure, Except.pure]
    | cons head tail ih =>
      simp only [List.map_cons, List.mapIdxM.go, hy head (by simp), bind, Except.bind]
      simpa using ih (acc.push head) (fun x hx => hy x (by simp [hx]))
  simp only [array]
  rw [Array.toList_mapIdxM]
  simpa [List.mapIdxM] using go xs #[] h

private def condition : Json := Json.mkObj [("var", .str "condition")]
private def selected (fields : List (String × Json)) : Json :=
  Json.mkObj [("conditional", Json.mkObj fields)]

example : listFieldBounded (α := String) (selected [("condition", condition)]) "payload"
    (Json.mkObj []) (by decide) "then" (fun p _ _ => .error p) = .ok [] := rfl

#eval Stmt.decode "leaf" (selected [("condition", condition),
  ("then", .arr #[Json.mkObj [], .null]), ("otherwise", .arr #[Json.mkObj []])])
#eval Stmt.decode "leaf" (selected [("condition", condition),
  ("then", .arr #[Json.mkObj [("emit", Json.mkObj [("value", condition)])], Json.mkObj []]),
  ("otherwise", .bool false)])
#eval Stmt.decode "leaf" (selected [("condition", Json.mkObj []),
  ("then", .bool false), ("otherwise", .bool false)])
#eval Stmt.decode "leaf" (selected [("condition", condition), ("then", .null), ("otherwise", .null)])

#print axioms mapIdxM_map
#print axioms array_attach_erasure
#print axioms array_mem_lt
#print axioms arrayBounded_erasure
#print axioms listFieldBounded_erasure
#print axioms array_encoded_roundtrip
#check Stmt.rec
end StmtCodecProbe
