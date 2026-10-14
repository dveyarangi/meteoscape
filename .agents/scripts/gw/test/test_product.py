# Mechanism: product
"""The product document's answers, and each answer's coverage read from the questions that realize it."""

from __future__ import annotations

import contextlib
import io
import json
import unittest

from repository import RepositoryCase

import product

DOCUMENT = "docs/product.md"
STORE = "docs/questions"


def document(*rows: str) -> str:
    """A product document whose answers table holds the rows given, under one group heading."""
    return (
        "# What the project is for\n\n## Pains\n\n1. **It hurts.**\n\n## Causes\n\n- **C1** A cause.\n\n"
        "## Answers\n\n| answer | causes | 1 | waits on |\n|---|---|---|---|\n"
        "| **The first group** | | | |\n" + "".join(f"{row}\n" for row in rows) + "\n## After\n\nProse.\n"
    )


def answer(identity: str, name: str, waits: str = "") -> str:
    return f"| **{identity} {name}** — what it does | C1 | ● | {waits} |"


def waiting_on(identity: str) -> str:
    return f'<straw-dog question="{identity}">✗</straw-dog>'


def question(
    identity: str,
    state: str = "open",
    parent: str | None = None,
    realizes: str | None = None,
    words: str | None = None,
    owner: str | None = None,
) -> str:
    kind = "what it intends to become" if state.startswith("open") else "what happened"
    parts = [f"- **record of** {kind}"]
    parts += [f"- **part of** {parent}"] if parent else []
    parts += [f"- **state** {state}"]
    parts += [f"- **owner** [{owner.split('/')[-1][:7]}](../{owner})"] if owner else []
    parts += ["- **answer** a reason"] if not state.startswith("open") else []
    parts += [f"- **realizes** {realizes}"] if realizes else []
    return "\n".join([f"# {identity} {words or f'Question {identity}?'}", "", *parts]) + "\n"


class Product(RepositoryCase):
    def run_script(self, *argv: str) -> tuple[int, str]:
        said = io.StringIO()
        with contextlib.redirect_stdout(said):
            status = product.main(list(argv), root=self.root)
        return status, said.getvalue()

    def checked(self) -> tuple[int, dict]:
        status, said = self.run_script("--check")
        return status, json.loads(said)

    def place(self, identity: str, text: str, folder: str = STORE) -> None:
        self.write(f"{folder}/{identity}-question-{identity.replace('.', '-')}.md", text)


class ATreeWithNoProductDocument(Product):
    def test_the_check_finds_nothing_and_passes(self) -> None:
        status, report = self.checked()

        self.assertEqual(0, status)
        self.assertEqual({"document": None, "answers": 0, "diagnostics": [], "findings": []}, report)

    def test_the_check_reports_no_orphan_without_a_document(self) -> None:
        self.place("q-0002", question("q-0002", words="How is this project built?"))
        self.place("q-0002.0001", question("q-0002.0001", parent="q-0002"))

        self.assertEqual([], self.checked()[1]["findings"])

    def test_coverage_renders_nothing(self) -> None:
        self.place("q-0001", question("q-0001", realizes='A1 "Something"'))

        self.assertEqual((0, ""), self.run_script("--coverage"))


SHELF = ".agents/skills/product/PRODUCT-ARRIVAL.md"
EMPTY = "# What this project is for\n\n## Answers\n\n| answer | causes | waits on |\n|---|---|---|\n"


def shelf_text(said: str = EMPTY) -> str:
    return f"# The document before anything is decided\n\nProse around it.\n\n```product-document\n{said}```\n"


class TheSeed(Product):
    def test_a_tree_with_no_document_gets_the_shelfs_and_the_check_passes_it(self) -> None:
        self.write(SHELF, shelf_text())

        written = product.seed(self.root)

        self.assertEqual([DOCUMENT], written)
        self.assertEqual(EMPTY, self.read(DOCUMENT))
        self.assertEqual(([], 0), (self.checked()[1]["diagnostics"], self.checked()[0]))

    def test_a_document_already_there_is_left_byte_for_byte_in_the_format_or_not(self) -> None:
        self.write(SHELF, shelf_text())
        for held in (document(answer("A1", "One")), "# Our vision\r\n\r\nMaps for farmers.\r\n"):
            with self.subTest(held=held[:12]):
                self.write(DOCUMENT, held)

                self.assertEqual([], product.seed(self.root))
                self.assertEqual(held.encode("utf-8"), (self.root / DOCUMENT).read_bytes())

    def test_a_shelf_with_no_block_is_refused_and_nothing_written(self) -> None:
        self.write(SHELF, "# A shelf\n\nNo block here.\n")

        with self.assertRaises(product.Refused):
            product.seed(self.root)
        self.assertFalse((self.root / DOCUMENT).exists())


class Coverage(Product):
    def setUp(self) -> None:
        super().setUp()
        self.write(
            DOCUMENT,
            document(
                answer("A1", "Nobody builds it"),
                answer("A2", "Still being built"),
                answer("A3", "Built"),
                answer("A4", "Only abandoned"),
            ),
        )
        self.place("q-0001", question("q-0001", realizes='A2 "Still being built"'))
        self.place("q-0001.0001", question("q-0001.0001", "closed:decided", parent="q-0001", realizes='A3 "Built"'))
        self.place("q-0001.0002", question("q-0001.0002", "open", parent="q-0001"))
        self.place("q-0002", question("q-0002", "closed:pruned", realizes='A4 "Only abandoned"'))

    def lines(self) -> list[str]:
        status, said = self.run_script("--coverage")
        self.assertEqual(0, status)
        return said.splitlines()

    def test_each_answer_reads_absent_in_progress_or_present_in_the_documents_order(self) -> None:
        self.assertEqual(
            [
                "A1 Nobody builds it — absent",
                "A2 Still being built — in progress: q-0001, q-0001.0002",
                "A3 Built — present: q-0001.0001",
                "A4 Only abandoned — absent",
            ],
            self.lines(),
        )

    def test_an_answer_whose_questions_are_all_decided_is_present(self) -> None:
        self.place("q-0001", question("q-0001", "closed:decided", realizes='A2 "Still being built"'))
        self.place("q-0001.0002", question("q-0001.0002", "closed:decided", parent="q-0001"))

        self.assertIn("A2 Still being built — present: q-0001, q-0001.0002", self.lines())

    def test_a_deferred_question_counts_as_open(self) -> None:
        self.place("q-0003", question("q-0003", "closed:deferred", realizes='A1 "Nobody builds it"'))

        self.assertIn("A1 Nobody builds it — in progress: q-0003", self.lines())

    def test_a_decided_question_in_done_counts(self) -> None:
        self.place("q-0004", question("q-0004", "closed:decided", realizes='A1 "Nobody builds it"'), f"{STORE}/done")

        self.assertIn("A1 Nobody builds it — present: q-0004", self.lines())

    def test_a_derived_question_realizes_nothing(self) -> None:
        self.place("q-0001.0002", question("q-0001.0002", "open", parent="q-0001", realizes="derived"))

        self.assertIn("A2 Still being built — in progress: q-0001", self.lines())


QUEUED = (
    "# What the project is for\n\n## Pains\n\n1. **It hurts.** Badly.\n2. **It costs.** Too much.\n\n"
    "## Goals\n\n- **G1 Keep it.** Never lose it.\n\n"
    "## Answers\n\n| answer | causes | 1 | 2 | G1 | G9 | waits on |\n|---|---|---|---|---|---|---|\n"
    "| **A1 Built by an item** — x | C1 | ● | | | | |\n"
    "| **A2 Built aside** — x | C1 | ● | ● | | | |\n"
    "| **A3 Present** — x | C1 | | | ● | | |\n"
    '| **A4 Undecided** — x | C1 | | ● | | | <straw-dog question="q-0005">✗</straw-dog> |\n'
    "| **A5 For nothing** — x | C1 | | | | | |\n"
    "| **A6 Unnamed goal** — x | C1 | | | | ● | |\n"
)


class TheQueue(Product):
    def setUp(self) -> None:
        super().setUp()
        self.write(DOCUMENT, QUEUED)
        self.place("q-0001", question("q-0001", realizes='A1 "Built by an item"', owner="tickets/01-0001-first.md"))
        self.place("q-0001.0001", question("q-0001.0001", parent="q-0001", owner="tickets/01-0001.0010-second.md"))
        self.place(
            "q-0001.0002",
            question("q-0001.0002", parent="q-0001", realizes='A5 "For nothing"', owner="tickets/01-0001-first.md"),
        )
        self.place("q-0001.0002.0001", question("q-0001.0002.0001", parent="q-0001.0002", owner="tickets/01-0001-first.md"))
        self.place("q-0002", question("q-0002", realizes="derived", owner="tickets/01-0002-aside.md"))
        self.place("q-0003", question("q-0003", realizes='A2 "Built aside"'))
        self.place("q-0004", question("q-0004", "closed:decided", realizes='A3 "Present"'))
        self.place("q-0006", question("q-0006", realizes='A6 "Unnamed goal"', owner="tickets/done/01-0000-old.md"))

    def shown(self) -> list[str]:
        status, said = self.run_script("--queue")
        self.assertEqual(0, status)
        return said.splitlines()

    def test_each_live_item_shows_once_what_its_questions_realize_in_id_order(self) -> None:
        shown = self.shown()

        items = shown[1 : shown.index("")]
        self.assertEqual(
            [
                "01-0001 first — q-0001: A1 Built by an item, A5 For nothing",
                "01-0001.0010 second — q-0001.0001: A1 Built by an item",
                "01-0002 aside — q-0002: derived",
            ],
            items,
        )

    def test_the_answers_no_item_realizes_stand_under_each_pain_and_goal_they_serve(self) -> None:
        left = self.shown()
        left = left[left.index("Left out") + 1 :]

        self.assertEqual(
            [
                "1 It hurts",
                "  A2 Built aside — in progress: q-0003",
                "2 It costs",
                "  A2 Built aside — in progress: q-0003",
                "  A4 Undecided — not decided",
                "G1 Keep it",
                "  nothing left out",
                "G9",
                "  A6 Unnamed goal — in progress: q-0006",
                "Serving no stated pain or goal",
                "  nothing left out",
            ],
            left,
        )

    def test_rendering_writes_nothing(self) -> None:
        before = self.snapshot()

        self.shown()

        self.assertEqual(before, self.snapshot())


class Drift(Product):
    """A tree where the document and the store agree, and each way they can come apart.

        q-0001 What is this project for?        purpose root
          q-0001.0001                           open, bound by A2's row
        q-0002 How is this project built?       structure root
          q-0002.0001                           open, realizes A1
    """

    def setUp(self) -> None:
        super().setUp()
        self.rows = [answer("A1", "One"), answer("A2", "Two", waiting_on("q-0001.0001"))]
        self.write(DOCUMENT, document(*self.rows))
        self.place("q-0001", question("q-0001", words="What is this project for?"))
        self.place("q-0001.0001", question("q-0001.0001", parent="q-0001"))
        self.place("q-0002", question("q-0002", words="How is this project built?"))
        self.place("q-0002.0001", question("q-0002.0001", parent="q-0002", realizes='A1 "One"'))

    def report(self) -> tuple[int, list[str], list[str]]:
        status, said = self.checked()
        return (
            status,
            [note["problem"] for note in said["diagnostics"]],
            [note["finding"] for note in said["findings"]],
        )

    def assertBroken(self, fragment: str) -> None:
        status, problems, _ = self.report()
        self.assertEqual(1, status)
        self.assertEqual(1, len(problems), problems)
        self.assertIn(fragment, problems[0])

    def assertMissing(self, fragment: str) -> None:
        status, problems, findings = self.report()
        self.assertEqual((0, []), (status, problems))
        self.assertEqual(1, len(findings), findings)
        self.assertIn(fragment, findings[0])

    def test_a_tree_in_agreement_reports_nothing(self) -> None:
        self.assertEqual((0, [], []), self.report())

    def test_a_link_naming_no_answer_fails(self) -> None:
        self.place("q-0002.0001", question("q-0002.0001", parent="q-0002", realizes='A1 "One", A9 "Ghost"'))

        self.assertBroken("A9")

    def test_a_link_quoting_a_name_its_answer_no_longer_has_fails(self) -> None:
        self.place("q-0002.0001", question("q-0002.0001", parent="q-0002", realizes='A1 "The old one"'))

        self.assertBroken('"The old one"')

    def test_a_row_bound_outside_the_purpose_root_fails(self) -> None:
        self.write(DOCUMENT, document(answer("A1", "One"), answer("A2", "Two", waiting_on("q-0002.0001"))))
        self.place("q-0001.0001", question("q-0001.0001", "closed:decided", parent="q-0001"))

        self.assertBroken("q-0002.0001")

    def test_an_undecided_row_with_no_binding_fails(self) -> None:
        self.write(DOCUMENT, document(answer("A1", "One"), answer("A2", "Two", "✗")))
        self.place("q-0001.0001", question("q-0001.0001", "closed:decided", parent="q-0001"))

        self.assertBroken("A2")

    def test_an_open_structure_question_with_no_link_is_an_orphan(self) -> None:
        self.place("q-0002.0002", question("q-0002.0002", parent="q-0002"))

        self.assertMissing("q-0002.0002")

    def test_a_derived_question_is_no_orphan(self) -> None:
        self.place("q-0002.0002", question("q-0002.0002", parent="q-0002", realizes="derived"))

        self.assertEqual((0, [], []), self.report())

    def test_a_decided_answer_nothing_realizes_is_reported(self) -> None:
        self.write(DOCUMENT, document(*self.rows, answer("A3", "Three")))

        self.assertMissing("A3")

    def test_a_purpose_question_no_row_names_is_reported_and_its_named_ancestor_covers_it(self) -> None:
        self.place("q-0001.0002", question("q-0001.0002", parent="q-0001"))
        self.place("q-0001.0001.0001", question("q-0001.0001.0001", parent="q-0001.0001"))

        self.assertMissing("q-0001.0002")


class TheDocumentsForm(Product):
    def problems(self) -> list[str]:
        status, report = self.checked()
        self.assertEqual(1 if report["diagnostics"] else 0, status)
        return [note["problem"] for note in report["diagnostics"]]

    def test_answers_with_an_id_and_a_name_each_pass_and_a_group_heading_is_no_answer(self) -> None:
        self.write(DOCUMENT, document(answer("A1", "One"), answer("A2", "Two")))

        status, report = self.checked()

        self.assertEqual((0, 2, []), (status, report["answers"], report["diagnostics"]))

    def test_an_id_written_twice(self) -> None:
        self.write(DOCUMENT, document(answer("A1", "One"), answer("A1", "Again")))

        self.assertEqual(["answer A1 is written twice"], self.problems())

    def test_an_answer_row_with_no_id_and_name(self) -> None:
        self.write(DOCUMENT, document(answer("A1", "One"), "| an answer with no lead | C1 | ● | |"))

        problems = self.problems()
        self.assertEqual(1, len(problems), problems)
        self.assertIn("**A<n> <name>**", problems[0])

    def test_a_document_with_no_answers_heading_is_not_in_the_format(self) -> None:
        self.write(DOCUMENT, "# Our vision\n\nWe make maps for farmers.\n\n## Features\n\n- frost alerts\n")

        problems = self.problems()

        self.assertEqual(1, len(problems), problems)
        self.assertIn("not in the product format", problems[0])

    def test_an_answers_heading_with_no_row_is_in_the_format(self) -> None:
        self.write(DOCUMENT, "# What it is for\n\n## Answers\n\n| answer | causes | waits on |\n|---|---|---|\n")

        self.assertEqual([], self.problems())

    def test_a_call_with_no_mode_is_refused_with_its_usage(self) -> None:
        status, said = self.run_script()

        self.assertEqual(2, status)
        self.assertIn("usage", said)


if __name__ == "__main__":
    unittest.main()
