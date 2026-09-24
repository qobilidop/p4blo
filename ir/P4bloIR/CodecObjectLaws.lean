import P4bloIR.Json
import Std.Data.TreeMap.Raw.Lemmas
import Std.Data.TreeMap.Raw.WF
import Init.Data.List.Impl

/-!
Internal proof plumbing for actual encoded-object lookup. These helpers preserve
last-occurrence lookup and null removal; they do not define a competing decoder.
They are shared by declaration composition proofs, not production runtime APIs.
-/
namespace P4bloIR.CodecObject
open Lean

-- Reduce actual object lookup through omitted groups independently, avoiding
-- a Cartesian split over every field's presence. This is the real TreeMap
-- lookup law, not another JSON decoder or an assumed successful callback.
def fieldLookup (key : String) (fields : Encode.Fields) : Option Json :=
  fields.findSomeRev? (fun (name, value) => if compare name key = .eq then some value else none)

theorem fieldLookup_nil (key : String) : fieldLookup key [] = none := rfl

theorem fieldLookup_append (key : String) (xs ys : Encode.Fields) :
    fieldLookup key (xs ++ ys) = (fieldLookup key ys).or (fieldLookup key xs) := by
  simp [fieldLookup, List.findSomeRev?_eq_findSome?_reverse, List.findSome?_append]

def withoutNull : Option Json → Option Json
  | none | some .null => none
  | some value => some value

theorem get_mkObj (path key : String) (fields : Encode.Fields) :
    Decode.get? path (Json.mkObj fields) key = .ok (withoutNull (fieldLookup key fields)) := by
  have lookup : (Std.TreeMap.Raw.ofList fields : Std.TreeMap.Raw String Json)[key]? =
      fieldLookup key fields := by
    rw [Std.TreeMap.Raw.ofList_eq_insertMany_empty,
      Std.TreeMap.Raw.getElem?_insertMany_list Std.TreeMap.Raw.WF.emptyc]
    simp [fieldLookup]
  simp only [Decode.get?, Json.mkObj, Std.TreeMap.Raw.get?_eq_getElem?, lookup]
  cases fieldLookup key fields with
  | none => rfl
  | some v => cases v <;> rfl

theorem lookup_str (key name value : String) :
    fieldLookup key (Encode.ofStr name value) =
      if compare name key = .eq then
        (if value.isEmpty then none else some (.str value)) else none := by
  by_cases empty : value.isEmpty = true <;>
    simp [fieldLookup, Encode.ofStr, empty]

theorem lookup_list (key name : String) (values : List Json) :
    fieldLookup key (Encode.ofList name values) =
      if compare name key = .eq then
        (if values.isEmpty then none else some (.arr values.toArray)) else none := by
  cases values <;> simp [fieldLookup, Encode.ofList]

theorem omitted_string (path value : String) :
    (match withoutNull (if value = "" then none else some (.str value)) with
     | none => Except.ok "" | some v => Decode.str path v) = .ok value := by
  by_cases empty : value = ""
  · subst value
    rfl
  · simp [empty, withoutNull, Decode.str]
    rfl

theorem omitted_array (path : String) (xs : List β) (encode : β → Json)
    (decode : String → Json → Decode.Dec α) :
    (match withoutNull (if xs = [] then none else some (.arr (xs.map encode).toArray)) with
     | none => Except.ok [] | some v => Decode.array path v decode) =
      Decode.array path (.arr (xs.map encode).toArray) decode := by
  cases xs <;> rfl

end P4bloIR.CodecObject
