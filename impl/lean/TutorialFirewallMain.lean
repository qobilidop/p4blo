import P4blo.TutorialFirewall
import P4bloIR.Json
import P4bloIR.Observe
import P4bloIR.Hex

/-! A fixed authored Program, not a wrapper that reads a golden or caller Program.
The extern state returned by each public API call persists for the next request. -/

open P4bloIR P4bloArch

private def request (line : String) : Except String (Entries × Nat × ByteArray) := do
  let json ← Lean.Json.parse line
  let entries ← match ← Decode.get? "" json "entries" with
    | none => pure { tables := [] }
    | some entries => Entries.decode "entries" entries
  let port ← Decode.uint32Field "" json "ingress_port"
  let packet ← hexToBytes? (← Decode.strField "" json "packet")
  pure (entries, port, packet)

private def response (outcome : Except String SwitchResult) (externs : Externs) : String :=
  (match outcome with
  | .error message => Lean.Json.mkObj [("error", .str message), ("state", externs.observe)]
  | .ok result => Lean.Json.mkObj (
      [("outputs", Lean.Json.arr (result.outputs.map fun ((port, packet) : Nat × ByteArray) =>
        Lean.Json.arr #[Lean.toJson port, Lean.Json.str (bytesToHex packet)]).toArray),
       ("state", externs.observe)] ++
      (result.diagnostic.map fun message => ("diagnostic", Lean.Json.str message)).toList)).compress

private def serve : IO UInt32 := do
  let (sw, initial) ← IO.ofExcept (P4blo.prepareSwitch P4blo.TutorialFirewall.program 4)
  let stdin ← IO.getStdin
  let stdout ← IO.getStdout
  let mut externs := initial
  repeat
    let line ← stdin.getLine
    if line.isEmpty then break
    if line.trimAscii.isEmpty then continue
    let outcome := do
      let (entries, port, packet) ← request line
      P4blo.runSwitch sw externs entries port packet
    match outcome with
    | .ok (result, next) =>
      externs := next
      stdout.putStrLn (response (.ok result) externs)
    | .error message => stdout.putStrLn (response (.error message) externs)
    stdout.flush
  return 0

def main (args : List String) : IO UInt32 := do
  match args with
  | [] =>
    IO.println (Lean.toJson P4blo.TutorialFirewall.program).compress
    return 0
  | ["run"] => serve
  | _ =>
    IO.eprintln "usage: leanTutorialFirewall [run]"
    return 2
