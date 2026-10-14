# Mechanism: maintain
"""Which mechanisms are due for a re-check, and the marks only a maintenance writes."""

from __future__ import annotations

import contextlib
import io
import json
import unittest
from datetime import date

from repository import RepositoryCase

import inject_rules
import maintain

MARKS = "docs/mechanisms/maintenance.md"
SHAPE_SKILL = ".agents/skills/mechanism/SKILL.md"
SHAPE_RULES = ".agents/mechanisms/mechanism-shape/mechanism-shape.rules.md"
SAMPLE_DOC = ".agents/mechanisms/sample/sample.md"
SAMPLE_RULES = ".agents/mechanisms/sample/sample.rules.md"
SAMPLE_SKILL = ".agents/skills/sample/SKILL.md"
SAMPLE_SHELF = ".agents/skills/sample/SAMPLE-FORMAT.md"
SAMPLE_SCRIPT = ".agents/scripts/gw/sample.py"
SHAPE_DOC = ".agents/mechanisms/mechanism-shape/mechanism-shape.md"
SHAPE_TOOL = ".agents/scripts/gw/shape_tool.py"
ORIGIN_ENTRY = "# Entry\n\nEntry contract: v1, 2026-09-27.\n\n## General rules\n\n- Be clear.\n"
WHY_PARTS = "a part it owns moved since its mark"
WHY_OUTPUT = "what governs its records or its instructions moved since its mark"


def declaration(slug: str, instruction: str, parts: tuple[str, ...] = (), relied_on: tuple[str, ...] = ()) -> str:
    """A doc as far as the clock reads one: its title, its instruction bullet, and the two tables
    naming the files it owns and the files it only relies on."""
    owned = "".join(f"| a part | `{where}` |\n" for where in parts)
    borrowed = "".join(f"| a part | `{where}` | mechanism-shape |\n" for where in relied_on)
    return (
        f"# {slug} — what it is\n\n- **instruction** `{instruction}` — the act\n- **state** installed\n\n"
        f"## Install adds, uninstall removes\n\n| part | where |\n|---|---|\n{owned}\n"
        f"## Relies on, and does not own\n\n| part | where | owner |\n|---|---|---|\n{borrowed}"
    )


class Clocked(RepositoryCase):
    """A tree with the mechanism shape and one other mechanism, each with a skill, rules and the
    parts it owns; the sample relies on a tool of the shape's it does not own."""

    def setUp(self) -> None:
        super().setUp()
        self.write("AGENTS.md", ORIGIN_ENTRY)
        self.write(SHAPE_DOC, declaration("mechanism-shape", SHAPE_SKILL, parts=(SHAPE_SKILL, SHAPE_RULES, SHAPE_TOOL)))
        self.write(SHAPE_RULES, "# mechanism-shape — rules\n\n## R1 — a rule\n")
        self.write(SHAPE_SKILL, "# Mechanism\n\nThe shape.\n")
        self.write(SHAPE_TOOL, "print('the shape')\n")
        self.write(SAMPLE_DOC, declaration("sample", SAMPLE_SKILL,
                                           parts=(SAMPLE_DOC, SAMPLE_SKILL, SAMPLE_SHELF, SAMPLE_RULES, SAMPLE_SCRIPT),
                                           relied_on=(SHAPE_TOOL,)))
        self.write(SAMPLE_RULES, "# sample — rules\n\n## S1 — a rule\n")
        self.write(SAMPLE_SKILL, "# Sample\n\nThe act.\n")
        self.write(SAMPLE_SHELF, "# Sample format\n\nA record has a title.\n")
        self.write(SAMPLE_SCRIPT, "print('sample')\n")

    def run_maintain(self, *argv: str, today: str = "2026-09-27") -> tuple[int, dict]:
        printed = io.StringIO()
        with contextlib.redirect_stdout(printed):
            status = maintain.main(list(argv), self.root, date.fromisoformat(today))
        return status, json.loads(printed.getvalue())

    def states(self, report: dict) -> dict[tuple[str, str], str]:
        return {(row["mechanism"], row["level"]): row["state"] for row in report["mechanisms"]}

    def mark_every_level(self) -> None:
        for mechanism in ("mechanism-shape", "sample"):
            for level in ("parts", "output"):
                self.run_maintain("--mark", mechanism, level, "nothing to change")

    def due(self) -> dict[tuple[str, str], str]:
        _, report = self.run_maintain("--check")
        return {(row["mechanism"], row["level"]): row["why"]
                for row in report["mechanisms"] if row["state"] == "due"}

    def standing(self, mechanism: str, level: str) -> dict:
        _, report = self.run_maintain("--check")
        return next(row for row in report["mechanisms"] if (row["mechanism"], row["level"]) == (mechanism, level))

    def mark_rows(self) -> list[str]:
        """The rows of the marks' first table, the one a level's standing is decided by."""
        lines = self.read(MARKS).splitlines()
        rows = []
        for line in lines[lines.index("| mechanism | level | fingerprint | date | outcome |") + 2:]:
            if not line.startswith("|"):
                break
            rows.append(line)
        return rows


class NoMarks(Clocked):
    def test_every_mechanism_is_never_maintained_at_both_levels_and_nothing_fails(self) -> None:
        status, report = self.run_maintain("--check")

        self.assertEqual(0, status)
        self.assertEqual(
            {
                ("mechanism-shape", "parts"): "never maintained",
                ("mechanism-shape", "output"): "never maintained",
                ("sample", "parts"): "never maintained",
                ("sample", "output"): "never maintained",
            },
            self.states(report),
        )
        self.assertEqual([], report["diagnostics"])


class ABareInvocation(Clocked):
    def test_names_the_two_modes_and_exits_two(self) -> None:
        for argv in ([], ["--mark", "sample"], ["--check", "extra"]):
            with self.subTest(argv=argv):
                printed = io.StringIO()
                with contextlib.redirect_stdout(printed):
                    status = maintain.main(argv, self.root)

                self.assertEqual(2, status)
                self.assertIn("--check | --mark <mechanism> <level> <outcome>", printed.getvalue())


class AMark(Clocked):
    def test_makes_that_level_current_and_leaves_the_others_as_they_were(self) -> None:
        status, _ = self.run_maintain("--mark", "sample", "output", "amended")
        self.assertEqual(0, status)

        _, report = self.run_maintain("--check")

        states = self.states(report)
        self.assertEqual("current", states[("sample", "output")])
        self.assertEqual("never maintained", states[("sample", "parts")])
        self.assertEqual("never maintained", states[("mechanism-shape", "output")])

    def test_may_say_the_thing_was_repaired_to_the_record(self) -> None:
        status, report = self.run_maintain("--mark", "sample", "parts", "repaired")

        self.assertEqual(0, status, report)
        self.assertIn("| sample | parts |", report["marked"])
        self.assertTrue(report["marked"].endswith("| repaired |"), report["marked"])

    def test_is_one_row_holding_what_was_checked_the_date_and_the_outcome(self) -> None:
        self.run_maintain("--mark", "sample", "output", "nothing to change", today="2026-09-27")

        rows = [line for line in self.mark_rows() if line.startswith("| sample")]

        self.assertEqual(1, len(rows))
        cells = [cell.strip() for cell in rows[0].strip("|").split("|")]
        self.assertEqual(["sample", "output"], cells[:2])
        self.assertRegex(cells[2], r"^[0-9a-f]{64}$")
        self.assertEqual(["2026-09-27", "nothing to change"], cells[3:])

    def test_rows_stand_sorted_by_mechanism_then_level_whatever_order_they_were_marked_in(self) -> None:
        for mechanism, level in (("sample", "output"), ("mechanism-shape", "output"),
                                 ("sample", "parts"), ("mechanism-shape", "parts")):
            self.run_maintain("--mark", mechanism, level, "amended")

        rows = [line.split("|")[1:3] for line in self.mark_rows()]

        self.assertEqual(
            [["mechanism-shape", "parts"], ["mechanism-shape", "output"], ["sample", "parts"], ["sample", "output"]],
            [[cell.strip() for cell in row] for row in rows],
        )


class AfterEveryLevelIsMarked(Clocked):
    """Each test moves one thing and names what fell due, and why."""

    def setUp(self) -> None:
        super().setUp()
        self.mark_every_level()

    def append(self, name: str, text: str) -> None:
        self.write(name, self.read(name) + text)

    def test_nothing_moved_is_nothing_due(self) -> None:
        self.assertEqual({}, self.due())

    def test_a_part_a_mechanism_owns_moving_makes_its_doc_alone_due_naming_the_part(self) -> None:
        self.append(SAMPLE_SCRIPT, "print('more')\n")

        self.assertEqual({("sample", "parts"): WHY_PARTS}, self.due())
        self.assertEqual([SAMPLE_SCRIPT], self.standing("sample", "parts")["moved"])

    def test_a_part_a_mechanism_relies_on_moving_is_its_owner_s_doc_to_notice(self) -> None:
        self.append(SHAPE_TOOL, "print('more')\n")

        self.assertEqual({("mechanism-shape", "parts"): WHY_PARTS}, self.due())

    def test_a_mechanism_s_own_doc_moving_makes_its_records_due_and_never_the_doc_itself(self) -> None:
        self.append(SAMPLE_DOC, "\nMore about it.\n")

        self.assertEqual({("sample", "output"): WHY_OUTPUT}, self.due())

    def test_a_mechanism_s_rules_file_skill_or_shelf_moving_makes_its_doc_and_its_records_due(self) -> None:
        for moved in (SAMPLE_RULES, SAMPLE_SKILL, SAMPLE_SHELF):
            with self.subTest(moved=moved):
                before = self.read(moved)
                self.append(moved, "One more line.\n")

                self.assertEqual({("sample", "parts"): WHY_PARTS, ("sample", "output"): WHY_OUTPUT}, self.due())
                self.write(moved, before)

    def test_the_shape_s_doc_rules_file_or_skill_moving_makes_every_mechanism_s_output_due_one_row_each(self) -> None:
        """Every mechanism's doc and skill are the shape's outputs, read against it one mechanism
        at a time in that mechanism's own row (the user, 2026-10-11)."""
        for moved, shape_parts_too in ((SHAPE_DOC, False), (SHAPE_RULES, True), (SHAPE_SKILL, True)):
            with self.subTest(moved=moved):
                before = self.read(moved)
                self.append(moved, "A new meta-rule.\n")

                expected = {("mechanism-shape", "output"): WHY_OUTPUT, ("sample", "output"): WHY_OUTPUT}
                if shape_parts_too:
                    expected[("mechanism-shape", "parts")] = WHY_PARTS
                self.assertEqual(expected, self.due())
                self.assertEqual([moved], self.standing("sample", "output")["moved"])
                self.write(moved, before)

    def test_the_entry_file_moving_makes_nothing_due(self) -> None:
        """A meta-principle every session reads governs no doc in particular; the mechanism whose
        part the entry file is watches it at `parts` (the user, 2026-10-11)."""
        self.append("AGENTS.md", "- Be brief.\n")

        self.assertEqual({}, self.due())

    def test_evidence_moving_makes_nothing_due(self) -> None:
        self.write("docs/mechanisms/sample.evidence.md", "# Why sample is what it is\n")
        self.write(".agents/skills/sample/EVIDENCE.md", "# What was tried\n")

        self.assertEqual({}, self.due())

    def test_line_endings_flipping_make_nothing_due(self) -> None:
        for name in ("AGENTS.md", SHAPE_SKILL, SAMPLE_DOC, SAMPLE_SHELF):
            self.write(name, self.read(name).replace("\n", "\r\n"))

        self.assertEqual({}, self.due())


class ADueLevelNamesWhatChanged(Clocked):
    """A mark keeps each file it was checked against, so a level falling due says which files to
    read rather than leaving the re-check to guess (the user, 2026-10-11)."""

    def setUp(self) -> None:
        super().setUp()
        self.mark_every_level()

    def test_a_file_that_moved_is_named_and_no_other(self) -> None:
        self.write(SAMPLE_SHELF, self.read(SAMPLE_SHELF) + "And a date.\n")

        standing = self.standing("sample", "output")

        self.assertEqual("due", standing["state"])
        self.assertEqual([SAMPLE_SHELF], standing["moved"])
        self.assertNotIn("added", standing)
        self.assertNotIn("gone", standing)

    def test_a_file_added_beside_the_skill_is_named_as_added(self) -> None:
        self.write(".agents/skills/sample/QUEUE-ARRIVAL.md", "# A fresh queue\n")

        standing = self.standing("sample", "output")

        self.assertEqual([".agents/skills/sample/QUEUE-ARRIVAL.md"], standing["added"])
        self.assertNotIn("moved", standing)

    def test_a_file_that_went_is_named_as_gone(self) -> None:
        (self.root / SAMPLE_SHELF).unlink()

        standing = self.standing("sample", "output")

        self.assertEqual([SAMPLE_SHELF], standing["gone"])
        self.assertNotIn("moved", standing)

    def test_a_current_level_names_nothing(self) -> None:
        standing = self.standing("sample", "output")

        self.assertEqual("current", standing["state"])
        self.assertEqual({"mechanism", "level", "state", "why"}, set(standing))


class AScriptAmongTheParts(Clocked):
    """A script or a test is read as written: the installer writes blocks into markdown alone, so
    its tag in a script's text is the script's own words, never a block to take back out."""

    def test_quoting_the_installer_s_tag_twice_reads_clean_and_is_named_when_it_moves(self) -> None:
        self.write(SAMPLE_SCRIPT, 'A = \'<installed by="sample">\'\nB = \'<installed by="sample">\'\n')
        self.mark_every_level()

        status, report = self.run_maintain("--check")
        self.assertEqual(0, status, report["diagnostics"])
        self.assertEqual([], report["diagnostics"])

        self.write(SAMPLE_SCRIPT, self.read(SAMPLE_SCRIPT) + "C = 3\n")
        self.assertEqual([SAMPLE_SCRIPT], self.standing("sample", "parts")["moved"])


class AMarkWrittenBeforeFilesWereKept(Clocked):
    """A marks file holding the first table alone, as every one did before a mark kept its files."""

    def setUp(self) -> None:
        super().setUp()
        self.mark_every_level()
        text = self.read(MARKS)
        self.write(MARKS, text[: text.index("| mechanism | level | file | fingerprint |")].rstrip("\n") + "\n")

    def test_reads_clean_and_current_while_nothing_moved(self) -> None:
        status, report = self.run_maintain("--check")

        self.assertEqual(0, status)
        self.assertEqual([], report["diagnostics"])
        self.assertEqual({"current"}, set(self.states(report).values()))

    def test_falls_due_naming_no_file_and_saying_why(self) -> None:
        self.write(SAMPLE_SHELF, self.read(SAMPLE_SHELF) + "And a date.\n")

        standing = self.standing("sample", "output")

        self.assertEqual("due", standing["state"])
        self.assertIn("named no files", standing["why"])
        self.assertNotIn("moved", standing)

    def test_its_next_mark_keeps_its_files(self) -> None:
        self.run_maintain("--mark", "sample", "output", "nothing to change")
        self.write(SAMPLE_SHELF, self.read(SAMPLE_SHELF) + "And a date.\n")

        self.assertEqual([SAMPLE_SHELF], self.standing("sample", "output")["moved"])


class InstallingABlock(Clocked):
    """A rule reaching a skill as an installed block is policed as injection drift, not content:
    it moves no fingerprint on its way in or out."""

    RULES = (
        "# sample — rules installed into skills\n\n"
        "| target | anchor |\n|---|---|\n"
        f"| `{SHAPE_SKILL}` | `# Mechanism` |\n"
        f"| `{SAMPLE_SKILL}` | `# Sample` |\n"
        "| `AGENTS.md` | `## General rules` |\n\n"
        "## S1 — a rule\n\n"
        f"- **target** `{SHAPE_SKILL}`\n"
        f"- **target** `{SAMPLE_SKILL}`\n"
        "- **target** `AGENTS.md`\n"
        "- **authority** the user\n\n"
        "<rule>\nDo the thing.\n</rule>\n"
    )

    def setUp(self) -> None:
        super().setUp()
        self.write(SAMPLE_RULES, self.RULES)
        self.mark_every_level()

    def test_installing_and_then_retracting_it_makes_nothing_due(self) -> None:
        rules = inject_rules.read_rules_file(self.root, "sample")

        installed = inject_rules.install(self.root, rules, overwrite=False)
        self.assertEqual([], installed["refusals"])
        self.assertIn('<installed by="sample">', self.read(SHAPE_SKILL))
        self.assertIn('<installed by="sample">', self.read("AGENTS.md"))
        self.assertEqual({}, self.due())

        inject_rules.retract(self.root, rules)
        self.assertEqual({}, self.due())


class MalformedMarks(Clocked):
    """A row the check cannot read would make its mechanism silently ineligible; it is reported
    instead, the file left as it is, and no mark is written over it."""

    GOOD = "| sample | parts | " + "a" * 64 + " | 2026-09-27 | amended |\n"
    BAD_ROWS = {
        "a row of four cells": "| sample | parts | 2026-09-27 | amended |\n",
        "a level that is not one": GOOD.replace("| parts |", "| records |"),
        "the retired level": GOOD.replace("| parts |", "| rules |"),
        "a fingerprint that is not one": GOOD.replace("a" * 64, "abc"),
        "a date that is not one": GOOD.replace("2026-09-27", "2026-13-40"),
        "an outcome that is not one": GOOD.replace("amended", "fixed"),
        "a second row for one level": GOOD + GOOD,
    }

    def marks_holding(self, rows: str) -> str:
        return ("# Maintenance marks\n\n"
                "| mechanism | level | fingerprint | date | outcome |\n|---|---|---|---|---|\n" + rows)

    def test_each_bad_row_is_a_diagnostic_naming_its_line_and_the_file_is_untouched(self) -> None:
        for kind, rows in self.BAD_ROWS.items():
            with self.subTest(kind=kind):
                self.write(MARKS, self.marks_holding(rows))
                before = self.snapshot()

                status, report = self.run_maintain("--check")

                self.assertEqual(1, status)
                self.assertEqual(1, len(report["diagnostics"]), report["diagnostics"])
                self.assertTrue(report["diagnostics"][0].startswith(f"{MARKS}:"), report["diagnostics"][0])
                self.assertEqual(before, self.snapshot())

    def test_a_bad_file_row_is_a_diagnostic_and_refuses_a_mark(self) -> None:
        files = "\n| mechanism | level | file | fingerprint |\n|---|---|---|---|\n"
        bad_rows = {
            "a row of three cells": f"| sample | parts | {SAMPLE_SKILL} |\n",
            "a fingerprint that is not one": f"| sample | parts | {SAMPLE_SKILL} | abc |\n",
            "a level with no mark": f"| sample | output | {SAMPLE_SKILL} | {'b' * 64} |\n",
        }
        for kind, row in bad_rows.items():
            with self.subTest(kind=kind):
                self.write(MARKS, self.marks_holding(self.GOOD) + files + row)
                before = self.snapshot()

                status, report = self.run_maintain("--check")
                self.assertEqual(1, status)
                self.assertEqual(1, len(report["diagnostics"]), report["diagnostics"])
                self.assertTrue(report["diagnostics"][0].startswith(f"{MARKS}:"), report["diagnostics"][0])

                status, report = self.run_maintain("--mark", "sample", "output", "amended")
                self.assertEqual(1, status)
                self.assertIn("the marks do not read", report["refusals"][0])
                self.assertEqual(before, self.snapshot())

    def test_a_table_under_another_header_is_a_diagnostic(self) -> None:
        self.write(MARKS, "# Maintenance marks\n\n| mechanism | when |\n|---|---|\n| sample | today |\n")

        status, report = self.run_maintain("--check")

        self.assertEqual(1, status)
        self.assertIn("header", report["diagnostics"][0])

    def test_a_conforming_file_is_left_byte_identical_by_the_check(self) -> None:
        self.mark_every_level()
        before = self.snapshot()

        status, _ = self.run_maintain("--check")

        self.assertEqual(0, status)
        self.assertEqual(before, self.snapshot())

    def test_no_mark_is_written_over_marks_that_do_not_read(self) -> None:
        self.write(MARKS, self.marks_holding(self.BAD_ROWS["an outcome that is not one"]))
        before = self.snapshot()

        status, report = self.run_maintain("--mark", "sample", "output", "amended")

        self.assertEqual(1, status)
        self.assertIn("the marks do not read", report["refusals"][0])
        self.assertEqual(before, self.snapshot())


class AnUnreadableSurface(Clocked):
    """What cannot be fingerprinted is said, never guessed around: a guess would read as current."""

    def assert_unreadable_naming(self, words: str, level: str = "output") -> None:
        status, report = self.run_maintain("--check")

        self.assertEqual(1, status)
        self.assertTrue(any(words in note for note in report["diagnostics"]), report["diagnostics"])
        self.assertNotIn(("sample", level), self.states(report))

        before = self.snapshot()
        status, report = self.run_maintain("--mark", "sample", level, "amended")
        self.assertEqual(1, status)
        self.assertIn(words, report["refusals"][0])
        self.assertEqual(before, self.snapshot())

    def test_a_block_spaced_by_hand(self) -> None:
        self.write(SHAPE_SKILL, 'The shape. <installed by="sample">\n**S1** Do it.\n</installed>\n')

        self.assert_unreadable_naming(f"{SHAPE_SKILL}: the block is not spaced as the installer writes it")

    def test_a_block_that_never_closes(self) -> None:
        self.write(SHAPE_SKILL, '# Mechanism\n\n<installed by="sample">\n**S1** Do it.\n')

        self.assert_unreadable_naming(f"{SHAPE_SKILL}: the sample block never closes")

    def test_a_file_that_is_not_utf_8(self) -> None:
        (self.root / SAMPLE_SHELF).write_bytes("A record has a naïve title.\n".encode("latin-1"))

        self.assert_unreadable_naming(f"{SAMPLE_SHELF} is not UTF-8", level="output")

    def test_an_instruction_file_that_does_not_resolve(self) -> None:
        (self.root / SAMPLE_SKILL).unlink()

        self.assert_unreadable_naming(f"{SAMPLE_SKILL} does not resolve", level="output")

    def test_a_tree_declaring_no_mechanism_shape(self) -> None:
        (self.root / SHAPE_DOC).unlink()

        self.assert_unreadable_naming("no mechanism-shape is declared")

    def test_a_part_that_does_not_resolve(self) -> None:
        (self.root / SAMPLE_SCRIPT).unlink()

        self.assert_unreadable_naming(f"{SAMPLE_SCRIPT} does not resolve", level="parts")

    def test_a_part_that_is_a_directory(self) -> None:
        (self.root / SAMPLE_SCRIPT).unlink()
        (self.root / SAMPLE_SCRIPT).mkdir()

        self.assert_unreadable_naming(f"sample's part {SAMPLE_SCRIPT} is a directory", level="parts")


class AMarkForAMechanismNoLongerDeclared(Clocked):
    def setUp(self) -> None:
        super().setUp()
        self.run_maintain("--mark", "sample", "parts", "amended")
        (self.root / SAMPLE_DOC).unlink()

    def test_is_reported_by_the_check_without_failing_it(self) -> None:
        status, report = self.run_maintain("--check")

        self.assertEqual(0, status)
        self.assertEqual([("sample", "parts")],
                         [(row["mechanism"], row["level"]) for row in report["undeclared"]])
        self.assertNotIn("sample", {row["mechanism"] for row in report["mechanisms"]})

    def test_is_dropped_by_the_next_mark(self) -> None:
        self.run_maintain("--mark", "mechanism-shape", "output", "amended")

        self.assertNotIn("| sample", self.read(MARKS))
        self.assertIn("| mechanism-shape | output", self.read(MARKS))


class InARecipient(Clocked):
    """A tree whose entry file announces the core it received: its built-in mechanisms were
    maintained where core is made, so they are not this tree's to re-check."""

    def setUp(self) -> None:
        super().setUp()
        self.write("AGENTS.md", ORIGIN_ENTRY.replace("v1,", "goodwolf-harness@abc1234,"))

    def test_the_check_derives_no_built_in_mechanism_says_why_and_passes(self) -> None:
        status, report = self.run_maintain("--check")

        self.assertEqual(0, status)
        self.assertEqual([], report["mechanisms"])
        self.assertEqual(["mechanism-shape", "sample"], report["built in"]["mechanisms"])
        self.assertIn("where core is made", report["built in"]["why"])

    def test_a_mark_on_a_built_in_mechanism_is_refused_and_writes_nothing(self) -> None:
        before = self.snapshot()

        status, report = self.run_maintain("--mark", "sample", "output", "amended")

        self.assertEqual(1, status)
        self.assertIn("sample came with core", report["refusals"][0])
        self.assertEqual(before, self.snapshot())


class ARefusedMark(Clocked):
    def setUp(self) -> None:
        super().setUp()
        self.run_maintain("--mark", "sample", "parts", "amended")
        self.before = self.snapshot()

    def assert_refused_naming(self, words: str, *argv: str) -> None:
        status, report = self.run_maintain("--mark", *argv)

        self.assertEqual(1, status)
        self.assertEqual(1, len(report["refusals"]))
        self.assertIn(words, report["refusals"][0])
        self.assertEqual(self.before, self.snapshot())

    def test_names_a_mechanism_the_tree_does_not_declare(self) -> None:
        self.assert_refused_naming("elsewhere is not a declared mechanism", "elsewhere", "parts", "amended")

    def test_names_a_level_that_is_not_one(self) -> None:
        self.assert_refused_naming("records is not a level", "sample", "records", "amended")

    def test_names_the_retired_level(self) -> None:
        self.assert_refused_naming("rules is not a level", "sample", "rules", "amended")

    def test_names_an_outcome_that_is_not_one(self) -> None:
        self.assert_refused_naming("fixed is not an outcome", "sample", "parts", "fixed")


if __name__ == "__main__":
    unittest.main()
