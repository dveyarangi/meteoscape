# Mechanism: ticket
"""The mover as `/maintain` actually calls it: operands in, a report and an exit status out."""

from __future__ import annotations

import contextlib
import io
import unittest

from repository import RepositoryCase

import move_doc

TICKET = "docs/tickets/01-0010.0040-install-plan.md"
RFC = "docs/rfc/01-0010.0040-install-plan.md"
CLOSED_TICKET = "docs/tickets/done/01-0010.0040-install-plan.md"
CLOSED_RFC = "docs/rfc/done/01-0010.0040-install-plan.md"
QUEUE = "docs/tickets/README.md"


class CommandLine(RepositoryCase):
    def setUp(self) -> None:
        super().setUp()
        self.write(TICKET, "# Install /plan\n\n[the RFC](../rfc/01-0010.0040-install-plan.md)\n")
        self.write(RFC, "# Install /plan — plan\n\n[the ticket](../tickets/01-0010.0040-install-plan.md)\n")
        self.write(QUEUE, "# Queue\n\n[plan](01-0010.0040-install-plan.md)\n")

    def run_mover(self, *operands: str) -> tuple[int, str]:
        said = io.StringIO()
        with contextlib.redirect_stdout(said), contextlib.redirect_stderr(said):
            status = move_doc.main(list(operands), root=self.root)
        return status, said.getvalue()

    def test_a_preview_reports_the_close_without_touching_the_tree(self) -> None:
        untouched = self.snapshot()

        status, said = self.run_mover("--dry-run", TICKET, CLOSED_TICKET, RFC, CLOSED_RFC)

        self.assertEqual(0, status)
        self.assertIn(f"would move {TICKET} -> {CLOSED_TICKET}", said)
        self.assertIn(f"would repair citations in {QUEUE}", said)
        self.assertEqual(untouched, self.snapshot())

    def test_a_refused_selection_says_why_and_leaves_the_tree_alone(self) -> None:
        untouched = self.snapshot()

        status, said = self.run_mover(TICKET, TICKET)

        self.assertEqual(2, status)
        self.assertIn("refused", said)
        self.assertEqual(untouched, self.snapshot())

    def test_operands_that_do_not_pair_up_are_a_usage_error(self) -> None:
        status, said = self.run_mover(TICKET)

        self.assertEqual(2, status)
        self.assertIn("SRC DST", said)

    def test_a_completed_close_reports_what_moved(self) -> None:
        status, said = self.run_mover(TICKET, CLOSED_TICKET, RFC, CLOSED_RFC)

        self.assertEqual(0, status)
        self.assertIn(f"moved {TICKET} -> {CLOSED_TICKET}", said)
        self.assertIn(f"repaired citations in {QUEUE}", said)
        self.assertLess(
            said.index(f"moved {TICKET} -> {CLOSED_TICKET}"),
            said.index(f"repaired citations in {QUEUE}"),
            "each operation is announced in the order it happens",
        )
        self.assertTrue((self.root / CLOSED_RFC).exists())

    def test_an_interrupted_close_reports_the_half_it_finished(self) -> None:
        self.write("docs/rfc/done", "a file where the archive folder should be")

        status, said = self.run_mover(TICKET, CLOSED_TICKET, RFC, CLOSED_RFC)

        self.assertEqual(1, status)
        self.assertIn("nothing was rolled back", said)
        self.assertIn(f"completed: {TICKET} -> {CLOSED_TICKET}", said)
        self.assertIn(f"pending:   {RFC} -> {CLOSED_RFC}", said)

    def test_a_mention_this_mover_cannot_rewrite_is_reported_not_hidden(self) -> None:
        self.write(
            "docs/notes.md",
            '# Notes\n\n<a href="tickets/01-0010.0040-install-plan.md">the plan</a>\n',
        )

        status, said = self.run_mover(TICKET, CLOSED_TICKET)

        self.assertEqual(0, status)
        self.assertIn("docs/notes.md:3", said)
        self.assertIn("still names", said)


class OutgoingReferences(RepositoryCase):
    def setUp(self) -> None:
        super().setUp()
        self.write("docs/tickets/README.md", "# Queue\n\n[plan](01-0010.0040-install-plan.md)\n")

    def run_mover(self, *operands: str) -> tuple[int, str]:
        said = io.StringIO()
        with contextlib.redirect_stdout(said), contextlib.redirect_stderr(said):
            status = move_doc.main(list(operands), root=self.root)
        return status, said.getvalue()

    def test_a_moved_records_reference_that_leads_nowhere_is_reported_not_swallowed(self) -> None:
        self.write(TICKET, "# Install /plan\n\n[the spec](../spec/never-written.md)\n")

        status, said = self.run_mover(TICKET, CLOSED_TICKET)

        self.assertEqual(0, status, "a defect that predates the close does not fail it")
        self.assertIn("../../spec/never-written.md", said)
        self.assertIn("leads nowhere", said)


if __name__ == "__main__":
    unittest.main()
