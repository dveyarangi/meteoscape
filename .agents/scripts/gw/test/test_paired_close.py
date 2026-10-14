# Mechanism: ticket
"""The paired close: two records move together and every citation still points at a record."""

from __future__ import annotations

import unittest

from repository import RepositoryCase

import move_doc

TICKET = "docs/tickets/01-0010.0040-install-plan.md"
RFC = "docs/rfc/01-0010.0040-install-plan.md"
CLOSED_TICKET = "docs/tickets/done/01-0010.0040-install-plan.md"
CLOSED_RFC = "docs/rfc/done/01-0010.0040-install-plan.md"


class PairedClose(RepositoryCase):
    def setUp(self) -> None:
        super().setUp()
        self.write(TICKET, "# Install /plan\n\nPlan: [the RFC](../rfc/01-0010.0040-install-plan.md).\n")
        self.write(RFC, "# Install /plan — plan\n\nImplements [the ticket](../tickets/01-0010.0040-install-plan.md).\n")
        self.write(
            "docs/tickets/README.md",
            "# Delivery status\n\n| [Install /plan](01-0010.0040-install-plan.md) | Done |\n",
        )

    def test_the_pair_lands_in_done_citing_each_other_and_the_queue_follows(self) -> None:
        move_doc.perform(self.root, [(TICKET, CLOSED_TICKET), (RFC, CLOSED_RFC)])

        self.assertFalse((self.root / TICKET).exists())
        self.assertFalse((self.root / RFC).exists())
        self.assertIn("../../rfc/done/01-0010.0040-install-plan.md", self.read(CLOSED_TICKET))
        self.assertIn("../../tickets/done/01-0010.0040-install-plan.md", self.read(CLOSED_RFC))
        self.assertEqual(
            "# Delivery status\n\n| [Install /plan](done/01-0010.0040-install-plan.md) | Done |\n",
            self.read("docs/tickets/README.md"),
        )


class TheMarkAtClose(RepositoryCase):
    """A record landing on a `done/` shelf is a record of what happened, and the mover, which lands
    it there, writes so — the one line of a header it touches (the user, 2026-10-10)."""

    def setUp(self) -> None:
        super().setUp()
        self.write(
            TICKET,
            "# Install /plan\n\n- **record of** what it intends to become\n- **Status:** Done (2026-10-10)\n\n"
            "Plan: [the RFC](../rfc/01-0010.0040-install-plan.md). A note on `- **record of** what it intends to become`.\n",
        )
        self.write(
            RFC,
            "# Install /plan — plan\n\n- **record of** what it intends to become\n\n"
            "Implements [the ticket](../tickets/01-0010.0040-install-plan.md).\n",
        )

    def test_the_pair_closing_into_done_is_marked_what_happened_and_nothing_else_changes(self) -> None:
        move_doc.perform(self.root, [(TICKET, CLOSED_TICKET), (RFC, CLOSED_RFC)])

        self.assertEqual(
            "# Install /plan\n\n- **record of** what happened\n- **Status:** Done (2026-10-10)\n\n"
            "Plan: [the RFC](../../rfc/done/01-0010.0040-install-plan.md). A note on `- **record of** what it intends to become`.\n",
            self.read(CLOSED_TICKET),
        )
        self.assertEqual(
            "# Install /plan — plan\n\n- **record of** what happened\n\n"
            "Implements [the ticket](../../tickets/done/01-0010.0040-install-plan.md).\n",
            self.read(CLOSED_RFC),
        )
        self.assertEqual([], move_doc.unfinished(self.root, [(TICKET, CLOSED_TICKET), (RFC, CLOSED_RFC)]))

    def test_a_record_carrying_no_mark_is_moved_without_one(self) -> None:
        self.write(TICKET, "# Install /plan\n\n- **Status:** Done (2026-10-10)\n")

        move_doc.perform(self.root, [(TICKET, CLOSED_TICKET), (RFC, CLOSED_RFC)])

        self.assertEqual("# Install /plan\n\n- **Status:** Done (2026-10-10)\n", self.read(CLOSED_TICKET))

    def test_a_move_onto_another_shelf_keeps_the_mark(self) -> None:
        elsewhere = "docs/rfc/01-0010.0041-install-plan.md"

        move_doc.perform(self.root, [(RFC, elsewhere)])

        self.assertIn("- **record of** what it intends to become\n", self.read(elsewhere))

    def test_a_closed_record_still_marked_as_live_is_an_unfinished_close(self) -> None:
        move_doc.perform(self.root, [(TICKET, CLOSED_TICKET), (RFC, CLOSED_RFC)])
        self.write(CLOSED_RFC, self.read(CLOSED_RFC).replace("what happened", "what it intends to become"))

        problems = move_doc.unfinished(self.root, [(TICKET, CLOSED_TICKET), (RFC, CLOSED_RFC)])

        self.assertEqual(1, len(problems))
        self.assertIn(CLOSED_RFC, problems[0])
        self.assertIn("what it intends to become", problems[0])


if __name__ == "__main__":
    unittest.main()
