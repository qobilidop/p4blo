import P4bloIRTest.BlockCodec

open Lean P4bloIR

namespace ProgramCodecTests

def exportValue (e : Export) : Json := Json.mkObj
  [("role", .str e.role), ("block", .str e.block)]
def programValue (p : Program) : Json := Json.mkObj
  [("name", .str p.name), ("errors", toJson p.errors),
   ("header_types", toJson (p.headerTypes.map DeclarationCodecTests.headerValue)),
   ("struct_types", toJson (p.structTypes.map DeclarationCodecTests.structValue)),
   ("enum_types", toJson (p.enumTypes.map DeclarationCodecTests.enumValue)),
   ("extern_types", toJson (p.externTypes.map DeclarationCodecTests.externTypeValue)),
   ("extern_instances", toJson (p.externInstances.map DeclarationCodecTests.instanceValue)),
   ("blocks", toJson (p.blocks.map BlockCodecTests.blockValue)),
   ("headers", .str p.headers), ("metadata", .str p.metadata),
   ("exports", toJson (p.exports.map exportValue))]

def reply (request : Json) : Except String Json := do
  let kind ← (← request.getObjVal? "kind").getStr?
  let wire ← request.getObjVal? "wire"
  match kind with
  | "export" =>
    let e ← Export.decode "leaf" wire
    pure (Json.mkObj [("value", exportValue e), ("encoded", e.toJson)])
  | "program" =>
    let p ← Program.decode "leaf" wire
    pure (Json.mkObj [("value", programValue p), ("encoded", p.toJson)])
  | _ => BlockCodecTests.reply request

private def empty : Json := Json.mkObj []
private def emptyProgram : Program := ⟨"", [], [], [], [], [], [], [], "", "", []⟩
private def mixedWire : String :=
  "{\"name\":\"program\",\"errors\":[\"last\",\"\",\"first\"],\"header_types\":[{\"name\":\"H\"},{},{\"name\":\"H2\"}],\"struct_types\":[{\"name\":\"S\"},{\"name\":\"S2\"},{}],\"enum_types\":[{\"name\":\"E\",\"members\":[\"z\",\"\",\"a\"]}],\"extern_types\":[{\"name\":\"X\"}],\"extern_instances\":[{\"name\":\"instance\",\"extern_type\":\"Missing\"}],\"blocks\":[{\"name\":\"P\",\"kind\":\"BLOCK_KIND_PARSER\"},{\"name\":\"C\",\"kind\":\"BLOCK_KIND_CONTROL\"},{\"name\":\"D\",\"kind\":\"BLOCK_KIND_DEPARSER\"}],\"headers\":\"HdrOnly\",\"metadata\":\"MetaOnly\",\"exports\":[{\"role\":\"role-left\",\"block\":\"block-right\"},{},{\"role\":\"same\",\"block\":\"Missing\"}]}"
private def mixed : Program := ⟨"program", ["last", "", "first"],
  [⟨"H", []⟩, ⟨"", []⟩, ⟨"H2", []⟩], [⟨"S", []⟩, ⟨"S2", []⟩, ⟨"", []⟩],
  [⟨"E", ["z", "", "a"]⟩], [⟨"X", [], []⟩], [⟨"instance", "Missing", []⟩],
  [⟨"P", .parser, [], [], [], [], [], "", []⟩,
   ⟨"C", .control, [], [], [], [], [], "", []⟩,
   ⟨"D", .deparser, [], [], [], [], [], "", []⟩], "HdrOnly", "MetaOnly",
  [⟨"role-left", "block-right"⟩, ⟨"", ""⟩, ⟨"same", "Missing"⟩]⟩

def tests : T Unit := do
  checkOk "program complete independent constructor" (Program.fromJsonString mixedWire) (· == mixed)
  checkOk "program empty defaults" (Program.decode "" empty) (· == emptyProgram)
  checkOk "export empty defaults" (Export.decode "" empty) (· == ⟨"", ""⟩)
  let asymmetric := Json.mkObj [("role", .str "left"), ("block", .str "right")]
  checkOk "export asymmetric fields" (Export.decode "" asymmetric) (· == ⟨"left", "right"⟩)
  check "export independent observer" (exportValue ⟨"left", "right"⟩ == asymmetric)
  check "program independent nominal slots"
    (((programValue mixed).getObjVal? "headers").toOption == some (.str "HdrOnly") &&
     ((programValue mixed).getObjVal? "metadata").toOption == some (.str "MetaOnly"))
  check "export error order at empty path"
    (Export.decode "" (Json.mkObj [("role", .bool false), ("block", .bool false)]) matches
      .error "role: expected a string")
  let order := ["name", "errors", "header_types", "struct_types", "enum_types",
    "extern_types", "extern_instances", "blocks", "headers", "metadata", "exports"]
  for (first, second) in order.zip order.tail do
    let what := if ["name", "headers", "metadata"].contains first then "a string" else "an array"
    check "program adjacent first error"
      (match Program.decode "" (Json.mkObj [(first, .bool false), (second, .bool false)]) with
       | .error e => e == first ++ ": expected " ++ what
       | .ok _ => false)
  check "program later nested bound"
    (Program.fromJsonString "{\"header_types\":[{}, {\"fields\":[{\"type\":{\"bits\":4294967296}}]}]}" matches
      .error "header_types[1].fields[0].type.bits: 4294967296 does not fit in uint32")

end ProgramCodecTests
