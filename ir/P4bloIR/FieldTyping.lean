import P4bloIR.FieldLaws
import P4bloIR.ScalarStatements

/-!
# Scoped field-read typing

Declarative typing for variable/member paths and scalar expressions using
them. Actual block declarations and exact nominal index declarations are
explicit. This is not a total aggregate checker or whole-program validity.
No action scope, stack indexing, aggregate operators or packet operations
are admitted by these rules.
-/

namespace P4bloIR.FieldTyping

inductive FieldsOf (index : Index) : Ty → List Field → Prop
  | header : FieldLaws.Declared index .header name fields → FieldsOf index (.header name) fields
  | struct : FieldLaws.Declared index .struct name fields → FieldsOf index (.struct name) fields

inductive Path (index : Index) (scope : BlockScope) : Expr → Ty → Prop
  | var (name : String) (decl : VarDecl) : name ≠ "" →
      scope.var? name = some decl → decl.name = name → Path index scope (.var name) decl.type
  | member {base container fields} (field : Field) :
      Path index scope base container → FieldsOf index container fields → field ∈ fields →
      Path index scope (.member base field.name) field.type

open ScalarTyping (ScalarTy)

inductive Typed (index : Index) (scope : BlockScope) : Expr → ScalarTy → Prop
  | bits (width value : Nat) : 0 < width → value < 2 ^ width →
      Typed index scope (.literal (.bits width value)) (.bits width)
  | boolean (value : Bool) : Typed index scope (.literal (.boolean value)) .boolean
  | read {e t} : Path index scope e (ScalarStatements.irType t) → t.Valid → Typed index scope e t
  | binary {left right a b c} (op : BinaryOp) :
      Typed index scope left a → Typed index scope right b →
      ScalarTyping.binaryType op a b = some c → Typed index scope (.binary op left right) c
  | mux {condition yes no t} : Typed index scope condition .boolean →
      Typed index scope yes t → Typed index scope no t → Typed index scope (.mux condition yes no) t

end P4bloIR.FieldTyping
