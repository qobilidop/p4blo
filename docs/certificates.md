# Execution-claim checker experiment

This is a deliberately narrow prototype, not a general Python verifier.
`ExecutionCertificate.check_sound` proves that an accepted observation
equals the actual Lean execution result for the supplied initial machine.
The checker reexecutes the machine with a budget; exhaustion is not a
language error. The theorem is kernel-checked and covered by `ProofAudit`.
Running the compiled checker additionally trusts the compiler, runtime,
wire codecs and observation adapter. A JSON artifact is not a kernel proof.

## Fixed experiment and binding

`ExecutionCertificate.Example.program` is a standalone control fragment:
read register `r[0]`, increment its bit<8> value, write it back, and increment
counter `k[0]`. Initial register/counter values are supplied; all other
initial machine fields are fixed by `Example.initial`. The observation
includes completion kind/message, register width/cells, counter cells and
the local value's width/value. It does not expose every final machine field.
This fixture is indexed and bound directly, not loaded as a complete switch
program or claimed to satisfy whole-program validation.

The executable modes are:

```
lean/.lake/build/bin/p4blo-lean certificate-example-program
lean/.lake/build/bin/p4blo-lean check-example-certificate artifact.json
```

The second mode also accepts `-` for stdin. Exit 0 means `accepted`; exit 1
means `mismatch` or `exhausted`; exit 2 means invalid input. Verdicts/errors
are JSON objects. The artifact includes the complete program as protobuf
JSON, not just its name. The decoded AST must equal the fixed example.
Exporting common syntax does not share evaluation algorithms with Python.

Version 1 has `format: "p4blo.example-certificate"`,
`example: "register-counter-v1"`, numeric `version: 1`, `program`, `initial`
as `[register, counter]`, nonnegative numeric `fuel`, and `claim`.
Naturals in initial values and observations use canonical lowercase `0x`
hexadecimal strings, including `0x0`; widths and fuel are JSON numbers.
The claim has `completion` (a tagged object), `register` (width/cells pair),
`counter` (cells), and `local` (width/value pair). State fields can be null
to represent absence, but absence does not match the normal fixture.
Fuel 10 suffices for this fixed program; 9 exhausts the checker.

## Create a claim from production Python

Build Lean first, then run from the repository root inside the flake:

```
uv run python -m p4blo.drt.certificate create --register 41 --counter 9 -o claim.json
uv run python -m p4blo.drt.certificate verify claim.json
```

Creation alone does **not** mean acceptance. The second command must report
`{"verdict": "accepted"}` and exit 0. `--fuel 9` produces a well-formed claim
whose check exhausts. Register 255 exercises wraparound. Integers may be
given in decimal or `0x` hex. Both modes accept `--lean` and `--timeout`;
`-` means stdout for creation or stdin for verification.

The Python adapter decodes the exported program unchanged, builds its own
index and extern bindings, initializes its production environment, seeds
the two cells, and invokes `p4blo.interp.stmt.execute`. It reads the actual
resulting state and completion status, rather than computing a second
expected-answer algorithm. The checker independently reruns Lean from the
bound initial machine. Malformed or contradictory checker replies and
timeouts fail closed; POSIX subprocesses use an owned process group.

`tests/test_drt_certificate.py` exercises wraparound and large counters,
tampered program/initial/result fields, missing fields, insufficient budgets,
CLI verdicts, malformed peers and descendant-held pipes. Suppressing Python's
counter update produces a rejected claim. The exported-zero regression
also guards a real encoder defect discovered while building this adapter.

## Remaining obligations

- Generalize initial machines and program coverage only with explicit
  validation and observation contracts.
- Do not present finite accepted runs as universal implementation
  equivalence, a termination proof, or proof of unobserved state equality.
