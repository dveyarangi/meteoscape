# Mechanism: edge
"""Reading a live edge record and its sidecars, and saying whether each keeps the format's shape."""

from __future__ import annotations

import contextlib
import io
import json
import unittest

from repository import RepositoryCase

import edges

RECORD = "docs/edge/hosts.md"
SIDECAR = "docs/edge/hosts/alpha.md"
VALIDATOR = ".agents/scripts/gw/test/test_something.py"

CONTRACT = "## Contract\n\nWhat a host is owed and owes.\n\n"
INVARIANTS = (
    "## Invariants\n\n"
    f"- A hook never fails the host — *validated by:* `{VALIDATOR}`\n"
    "- The wake arrives first — *validated by:* live — **Wake**\n\n"
)
EXTENDING = (
    "## Extending\n\n"
    "1. **Entry file** — the first reply opens with the contract line.\n"
    "2. **Wake** — the wake's read is in context before the first command.\n\n"
)
EXTENSIONS = (
    "## Extensions\n\n"
    "| extension | standing | sidecar |\n"
    "|---|---|---|\n"
    "| Alpha | both observed | [alpha](hosts/alpha.md) |\n\n"
)
TAIL = "## Concerns\n\n- q-0001, read here as a host's.\n\n## Roadmap\n\n- More hosts.\n"


def record(
    status: str = "Stub",
    contract: str = CONTRACT,
    invariants: str = INVARIANTS,
    extending: str = EXTENDING,
    extensions: str = EXTENSIONS,
    tail: str = TAIL,
    title: str = "# Edge — Hosts",
) -> str:
    return f"{title}\n\n- **Status:** {status}\n\n{contract}{invariants}{extending}{extensions}{tail}"


def sidecar(
    conformance: str = (
        "- **Entry file** — observed 2026-10-02, version 1.2, the line opened the reply.\n"
        "- **Wake** — absent; the entry file's rule stands in.\n"
    ),
    title: str = "# Alpha — Hosts edge",
    integration: str = "## Integration\n\n- `.alpha/hooks.json`\n\n",
) -> str:
    return f"{title}\n\n{integration}## Conformance\n\n{conformance}"


class Records(RepositoryCase):
    """A tree with one edge record, one extension and its sidecar, all conforming."""

    def setUp(self) -> None:
        super().setUp()
        self.write(VALIDATOR, "")
        self.write(RECORD, record())
        self.write(SIDECAR, sidecar())

    def checked(self) -> edges.Checked:
        return edges.check(self.root)

    def problems(self) -> list[str]:
        return [note.problem for note in self.checked().diagnostics]

    def assertFlagged(self, fragment: str) -> None:
        problems = self.problems()
        self.assertTrue(any(fragment in problem for problem in problems), problems)


class AConformingTree(Records):
    def test_a_record_and_its_sidecar_in_shape_raise_nothing(self) -> None:
        checked = self.checked()
        self.assertEqual([], checked.diagnostics)
        self.assertEqual(["docs/edge/hosts.md"], [read.record for read in checked.records])

    def test_a_tree_with_no_edge_records_is_clean_and_says_it_read_none(self) -> None:
        (self.root / SIDECAR).unlink()
        (self.root / SIDECAR).parent.rmdir()
        (self.root / RECORD).unlink()
        checked = self.checked()
        self.assertEqual(([], [], []), (checked.records, checked.diagnostics, checked.skipped))

    def test_an_edge_nothing_attaches_to_needs_neither_extending_nor_extensions(self) -> None:
        (self.root / SIDECAR).unlink()
        (self.root / SIDECAR).parent.rmdir()
        only_tests = "## Invariants\n\n" f"- A hook never fails the host — *validated by:* `{VALIDATOR}`\n\n"
        self.write(RECORD, record(invariants=only_tests, extending="", extensions=""))
        self.assertEqual([], self.problems())


class TheRecord(Records):
    def test_a_title_not_naming_the_edge_is_flagged(self) -> None:
        self.write(RECORD, record(title="# Hosts"))
        self.assertFlagged("title")

    def test_a_missing_status_is_flagged(self) -> None:
        self.write(RECORD, record().replace("- **Status:** Stub\n\n", ""))
        self.assertFlagged("Status")

    def test_a_status_outside_the_vocabulary_is_flagged(self) -> None:
        self.write(RECORD, record(status="Draft"))
        self.assertFlagged("Status")

    def test_a_section_the_format_does_not_name_is_flagged(self) -> None:
        self.write(RECORD, record(tail=TAIL + "\n## History\n\nOnce.\n"))
        self.assertFlagged("History")

    def test_a_required_section_missing_is_flagged(self) -> None:
        self.write(RECORD, record(contract=""))
        self.assertFlagged("Contract")

    def test_sections_out_of_order_are_flagged(self) -> None:
        self.write(RECORD, record(contract=INVARIANTS, invariants=CONTRACT))
        self.assertFlagged("order")

    def test_a_numbered_line_of_extending_not_in_the_check_form_is_flagged(self) -> None:
        self.write(RECORD, record(extending=EXTENDING + "3. Nap — the agent sleeps.\n\n"))
        self.assertFlagged("check form")

    def test_a_heading_inside_a_fence_is_not_a_section(self) -> None:
        fenced = CONTRACT + "```md\n## History\n```\n\n"
        self.write(RECORD, record(contract=fenced))
        self.assertEqual([], self.problems())

    def test_extending_without_extensions_is_flagged(self) -> None:
        self.write(RECORD, record(extensions=""))
        self.assertFlagged("together")


class Invariants(Records):
    def test_a_promise_naming_no_validator_and_not_marked_unguarded_is_flagged(self) -> None:
        self.write(RECORD, record(invariants="## Invariants\n\n- A promise on its own.\n\n"))
        self.assertFlagged("validator")

    def test_an_unguarded_promise_is_legal_in_a_stub(self) -> None:
        self.write(RECORD, record(invariants="## Invariants\n\n- A promise — **⚠ unguarded**\n\n"))
        self.assertEqual([], self.problems())

    def test_an_unguarded_promise_in_a_normative_record_is_flagged(self) -> None:
        self.write(RECORD, record("Normative", invariants="## Invariants\n\n- A promise — **⚠ unguarded**\n\n"))
        self.assertFlagged("unguarded")

    def test_an_unguarded_promise_in_a_tentative_normative_record_is_flagged(self) -> None:
        unguarded = "## Invariants\n\n- A promise — **⚠ unguarded**\n\n"
        self.write(RECORD, record("Normative (tentative)", invariants=unguarded))
        self.assertFlagged("unguarded")

    def test_a_validator_path_that_does_not_exist_is_flagged(self) -> None:
        (self.root / VALIDATOR).unlink()
        self.assertFlagged(VALIDATOR)

    def test_a_validator_neither_a_path_nor_live_is_flagged(self) -> None:
        self.write(RECORD, record(invariants="## Invariants\n\n- A promise — *validated by:* someone\n\n"))
        self.assertFlagged("neither a backticked path")

    def test_a_validator_on_a_continuation_line_is_read(self) -> None:
        wrapped = "## Invariants\n\n- A promise — *validated by:*\n  `" + VALIDATOR + "`, its case\n\n"
        self.write(RECORD, record(invariants=wrapped))
        self.assertEqual([], self.problems())

    def test_a_missing_validator_on_a_continuation_line_is_flagged(self) -> None:
        wrapped = "## Invariants\n\n- A promise — *validated by:*\n  `tests/gone.py`\n\n"
        self.write(RECORD, record(invariants=wrapped))
        self.assertFlagged("`tests/gone.py` does not exist")

    def test_a_live_validator_naming_no_check_of_extending_is_flagged(self) -> None:
        self.write(RECORD, record(invariants="## Invariants\n\n- A promise — *validated by:* live — **Nap**\n\n"))
        self.assertFlagged("Nap")


class Extensions(Records):
    def test_a_row_whose_sidecar_does_not_exist_is_flagged(self) -> None:
        (self.root / SIDECAR).unlink()
        self.assertFlagged("hosts/alpha.md")

    def test_a_sidecar_no_row_names_is_flagged(self) -> None:
        self.write("docs/edge/hosts/beta.md", sidecar(title="# Beta — Hosts edge"))
        self.assertFlagged("beta.md")

    def test_two_rows_naming_one_sidecar_are_flagged(self) -> None:
        twice = EXTENSIONS.rstrip("\n") + "\n| Alpha again | the same | [alpha](hosts/alpha.md) |\n\n"
        self.write(RECORD, record(extensions=twice))
        self.assertFlagged("two rows")

    def test_a_sidecar_directory_with_no_record_is_flagged(self) -> None:
        self.write("docs/edge/orphan/one.md", sidecar(title="# One — Orphan edge"))
        self.assertFlagged("orphan")

    def test_an_extensions_table_with_other_columns_is_flagged(self) -> None:
        self.write(RECORD, record(extensions=EXTENSIONS.replace("| extension | standing | sidecar |", "| host | sidecar |")))
        self.assertFlagged("columns")


class Sidecars(Records):
    def test_a_sidecar_title_not_naming_its_extension_and_edge_is_flagged(self) -> None:
        self.write(SIDECAR, sidecar(title="# Alpha"))
        self.assertFlagged("title")

    def test_a_sidecar_missing_integration_is_flagged(self) -> None:
        self.write(SIDECAR, sidecar(integration=""))
        self.assertFlagged("Integration")

    def test_a_check_of_extending_missing_from_conformance_is_flagged(self) -> None:
        self.write(SIDECAR, sidecar(conformance="- **Entry file** — unobserved.\n"))
        self.assertFlagged("Wake")

    def test_a_conformance_bullet_naming_no_check_of_extending_is_flagged(self) -> None:
        self.write(SIDECAR, sidecar(conformance=(
            "- **Entry file** — unobserved.\n- **Wake** — unobserved.\n- **Nap** — unobserved.\n"
        )))
        self.assertFlagged("Nap")

    def test_a_result_opening_with_no_word_of_the_format_is_flagged(self) -> None:
        self.write(SIDECAR, sidecar(conformance="- **Entry file** — works.\n- **Wake** — unobserved.\n"))
        self.assertFlagged("the result opens with `works`")

    def test_a_sidecar_titled_for_another_edge_is_flagged(self) -> None:
        self.write(SIDECAR, sidecar(title="# Alpha — Plugins edge"))
        self.assertFlagged("— Hosts edge")

    def test_a_check_answered_twice_is_flagged(self) -> None:
        self.write(SIDECAR, sidecar(conformance=(
            "- **Entry file** — unobserved.\n- **Wake** — unobserved.\n- **Wake** — absent.\n"
        )))
        self.assertFlagged("twice")

    def test_a_result_word_followed_by_its_colon_is_read(self) -> None:
        self.write(SIDECAR, sidecar(conformance="- **Entry file** — documented: the docs.\n- **Wake** — absent: the rule.\n"))
        self.assertEqual([], self.problems())

    def test_an_observation_without_its_date_is_flagged(self) -> None:
        self.write(SIDECAR, sidecar(conformance="- **Entry file** — observed, fine.\n- **Wake** — unobserved.\n"))
        self.assertFlagged("date")


class TheCommandLine(Records):
    def run_main(self, *argv: str) -> tuple[int, str]:
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            status = edges.main(list(argv), self.root)
        return status, out.getvalue()

    def test_a_clean_tree_exits_zero_with_its_report(self) -> None:
        status, out = self.run_main("--check")
        self.assertEqual(0, status)
        self.assertEqual([], json.loads(out)["diagnostics"])

    def test_a_diagnostic_exits_one(self) -> None:
        self.write(RECORD, record(status="Draft"))
        self.assertEqual(1, self.run_main("--check")[0])

    def test_an_unreadable_record_is_skipped_and_fails_the_run(self) -> None:
        (self.root / RECORD).write_bytes(b"\xff\xfe\x00 not utf-8")
        status, out = self.run_main("--check")
        self.assertEqual(1, status)
        self.assertEqual([RECORD], [passed["record"] for passed in json.loads(out)["skipped"]])

    def test_a_bare_invocation_refuses(self) -> None:
        self.assertEqual(2, self.run_main()[0])


if __name__ == "__main__":
    unittest.main()
