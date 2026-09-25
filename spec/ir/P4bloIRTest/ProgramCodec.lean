import P4bloIRTest.BlockCodec

open Lean P4bloIR

namespace ProgramCodecTests

def programValue (p : BlockLibrary) : Json := Json.mkObj
  [("name", .str p.name), ("errors", toJson p.errors),
   ("header_types", toJson (p.headerTypes.map DeclarationCodecTests.headerValue)),
   ("struct_types", toJson (p.structTypes.map DeclarationCodecTests.structValue)),
   ("enum_types", toJson (p.enumTypes.map DeclarationCodecTests.enumValue)),
   ("extern_types", toJson (p.externTypes.map DeclarationCodecTests.externTypeValue)),
   ("extern_instances", toJson (p.externInstances.map DeclarationCodecTests.instanceValue)),
   ("blocks", toJson (p.blocks.map BlockCodecTests.blockValue))]

def reply (request : Json) : Except String Json := do
  let kind ← (← request.getObjVal? "kind").getStr?
  let wire ← request.getObjVal? "wire"
  match kind with
  | "library" =>
    let p ← BlockLibrary.decode "leaf" wire
    pure (Json.mkObj [("value", programValue p), ("encoded", p.toJson)])
  | _ => BlockCodecTests.reply request

private def empty : Json := Json.mkObj []
private def emptyProgram : BlockLibrary := ⟨"", [], [], [], [], [], [], []⟩
private def mixedWire : String :=
  "{\"name\":\"program\",\"errors\":[\"last\",\"\",\"first\"],\"header_types\":[{\"name\":\"H\"},{},{\"name\":\"H2\"}],\"struct_types\":[{\"name\":\"S\"},{\"name\":\"S2\"},{}],\"enum_types\":[{\"name\":\"E\",\"members\":[\"z\",\"\",\"a\"]}],\"extern_types\":[{\"name\":\"X\"}],\"extern_instances\":[{\"name\":\"instance\",\"extern_type\":\"Missing\"}],\"blocks\":[{\"name\":\"P\",\"kind\":\"BLOCK_KIND_PARSER\"},{\"name\":\"C\",\"kind\":\"BLOCK_KIND_CONTROL\"},{\"name\":\"D\",\"kind\":\"BLOCK_KIND_DEPARSER\"}],\"headers\":\"HdrOnly\",\"metadata\":\"MetaOnly\",\"exports\":[{\"role\":\"role-left\",\"block\":\"block-right\"},{},{\"role\":\"same\",\"block\":\"Missing\"}]}"
private def mixed : BlockLibrary := ⟨"program", ["last", "", "first"],
  [⟨"H", []⟩, ⟨"", []⟩, ⟨"H2", []⟩], [⟨"S", []⟩, ⟨"S2", []⟩, ⟨"", []⟩],
  [⟨"E", ["z", "", "a"]⟩], [⟨"X", [], []⟩], [⟨"instance", "Missing", []⟩],
  [⟨"P", .parser, [], [], [], [], [], "", []⟩,
   ⟨"C", .control, [], [], [], [], [], "", []⟩,
   ⟨"D", .deparser, [], [], [], [], [], "", []⟩]⟩

def tests : T Unit := do
  checkOk "program complete independent constructor" (BlockLibrary.fromJsonString mixedWire) (· == mixed)
  checkOk "program empty defaults" (BlockLibrary.decode "" empty) (· == emptyProgram)
  let order := ["name", "errors", "header_types", "struct_types", "enum_types",
    "extern_types", "extern_instances", "blocks"]
  for (first, second) in order.zip order.tail do
    let what := if ["name", "headers", "metadata"].contains first then "a string" else "an array"
    check "program adjacent first error"
      (match BlockLibrary.decode "" (Json.mkObj [(first, .bool false), (second, .bool false)]) with
       | .error e => e == first ++ ": expected " ++ what
       | .ok _ => false)
  check "program later nested bound"
    (BlockLibrary.fromJsonString "{\"header_types\":[{}, {\"fields\":[{\"type\":{\"bits\":4294967296}}]}]}" matches
      .error "header_types[1].fields[0].type.bits: 4294967296 does not fit in uint32")

end ProgramCodecTests
