import ArchTests.Check
import P4bloArch.Coverage

/-!
The coverage observer of `P4bloArch.Coverage`: fixed requests report the rule
tags they must exercise, and every block traced by the observer ends where
the real entry point of `P4bloIR.Interp` ends, so the tags describe the run
the reply comes from.
-/

open P4bloIR P4bloArch

namespace CoverageTests

/-- A small program with a select, a stack push past the size and a shift
past the width, as protobuf JSON. Generated once from its text form with
`p4blo.ir.dump_json` and checked by the Python validator. -/
def program : String := "{\"name\":\"coverage\",\"errors\":[\"NoError\",\"PacketTooShort\",\"NoMatch\",\"StackOutOfBounds\",\"HeaderTooShort\",\"ParserTimeout\",\"ParserInvalidArgument\"],\"header_types\":[{\"name\":\"h_t\",\"fields\":[{\"name\":\"a\",\"type\":{\"bits\":8}}]}],\"struct_types\":[{\"name\":\"H\",\"fields\":[{\"name\":\"h\",\"type\":{\"header\":\"h_t\"}},{\"name\":\"s\",\"type\":{\"stack\":{\"header\":\"h_t\",\"size\":2}}}]},{\"name\":\"M\"}],\"blocks\":[{\"name\":\"P\",\"kind\":\"BLOCK_KIND_PARSER\",\"params\":[{\"name\":\"hdr\",\"type\":{\"struct\":\"H\"},\"direction\":\"DIRECTION_OUT\"},{\"name\":\"meta\",\"type\":{\"struct\":\"M\"},\"direction\":\"DIRECTION_INOUT\"}],\"states\":[{\"name\":\"start\",\"body\":[{\"extract\":{\"target\":{\"member\":{\"base\":{\"var\":\"hdr\"},\"field\":\"h\"}}}}],\"transition\":{\"select\":{\"keys\":[{\"member\":{\"base\":{\"member\":{\"base\":{\"var\":\"hdr\"},\"field\":\"h\"}},\"field\":\"a\"}}],\"cases\":[{\"sets\":[{\"exact\":{\"bits\":{\"width\":8,\"value\":\"1\"}}}],\"target\":{\"reject\":{}}},{\"sets\":[{\"dont_care\":{}}],\"target\":{\"accept\":{}}}]}}}],\"start_state\":\"start\"},{\"name\":\"C\",\"kind\":\"BLOCK_KIND_CONTROL\",\"params\":[{\"name\":\"hdr\",\"type\":{\"struct\":\"H\"},\"direction\":\"DIRECTION_INOUT\"},{\"name\":\"meta\",\"type\":{\"struct\":\"M\"},\"direction\":\"DIRECTION_INOUT\"}],\"body\":[{\"push\":{\"stack\":{\"member\":{\"base\":{\"var\":\"hdr\"},\"field\":\"s\"}},\"count\":3}},{\"assign\":{\"target\":{\"member\":{\"base\":{\"member\":{\"base\":{\"var\":\"hdr\"},\"field\":\"h\"}},\"field\":\"a\"}},\"value\":{\"binary\":{\"op\":\"BINARY_OP_SHL\",\"left\":{\"member\":{\"base\":{\"member\":{\"base\":{\"var\":\"hdr\"},\"field\":\"h\"}},\"field\":\"a\"}},\"right\":{\"literal\":{\"bits\":{\"width\":8,\"value\":\"9\"}}}}}}}]},{\"name\":\"D\",\"kind\":\"BLOCK_KIND_DEPARSER\",\"params\":[{\"name\":\"hdr\",\"type\":{\"struct\":\"H\"},\"direction\":\"DIRECTION_IN\"}],\"body\":[{\"emit\":{\"value\":{\"member\":{\"base\":{\"var\":\"hdr\"},\"field\":\"h\"}}}},{\"emit\":{\"value\":{\"member\":{\"base\":{\"var\":\"hdr\"},\"field\":\"s\"}}}}]}],\"headers\":\"H\",\"metadata\":\"M\",\"exports\":[{\"role\":\"parser\",\"block\":\"P\"},{\"role\":\"control\",\"block\":\"C\"},{\"role\":\"deparser\",\"block\":\"D\"}]}"

/-- The tags one request reports, or the load error. -/
def tagsOf (p : Program) (host : Entries) (packet : ByteArray) : Except String (List String) := do
  let index ← Index.build p
  let sw ← Switch.load index 4
  let externs ← P4bloArch.bind index
  pure (Coverage.run sw externs host 0 packet).sorted

/-- Whether the traced parser, control and deparser end where `runParser`,
`runControl` and `runDeparser` end on the same inputs: the same acceptance,
error, cursor and headers, then the same headers and metadata, then the same
bytes. -/
def tracesAgree (p : Program) (host : Entries) (packet : ByteArray) : Except String Bool := do
  let index ← Index.build p
  let sw ← Switch.load index 4
  let externs ← P4bloArch.bind index
  let installed ← Installed.build index (some host)
  let metadata ← Value.zero (.struct sw.metadataType) index
  let parsed ← runParser index sw.parser packet metadata externs
  let some (result, run) := (Coverage.traceParser index sw.parser packet metadata externs).1
    | throw "the parser was not traced"
  let (accepted, error) := match result with
    | .ok () => (true, "NoError")
    | .error (.parse e) => (false, e)
    | .error (.interp m) => (false, m)
  let some decl := index.blocks[sw.parser]? | throw "no parser"
  let headersName := (decl.params.head?.map (·.name)).getD ""
  let parserAgrees := accepted == parsed.accepted && error == parsed.error &&
    (run.packet.map (·.cursor)) == some parsed.consumedBits &&
    run.frame.vars[headersName]? == some parsed.headers
  let (headers, metadataAfter, _) ← runControl index sw.control parsed.headers parsed.metadata installed externs
  let some (cResult, cRun) :=
      (Coverage.traceControl index sw.control parsed.headers parsed.metadata installed externs).1
    | throw "the control was not traced"
  let some cDecl := index.blocks[sw.control]? | throw "no control"
  let controlAgrees := match cResult, cDecl.params with
    | .ok (), [h, m] => cRun.frame.vars[h.name]? == some headers && cRun.frame.vars[m.name]? == some metadataAfter
    | _, _ => false
  let (bytes, _) ← runDeparser index sw.deparser headers externs
  let some (dResult, dRun) := (Coverage.traceDeparser index sw.deparser headers externs).1
    | throw "the deparser was not traced"
  let deparserAgrees := match dResult, dRun.emitter with
    | .ok (), some e => e.toBytes == bytes
    | _, _ => false
  pure (parserAgrees && controlAgrees && deparserAgrees)

/-- `check` that the request's tags include every one of `expected`. -/
def checkTags (name : String) (r : Except String (List String)) (expected : List String) :
    T Unit :=
  checkOk name r fun tags => expected.all tags.contains

/-- The inventory is complete and its names are unique and well formed. -/
def inventoryTests : T Unit := do
  let names := Coverage.all.map (·.name)
  check "coverage inventory names are unique" (names.eraseDups.length == names.length)
  check "coverage inventory docstrings are nonempty" (Coverage.all.all (!·.doc.isEmpty))
  check "coverage tag names round-trip"
    (Coverage.all.all fun i => i.tag.name == i.name)

def tests (forwarder : Program) : T Unit := do
  inventoryTests
  let bytes (l : List UInt8) : ByteArray := ⟨l.toArray⟩
  checkTags "a truncated packet hits parser.extract.tooShort"
    (tagsOf forwarder ⟨[]⟩ (bytes [0, 0])) ["parser.extract.tooShort", "stmt.extract"]
  checkTags "a whole ethernet frame takes the select default"
    (tagsOf forwarder ⟨[]⟩ (bytes (List.replicate 34 0)))
    ["parser.transition.select", "select.dontCare", "parser.target.accept"]
  checkOk "a request that cannot run reports no tags"
    (do
      let index ← Index.build forwarder
      let sw ← Switch.load index 4
      let externs ← P4bloArch.bind index
      pure (Coverage.run sw externs ⟨[]⟩ 9 (bytes [0])).sorted)
    (·.isEmpty)
  match Program.fromJsonString program with
  | .error e =>
    IO.println s!"     got: {e}"
    check "coverage program decodes" false
  | .ok p =>
    checkTags "a push past the size and a shift past the width"
      (tagsOf p ⟨[]⟩ (bytes [5]))
      ["stack.push.clamp", "stack.push.oversize", "expr.shl.overflow", "emit.stack",
       "emit.header.invalid", "emit.header.valid", "select.dontCare"]
    checkTags "an exact select case to reject"
      (tagsOf p ⟨[]⟩ (bytes [1])) ["select.exact", "parser.target.reject"]
    checkTags "an empty packet is too short" (tagsOf p ⟨[]⟩ ByteArray.empty)
      ["parser.extract.tooShort"]
    checkOk "a rejected parse is not a shift" (tagsOf p ⟨[]⟩ (bytes [1]))
      (!·.contains "parser.target.accept")
    for packet in [bytes [5], bytes [1], ByteArray.empty] do
      checkOk s!"traced blocks agree with the entry points on {packet.size} bytes"
        (tracesAgree p ⟨[]⟩ packet) id
  for packet in [bytes [0, 0], bytes (List.replicate 34 0)] do
    checkOk s!"traced forwarder blocks agree on {packet.size} bytes"
      (tracesAgree forwarder ⟨[]⟩ packet) id

end CoverageTests
