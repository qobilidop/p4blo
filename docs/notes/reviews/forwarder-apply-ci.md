# Forwarder application BMv2 selection

Review: CLEAR for the narrow workflow/documentation addition.

Read the pending main diff in `.github/workflows/oracle-bmv2.yml` and
`docs/workflows.md`, the exact selected test, and its fixture dependencies.
The dedicated workflow explicitly selects
`tests/test_lean_forwarder_apply.py::test_apply_packets_bmv2`; the earlier
corpus/CRC/firewall selectors do not discover this new profile. All earlier
steps remain unchanged. The added availability preflight asserts failure
rather than silently skipping when the image is unavailable at that check.
It uses the same default-image resolution as the selected test and follows
the existing image build/load step.

An independent `pytest --setup-plan` on the exact node exited 0 and selected
only tmp_path/tmp_path_factory/request fixtures. It does not request
lean_binary, the module's Lean exporter fixtures, or any native compilation.
No test execution, Docker operation, image build, or main rebuild was performed
by this reviewer. The profile itself requires exactly five passing verdicts:
both overlapping-route orders plus drop, NoAction and forwarding defaults.
The source test's optional local skip remains unchanged; this patch adds the
dedicated CI preflight rather than a general no-skip mechanism.

Workflow actionlint and the actual profile run are root-owned checks, not
independent executions claimed by this report. The documentation correctly
distinguishes this explicit oracle profile from Lean conformance coverage.
