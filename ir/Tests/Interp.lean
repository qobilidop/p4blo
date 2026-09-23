import Tests.Check

/-!
Unit tests for the interpreter's primitives, per docs/semantics.md: bits
arithmetic, casts, slices, concatenation, comparison, header stacks, the
parser (extract, select, errors, the revisit rule, sub-parsers), the
deparser, tables and the extern models. The cases mirror the Python
`tests/test_interp_*.py` and `tests/test_externs.py` where they exist.
-/

open P4blo

-- ---------------------------------------------------------------------------
-- Expressions over an empty program
-- ---------------------------------------------------------------------------

/-- A run over the empty program, with `vars` as the only variables. -/
def runWith (vars : List (String × Value)) : Run :=
  let index := match Index.build default with | .ok i => i | .error _ => default
  { index, frame := { scope := default, vars := Std.HashMap.ofList vars } }

/-- Evaluate `e` with `vars` in scope. -/
def eval (e : Expr) (vars : List (String × Value) := []) : Except String Value :=
  match (evaluate e).run (runWith vars) with
  | (.ok v, _) => .ok v
  | (.error f, _) => .error (reprStr f)

/-- The `(width, value)` of a bits result. -/
def evalBits (e : Expr) : Except String (Nat × Nat) := do
  let b ← (← eval e).expectBits
  pure (b.width, b.value)

def evalBool (e : Expr) : Except String Bool := do (← eval e).expectBool

def lit (w v : Nat) : Expr := .literal (.bits w v)
def bin (op : BinaryOp) (a b : Expr) : Expr := .binary op a b
def bits (w v : Nat) : Value := .bits (Bits.wrap w v)

def arithmeticTests : T Unit := do
  checkOk "add wraps" (evalBits (bin .add (lit 8 250) (lit 8 10))) (· == (8, 4))
  checkOk "sub wraps" (evalBits (bin .sub (lit 8 3) (lit 8 5))) (· == (8, 254))
  checkOk "mul wraps" (evalBits (bin .mul (lit 8 16) (lit 8 16))) (· == (8, 0))
  checkOk "add saturates" (evalBits (bin .addSat (lit 8 250) (lit 8 10))) (· == (8, 255))
  checkOk "sub saturates" (evalBits (bin .subSat (lit 8 3) (lit 8 5))) (· == (8, 0))
  checkOk "negate is two's complement" (evalBits (.unary .negate (lit 8 1))) (· == (8, 255))
  checkOk "negate zero" (evalBits (.unary .negate (lit 8 0))) (· == (8, 0))
  checkOk "complement" (evalBits (.unary .complement (lit 8 0x0f))) (· == (8, 0xf0))
  checkOk "and or xor"
    (do pure ((← evalBits (bin .bitAnd (lit 8 0xf0) (lit 8 0x3c))),
              (← evalBits (bin .bitOr (lit 8 0xf0) (lit 8 0x3c))),
              (← evalBits (bin .bitXor (lit 8 0xf0) (lit 8 0x3c)))))
    (· == ((8, 0x30), (8, 0xfc), (8, 0xcc)))
  checkOk "shl truncates" (evalBits (bin .shl (lit 8 255) (lit 8 1))) (· == (8, 254))
  checkOk "shl by the width is zero" (evalBits (bin .shl (lit 8 1) (lit 8 8))) (· == (8, 0))
  checkOk "shl by width - 1" (evalBits (bin .shl (lit 8 1) (lit 8 7))) (· == (8, 128))
  checkOk "shr" (evalBits (bin .shr (lit 8 128) (lit 8 7))) (· == (8, 1))
  checkOk "shr by more than the width is zero" (evalBits (bin .shr (lit 8 128) (lit 8 9))) (· == (8, 0))
  checkOk "shift amount width is irrelevant" (evalBits (bin .shl (lit 8 1) (lit 16 9))) (· == (8, 0))
  checkOk "shift amount wider than the left" (evalBits (bin .shl (lit 8 1) (lit 32 3))) (· == (8, 8))
  checkOk "unsigned comparison"
    (do pure ((← evalBool (bin .lt (lit 8 200) (lit 8 3))), (← evalBool (bin .gt (lit 8 200) (lit 8 3))),
              (← evalBool (bin .le (lit 8 3) (lit 8 3))), (← evalBool (bin .ge (lit 8 2) (lit 8 3)))))
    (· == (false, true, true, false))
  checkOk "eq and ne on bits"
    (do pure ((← evalBool (bin .eq (lit 8 7) (lit 8 7))), (← evalBool (bin .ne (lit 8 7) (lit 8 7)))))
    (· == (true, false))
  checkOk "and short-circuits"
    (evalBool (bin .and (.literal (.boolean false)) (.isValid (lit 1 0)))) (· == false)
  checkOk "or short-circuits"
    (evalBool (bin .or (.literal (.boolean true)) (.isValid (lit 1 0)))) (· == true)
  checkOk "mux evaluates one branch"
    (evalBits (.mux (.literal (.boolean false)) (.isValid (lit 1 0)) (lit 4 9))) (· == (4, 9))
  checkOk "not" (evalBool (.unary .not (.literal (.boolean true)))) (· == false)
  checkOk "enum and error equality"
    (do pure ((← evalBool (bin .eq (.literal (.enumMember "E" "a")) (.literal (.enumMember "E" "a")))),
              (← evalBool (bin .ne (.literal (.error "NoError")) (.literal (.error "NoMatch"))))))
    (· == (true, true))

def castTests : T Unit := do
  checkOk "cast truncates to the low bits" (evalBits (.cast (.bits 8) (lit 16 0x1234))) (· == (8, 0x34))
  checkOk "cast zero-extends" (evalBits (.cast (.bits 16) (lit 8 0xff))) (· == (16, 0xff))
  checkOk "bool to bit<1>"
    (do pure ((← evalBits (.cast (.bits 1) (.literal (.boolean true)))),
              (← evalBits (.cast (.bits 1) (.literal (.boolean false))))))
    (· == ((1, 1), (1, 0)))
  checkOk "bit<1> to bool"
    (do pure ((← evalBool (.cast .boolean (lit 1 1))), (← evalBool (.cast .boolean (lit 1 0)))))
    (· == (true, false))
  checkError "no cast to error" (eval (.cast .error (lit 1 0))) "no cast"

def sliceAndConcatTests : T Unit := do
  checkOk "slice [11:4]" (evalBits (.slice (lit 16 0xabcd) 11 4)) (· == (8, 0xbc))
  checkOk "slice [15:15]" (evalBits (.slice (lit 16 0xabcd) 15 15)) (· == (1, 1))
  checkOk "slice [3:0]" (evalBits (.slice (lit 16 0xabcd) 3 0)) (· == (4, 0xd))
  checkOk "concat puts the left operand high" (evalBits (bin .concat (lit 4 0xa) (lit 8 0x5c))) (· == (12, 0xa5c))
  checkOk "concat then slice" (evalBits (.slice (bin .concat (lit 4 0xa) (lit 8 0x5c)) 11 8)) (· == (4, 0xa))

-- ---------------------------------------------------------------------------
-- Values: equality and stacks
-- ---------------------------------------------------------------------------

def h8 (valid : Bool) (f : Nat) : Value := .header "h8" valid [bits 8 f]

def equalityTests : T Unit := do
  let samples := ([0, 1, 2, 8, 32, 64, 129].flatMap fun w =>
    [bits w 0, bits w 1, bits w (2 ^ w - 1)]) ++ [.bool false, .bool true]
  check "proof-visible scalar equality agrees with prior derived equality"
    (samples.all fun a => samples.all fun b => Value.equal a b == (a == b))
  check "two invalid headers are equal whatever their fields" (Value.equal (h8 false 1) (h8 false 2))
  check "valid and invalid headers differ" (!Value.equal (h8 true 1) (h8 false 1))
  check "valid headers compare fieldwise"
    (Value.equal (h8 true 1) (h8 true 1) && !Value.equal (h8 true 1) (h8 true 2))
  check "structs compare fieldwise"
    (Value.equal (.struct "S" [bits 8 1, h8 false 9]) (.struct "S" [bits 8 1, h8 false 3]) &&
     !Value.equal (.struct "S" [bits 8 1]) (.struct "S" [bits 8 2]))
  check "stacks compare elementwise and ignore nextIndex"
    (Value.equal (.stack "h8" [h8 true 1, h8 false 0] 1) (.stack "h8" [h8 true 1, h8 false 5] 2) &&
     !Value.equal (.stack "h8" [h8 true 1] 1) (.stack "h8" [h8 true 2] 1))
  check "bits equality is by width and value" ((bits 8 1 == bits 8 1) && !(bits 8 1 == bits 9 1))

/-- A program with header `h8` and struct `H { hs : h8[3] }`. -/
def stackIndex : Except String Index :=
  Index.build { (default : Program) with
    headerTypes := [{ name := "h8", fields := [{ name := "f", type := .bits 8 }] }],
    structTypes := [{ name := "H", fields := [{ name := "hs", type := .stack "h8" 3 }] }] }

/-- Evaluate `e` with `vars` in scope over the program of `index`. -/
def evalIn (index : Except String Index) (e : Expr) (vars : List (String × Value)) : Except String Value := do
  let index ← index
  match (evaluate e).run { runWith vars with index } with
  | (.ok v, _) => pure v
  | (.error f, _) => throw (reprStr f)

/-- The `(width, value)` of a bits value. -/
def bitsOf (v : Except String Value) : Except String (Nat × Nat) := do
  let b ← (← v).expectBits
  pure (b.width, b.value)

def stackTests : T Unit := do
  let stack : Value := .stack "h8" [h8 true 1, h8 true 2, h8 false 0] 2
  checkOk "push_front shifts up, fills invalid zeros, bumps nextIndex"
    (do pushFront stack 1 (← stackIndex))
    (· == .stack "h8" [h8 false 0, h8 true 1, h8 true 2] 3)
  checkOk "push_front beyond the size acts as the size"
    (do pushFront stack 5 (← stackIndex))
    (· == .stack "h8" [h8 false 0, h8 false 0, h8 false 0] 3)
  checkOk "pop_front shifts down, fills invalid zeros, lowers nextIndex"
    (do popFront stack 1 (← stackIndex))
    (· == .stack "h8" [h8 true 2, h8 false 0, h8 false 0] 1)
  checkOk "pop_front stops nextIndex at zero"
    (do popFront stack 3 (← stackIndex))
    (· == .stack "h8" [h8 false 0, h8 false 0, h8 false 0] 0)
  checkOk "lastIndex is nextIndex - 1 as bit<32>"
    (bitsOf (eval (.lastIndex (.var "hs")) [("hs", stack)])) (· == (32, 1))
  checkOk "lastIndex wraps at nextIndex 0"
    (bitsOf (eval (.lastIndex (.var "hs")) [("hs", .stack "h8" [] 0)])) (· == (32, 2 ^ 32 - 1))
  checkOk "index in range" (eval (.index (.var "hs") (lit 32 1)) [("hs", stack)]) (· == h8 true 2)
  checkOk "index out of range is a zero invalid header"
    (evalIn stackIndex (.index (.var "hs") (lit 32 7)) [("hs", stack)]) (· == h8 false 0)
  checkOk "reading a field of an invalid header gives the stored value"
    (evalIn stackIndex (.member (.var "h") "f") [("h", h8 false 7)]) (· == bits 8 7)
  checkOk "isValid is the validity bit"
    (do pure ((← eval (.isValid (.var "h")) [("h", h8 false 7)]), (← eval (.isValid (.var "h")) [("h", h8 true 7)])))
    (· == (.bool false, .bool true))

-- ---------------------------------------------------------------------------
-- Parsers
-- ---------------------------------------------------------------------------

/-- The core error list plus one program error. -/
def errorList : List String :=
  ["NoError", "PacketTooShort", "NoMatch", "StackOutOfBounds", "HeaderTooShort", "ParserTimeout",
   "ParserInvalidArgument", "BadVersion"]

/-- The test program of `tests/test_interp_parser.py`: headers `h8 { f :
bit<8> }` and `mixed { a : bit<3>, flag : bool, b : bit<12> }`, `H { e :
h8, hs : h8[2], w : mixed }`, `M { n : bit<8>, flag : bool }`, a parser
`P` of the given states, a deparser `D` emitting `hdr.w`, and `extra`
blocks. -/
def parserProgram (states : List State) (extra : List Block := []) : Program :=
  { (default : Program) with
    name := "t", errors := errorList,
    headerTypes := [{ name := "h8", fields := [{ name := "f", type := .bits 8 }] },
                    { name := "mixed", fields := [{ name := "a", type := .bits 3 }, { name := "flag", type := .boolean },
                                                  { name := "b", type := .bits 12 }] }],
    structTypes := [{ name := "H", fields := [{ name := "e", type := .header "h8" }, { name := "hs", type := .stack "h8" 2 },
                                              { name := "w", type := .header "mixed" }] },
                    { name := "M", fields := [{ name := "n", type := .bits 8 }, { name := "flag", type := .boolean }] }],
    blocks := [{ (default : Block) with
                 name := "P", kind := .parser,
                 params := [{ name := "hdr", type := .struct "H", direction := .out },
                            { name := "meta", type := .struct "M", direction := .inout }],
                 states, startState := "start" },
               { (default : Block) with
                 name := "D", kind := .deparser,
                 params := [{ name := "hdr", type := .struct "H", direction := .«in» }],
                 body := [.emit (.member (.var "hdr") "w")] }] ++ extra,
    headers := "H", metadata := "M" }

def hdrE : Expr := .member (.var "hdr") "e"
def hdrW : Expr := .member (.var "hdr") "w"
def hdrHs : Expr := .member (.var "hdr") "hs"
def lhdrE : LValue := .member (.var "hdr") "e"
def lhdrW : LValue := .member (.var "hdr") "w"
def lhdrHs : LValue := .member (.var "hdr") "hs"
def eF : Expr := .member hdrE "f"
def lmetaN : LValue := .member (.var "meta") "n"
def metaN : Expr := .member (.var "meta") "n"
def accept : Transition := .direct .accept
def state (name : String) (body : List Stmt) (transition : Transition) : State := { name, body, transition }

/-- Run parser `P` of the program over `packet`. -/
def runP (states : List State) (packet : List UInt8) (extra : List Block := []) :
    Except String ParseOutcome := do
  let index ← Index.build (parserProgram states extra)
  let metadata ← Value.zero (.struct "M") index
  runParser index "P" ⟨packet.toArray⟩ metadata {}

def hdrField (out : ParseOutcome) (i : Nat) : Value :=
  match out.headers with | .struct _ fields => fields.getD i default | _ => default
def metaField (out : ParseOutcome) (i : Nat) : Value :=
  match out.metadata with | .struct _ fields => fields.getD i default | _ => default

instance : Repr ParseOutcome := ⟨fun o _ =>
  s!"ParseOutcome(headers := {reprStr o.headers}, metadata := {reprStr o.metadata}, " ++
  s!"consumed := {o.consumedBits}, accepted := {o.accepted}, error := {o.error})"⟩

def extractTests : T Unit := do
  checkOk "extract fills the fields and sets valid"
    (runP [state "start" [.extract lhdrE] accept] [0xab, 0xcd])
    fun o => o.accepted && o.error == "NoError" && hdrField o 0 == h8 true 0xab && o.consumedBits == 8
  checkOk "extract takes fields most significant first"
    (runP [state "start" [.extract lhdrW] accept] [0xb5, 0x67])
    fun o => hdrField o 2 == .header "mixed" true [bits 3 0b101, .bool true, bits 12 0x567] && o.consumedBits == 16
  checkOk "extract past the end is PacketTooShort and consumes nothing"
    (runP [state "start" [.extract lhdrE] accept] [])
    fun o => !o.accepted && o.error == "PacketTooShort" && o.consumedBits == 0 && hdrField o 0 == h8 false 0
  checkOk "lookahead reads without consuming and a header result is valid"
    (runP [state "start" [.assign lmetaN (.lookahead (.bits 8)), .assign lhdrW (.lookahead (.header "mixed")),
                          .extract lhdrE] accept] [0x2a, 0x01])
    fun o => metaField o 0 == bits 8 0x2a &&
      hdrField o 2 == .header "mixed" true [bits 3 1, .bool false, bits 12 0xa01] &&
      hdrField o 0 == h8 true 0x2a && o.consumedBits == 8
  checkOk "lookahead of a bool"
    (runP [state "start" [.assign (.member (.var "meta") "flag") (.lookahead .boolean)] accept] [0x80])
    fun o => metaField o 1 == .bool true && o.consumedBits == 0
  checkOk "lookahead past the end is PacketTooShort"
    (runP [state "start" [.assign lmetaN (.lookahead (.bits 8))] accept] [])
    fun o => o.error == "PacketTooShort"
  checkOk "advance skips bits"
    (runP [state "start" [.advance (lit 32 8), .extract lhdrE] accept] [1, 2])
    fun o => hdrField o 0 == h8 true 2 && o.consumedBits == 16
  checkOk "advance past the end is PacketTooShort and the cursor stays"
    (runP [state "start" [.advance (lit 32 16)] accept] [1])
    fun o => o.error == "PacketTooShort" && o.consumedBits == 0

/-- `name` sets `meta.n` to `value` and accepts. -/
def setN (name : String) (value : Nat) : State := state name [.assign lmetaN (lit 8 value)] accept

def selectStates : List State :=
  [state "start" [.extract lhdrE]
    (.select [eF]
      [{ sets := [.exact (.bits 8 1)], target := .state "s_exact" },
       { sets := [.masked (.bits 8 0x80) (.bits 8 0x80)], target := .state "s_masked" },
       { sets := [.range (.bits 8 0x10) (.bits 8 0x1f)], target := .state "s_range" },
       { sets := [.dontCare], target := .state "s_default" }]),
   setN "s_exact" 1, setN "s_masked" 2, setN "s_range" 3, setN "s_default" 4]

def selectTests : T Unit := do
  for (byte, expected) in [(0x01, 1), (0x81, 2), (0x15, 3), (0x05, 4), (0x91, 2), (0x10, 3)] do
    checkOk s!"select tries the cases in order: {byte} -> {expected}"
      (runP selectStates [UInt8.ofNat byte]) fun o => o.accepted && metaField o 0 == bits 8 expected
  checkOk "select with no matching case rejects with NoMatch"
    (runP [state "start" [.extract lhdrE]
      (.select [eF] [{ sets := [.exact (.bits 8 1)], target := .accept }])] [2])
    fun o => !o.accepted && o.error == "NoMatch" && o.consumedBits == 8
  checkOk "select on several keys needs every set to match"
    (runP [state "start" [.extract lhdrE]
      (.select [eF, .member (.var "meta") "flag"]
        [{ sets := [.exact (.bits 8 1), .exact (.boolean true)], target := .accept },
         { sets := [.dontCare, .dontCare], target := .reject }])] [1])
    fun o => !o.accepted && o.error == "NoError"
  let verifyBody : List Stmt := [.extract lhdrE, .verify (bin .eq eF (lit 8 1)) "BadVersion"]
  checkOk "verify passes" (runP [state "start" verifyBody accept] [1]) (·.accepted)
  checkOk "verify raises its error and keeps the state at that moment"
    (runP [state "start" verifyBody accept] [2])
    fun o => !o.accepted && o.error == "BadVersion" && hdrField o 0 == h8 true 2
  checkOk "verify with NoError is an explicit reject"
    (runP [state "start" [.verify (.literal (.boolean false)) "NoError"] accept] [1])
    fun o => !o.accepted && o.error == "NoError"
  checkOk "explicit reject is not accepted and has no error"
    (runP [state "start" [] (.direct .reject)] [1]) fun o => !o.accepted && o.error == "NoError"
  checkOk "an error keeps the partial headers and metadata"
    (runP [state "start" [.assign lmetaN (lit 8 5), .extract lhdrE, .extract lhdrW] accept] [7])
    fun o => o.error == "PacketTooShort" && metaField o 0 == bits 8 5 && hdrField o 0 == h8 true 7 &&
      hdrField o 2 == .header "mixed" false [bits 3 0, .bool false, bits 12 0] && o.consumedBits == 8

def loopUntilLast : List State :=
  [state "start" [.extract (.next lhdrHs)]
    (.select [.lastIndex hdrHs]
      [{ sets := [.exact (.bits 32 1)], target := .accept },
       { sets := [.dontCare], target := .state "start" }])]

def loopForever : List State := [state "start" [.extract (.next lhdrHs)] (.direct (.state "start"))]

def stackParserTests : T Unit := do
  checkOk "a loop over a stack terminates by extraction"
    (runP loopUntilLast [0x0a, 0x0b, 0x0c])
    fun o => o.accepted && hdrField o 1 == .stack "h8" [h8 true 0x0a, h8 true 0x0b] 2 && o.consumedBits == 16
  checkOk "extract into a full stack is StackOutOfBounds"
    (runP loopForever [0x0a, 0x0b, 0x0c])
    fun o => o.error == "StackOutOfBounds" && hdrField o 1 == .stack "h8" [h8 true 0x0a, h8 true 0x0b] 2 &&
      o.consumedBits == 16
  checkOk "a full stack is reported before a short packet"
    (runP loopForever [0x0a, 0x0b]) fun o => o.error == "StackOutOfBounds" && o.consumedBits == 16
  checkOk "revisiting a state without consuming is ParserTimeout"
    (runP [state "start" [] (.direct (.state "start"))] [1])
    fun o => o.error == "ParserTimeout" && o.consumedBits == 0
  checkOk "the revisit rule sees a cycle through another state"
    (runP [state "start" [] (.direct (.state "other")), state "other" [] (.direct (.state "start"))] [1])
    fun o => o.error == "ParserTimeout"
  checkOk "extract into hs[i] past the end consumes and stores nothing"
    (runP [state "start" [.extract (.index lhdrHs (lit 32 5))] accept] [0x42])
    fun o => o.accepted && o.consumedBits == 8 && hdrField o 1 == .stack "h8" [h8 false 0, h8 false 0] 0
  checkOk "writing hs[i] past the end does nothing, reading it is a zero header"
    (runP [state "start" [.assign (.member (.index lhdrHs (lit 32 9)) "f") (lit 8 3),
                          .assign lmetaN (.member (.index hdrHs (lit 32 9)) "f")] accept] [])
    fun o => o.accepted && hdrField o 1 == .stack "h8" [h8 false 0, h8 false 0] 0 && metaField o 0 == bits 8 0
  checkOk "setValid and setInvalid touch only validity"
    (runP [state "start" [.assign (.member lhdrE "f") (lit 8 9), .setValid lhdrE, .setInvalid lhdrE] accept] [])
    fun o => hdrField o 0 == h8 false 9
  checkOk "push and pop in a parser"
    (runP [state "start" [.extract (.next lhdrHs), .push lhdrHs 1] accept] [0x0a])
    fun o => hdrField o 1 == .stack "h8" [h8 false 0, h8 true 0x0a] 2

/-- A sub-parser block `Sub` with `params` and `states`. -/
def subParser (params : List Param) (states : List State) : Block :=
  { (default : Block) with name := "Sub", kind := .parser, params, states, startState := "start" }

def subParserTests : T Unit := do
  let outX : Param := { name := "x", type := .header "h8", direction := .out }
  checkOk "sub-parser call copies out arguments back"
    (runP [state "start" [.callBlock "Sub" [.lvalue lhdrE]] accept] [0x42]
      [subParser [outX] [state "start" [.extract (.var "x")] accept]])
    fun o => o.accepted && hdrField o 0 == h8 true 0x42 && o.consumedBits == 8
  checkOk "sub-parser error copies back before propagating"
    (runP [state "start" [.callBlock "Sub" [.lvalue lhdrE, .lvalue (.index lhdrHs (lit 32 0))]] accept] [0x42]
      [subParser [outX, { name := "y", type := .header "h8", direction := .out }]
        [state "start" [.extract (.var "x"), .extract (.var "y")] accept]])
    fun o => o.error == "PacketTooShort" && hdrField o 0 == h8 true 0x42 &&
      hdrField o 1 == .stack "h8" [h8 false 0, h8 false 0] 0 && o.consumedBits == 8
  checkOk "sub-parser states count for the revisit rule"
    (runP [state "start" [.callBlock "Sub" [.lvalue lhdrE], .callBlock "Sub" [.lvalue lhdrE]] accept] [0x42]
      [subParser [outX] [state "start" [] accept]])
    fun o => o.error == "ParserTimeout"
  checkOk "in arguments are copied in and inout back"
    (runP [state "start" [.assign lmetaN (lit 8 4), .callBlock "Sub" [.lvalue lmetaN, .expr (lit 8 10)]] accept] []
      [subParser [{ name := "n", type := .bits 8, direction := .inout }, { name := "k", type := .bits 8, direction := .«in» }]
        [state "start" [.assign (.var "n") (bin .add (.var "n") (.var "k"))] accept]])
    fun o => o.accepted && metaField o 0 == bits 8 14

-- ---------------------------------------------------------------------------
-- Deparser
-- ---------------------------------------------------------------------------

def deparserTests : T Unit := do
  -- `D2` emits the whole headers struct; `D` emits `hdr.w` only.
  let d2 : Block := { (default : Block) with
    name := "D2", kind := .deparser,
    params := [{ name := "hdr", type := .struct "H", direction := .«in» }], body := [.emit (.var "hdr")] }
  let index := Index.build (parserProgram [] [d2])
  let emit (block : String) (headers : Value) : Except String (List UInt8) := do
    let (bytes, _) ← runDeparser (← index) block headers {}
    pure bytes.toList
  let withW (w : Value) : Value := .struct "H" [h8 false 0, .stack "h8" [h8 false 0, h8 false 0] 0, w]
  checkOk "emit of an invalid header writes nothing"
    (emit "D" (withW (.header "mixed" false [bits 3 5, .bool true, bits 12 0x567]))) (· == [])
  checkOk "emit concatenates the fields most significant first"
    (emit "D" (withW (.header "mixed" true [bits 3 0b101, .bool true, bits 12 0x567]))) (· == [0xb5, 0x67])
  checkOk "emit of a struct walks fields and stacks, skips invalid headers and pads the total"
    (emit "D2" (.struct "H" [h8 true 0xff, .stack "h8" [h8 true 0x12, h8 false 0] 1,
                             .header "mixed" true [bits 3 7, .bool false, bits 12 0]]))
    (· == [0xff, 0x12, 0b11100000, 0])
  checkOk "emit then extract roundtrips a header"
    (do
      let w : Value := .header "mixed" true [bits 3 6, .bool true, bits 12 0xabc]
      let (bytes, _) ← runDeparser (← index) "D" (withW w) {}
      let index ← Index.build (parserProgram [state "start" [.extract lhdrW] accept])
      let out ← runParser index "P" bytes (← Value.zero (.struct "M") index) {}
      pure (out.accepted && Value.equal (hdrField out 2) w))
    (· == true)

-- ---------------------------------------------------------------------------
-- Tables and controls
-- ---------------------------------------------------------------------------

def metaA : Expr := .member (.var "meta") "a"
def metaB : Expr := .member (.var "meta") "b"

/-- The test program of `tests/test_interp_tables.py`, plus a body that
applies `exact_t` and records `hit` in `meta.h`. -/
def tableProgram : Program :=
  { (default : Program) with
    name := "t", errors := ["NoError"],
    structTypes := [{ name := "H", fields := [] },
                    { name := "M", fields := [{ name := "a", type := .bits 8 }, { name := "b", type := .bits 8 },
                                              { name := "h", type := .boolean }] }],
    blocks := [{ (default : Block) with
      name := "C", kind := .control,
      params := [{ name := "hdr", type := .struct "H", direction := .inout },
                 { name := "meta", type := .struct "M", direction := .inout }],
      actions := [{ name := "set", params := [{ name := "v", type := .bits 8, direction := .none }],
                    body := [.assign (.member (.var "meta") "a") (.var "v")] },
                  { name := "NoAction", params := [], body := [] },
                  { name := "other", params := [], body := [] }],
      tables := [
        { (default : Table) with
          name := "exact_t", keys := [{ expr := metaA, matchKind := .exact, name := "" }],
          actions := ["set", "NoAction"] },
        { (default : Table) with
          name := "lpm_t", keys := [{ expr := metaA, matchKind := .lpm, name := "" }],
          actions := ["set"], defaultAction := some { action := "set", args := [.bits 8 9] } },
        { (default : Table) with
          name := "tern_t",
          keys := [{ expr := metaA, matchKind := .ternary, name := "" }, { expr := metaB, matchKind := .exact, name := "" }],
          actions := ["set"] },
        { (default : Table) with
          name := "const_t", keys := [{ expr := metaA, matchKind := .exact, name := "" }],
          actions := ["set"], defaultAction := some { action := "set", args := [.bits 8 7] },
          constDefaultAction := true,
          constEntries := [{ keys := [.exact 1], action := { action := "set", args := [.bits 8 1] }, priority := 0 }] }],
      body := [.apply "exact_t" (some (.member (.var "meta") "h"))] }],
    headers := "H", metadata := "M" }

def call (action : String) (args : List Nat) : ActionCall := { action, args := args.map (.bits 8 ·) }
def entry (keys : List KeyValue) (action : ActionCall) (priority : Nat := 0) : Entry := { keys, action, priority }
def key (values : List Nat) : List Bits := values.map (Bits.wrap 8)

def installed (host : Option Entries := none) : Except String Installed := do
  Installed.build (← Index.build tableProgram) host

instance : Repr Installed := ⟨fun i _ => s!"Installed({i.entries.size} tables)"⟩

def tableTests : T Unit := do
  let exact := ("C", "exact_t")
  let lpm := ("C", "lpm_t")
  let tern := ("C", "tern_t")
  let const := ("C", "const_t")
  checkOk "exact hit and miss without a default"
    (do
      let t ← (← installed).install exact (entry [.exact 5] (call "set" [1]))
      pure ((← t.lookup exact (key [5])), (← t.lookup exact (key [6]))))
    (· == ({ action := some (call "set" [1]), hit := true }, { action := none, hit := false }))
  checkOk "lpm: the longest prefix wins and the default runs on a miss"
    (do
      let t ← (← installed).install lpm (entry [.lpm 0 0] (call "set" [1]))
      let t ← t.install lpm (entry [.lpm 128 1] (call "set" [2]))
      let t ← t.install lpm (entry [.lpm 160 3] (call "set" [3]))
      pure ((← t.lookup lpm (key [0b10100001])).action, (← t.lookup lpm (key [0b10010000])).action,
            (← t.lookup lpm (key [0b01000000])).action, (← (← installed).lookup lpm (key [0]))))
    (· == (some (call "set" [3]), some (call "set" [2]), some (call "set" [1]),
           { action := some (call "set" [9]), hit := false }))
  checkOk "ternary: the largest priority wins"
    (do
      let t ← (← installed).install tern (entry [.ternary 0 0, .exact 1] (call "set" [1]) 1)
      let t ← t.install tern (entry [.ternary 128 128, .exact 1] (call "set" [5]) 5)
      pure ((← t.lookup tern (key [0x81, 1])).action, (← t.lookup tern (key [0x01, 1])).action,
            (← t.lookup tern (key [0x81, 2]))))
    (· == (some (call "set" [5]), some (call "set" [1]), { action := none, hit := false }))
  checkOk "const entries are installed first"
    (do pure ((← (← installed).lookup const (key [1])), (← (← installed).lookup const (key [2]))))
    (· == ({ action := some (call "set" [1]), hit := true }, { action := some (call "set" [7]), hit := false }))
  let host : Entries := { tables := [{ block := "C", table := "exact_t", entries := [entry [.exact 5] (call "set" [1])],
                                       defaultAction := none }] }
  checkOk "host entries come from the block-scoped table name"
    (do (← installed (some host)).lookup exact (key [5])) (· == { action := some (call "set" [1]), hit := true })
  checkError "host entries for an unknown block are rejected"
    (installed (some { tables := [{ block := "X", table := "exact_t", entries := [], defaultAction := none }] }) >>=
      fun i => i.install ("X", "exact_t") (entry [.exact 1] (call "set" [1])))
    "no table"
  let rejects : List (String × TableRef × List KeyValue × ActionCall × Nat × String) :=
    [("arity", exact, [.exact 1, .exact 2], call "set" [1], 0, "has 1 keys"),
     ("wider than the key", exact, [.exact 256], call "set" [1], 0, "does not fit in 8 bits"),
     ("wrong kind", exact, [.lpm 0 0], call "set" [1], 0, "wants a exact value"),
     ("priority without a ternary key", exact, [.exact 1], call "set" [1], 1, "priority must be 0"),
     ("action not in the table", exact, [.exact 1], call "other" [], 0, "has no action 'other'"),
     ("missing action data", exact, [.exact 1], call "set" [], 0, "takes 1 arguments"),
     ("too much action data", exact, [.exact 1], call "set" [1, 2], 0, "takes 1 arguments"),
     ("no such action", exact, [.exact 1], call "missing" [1], 0, "has no action 'missing'"),
     ("bit outside the prefix", lpm, [.lpm 1 7], call "set" [1], 0, "outside its prefix"),
     ("prefix too long", lpm, [.lpm 0 9], call "set" [1], 0, "exceeds width 8"),
     ("bit outside the mask", tern, [.ternary 1 0, .exact 1], call "set" [1], 0, "outside its mask")]
  for (what, ref, keys, action, priority, fragment) in rejects do
    checkError s!"install rejects: {what}" (do (← installed).install ref (entry keys action priority)) fragment
  checkError "install rejects action data of the wrong width"
    (do (← installed).install exact (entry [.exact 1] { action := "set", args := [.bits 16 1] })) "is bit<16>, not"
  checkError "install rejects a duplicate exact entry"
    (do (← (← installed).install exact (entry [.exact 1] (call "set" [1]))).install exact (entry [.exact 1] (call "set" [2])))
    "duplicate"
  checkOk "a different prefix length with the same bits is another prefix"
    (do
      let t ← (← installed).install lpm (entry [.lpm 128 1] (call "set" [1]))
      let dup := t.install lpm (entry [.lpm 128 1] (call "set" [2]))
      let t ← t.install lpm (entry [.lpm 128 2] (call "set" [3]))
      pure (dup matches .error _, (t.entries.getD lpm #[]).size))
    (· == (true, 2))
  checkOk "overlapping ternary entries of equal priority are rejected, disjoint or other priorities fine"
    (do
      let t ← (← installed).install tern (entry [.ternary 128 128, .exact 1] (call "set" [1]) 3)
      let overlap := t.install tern (entry [.ternary 0 0, .exact 1] (call "set" [2]) 3)
      let t ← t.install tern (entry [.ternary 0 0, .exact 2] (call "set" [2]) 3)
      let t ← t.install tern (entry [.ternary 0 0, .exact 1] (call "set" [2]) 4)
      pure (overlap matches .error _, (t.entries.getD tern #[]).size))
    (· == (true, 3))
  checkError "a host entry duplicating a const entry is rejected"
    (installed (some { tables := [{ block := "C", table := "const_t", entries := [entry [.exact 1] (call "set" [2])],
                                    defaultAction := none }] }))
    "duplicate"
  checkOk "a host default replaces a non-const default and none restores the program's"
    (do
      let t ← installed (some { tables := [{ block := "C", table := "lpm_t", entries := [],
                                             defaultAction := some (call "set" [2]) }] })
      let a ← t.lookup lpm (key [0])
      let t ← t.setDefault lpm none
      pure (a, ← t.lookup lpm (key [0])))
    (· == ({ action := some (call "set" [2]), hit := false }, { action := some (call "set" [9]), hit := false }))
  checkError "a host default cannot replace a const default"
    (do (← installed).setDefault const (some (call "set" [2]))) "const default"
  checkError "a host default must be one of the table's actions"
    (do (← installed).setDefault lpm (some (call "NoAction" []))) "has no action"
  checkError "a host default must carry the action data"
    (do (← installed).setDefault lpm (some (call "set" []))) "takes 1 arguments"
  checkOk "a table without a default falls back to NoAction"
    (do (← (← installed).setDefault exact none).lookup exact (key [0])) (· == { action := none, hit := false })

def controlTests : T Unit := do
  let run (a : Nat) (host : Entries) : Except String (Value × Value) := do
    let index ← Index.build tableProgram
    let entries ← Installed.build index (some host)
    let (h, m, _) ← runControl index "C" (.struct "H" []) (.struct "M" [bits 8 a, bits 8 0, .bool false]) entries {}
    pure (h, m)
  let host : Entries := { tables := [{ block := "C", table := "exact_t", entries := [entry [.exact 5] (call "set" [1])],
                                       defaultAction := none }] }
  checkOk "apply runs the matched action with its data and writes hit"
    (run 5 host) (· == (.struct "H" [], .struct "M" [bits 8 1, bits 8 0, .bool true]))
  checkOk "apply on a miss runs the default and writes hit false"
    (run 6 host) (· == (.struct "H" [], .struct "M" [bits 8 6, bits 8 0, .bool false]))
  -- A direct action call with an inout argument and an action calling an action.
  let program := { tableProgram with blocks := tableProgram.blocks.map fun b =>
    { b with
      actions := b.actions ++
        [{ name := "bump", params := [{ name := "x", type := .bits 8, direction := .inout }],
           body := [.assign (.var "x") (bin .add (.var "x") (lit 8 1))] },
         { name := "twice", params := [], body := [.callAction "bump" [.lvalue (.member (.var "meta") "b")],
                                                   .callAction "bump" [.lvalue (.member (.var "meta") "b")]] }],
      body := [.callAction "twice" []] } }
  checkOk "a direct action call copies inout arguments back, through a nested action call"
    (do
      let index ← Index.build program
      let entries ← Installed.build index none
      let (_, m, _) ← runControl index "C" (.struct "H" []) (.struct "M" [bits 8 0, bits 8 40, .bool false]) entries {}
      pure m)
    (· == .struct "M" [bits 8 0, bits 8 42, .bool false])

-- ---------------------------------------------------------------------------
-- Externs
-- ---------------------------------------------------------------------------

/-- A program declaring `register` (16-bit cells), `counter` and
`checksum16` with one instance each, and a control that reads and writes
them. -/
def externProgram : Program :=
  { (default : Program) with
    name := "x", errors := ["NoError"],
    structTypes := [{ name := "H", fields := [] },
                    { name := "M", fields := [{ name := "a", type := .bits 16 }, { name := "c", type := .bits 16 }] }],
    externTypes := [
      { name := "register", constructorParams := [{ name := "size", type := .bits 32, direction := .«in» }],
        methods := [{ name := "read", params := [{ name := "result", type := .bits 16, direction := .out },
                                                 { name := "index", type := .bits 32, direction := .«in» }], returns := none },
                    { name := "write", params := [{ name := "index", type := .bits 32, direction := .«in» },
                                                  { name := "value", type := .bits 16, direction := .«in» }], returns := none }] },
      { name := "counter", constructorParams := [{ name := "size", type := .bits 32, direction := .«in» }],
        methods := [{ name := "count", params := [{ name := "index", type := .bits 32, direction := .«in» }], returns := none }] },
      { name := "checksum16", constructorParams := [],
        methods := [{ name := "compute", params := [{ name := "data", type := .bits 64, direction := .«in» }],
                      returns := some (.bits 16) }] }],
    externInstances := [{ name := "r", externType := "register", args := [.bits 32 4] },
                        { name := "k", externType := "counter", args := [.bits 32 2] },
                        { name := "ck", externType := "checksum16", args := [] }],
    blocks := [{ (default : Block) with
      name := "C", kind := .control,
      params := [{ name := "hdr", type := .struct "H", direction := .inout },
                 { name := "meta", type := .struct "M", direction := .inout }],
      body := [
        -- meta.a += r[1]; r[1] = meta.a; count 1 twice and 9 once; meta.c = checksum of the RFC example
        .callExtern "r" "read" [.lvalue (.member (.var "meta") "c"), .expr (lit 32 1)] none,
        .assign (.member (.var "meta") "a") (bin .add (.member (.var "meta") "a") (.member (.var "meta") "c")),
        .callExtern "r" "write" [.expr (lit 32 1), .expr (.member (.var "meta") "a")] none,
        .callExtern "k" "count" [.expr (lit 32 1)] none,
        .callExtern "k" "count" [.expr (lit 32 1)] none,
        .callExtern "k" "count" [.expr (lit 32 9)] none,
        .callExtern "ck" "compute" [.expr (lit 64 0x0001f203f4f5f6f7)] (some (.member (.var "meta") "c"))] }],
    headers := "H", metadata := "M" }

def externTests : T Unit := do
  checkOk "RFC 1071 worked example" (pure (internetChecksum 64 0x0001f203f4f5f6f7) : Except String Nat)
    (· == (0xffff - 0xddf2))
  checkOk "checksum validates an IPv4 header"
    (do
      let header ← hexToBytes? "450000730000400040110000c0a80001c0a800c7"
      let sum := internetChecksum (header.size * 8) (bytesToNat header)
      let withSum ← hexToBytes? "45000073000040004011b861c0a80001c0a800c7"
      pure (sum, internetChecksum (withSum.size * 8) (bytesToNat withSum)))
    (· == (0xb861, 0))
  checkOk "checksum pads an odd width at the end"
    (pure (internetChecksum 8 0x12) : Except String Nat) (· == (0xffff - 0x1200))
  let runTwice : Except String (Value × Value × Externs) := do
    let index ← Index.build externProgram
    let externs ← Externs.bind index
    let entries ← Installed.build index none
    let (_, m1, externs) ← runControl index "C" (.struct "H" []) (.struct "M" [bits 16 5, bits 16 0]) entries externs
    let (_, m2, externs) ← runControl index "C" (.struct "H" []) (.struct "M" [bits 16 7, bits 16 0]) entries externs
    pure (m1, m2, externs)
  checkOk "register state persists across runs; out args and return values are written back"
    (runTwice.map fun (m1, m2, _) => (m1, m2))
    (· == (.struct "M" [bits 16 5, bits 16 0x220d], .struct "M" [bits 16 12, bits 16 0x220d]))
  checkOk "counter counts in range and ignores out of range"
    (runTwice.map fun (_, _, e) => e.instances["k"]?.map reprStr)
    (· == some "P4blo.ExternState.counter #[0, 4]")
  checkOk "register out of range reads zero and ignores writes"
    (do
      let (s, r) ← (ExternState.register 16 #[0, 0]).call "read" [bits 16 0, bits 32 7]
      let (s, _) ← s.call "write" [bits 32 7, bits 16 1]
      pure (r.outs, reprStr s))
    (· == ([bits 16 0], "P4blo.ExternState.register 16 #[0, 0]"))
  checkError "an unknown extern type does not bind"
    (Index.build { externProgram with
        externInstances := [{ name := "m", externType := "mystery", args := [] }],
        externTypes := externProgram.externTypes ++ [{ name := "mystery", constructorParams := [], methods := [] }] }
      >>= Externs.bind)
    "no implementation"
  checkError "an inconsistent width variable does not bind"
    (Index.build { externProgram with externTypes := externProgram.externTypes.map fun t =>
        if t.name == "register" then { t with methods := t.methods.map fun m =>
          if m.name == "write" then { m with params := m.params.map fun p =>
            if p.name == "value" then { p with type := .bits 8 } else p } else m } else t }
      >>= Externs.bind)
    "T is bit<16> elsewhere"
  checkError "an extra method does not bind"
    (Index.build { externProgram with externTypes := externProgram.externTypes.map fun t =>
        if t.name == "counter" then { t with methods := t.methods ++ [{ name := "clear", params := [], returns := none }] } else t }
      >>= Externs.bind)
    "methods"
  checkError "a constructor argument must fit"
    (Index.build { externProgram with externInstances := externProgram.externInstances.map fun i =>
        if i.name == "k" then { i with args := [.bits 8 2] } else i }
      >>= Externs.bind)
    "does not fit"

def interpTests : T Unit := do
  arithmeticTests
  castTests
  sliceAndConcatTests
  equalityTests
  stackTests
  extractTests
  selectTests
  stackParserTests
  subParserTests
  deparserTests
  tableTests
  controlTests
  externTests
