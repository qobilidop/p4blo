import P4blo.FieldCommandExamples
import P4blo.ScalarCommandExamples

namespace P4blo.CommandBlockTests

open Fields FieldCommandExamples
open scoped Scalar

def statements : List (Cmd modes) :=
  [Cmd.assign scratch bits[8, 10],
   Cmd.ite (.read routeHit)
     (Cmd.block [Cmd.assign scratch (scratch.read + bits[8, 1])])
     (Cmd.block [Cmd.assign scratch (scratch.read + bits[8, 2])]),
   Cmd.assign scratch (scratch.read + bits[8, 3])]

example : (Cmd.block ([] : List (Cmd modes))).lower = [] := rfl

example (cmd : Cmd modes) : Cmd.block [cmd] = cmd :=
  Scalar.CmdWith.block_singleton cmd

-- Exact previous authored ASTs, not merely equivalent selected outputs.
example : dependent =
    (Cmd.assign ttl (ttl.read + bits[8, 1])).seq
    ((Cmd.assign protocol (ttl.read + protocol.read)).seq
    ((Cmd.ite (ttl.read === bits[8, 0])
      ((Cmd.assign port (.read routePort)).seq (Cmd.assign drop (.boolean true)))
      ((Cmd.assign port (port.read + bits[9, 1])).seq (Cmd.assign drop (.boolean false)))).seq
      (Cmd.assign scratch ttl.read))) := rfl

example : forward =
    (let reject := Cmd.assign drop (.boolean true)
     let rewrite := (Cmd.assign dst (.read routeDst)).seq
       ((Cmd.assign src (.read routeSrc)).seq
       ((Cmd.assign ttl (ttl.read + bits[8, 255])).seq
       ((Cmd.assign port (.read routePort)).seq (Cmd.assign drop (.boolean false)))))
     Cmd.ite (.read routeHit)
       (Cmd.ite (ttl.read === bits[8, 0]) reject
         (Cmd.ite (ttl.read === bits[8, 1]) reject rewrite)) reject) := rfl

-- This independent syntax anchor fixes statement/branch-tail order without
-- obtaining expected statements by calling the block implementation.
example : (Cmd.block statements).lower =
    [P4bloIR.Stmt.assign (.var "scratch") (.literal (.bits 8 10)),
     .conditional (.member (.var "route") "hit")
       [.assign (.var "scratch") (.binary .add (.var "scratch") (.literal (.bits 8 1)))]
       [.assign (.var "scratch") (.binary .add (.var "scratch") (.literal (.bits 8 2)))],
     .assign (.var "scratch") (.binary .add (.var "scratch") (.literal (.bits 8 3)))] := rfl

def run : IO Unit := do
  for (hit, expected) in [(true, 14), (false, 15)] do
    let source := store 64 false true hit
    let command := Cmd.block statements
    unless (scratch.ref.get (command.denote source)).val == expected do
      throw (IO.userError "command list source order/branch tail")
    -- Confirm the examples distinguish the two intentional list faults,
    -- independently of which compositional proof first rejects them.
    unless (scratch.ref.get ((Cmd.block statements.reverse).denote source)).val == 10 do
      throw (IO.userError "reversed command list negative control")
    unless (scratch.ref.get ((Cmd.block statements.tail).denote source)).val ==
        (if hit then 23 else 24) do
      throw (IO.userError "skipped first command negative control")
    let (result, final) := (P4bloIR.execute command.lower).run (initial source)
    match result with
    | .error _ => throw (IO.userError "command list actual execution")
    | .ok () => pure ()
    match final.frame.read? "scratch" with
    | some (.bits value) =>
      unless value.width == 8 && value.value == expected do
        throw (IO.userError "command list actual order/branch tail")
    | _ => throw (IO.userError "command list scratch type")
    for name in ["hdr", "meta", "route", "outside"] do
      unless final.frame.read? name == (initial source).frame.read? name do
        throw (IO.userError s!"command list preserved root {name}")
  IO.println "Command list order, both branches, shared tails and preserved roots passed"

end P4blo.CommandBlockTests
