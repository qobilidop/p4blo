import P4bloIRTest.CodecLaws
import P4bloIRTest.DeclarationCodec
import P4bloIRTest.TableCodec
import P4bloIRTest.ParserCodec
import P4bloIRTest.BlockCodec
import P4bloIRTest.ProgramCodec
import P4bloIRTest.EntriesCodec

open Lean

/-- A test executable, not a new production wire protocol. -/
def main (args : List String) : IO Unit := do
  if args == ["--self-test"] then
    let (_, failed) ← CodecLawTests.tests.run []
    if !failed.isEmpty then throw (IO.userError s!"codec tests failed: {failed}")
    let (_, failed) ← DeclarationCodecTests.tests.run []
    if !failed.isEmpty then throw (IO.userError s!"declaration codec tests failed: {failed}")
    let (_, failed) ← TableCodecTests.tests.run []
    if !failed.isEmpty then throw (IO.userError s!"table codec tests failed: {failed}")
    let (_, failed) ← ParserCodecTests.tests.run []
    if !failed.isEmpty then throw (IO.userError s!"parser codec tests failed: {failed}")
    let (_, failed) ← BlockCodecTests.tests.run []
    if !failed.isEmpty then throw (IO.userError s!"block codec tests failed: {failed}")
    let (_, failed) ← ProgramCodecTests.tests.run []
    if !failed.isEmpty then throw (IO.userError s!"program codec tests failed: {failed}")
    let (_, failed) ← EntriesCodecTests.tests.run []
    if !failed.isEmpty then throw (IO.userError s!"entries codec tests failed: {failed}")
    return
  if !args.isEmpty then throw (IO.userError "usage: codec-leaves [--self-test]")
  let stdin ← IO.getStdin
  let stdout ← IO.getStdout
  repeat
    let line ← stdin.getLine
    if line.isEmpty then break
    let result := do EntriesCodecTests.reply (← Json.parse line)
    let response := match result with
      | .ok value => value
      | .error error => Json.mkObj [("error", .str error)]
    stdout.putStrLn response.compress
    stdout.flush
