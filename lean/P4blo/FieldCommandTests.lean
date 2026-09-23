import P4blo.FieldCommandExamples

namespace P4blo.FieldCommandTests

open Fields FieldCommandExamples

private def directionlessModes : Modes (.cons "x" (.scalar (.bits 8)) .nil) := .cons (.param .none) .nil

example : True := by
  fail_if_success have bad : Place modes (.bits 9) := ⟨routePort, by decide⟩
  trivial
example : True := by
  fail_if_success have bad : Place directionlessModes (.bits 8) :=
    ⟨.mk .here .scalar, by decide⟩
  trivial
example : True := by
  fail_if_success have bad : Cmd modes := Cmd.assign ttl port.read
  trivial
example : True := by
  fail_if_success have bad : Cmd modes := Cmd.ite ttl.read .done .done
  trivial

private def wrongDirection : P4bloIR.BlockScope :=
  { modes.scope with vars := modes.declarations.insert "hdr" (.param ⟨"hdr", headers.toIR, .«in»⟩) }
private def wrongType : P4bloIR.BlockScope :=
  { modes.scope with vars := modes.declarations.insert "hdr" (.param ⟨"hdr", .header "Headers", .inout⟩) }

-- Matching mutable storage does not repair a false declaration claim.
example : ¬modes.Agrees wrongDirection := by
  intro h
  have bad := h (.here : Slot roots headers)
  change (modes.declarations.insert "hdr" (.param ⟨"hdr", headers.toIR, .«in»⟩))["hdr"]? =
    some (.param ⟨"hdr", headers.toIR, .inout⟩) at bad
  simp at bad
example : ¬modes.Agrees wrongType := by
  intro h
  have bad := h (.here : Slot roots headers)
  change (modes.declarations.insert "hdr" (.param ⟨"hdr", .header "Headers", .inout⟩))["hdr"]? =
    some (.param ⟨"hdr", .struct "Headers", .inout⟩) at bad
  simp at bad
example (source : Store roots) : FrameMatches source
    { (initial source).frame with scope := wrongDirection } := initial_matches source

example : ¬roots.IndexAgrees ({ program := default } : P4bloIR.Index) := by
  intro h
  have bad := h.1.1
  simp [P4bloIR.FieldLaws.Declared] at bad

example (source : Store roots) : ¬P4bloIR.ScalarStatements.BlockFrame
    { (initial source).frame with actionVars := some {} } := by
  simp [P4bloIR.ScalarStatements.BlockFrame]

private def faultingContinuation : List P4bloIR.Execution.Work :=
  [.statement (.verify (.literal (.boolean false)) "field-continuation-must-not-run")]

example (source : Store roots) : ∃ final,
    P4bloIR.Execution.Steps
      { work := .statements dependent.lower :: faultingContinuation, run := initial source }
      { work := faultingContinuation, run := final } ∧
    FrameMatches (dependent.denote source) final.frame := by
  obtain ⟨_, final, trace, hm, _, _⟩ := dependent.steps source (initial source) faultingContinuation
    rootWF indexAgrees (modes.scope_agrees rootWF) (initial_matches source) ⟨rfl, rfl⟩
  exact ⟨final, trace, hm⟩

private def bits (width value : Nat) : P4bloIR.Value := .bits (P4bloIR.Bits.wrap width value)

private def expected (c : Case) (dst src ttl protocol port : Nat) (drop : Bool) (scratch : Nat) :
    List P4bloIR.Value :=
  [.struct "Headers" [.header "Ethernet" c.ethernetValid
      [bits 48 dst, bits 48 src, bits 16 0x0800],
    .header "IPv4" c.ipv4Valid [bits 8 ttl, bits 8 protocol, bits 16 0xabcd]],
   .struct "Metadata" [bits 9 port, .bool drop, bits 16 0x1234],
   .struct "Route" [.bool c.hit, bits 48 0xaabbccddeeff, bits 48 0x102030405060, bits 9 7],
   bits 8 scratch]

def run : IO Unit := do
  let answers : List (Nat × Nat × Nat × Nat × Nat × Bool × Nat) :=
    [(0x111213141516, 0x212223242526, 0, 6, 7, true, 0),
     (0x111213141516, 0x212223242526, 0, 6, 7, true, 0),
     (0x111213141516, 0x212223242526, 4, 10, 4, false, 4),
     (0x111213141516, 0x212223242526, 250, 0, 4, false, 250),
     (0xaabbccddeeff, 0x102030405060, 63, 6, 7, false, 19),
     (0xaabbccddeeff, 0x102030405060, 1, 6, 7, false, 19),
     (0xaabbccddeeff, 0x102030405060, 254, 6, 7, false, 19),
     (0x111213141516, 0x212223242526, 0, 6, 3, true, 19),
     (0x111213141516, 0x212223242526, 1, 6, 3, true, 19),
     (0x111213141516, 0x212223242526, 64, 6, 3, true, 19)]
  unless cases.length == answers.length do
    throw (IO.userError "field command fixture/answer length")
  for (c, (dst, src, ttl, protocol, port, drop, scratch)) in cases.zip answers do
    let source := store c.initialTTL c.ethernetValid c.ipv4Valid c.hit
    let answer := expected c dst src ttl protocol port drop scratch
    unless (c.command.denote source).toValues == answer do
      throw (IO.userError s!"field command independent source answer: {c.name}")
    let before := initial source
    let (outcome, after) := (P4bloIR.execute c.command.lower).run before
    unless outcome matches .ok () do
      throw (IO.userError s!"field command execution: {c.name}")
    unless (["hdr", "meta", "route", "scratch"].map after.frame.read?) == answer.map some do
      throw (IO.userError s!"field command exact final root values: {c.name}")
    unless after.index.program == before.index.program &&
        after.frame.scope.block == before.frame.scope.block && after.frame.action.isNone &&
        after.frame.actionVars.isNone &&
        after.frame.read? "outside" == some (.header "Outside" false [.bool true]) &&
        after.packet.any (fun p => p.data == ⟨#[0xde, 0xad, 0xbe, 0xef]⟩ && p.value == 0xdeadbeef && p.cursor == 3) &&
        after.emitter.any (fun e => e.width == 3 && e.value == 5) &&
        after.entries.any (fun e => e.defaults[("untouched", "table")]? == some (some ⟨"action", []⟩)) &&
        (after.externs.instances["untouched-register"]?).any (fun state => match state with
          | .register width cells => width == 8 && cells == #[3, 9, 27]
          | _ => false) && after.visits[("parser", "state")]? == some 13 do
      throw (IO.userError s!"field command unrelated Run state: {c.name}")
  let (outcome, _) := (P4bloIR.Execution.run faultingContinuation).run
    (initial (store 64 true true true))
  unless outcome matches .error (.parse "field-continuation-must-not-run") do
    throw (IO.userError "field command continuation must fault if executed")
  -- The real constructors initialize aggregate locals/out/inout roots; this
  -- finite runtime witness is not a general initialization correctness proof.
  for mode in [Scalar.Mode.local, .param .out, .param .inout] do
    let permissions : Modes (.cons "hdr" headers .nil) := .cons mode .nil
    let p := { program with blocks := [permissions.scope.block] }
    let i ← IO.ofExcept (P4bloIR.Index.build p)
    let frame ← IO.ofExcept (P4bloIR.Frame.forBlock i permissions.scope.block)
    if h : mode.writable = true then
      let place : Place permissions (.bits 8) :=
        ⟨.mk .here (.field (.there .here) (.field .here .scalar)), h⟩
      let body := Cmd.assign place (Scalar.bitsWith 8 42)
      let (result, final) := (P4bloIR.execute body.lower).run { index := i, frame }
      unless result matches .ok () do
        throw (IO.userError "initialized aggregate writable root must execute")
      unless final.frame.read? "hdr" == some (.struct "Headers"
          [.header "Ethernet" false [bits 48 0, bits 48 0, bits 16 0],
           .header "IPv4" false [bits 8 42, bits 8 0, bits 16 0]]) do
        throw (IO.userError "initialized aggregate write must retain invalidity and siblings")
    else throw (IO.userError "local/out/inout root must be writable")
  IO.println "10 field command full-state answers, permissions, continuation and real initialization passed"

end P4blo.FieldCommandTests
