import Tests.CodecLaws
import Tests.DeclarationCodec

open Lean

/-- A test executable, not a new production wire protocol. -/
def main (args : List String) : IO Unit := do
  if args == ["--self-test"] then
    let (_, failed) ← CodecLawTests.tests.run []
    if !failed.isEmpty then throw (IO.userError s!"codec tests failed: {failed}")
    let (_, failed) ← DeclarationCodecTests.tests.run []
    if !failed.isEmpty then throw (IO.userError s!"declaration codec tests failed: {failed}")
    return
  if !args.isEmpty then throw (IO.userError "usage: codec-leaves [--self-test]")
  let stdin ← IO.getStdin
  let stdout ← IO.getStdout
  repeat
    let line ← stdin.getLine
    if line.isEmpty then break
    let result := do DeclarationCodecTests.reply (← Json.parse line)
    let response := match result with
      | .ok value => value
      | .error error => Json.mkObj [("error", .str error)]
    stdout.putStrLn response.compress
    stdout.flush
