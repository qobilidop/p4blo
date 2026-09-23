import P4bloIR.FieldLaws
import P4bloIR.ScalarStatements

/-!
# Scoped field typing and root permissions

Declarative typing for variable/member and header-validity reads, writable paths, scalar
expressions and assignment/conditional bodies. Actual block declarations,
root permissions and exact nominal index declarations are explicit.
This is not a total aggregate checker or whole-program validity.
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
  | isValid {header name fields} : Path index scope header (.header name) →
      FieldLaws.Declared index .header name fields → Typed index scope (.isValid header) .boolean
  | binary {left right a b c} (op : BinaryOp) :
      Typed index scope left a → Typed index scope right b →
      ScalarTyping.binaryType op a b = some c → Typed index scope (.binary op left right) c
  | mux {condition yes no t} : Typed index scope condition .boolean →
      Typed index scope yes t → Typed index scope no t → Typed index scope (.mux condition yes no) t

/-- Writable variable/member paths. Permission belongs to the actual root
declaration and cannot be gained by descending through a member. Runtime
storage and value agreement alone do not establish this relation. -/
inductive WritablePath (index : Index) (scope : BlockScope) : LValue → Ty → Prop
  | var (name : String) (decl : VarDecl) : name ≠ "" →
      scope.var? name = some decl → decl.name = name →
      ScalarStatements.writable decl = true → WritablePath index scope (.var name) decl.type
  | member {base container fields} (field : Field) :
      WritablePath index scope base container → FieldsOf index container fields → field ∈ fields →
      WritablePath index scope (.member base field.name) field.type

mutual
/-- Scalar-leaf assignments and conditionals over existing IR statements.
This is not a total checker, an aggregate-assignment rule or global validity. -/
inductive StatementTyped (index : Index) (scope : BlockScope) : Stmt → Prop
  | assign {target expression t} :
      WritablePath index scope target (ScalarStatements.irType t) →
      Typed index scope expression t → StatementTyped index scope (.assign target expression)
  | conditional {condition yes no} : Typed index scope condition .boolean →
      BodyTyped index scope yes → BodyTyped index scope no →
      StatementTyped index scope (.conditional condition yes no)

inductive BodyTyped (index : Index) (scope : BlockScope) : List Stmt → Prop
  | nil : BodyTyped index scope []
  | cons : StatementTyped index scope statement → BodyTyped index scope rest →
      BodyTyped index scope (statement :: rest)
end

end P4bloIR.FieldTyping
