"""tcp-flow-policy-v1: independent Bloom model over shrinking flow sequences."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from hypothesis import given, settings

from p4blo.drt.case import Case
from p4blo.drt.replay import load, save
from p4blo.drt.run import (
    Report,
)
from tests.oracles import firewall as original
from tests.oracles.bmv2 import run as bmv2
from tests.programs.corpus.tutorial_firewall.tutorial_firewall import build
from tests.support.firewall import (
    SENTINEL_OUTPUT,
    assert_original_observations,
    observation_plan,
)
from tests.support.firewall_generated import (
    Event,
    Policy,
    campaigns,
    check_hash_reference,
    check_lean,
    check_python,
    complete_state,
    entries,
    failure_path,
    model,
    oracle_sample,
    targeted,
)
from tests.support.firewall_generated import (
    original_bmv2 as original_bmv2,
)


def test_reference_hash_known_answers() -> None:
    check_hash_reference()


def test_model_named_witnesses() -> None:
    scenarios = targeted()
    assert [bool(item.outputs) for item in model(scenarios["bloom-false-positive"])] == [
        False,
        True,
        False,
        True,
        True,
    ]
    changes = model(scenarios["host-policy-changes"])
    assert [bool(item.outputs) for item in changes] == [
        True,
        False,
        True,
        True,
        True,
        True,
        True,
        False,
    ]
    assert [sum(sum(obs.values) for obs in item.state) for item in changes] == [
        0,
        0,
        2,
        2,
        2,
        4,
        4,
        4,
    ]
    missing = model(scenarios["missing-direction-syn"])[0]
    assert missing.outputs and missing.state == complete_state((set(), set()))


def test_replay_identity_preserves_policy_and_sequence(tmp_path: Path) -> None:
    program = build()
    events = targeted()["host-policy-changes"]
    cases = tuple(item.case for item in model(events))
    report = Report(program.name, 0, 4, inputs=cases, program_ir=program)
    path = failure_path(report, tmp_path)
    save(report, path)
    restored, inputs, ports, seed = load(path)
    assert restored == program and inputs == list(cases) and (ports, seed) == (4, 0)
    shorter = Report(program.name, 0, 4, inputs=cases[:-1], program_ir=program)
    assert failure_path(shorter, tmp_path) != path
    # Same packet bytes/ports, different host snapshot: a distinct experiment.
    changed = list(cases)
    changed[0] = Case(entries(Policy()), cases[0].ingress_port, cases[0].packet)
    changed_report = Report(program.name, 0, 4, inputs=tuple(changed), program_ir=program)
    assert failure_path(changed_report, tmp_path) != path


@pytest.mark.parametrize("events", targeted().values(), ids=targeted())
def test_generated_profile_known_answers(events: list[Event]) -> None:
    check_python(model(events))


@settings(max_examples=40, deadline=None, derandomize=True)
@given(events=campaigns())
def test_generated_profile_shrinks_valid_configurations(events: list[Event]) -> None:
    check_python(model(events))


@pytest.mark.parametrize("events", targeted().values(), ids=targeted())
def test_lean_agrees_on_targeted_flow_policies(lean_binary: Path, events: list[Event]) -> None:
    check_lean(events, lean_binary)


@settings(max_examples=40, deadline=None, derandomize=True)
@given(events=campaigns())
def test_lean_agrees_on_shrinking_flow_policies(lean_binary: Path, events: list[Event]) -> None:
    check_lean(events, lean_binary)


@pytest.mark.parametrize(
    "events",
    [
        oracle_sample(20260923, False),
        oracle_sample(20260924, True),
        targeted()["missing-direction-syn"],
    ],
    ids=["seed-20260923", "seed-20260924-swapped", "missing-direction-syn"],
)
def test_generated_original_prefixes_on_bmv2(
    original_bmv2: tuple[str, bmv2.Compiled], events: list[Event]
) -> None:
    image, compiled = original_bmv2
    sequence = model(events)
    policy = events[0].policy
    assert all(event.policy == policy for event in events)
    commands = list(original.COMMANDS[:2])
    for ingress, egress, direction in [(1, 2, policy.outbound), (2, 1, policy.inbound)]:
        if direction is not None:
            commands.append(
                f"table_add MyIngress.check_ports MyIngress.set_direction {ingress} {egress} "
                f"=> {direction}"
            )
    plan = observation_plan(sequence)
    for phase in plan.phases:
        phase.commands = commands
    request = plan.request(compiled)
    for phase in request["phases"]:
        phase["post_commands"] = [
            "register_read MyIngress.bloom_filter_1",
            "register_read MyIngress.bloom_filter_2",
        ]
        phase["completion_packet"] = {"port": 2, "data": SENTINEL_OUTPUT.hex()}
    reply = bmv2._driver(image, "replay", json.dumps(request))
    assert_original_observations(sequence, plan, reply)
