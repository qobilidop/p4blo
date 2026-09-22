# Semantics

The closed behaviors: everything P4 leaves open or target-defined that
p4blo closes, each with its choice. Until the Lean interpreter exists
this file is the normative meaning together with the Python
interpreter, which is provisional. After that the Lean interpreter is
normative and this file is commentary on it.

A behavior is added here before it is implemented, and a divergence
between interpreters that turns out to be an unlisted open behavior is
resolved by adding it here, not by patching one side.

Status: skeleton. Each entry is filled in during step 1.

## Values

- **Arithmetic overflow on `bit<N>`.** To be decided in step 1.
  Expected choice: wrapping modulo 2^N, as the P4 specification
  requires for unsigned types.
- **Shifts by the width or more.** To be decided in step 1.
- **Explicit casts between widths.** Truncation and zero extension; to
  be stated precisely in step 1.

## Headers

- **Reading a field of an invalid header.** To be decided in step 1.
- **Header-stack index out of range.** To be decided in step 1.
- **Push and pop beyond the stack size.** To be decided in step 1.

## Parsers

- **Extraction past the packet end.** A parse error; the error value
  is `PacketTooShort`.
- **Parser loop bound.** The no-consumption revisit rule: a state that
  has consumed no bits since it was last entered may not be entered
  again, and doing so is a parse error. Decided in the design doc.
- **`verify` failure.** A parse error carrying the given error value.

## Tables

- **Table miss.** The default action runs.
- **LPM tie-breaking.** To be decided in step 1. Expected choice: the
  longest prefix wins; equal prefixes are a validator error at entry
  installation.
- **Ternary tie-breaking.** To be decided in step 1. Expected choice:
  the highest priority wins; equal priorities are an installation
  error.

## Deparsers

- **Emit of an invalid header.** Emits nothing.
