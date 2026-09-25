import P4bloIR
import P4bloArch

/-!
The test log shared by the test modules: every check prints one line and
the failures are collected for the exit code.
-/

/-- A test log: failures so far. -/
abbrev T := StateT (List String) IO

/-- Record `name` as failed unless `ok`. -/
def check (name : String) (ok : Bool) : T Unit := do
  if ok then IO.println s!"ok   {name}"
  else
    IO.println s!"FAIL {name}"
    modify (· ++ [name])

/-- `check` that `r` succeeded and its value satisfies `p`; on failure the
value or the error is printed. -/
def checkOk [Repr α] (name : String) (r : Except String α) (p : α → Bool) : T Unit :=
  match r with
  | .ok v =>
    if p v then check name true
    else do
      IO.println s!"     got: {repr v}"
      check name false
  | .error e => do
    IO.println s!"     error: {e}"
    check name false

/-- `check` that an `Except` failed with a message containing `fragment`. -/
def checkError (name : String) (r : Except String α) (fragment : String) : T Unit :=
  match r with
  | .error e =>
    if (e.splitOn fragment).length > 1 then check name true
    else do
      IO.println s!"     got: {e}"
      check name false
  | .ok _ => check s!"{name} (unexpectedly succeeded)" false
