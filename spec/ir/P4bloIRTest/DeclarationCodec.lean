import P4bloIRTest.CodecLaws
import P4bloIR.DeclarationCodecLaws

open Lean P4bloIR

namespace DeclarationCodecTests

def wireFields : List Field :=
  [⟨"", .bits 0⟩, ⟨"same", .struct "Unresolved"⟩, ⟨"same", .header ""⟩,
   ⟨"", .stack "Missing" (2 ^ 32 - 1)⟩, ⟨"", .enumType ""⟩, ⟨"", .error⟩, ⟨"", .boolean⟩]
def wireHeader : HeaderType := ⟨"", wireFields⟩
def wireStruct : StructType := ⟨"", wireFields.reverse⟩
def wireEnum : EnumType := ⟨"", ["", "same", "same"]⟩
def wireField : Field := ⟨"", .bits (2 ^ 32 - 1)⟩
def wireVar : Var := ⟨"", .stack "" 0⟩
def wireParam : Param := ⟨"", .struct "Missing", .none⟩
def wireMethod : Method := ⟨"", [wireParam, ⟨"", .bits 0, .inout⟩], some (.bits 0)⟩
def wireExtern : ExternType := ⟨"",
  [⟨"duplicate", .bits 0, .none⟩, ⟨"duplicate", .stack "missing" 0, .inout⟩],
  [⟨"", [⟨"", .header "missing", .out⟩], some (.bits (2 ^ 32 - 1))⟩,
   ⟨"", [⟨"", .boolean, .«in»⟩], none⟩, wireMethod]⟩
def wireInstance : ExternInstance := ⟨"object", "Unresolved",
  [.bits 0 (10 ^ 100 + 7), .boolean false, .enumMember "" "", .error "",
   .bits (2 ^ 32 - 1) 0]⟩

/-- Kernel-checked nonvacuity of every selected law, not global declaration validity. -/
theorem declarations_roundtrip (path : String) :
    Field.decode path wireField.toJson = .ok wireField ∧
    HeaderType.decode path wireHeader.toJson = .ok wireHeader ∧
    StructType.decode path wireStruct.toJson = .ok wireStruct ∧
    EnumType.decode path wireEnum.toJson = .ok wireEnum ∧
    Var.decode path wireVar.toJson = .ok wireVar ∧
    Param.decode path wireParam.toJson = .ok wireParam ∧
    Method.decode path wireMethod.toJson = .ok wireMethod ∧
    ExternType.decode path wireExtern.toJson = .ok wireExtern ∧
    ExternInstance.decode path wireInstance.toJson = .ok wireInstance := by
  refine ⟨CodecLaws.field_roundtrip _ _ ?_, CodecLaws.headerType_roundtrip _ _ ?_,
    CodecLaws.structType_roundtrip _ _ ?_, CodecLaws.enumType_roundtrip _ _,
    CodecLaws.var_roundtrip _ _ ?_, CodecLaws.param_roundtrip _ _ ?_,
    CodecLaws.method_roundtrip _ _ ?_, CodecLaws.externType_roundtrip _ _ ?_,
    CodecLaws.externInstance_roundtrip _ _ ?_⟩
  all_goals simp [wireField, wireHeader, wireStruct, wireFields, wireVar, wireParam,
    wireMethod, wireExtern, wireInstance, CodecLaws.FieldRepresentable,
    CodecLaws.HeaderTypeRepresentable, CodecLaws.StructTypeRepresentable,
    CodecLaws.VarRepresentable, CodecLaws.ParamRepresentable,
    CodecLaws.MethodRepresentable, CodecLaws.ExternTypeRepresentable,
    CodecLaws.ExternInstanceRepresentable, CodecLaws.TypeRepresentable,
    CodecLaws.LiteralRepresentable, CodecLaws.UInt32]

example : ¬ CodecLaws.FieldRepresentable ⟨"", .bits (2 ^ 32)⟩ := by
  simp [CodecLaws.FieldRepresentable, CodecLaws.TypeRepresentable, CodecLaws.UInt32]
example : ¬ CodecLaws.HeaderTypeRepresentable ⟨"", [⟨"", .stack "" (2 ^ 32)⟩]⟩ := by
  simp [CodecLaws.HeaderTypeRepresentable, CodecLaws.FieldRepresentable,
    CodecLaws.TypeRepresentable, CodecLaws.UInt32]
example : ¬ CodecLaws.StructTypeRepresentable ⟨"", [⟨"", .bits (2 ^ 32)⟩]⟩ := by
  simp [CodecLaws.StructTypeRepresentable, CodecLaws.FieldRepresentable,
    CodecLaws.TypeRepresentable, CodecLaws.UInt32]
example : ¬ CodecLaws.VarRepresentable ⟨"", .bits (2 ^ 32)⟩ := by
  simp [CodecLaws.VarRepresentable, CodecLaws.TypeRepresentable, CodecLaws.UInt32]
example : ¬ CodecLaws.ParamRepresentable ⟨"", .bits (2 ^ 32), .none⟩ := by
  simp [CodecLaws.ParamRepresentable, CodecLaws.TypeRepresentable, CodecLaws.UInt32]
example : ¬ CodecLaws.MethodRepresentable ⟨"", [], some (.bits (2 ^ 32))⟩ := by
  simp [CodecLaws.MethodRepresentable, CodecLaws.TypeRepresentable, CodecLaws.UInt32]
example : ¬ CodecLaws.ExternTypeRepresentable
    ⟨"", [⟨"", .bits (2 ^ 32), .out⟩], []⟩ := by
  simp [CodecLaws.ExternTypeRepresentable, CodecLaws.ParamRepresentable,
    CodecLaws.TypeRepresentable, CodecLaws.UInt32]
example : ¬ CodecLaws.ExternTypeRepresentable
    ⟨"", [], [⟨"", [], some (.stack "" (2 ^ 32))⟩]⟩ := by
  simp [CodecLaws.ExternTypeRepresentable, CodecLaws.MethodRepresentable,
    CodecLaws.TypeRepresentable, CodecLaws.UInt32]
example : ¬ CodecLaws.ExternInstanceRepresentable ⟨"", "", [.bits (2 ^ 32) 0]⟩ := by
  simp [CodecLaws.ExternInstanceRepresentable, CodecLaws.LiteralRepresentable, CodecLaws.UInt32]

/-- Independent of both Direction.names and protoName. -/
def directionValue : Direction → String
  | .none => "DIRECTION_NONE"
  | .«in» => "DIRECTION_IN"
  | .out => "DIRECTION_OUT"
  | .inout => "DIRECTION_INOUT"

def fieldValue (v : Field) : Json := Json.mkObj
  [("name", .str v.name), ("type", CodecLawTests.typeValue v.type)]
def headerValue (v : HeaderType) : Json := Json.mkObj
  [("name", .str v.name), ("fields", toJson (v.fields.map fieldValue))]
def structValue (v : StructType) : Json := Json.mkObj
  [("name", .str v.name), ("fields", toJson (v.fields.map fieldValue))]
def enumValue (v : EnumType) : Json := Json.mkObj
  [("name", .str v.name), ("members", toJson v.members)]
def varValue (v : Var) : Json := Json.mkObj
  [("name", .str v.name), ("type", CodecLawTests.typeValue v.type)]
def paramValue (v : Param) : Json := Json.mkObj
  [("name", .str v.name), ("type", CodecLawTests.typeValue v.type),
   ("direction", .str (directionValue v.direction))]
def methodValue (v : Method) : Json := Json.mkObj
  [("name", .str v.name), ("params", toJson (v.params.map paramValue)),
   ("returns", v.returns.map CodecLawTests.typeValue |>.getD .null)]
def externTypeValue (v : ExternType) : Json := Json.mkObj
  [("name", .str v.name), ("constructor_params", toJson (v.constructorParams.map paramValue)),
   ("methods", toJson (v.methods.map methodValue))]
def instanceValue (v : ExternInstance) : Json := Json.mkObj
  [("name", .str v.name), ("extern_type", .str v.externType),
   ("args", toJson (v.args.map CodecLawTests.literalValue))]

/-- Test-only dispatch to actual declaration codecs, without validation. -/
def reply (request : Json) : Except String Json := do
  let kind ← (← request.getObjVal? "kind").getStr?
  let wire ← request.getObjVal? "wire"
  let observe := fun {α : Type} (dec : String → Json → Except String α)
      (value encoded : α → Json) => do
    let v ← dec "leaf" wire
    pure (Json.mkObj [("value", value v), ("encoded", encoded v)])
  match kind with
  | "field" => observe Field.decode fieldValue Field.toJson
  | "header_type" => observe HeaderType.decode headerValue HeaderType.toJson
  | "struct_type" => observe StructType.decode structValue StructType.toJson
  | "enum_type" => observe EnumType.decode enumValue EnumType.toJson
  | "var" => observe Var.decode varValue Var.toJson
  | "param" => observe Param.decode paramValue Param.toJson
  | "method" => observe Method.decode methodValue Method.toJson
  | "extern_type" => observe ExternType.decode externTypeValue ExternType.toJson
  | "extern_instance" => observe ExternInstance.decode instanceValue ExternInstance.toJson
  | _ => CodecLawTests.reply request

def tests : T Unit := do
  -- Literal wire anchors remain independent even if Python fixtures are remapped.
  for (wire, direction) in [("DIRECTION_NONE", Direction.none), ("DIRECTION_IN", .«in»),
      ("DIRECTION_OUT", .out), ("DIRECTION_INOUT", .inout)] do
    checkOk s!"declaration literal direction {wire}"
      (Param.decode "test" (Json.mkObj [("type", Json.mkObj [("bits", toJson (0 : Nat))]),
        ("direction", .str wire)])) (· == { name := "", type := .bits 0, direction })
    check s!"declaration direct direction observer {wire}" (directionValue direction == wire)
  checkOk "declaration aggregate header fields retain exact order"
    (HeaderType.decode "test" (Json.mkObj [("fields", toJson
      [Json.mkObj [("name", .str "z"), ("type", Json.mkObj [("struct", .str "Missing")])],
       Json.mkObj [("name", .str ""), ("type", Json.mkObj [("bits", toJson (0 : Nat))])],
       Json.mkObj [("name", .str "z"), ("type", Json.mkObj [("boolean", Json.mkObj [])])]])]))
    (· == { name := "", fields := [⟨"z", .struct "Missing"⟩, ⟨"", .bits 0⟩, ⟨"z", .boolean⟩] })
  checkOk "declaration instance names and unequal arguments"
    (ExternInstance.decode "test" (Json.mkObj [("name", .str "instance"),
      ("extern_type", .str "Unresolved"), ("args", toJson
        [Json.mkObj [("boolean", .bool false)], Json.mkObj [("error", .str "E")],
         Json.mkObj [("bits", Json.mkObj [("value", .str "999")])]])]))
    (· == { name := "instance", externType := "Unresolved", args := [.boolean false, .error "E", .bits 0 999] })
  check "declaration type error precedes direction error"
    (match Param.decode "test" (Json.mkObj [("direction", .str "UNKNOWN")]) with
     | .error e => e == "test.type: no kind set"
     | .ok _ => false)
  check "declaration later nested error retains exact index"
    (match ExternType.decode "test" (Json.mkObj [("methods", toJson [Json.mkObj [],
      Json.mkObj [("params", toJson [Json.mkObj []])]])]) with
     | .error e => e == "test.methods[1].params[0].type: no kind set"
     | .ok _ => false)
  checkOk "declaration null return is absent"
    (Method.decode "test" (Json.mkObj [("returns", .null)]))
    (· == { name := "", params := [], returns := none })
  check "declaration present empty return is not absent"
    (match Method.decode "test" (Json.mkObj [("returns", Json.mkObj [])]) with
     | .error e => e == "test.returns: no kind set"
     | .ok _ => false)

end DeclarationCodecTests
