# State-only diagnostics review

2026-09-23, independent read-only review of `5743625`.

Wide hexadecimal values, absent instances as null, and replay rendering
were correct. The two new tests passed. One confirmed gap remained:
`show` assembled the diagnostic inside an STF header and discarded it if
STF conversion failed. An empty packet therefore lost its differing state
and printed only the unsupported-STF message. Non-STF action data followed
the same path.

Fix: print the diagnostic header in the conversion-error branch too. Extend
the two-CLI regression to an empty packet, requiring both the state values
and the STF limitation to remain visible. No change to comparison semantics.
