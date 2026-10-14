# Mechanism: mechanism-shape
"""Reading a mechanism's declaration, and saying whether it is true."""

from __future__ import annotations

import contextlib
import io
import json
import unittest

from repository import RepositoryCase

import mechanisms

SLUG = "sample-shape"
MECHANISMS = ".agents/mechanisms"
DOC = f"{MECHANISMS}/{SLUG}/{SLUG}.md"
INSTRUCTION = ".agents/skills/sample/SKILL.md"
SCRIPT = ".agents/scripts/gw/sample.py"
TRIGGER = "is sample work: use"
# A part an agent edits names its mechanism on its first line: a skill past its frontmatter, code as
# a comment after any shebang (the user, 2026-10-11).
NAMED_SKILL = f"Mechanism: {SLUG}\n\n# Sample\n"
NAMED_SCRIPT = f'# Mechanism: {SLUG}\n"""The sample\'s script."""\n'

MOMENTS = (
    "| moment | instructed by | kind, and why |\n"
    "|---|---|---|\n"
    f"| doing the thing | `{INSTRUCTION}` | |\n"
    '| sweeping afterwards | — | <straw-dog question="q-0002">not yet</straw-dog> |\n'
)
SWEEPING = "Who sweeps afterwards?"


def question(identity: str, words: str, state: str = "open", **parts: str) -> str:
    """An entry of the question store, as a `not yet` binds to one."""
    bullets = [f"- **state** {state}", *(f"- **{name}** {value}" for name, value in parts.items())]
    return "\n".join([f"# {identity} {words}", "", *bullets]) + "\n"
PARTS = (
    "| part | where |\n"
    "|---|---|\n"
    f"| instruction file | `{INSTRUCTION}` |\n"
    f"| the script | `{SCRIPT}` |\n"
    f'| trigger | `AGENTS.md` → "{TRIGGER}" |\n'
)
RELIED_ON = (
    "| part | where | owner |\n"
    "|---|---|---|\n"
    "| corpus reader | `.agents/scripts/docs_corpus.py` | nobody removable |\n"
)


class Declared(RepositoryCase):
    """A tree holding one well-formed mechanism, which each test bends in exactly one way."""

    def setUp(self) -> None:
        super().setUp()
        self.write(INSTRUCTION, NAMED_SKILL)
        self.write(SCRIPT, NAMED_SCRIPT)
        self.write("AGENTS.md", f"- Doing it {TRIGGER} /sample.\n")
        self.write(".agents/scripts/docs_corpus.py", "# shared\n")
        self.write("docs/tickets/01-0002-sweep.md", "# Sweep\n")
        self.write("docs/tickets/01-0001-sample.md", "# Sample\n")
        self.write("docs/questions/q-0002-who-sweeps-afterwards.md", question("q-0002", SWEEPING))
        self.write(DOC, self.doc())

    def doc(self, **replaced: str) -> str:
        """The well-formed declaration, with any one section swapped for what a test is proving."""
        written = {
            "header": (
                f"# {SLUG} — one line saying what it is\n\n"
                f"- **instruction** `{INSTRUCTION}` — the act\n"
                "- **state** always on\n"
                "- **record of** what must always hold\n"
            ),
            "moments": MOMENTS,
            "parts": PARTS,
            "relied_on": RELIED_ON,
            "produces": "## What it produces, and who reads it\n\n"
            "The declaration, read by whoever amends this. Nothing else is emitted.\n",
            "grading":"## What would show it working, graded by someone who did not build it\n\n"
            "The next mechanism declared passes unedited, or the check changes to admit it.\n",
            **replaced,
        }
        return (
            f"{written['header']}\n"
            "## How it works\n\nProse nothing parses.\n\n"
            f"## Moments\n\n{written['moments']}\n"
            f"## Install adds, uninstall removes\n\n{written['parts']}\n"
            f"## Relies on, and does not own\n\n{written['relied_on']}\n"
            f"{written['produces']}\n"
            "## Not yet at the shape\n\nThe honest gaps.\n\n"
            "## What retires this\n\nA better shape.\n\n"
            f"{written['grading']}"
        )

    def header(self, bullets: str) -> str:
        """A header bending only the bullet under test; the rest stays well-formed."""
        if "**state**" not in bullets:
            bullets += "- **state** always on\n"
        if "**record of**" not in bullets:
            bullets += "- **record of** what must always hold\n"
        return f"# {SLUG} — one line saying what it is\n\n{bullets}"

    def checked(self):
        return mechanisms.check(self.root)

    def problems(self) -> list[str]:
        return [note.problem for note in self.checked().diagnostics]


class AWellFormedDeclaration(Declared):
    def test_is_reported_true_with_its_parts_and_its_moments(self) -> None:
        checked = self.checked()

        self.assertEqual([], checked.diagnostics)
        self.assertEqual(1, len(checked.declarations))
        declared = checked.declarations[0]
        self.assertEqual(SLUG, declared.slug)
        self.assertEqual(INSTRUCTION, declared.instruction)
        self.assertEqual("always on", declared.state)
        self.assertEqual(2, len(declared.moments))
        self.assertEqual(3, len(declared.parts))
        self.assertEqual(1, len(declared.relied_on))
        self.assertIsNone(declared.rules)
        not_yet = declared.moments[1]
        self.assertEqual(("not yet", SWEEPING, "q-0002"), (not_yet.kind, not_yet.why, not_yet.referent))


class ANamedPart(Declared):
    def test_that_does_not_resolve_is_reported_by_its_path(self) -> None:
        self.write(
            DOC,
            self.doc(
                parts=PARTS + "| a script | `.agents/scripts/nowhere.py` |\n"
            ),
        )

        problems = [note.problem for note in self.checked().diagnostics]

        self.assertEqual(1, len(problems))
        self.assertIn(".agents/scripts/nowhere.py", problems[0])

    def test_whose_anchor_phrase_is_not_in_the_file_it_names_is_reported(self) -> None:
        self.write(
            DOC,
            self.doc(
                parts=PARTS.replace(TRIGGER, "reworded away")
            ),
        )

        problems = [note.problem for note in self.checked().diagnostics]

        self.assertEqual(1, len(problems))
        self.assertIn("reworded away", problems[0])
        self.assertIn("AGENTS.md", problems[0])


class ANotYetReferent(Declared):
    def moments_binding(self, identity: str, body: str = "not yet") -> str:
        return (
            "| moment | instructed by | kind, and why |\n|---|---|---|\n"
            f'| sweeping | — | <straw-dog question="{identity}">{body}</straw-dog> |\n'
        )

    def test_saying_why_in_the_body_is_reported_since_the_reason_is_its_question(self) -> None:
        self.write(DOC, self.doc(moments=self.moments_binding("q-0002", "not yet — nobody sweeps")))

        problems = self.problems()

        self.assertEqual(1, len(problems))
        self.assertIn("the question it is bound to", problems[0])
        self.assertIn("sweeping", problems[0])

    def test_a_wrapper_around_another_kind_is_read_for_its_body(self) -> None:
        self.write(
            DOC,
            self.doc(
                moments="| moment | instructed by | kind, and why |\n|---|---|---|\n"
                '| archiving | — | <straw-dog question="q-0002">'
                f"elsewhere — `{INSTRUCTION}` owns it for now</straw-dog> |\n"
            ),
        )

        checked = self.checked()

        self.assertEqual([], checked.diagnostics)
        row = checked.declarations[0].moments[0]
        self.assertEqual(("elsewhere", INSTRUCTION), (row.kind, row.referent))

    def test_may_not_wait_on_a_question_whose_answer_has_landed_since_the_gap_is_filled(self) -> None:
        self.write("docs/architecture.md", "# Architecture\n\n## Sweeping\n\nSwept.\n")
        self.write(
            "docs/questions/q-0003-who-sweeps-now.md",
            question("q-0003", "Who sweeps now?", "closed:decided", answer="[sweeping](../architecture.md#sweeping)"),
        )
        self.write(DOC, self.doc(moments=self.moments_binding("q-0003")))

        problems = self.problems()

        self.assertEqual(1, len(problems))
        self.assertIn("q-0003", problems[0])
        self.assertIn("due", problems[0])

    def test_a_question_decided_in_the_work_that_owns_it_still_holds_the_gap(self) -> None:
        self.write(
            "docs/questions/q-0003-who-sweeps-now.md",
            question(
                "q-0003",
                "Who sweeps now?",
                "closed:decided",
                owner="[01-0002](../tickets/01-0002-sweep.md)",
                answer="[the sweep](../tickets/01-0002-sweep.md)",
            ),
        )
        self.write(DOC, self.doc(moments=self.moments_binding("q-0003")))

        self.assertEqual([], self.problems())

    def test_a_superseded_question_is_reported_with_the_one_to_rebind_to(self) -> None:
        self.write(
            "docs/questions/q-0003-who-sweeps-now.md",
            question("q-0003", "Who sweeps now?", "closed:superseded", answer="q-0002"),
        )
        self.write(DOC, self.doc(moments=self.moments_binding("q-0003")))

        problems = self.problems()

        self.assertEqual(1, len(problems))
        self.assertIn("rebind it to q-0002", problems[0])


class TheInstruction(Declared):
    def test_may_not_be_the_doc_itself(self) -> None:
        self.write(DOC, self.doc(header=self.header(f"- **instruction** `{DOC}` — the act\n")))

        problems = [note.problem for note in self.checked().diagnostics]

        # The declaration names no skill, so the sample skill names a mechanism that does not name
        # it: two findings, one cause.
        self.assertEqual(2, len(problems))
        self.assertIn("the doc", problems[0])
        self.assertIn("whose declaration does not name it", problems[1])

    def test_is_required(self) -> None:
        self.write(DOC, self.doc(header=self.header("- **state** always on\n")))

        problems = [note.problem for note in self.checked().diagnostics]

        self.assertEqual(2, len(problems))
        self.assertIn("instruction", problems[0])
        self.assertIn("whose declaration does not name it", problems[1])

    def test_must_resolve(self) -> None:
        self.write(
            DOC, self.doc(header=self.header("- **instruction** `.agents/skills/gone/SKILL.md`\n"))
        )

        problems = [note.problem for note in self.checked().diagnostics]

        self.assertEqual(2, len(problems))
        self.assertIn(".agents/skills/gone/SKILL.md", problems[0])
        self.assertIn("whose declaration does not name it", problems[1])


class AMomentsRow(Declared):
    def moments(self, *rows: str) -> str:
        header = "| moment | instructed by | kind, and why |\n|---|---|---|\n"
        return header + "".join(rows)

    def test_saying_not_yet_must_name_a_question(self) -> None:
        self.write(
            DOC,
            self.doc(moments=self.moments("| sweeping | — | not yet — nobody sweeps yet |\n")),
        )

        problems = self.problems()

        self.assertEqual(1, len(problems))
        self.assertIn("unbound", problems[0])
        self.assertIn("sweeping", problems[0])

    def test_saying_not_yet_must_name_a_question_the_store_holds(self) -> None:
        self.write(DOC, self.doc(moments=self.moments('| sweeping | — | <straw-dog question="q-0099">not yet</straw-dog> |\n')))

        problems = self.problems()

        self.assertTrue(any("q-0099" in problem and "no entry" in problem for problem in problems), problems)

    def test_saying_embedded_names_the_body_the_instruction_sits_in(self) -> None:
        sitting_here = f"| archiving | — | embedded — another mechanism's rule, here until installed, `{INSTRUCTION}` |\n"
        self.write(DOC, self.doc(moments=self.moments(sitting_here)))
        self.assertEqual([], self.checked().diagnostics)

        sitting_nowhere = sitting_here.replace(INSTRUCTION, ".agents/skills/gone/SKILL.md")
        self.write(DOC, self.doc(moments=self.moments(sitting_nowhere)))

        problems = self.problems()

        self.assertEqual(1, len(problems))
        self.assertIn(".agents/skills/gone/SKILL.md", problems[0])
        self.assertIn("does not resolve", problems[0])

    def test_takes_the_first_code_span_as_the_referent(self) -> None:
        # The format's rule: one code span per absence cell. A skill named in backticks before
        # the path is what the check resolves, and it is reported rather than skipped over.
        self.write(
            DOC,
            self.doc(
                moments=self.moments(
                    f"| archiving | — | elsewhere — `/other` owns it, `{INSTRUCTION}` |\n"
                )
            ),
        )

        problems = self.problems()

        self.assertEqual(1, len(problems))
        self.assertIn("names /other", problems[0])
        self.assertIn("does not resolve", problems[0])

    def test_declaring_a_kind_outside_the_vocabulary_is_reported_as_that(self) -> None:
        self.write(
            DOC, self.doc(moments=self.moments("| sweeping | — | someday — we will get to it |\n"))
        )

        problems = self.problems()

        self.assertEqual(1, len(problems))
        self.assertIn("someday", problems[0])

    def test_declaring_a_kind_without_saying_why_is_reported(self) -> None:
        self.write(DOC, self.doc(moments=self.moments("| sweeping | — | unowned by design |\n")))

        problems = self.problems()

        self.assertEqual(1, len(problems))
        self.assertIn("why", problems[0])

    def test_carrying_both_an_instruction_and_an_absence_is_reported(self) -> None:
        self.write(
            DOC,
            self.doc(
                moments=self.moments(
                    f"| doing the thing | `{INSTRUCTION}` | unowned by design — nobody acts |\n"
                )
            ),
        )

        problems = self.problems()

        self.assertEqual(1, len(problems))
        self.assertIn("both", problems[0])

    def test_carrying_neither_is_reported(self) -> None:
        self.write(DOC, self.doc(moments=self.moments("| sweeping | — | |\n")))

        problems = self.problems()

        self.assertEqual(1, len(problems))
        self.assertIn("neither", problems[0])

    def test_saying_unowned_by_design_may_not_carry_a_referent(self) -> None:
        self.write(
            DOC,
            self.doc(
                moments=self.moments(
                    f"| looking a path up | — | unowned by design — `{INSTRUCTION}` does it |\n"
                )
            ),
        )

        problems = self.problems()

        self.assertEqual(1, len(problems))
        self.assertIn("unowned by design", problems[0])


class TheHeader(Declared):
    def test_ends_at_the_first_section_so_prose_cannot_restate_a_bullet(self) -> None:
        hijacked = "- **instruction** `.agents/skills/hijacked/SKILL.md` — in prose\n"
        self.write(DOC, self.doc().replace("Prose nothing parses.", hijacked))

        checked = self.checked()

        self.assertEqual(INSTRUCTION, checked.declarations[0].instruction)
        self.assertEqual([], checked.diagnostics)

    def test_states_one_of_the_two_states_a_mechanism_can_be_in(self) -> None:
        with self.subTest(state="installed"):
            self.write(DOC, self.doc().replace("- **state** always on", "- **state** installed"))

            checked = self.checked()

            self.assertEqual([], checked.diagnostics)
            self.assertEqual("installed", checked.declarations[0].state)

        with self.subTest(state="occasionally on"):
            self.write(DOC, self.doc().replace("- **state** always on", "- **state** occasionally on"))

            problems = self.problems()

            self.assertEqual(1, len(problems))
            self.assertIn("occasionally on", problems[0])

    def test_carries_the_doc_s_kind_so_an_agent_editing_it_meets_the_kind_in_context(self) -> None:
        with self.subTest(kind="missing"):
            self.write(DOC, self.doc().replace("- **record of** what must always hold\n", ""))

            problems = self.problems()

            self.assertEqual(1, len(problems))
            self.assertIn("names no kind", problems[0])

        with self.subTest(kind="another"):
            self.write(DOC, self.doc().replace("- **record of** what must always hold", "- **record of** what exists"))

            problems = self.problems()

            self.assertEqual(1, len(problems))
            self.assertIn("what exists", problems[0])
            self.assertIn("what must always hold", problems[0])

        with self.subTest(kind="under the mark's old name"):
            self.write(DOC, self.doc().replace("- **record of** what must always hold", "- **kind** what must always hold"))

            problems = self.problems()

            self.assertEqual(1, len(problems))
            self.assertIn("`- **kind**`", problems[0])
            self.assertIn("`- **record of** what must always hold`", problems[0])


class TheRulesFile(Declared):
    def test_is_found_by_its_name_rather_than_by_a_bullet_declaring_it(self) -> None:
        self.write(f"{MECHANISMS}/{SLUG}/{SLUG}.rules.md", "# The rules, one section each\n")

        checked = self.checked()

        self.assertEqual([], checked.diagnostics)
        self.assertEqual(f"{MECHANISMS}/{SLUG}/{SLUG}.rules.md", checked.declarations[0].rules)

    def test_under_a_name_the_injector_would_never_find_is_reported(self) -> None:
        self.write(f"{MECHANISMS}/{SLUG}/rules.md", "# The rules, misfiled\n")

        problems = self.problems()

        self.assertEqual(1, len(problems))
        self.assertIn("rules.md", problems[0])


class TheDoc(Declared):
    def test_is_required_by_the_directory_that_should_hold_it(self) -> None:
        (self.root / MECHANISMS / "orphan").mkdir(parents=True)

        problems = self.problems()

        self.assertEqual(1, len(problems))
        self.assertIn("orphan", problems[0])

    def test_must_name_what_would_show_the_mechanism_working(self) -> None:
        self.write(DOC, self.doc(grading="## What retires this, again\n\nNothing.\n"))

        problems = self.problems()

        self.assertEqual(1, len(problems))
        self.assertIn("show it working", problems[0])

    def test_must_account_for_what_the_mechanism_produces(self) -> None:
        self.write(DOC, self.doc(produces=""))

        problems = self.problems()

        self.assertEqual(1, len(problems))
        self.assertIn("produces", problems[0])

    def test_names_the_kind_of_each_output_it_lists(self) -> None:
        produces = "## What it produces, and who reads it\n\n{bullets}\nNothing else is emitted.\n"
        admitted = (
            "- **The report** — *what exists* — read by whoever ran it.\n"
            "- **The rules file**, `sample.rules.md` — *what must always hold* — read by the installer.\n"
            "- **The entries** — *what it intends to become, what happened once closed* — read by all.\n"
            "- **The evidence** — *what happened* — read at amend time.\n"
            "- **Repaired files** — *its format's* — read by whoever reads them next,\n"
            "  the report naming each repair.\n"
        )
        with self.subTest(outputs="each kind admitted"):
            self.write(DOC, self.doc(produces=produces.format(bullets=admitted)))

            self.assertEqual([], self.problems())

        with self.subTest(outputs="one with no kind"):
            self.write(DOC, self.doc(produces=produces.format(bullets="- **The report** — read by whoever ran it.\n")))

            problems = self.problems()

            self.assertEqual(1, len(problems))
            self.assertIn("'The report' names no kind", problems[0])

        with self.subTest(outputs="one with a kind the format does not admit"):
            self.write(DOC, self.doc(produces=produces.format(bullets="- **The report** — *ephemeral* — read by whoever ran it.\n")))

            problems = self.problems()

            self.assertEqual(1, len(problems))
            self.assertIn("'The report' names a kind the format does not admit", problems[0])
            self.assertIn("ephemeral", problems[0])

    def test_reads_only_bullets_so_prose_beside_them_names_no_output(self) -> None:
        prose = (
            "## What it produces, and who reads it\n\n"
            "- **The report** — *what exists* — read by whoever ran it.\n"
            "  - **a nested note** — no kind, and not an output of its own\n\n"
            "The declaration, read by whoever amends this — **not** a bullet.\n"
        )
        self.write(DOC, self.doc(produces=prose))

        self.assertEqual([], self.problems())

    def test_must_carry_a_moments_table(self) -> None:
        self.write(DOC, self.doc(moments="Every moment here is instructed.\n"))

        problems = self.problems()

        self.assertEqual(1, len(problems))
        self.assertIn("Moments", problems[0])

    def test_reports_a_table_that_is_missing_a_column(self) -> None:
        self.write(
            DOC,
            self.doc(
                moments="| moment | kind, and why |\n|---|---|\n| sweeping | unowned by design — nobody acts |\n"
            ),
        )

        problems = self.problems()

        self.assertEqual(1, len(problems))
        self.assertIn("instructed by", problems[0])

    def test_reports_a_row_whose_cells_do_not_match_the_header(self) -> None:
        self.write(
            DOC,
            self.doc(
                moments="| moment | instructed by | kind, and why |\n|---|---|---|\n"
                "| sweeping | — |\n"
            ),
        )

        problems = self.problems()

        self.assertEqual(1, len(problems))
        self.assertIn("2", problems[0])
        self.assertIn("3", problems[0])

    def test_reads_an_escaped_pipe_as_part_of_a_cell_not_as_a_column(self) -> None:
        self.write(
            DOC,
            self.doc(
                moments="| moment | instructed by | kind, and why |\n|---|---|---|\n"
                f"| choosing install \\| retract | `{INSTRUCTION}` | |\n"
            ),
        )

        checked = self.checked()

        self.assertEqual([], checked.diagnostics)
        self.assertEqual("choosing install | retract", checked.declarations[0].moments[0].occasion)


class TheCommandLine(Declared):
    def run_check(self, *operands: str) -> tuple[int, str]:
        said = io.StringIO()
        with contextlib.redirect_stdout(said), contextlib.redirect_stderr(said):
            status = mechanisms.main(list(operands), root=self.root)
        return status, said.getvalue()

    def test_refuses_a_bare_invocation_rather_than_choosing_a_mode(self) -> None:
        status, said = self.run_check()

        self.assertEqual(2, status)
        self.assertIn("--check", said)
        self.assertIn("--index", said)
        self.assertNotIn(SLUG, said)

    def test_refuses_a_scope_operand_it_has_no_use_for(self) -> None:
        status, said = self.run_check("--check", "docs")

        self.assertEqual(2, status)
        self.assertIn("--check", said)

    def test_reports_a_true_declaration_as_clean(self) -> None:
        status, said = self.run_check("--check")

        self.assertEqual(0, status)
        reported = json.loads(said)
        self.assertEqual([], reported["diagnostics"])
        self.assertEqual(SLUG, reported["declarations"][0]["mechanism"])

    def test_reports_a_false_declaration_with_a_non_zero_status(self) -> None:
        self.write(
            DOC, self.doc(parts="| part | where |\n|---|---|\n| a script | `.agents/gone.py` |\n")
        )

        status, said = self.run_check("--check")

        self.assertEqual(1, status)
        self.assertIn(".agents/gone.py", json.loads(said)["diagnostics"][0]["problem"])


class TheIndex(Declared):
    def rendered(self) -> str:
        said = io.StringIO()
        with contextlib.redirect_stdout(said):
            mechanisms.main(["--index"], root=self.root)
        return said.getvalue()

    def test_has_one_row_for_each_directory_and_no_others(self) -> None:
        second = f"{MECHANISMS}/paired-close/paired-close.md"
        self.write(second, "# paired-close — a ticket and its RFC close together\n")

        rendered = self.rendered()

        rows = [line for line in rendered.splitlines() if line.startswith("| ")]
        self.assertEqual(3, len(rows))  # header plus one row per directory
        self.assertIn(SLUG, rendered)
        self.assertIn("one line saying what it is", rendered)
        self.assertIn("paired-close", rendered)

    def test_is_rendered_without_writing_it_or_reading_a_committed_copy(self) -> None:
        self.write(f"{MECHANISMS}/README.md", "| mechanism |\n|---|\n| a stale copy |\n")
        untouched = self.snapshot()

        rendered = self.rendered()

        self.assertNotIn("a stale copy", rendered)
        self.assertEqual(untouched, self.snapshot())

    def test_reports_a_doc_it_cannot_read_rather_than_dropping_the_row(self) -> None:
        self.write(f"{MECHANISMS}/unreadable/unreadable.md", "no heading, no bullets\n")

        rendered = self.rendered()

        self.assertIn("unreadable", rendered)
        rows = [line for line in rendered.splitlines() if line.startswith("| ")]
        self.assertEqual(3, len(rows))


STRAY = ".agents/skills/stray/SKILL.md"
FRONTMATTER = "---\nname: stray\ndescription: a skill nothing names\n---\n\n"
CLAIMING = '<straw-dog question="q-0002">Mechanism: not yet</straw-dog>\n\n# Stray\n'


class TheReversePass(Declared):
    """Every installed skill is one mechanism's instruction file, or says on its first line that none is."""

    def test_a_skill_nothing_names_that_claims_nothing_fails_the_run(self) -> None:
        self.write(STRAY, FRONTMATTER + "# Stray\n")

        problems = self.checked().diagnostics

        self.assertEqual(1, len(problems))
        self.assertEqual(".agents/skills/stray/", problems[0].mechanism)
        self.assertIn("no mechanism names it and it claims nothing", problems[0].problem)

    def test_a_skill_claiming_not_yet_passes_and_the_report_shows_the_claim(self) -> None:
        self.write(STRAY, FRONTMATTER + CLAIMING)

        checked = self.checked()

        self.assertEqual([], checked.diagnostics)
        stray = next(skill for skill in checked.skills if skill.directory == ".agents/skills/stray/")
        self.assertEqual(([], "not yet", SWEEPING, "q-0002"),
                         (stray.named_by, stray.claim.kind, stray.claim.why, stray.claim.referent))
        sample = next(skill for skill in checked.skills if skill.directory == ".agents/skills/sample/")
        self.assertEqual(([SLUG], None, SLUG), (sample.named_by, sample.claim.kind, sample.claim.why))

    def test_the_claim_is_read_past_the_frontmatter_and_without_one(self) -> None:
        self.write(STRAY, CLAIMING)

        self.assertEqual([], self.checked().diagnostics)

    def test_a_skill_both_named_and_claiming_is_reported_as_two_claims(self) -> None:
        self.write(INSTRUCTION, CLAIMING)

        problems = self.problems()

        self.assertEqual(1, len(problems))
        self.assertIn(f"named by {SLUG} and claims not yet", problems[0])

    def test_a_skill_two_declarations_name_is_reported_with_both(self) -> None:
        other = f"{MECHANISMS}/other-shape/other-shape.md"
        self.write(other, self.doc(parts=PARTS.replace(f"| the script | `{SCRIPT}` |\n", "")).replace(SLUG, "other-shape", 1))

        problems = self.problems()

        # The skill names one of the two, so the other's naming check reports it as well.
        self.assertEqual(2, len(problems))
        self.assertIn("named by other-shape and sample-shape", problems[0])
        self.assertIn(f"{INSTRUCTION} names {SLUG}", problems[1])

    def test_a_claim_pointing_at_an_owner_is_not_a_claim(self) -> None:
        self.write(STRAY, FRONTMATTER + f"Mechanism: elsewhere — `{INSTRUCTION}` owns it\n")

        problems = self.problems()

        self.assertEqual(1, len(problems))
        self.assertIn("claims elsewhere", problems[0])

    def test_an_unbound_claim_is_reported_like_an_unbound_moment(self) -> None:
        self.write(STRAY, FRONTMATTER + "Mechanism: not yet — someday\n")

        problems = self.problems()

        self.assertEqual(1, len(problems))
        self.assertIn("unbound", problems[0])

    def test_unowned_by_design_is_a_claim_that_is_kept(self) -> None:
        self.write(STRAY, FRONTMATTER + "Mechanism: unowned by design — a one-off nobody relies on\n")

        self.assertEqual([], self.checked().diagnostics)

    def test_a_skill_naming_a_mechanism_whose_declaration_does_not_name_it_is_reported(self) -> None:
        self.write(STRAY, FRONTMATTER + f"Mechanism: {SLUG}\n")

        problems = self.problems()

        self.assertEqual(1, len(problems))
        self.assertIn(f"names {SLUG}, whose declaration does not name it", problems[0])


class APartNamesItsMechanism(Declared):
    """Every skill, script, test and hook a mechanism owns opens with `Mechanism: <slug>`, so an agent
    editing it meets the doc that governs it; the check holds the line to the parts table both ways
    (the user, 2026-10-11)."""

    def test_a_named_skill_and_an_owned_script_opening_with_the_slug_pass(self) -> None:
        self.assertEqual([], self.problems())

    def test_a_named_skill_opening_with_no_line_is_reported(self) -> None:
        self.write(INSTRUCTION, "# Sample\n")

        self.assertEqual([f"{INSTRUCTION} names no mechanism"], self.problems())

    def test_a_named_skill_opening_with_another_slug_is_reported(self) -> None:
        self.write(INSTRUCTION, "Mechanism: other-shape\n\n# Sample\n")

        self.assertEqual([f"{INSTRUCTION} names other-shape"], self.problems())

    def test_the_skill_s_line_is_read_past_its_frontmatter(self) -> None:
        self.write(INSTRUCTION, FRONTMATTER + NAMED_SKILL)

        self.assertEqual([], self.problems())

    def test_an_owned_script_opening_with_no_line_is_reported(self) -> None:
        self.write(SCRIPT, '"""The sample\'s script."""\n')

        self.assertEqual([f"{SCRIPT} names no mechanism"], self.problems())

    def test_an_owned_script_naming_another_mechanism_is_reported_from_both_sides(self) -> None:
        self.write(SCRIPT, '# Mechanism: other-shape\n"""The sample\'s script."""\n')

        self.assertEqual(
            sorted([f"{SCRIPT} names other-shape", f"{SCRIPT} names other-shape, whose parts do not list it"]),
            sorted(self.problems()),
        )

    def test_a_shebang_comes_first_and_the_line_after_it(self) -> None:
        hook = ".agents/scripts/gw/hook.sh"
        self.write(DOC, self.doc(parts=PARTS + f"| the hook | `{hook}` |\n"))
        self.write(hook, f"#!/bin/sh\n# Mechanism: {SLUG}\nexit 0\n")

        self.assertEqual([], self.problems())

    def test_a_script_no_mechanism_lists_naming_one_is_reported(self) -> None:
        stray = ".agents/scripts/gw/stray.py"
        self.write(stray, f"# Mechanism: {SLUG}\n")

        self.assertEqual([f"{stray} names {SLUG}, whose parts do not list it"], self.problems())

    def test_a_script_no_mechanism_lists_and_naming_none_is_not_this_check_s(self) -> None:
        self.write(".agents/scripts/gw/stray.py", '"""Nobody\'s."""\n')

        self.assertEqual([], self.problems())

    def test_a_part_outside_the_scripts_and_not_the_skill_carries_no_line(self) -> None:
        shelf = ".agents/skills/sample/SAMPLE-FORMAT.md"
        self.write(DOC, self.doc(parts=PARTS + f"| format shelf | `{shelf}` |\n"))
        self.write(shelf, "# Sample format\n")

        self.assertEqual([], self.problems())


DOCUMENT = "docs/tickets/01-0001-sample.md"
CITING = ".agents/skills/sample/NOTES.md"


class CoreStandsAlone(Declared):
    """Core may name a painted door under `docs/` and nothing else — AGENTS.md § Core and instance."""

    def leaks(self) -> list[tuple[str, int, str]]:
        return [(c.file, c.line, c.cites) for c in self.checked().cites if c.standing == "leak"]

    def standing(self, standing: str, file: str = CITING) -> list[str]:
        """What one file's mentions stand as."""
        return [c.cites for c in self.checked().cites if c.standing == standing and c.file == file]

    def cites_from(self, file: str) -> list[str]:
        return [c.cites for c in self.checked().cites if c.file == file]

    def test_a_link_to_a_particular_document_fails_the_run_naming_the_line_and_the_rule(self) -> None:
        self.write(CITING, f"# Notes\n\nSee [the ticket](../../../{DOCUMENT}).\n")

        problems = self.problems()

        self.assertEqual(1, len(problems))
        self.assertIn(f"{CITING}:3 cites {DOCUMENT}", problems[0])
        self.assertIn("Core and instance", problems[0])
        self.assertEqual([(CITING, 3, DOCUMENT)], self.leaks())

    def test_a_stamped_source_is_not_a_citation_however_much_it_looks_like_one(self) -> None:
        # A recipient installed from a clone kept under a `docs/` directory carries that path in
        # its harness skill. Read as a citation it would be a document only the origin has, and
        # the tree would fail its own shape check for as long as it held it.
        self.write(CITING, "# Notes\n\nRepository: /srv/docs/goodwolf-harness\n")

        self.assertEqual([], self.problems())
        self.assertEqual([], self.cites_from(CITING))

    def test_a_docs_path_on_a_line_that_only_looks_stamped_is_still_a_citation(self) -> None:
        self.write(CITING, f"# Notes\n\nRepository: /srv/x and also {DOCUMENT}\n")

        self.assertEqual([(CITING, 3, DOCUMENT)], self.leaks())

    def test_a_painted_door_passes_and_is_reported_as_one(self) -> None:
        self.write(CITING, "# Notes\n\nThe queue is `docs/tickets/README.md`, under docs/tickets.\n")

        self.assertEqual([], self.problems())
        self.assertEqual(["docs/tickets/README.md", "docs/tickets"], self.standing("painted door"))

    def test_a_directory_row_covers_itself_and_not_a_path_beneath_it(self) -> None:
        self.write(CITING, f"# Notes\n\n`docs/tickets/` holds `{DOCUMENT}`.\n")

        self.assertEqual([(CITING, 3, DOCUMENT)], self.leaks())
        self.assertEqual(["docs/tickets/"], self.standing("painted door"))

    def test_a_citation_inside_the_local_block_is_skipped_and_reported(self) -> None:
        self.write(CITING, f'# Notes\n\n<installed by="local">\nSee [it](../../../{DOCUMENT}).\n</installed>\n')

        self.assertEqual([], self.problems())
        self.assertEqual([DOCUMENT], self.standing("skipped"))

    def test_the_front_page_beside_the_harness_skill_is_the_origins_document_and_its_citations_are_skipped(self) -> None:
        # Beside a skill the fixture claims, as the real one stands beside the harness skill.
        self.write(".agents/skills/harness/SKILL.md", "Mechanism: unowned by design — a fixture.\n")
        self.write(mechanisms.FRONT_PAGE, f"# Front\n\nThe evidence: [panel]({DOCUMENT}).\n")

        self.assertEqual([], self.problems())
        self.assertEqual([DOCUMENT], self.standing("skipped", mechanisms.FRONT_PAGE))

    def test_a_project_local_block_is_a_retired_tag_and_excuses_nothing(self) -> None:
        self.write(CITING, f"# Notes\n\n<project-local>\n`{DOCUMENT}`\n</project-local>\n")

        problems = self.problems()

        self.assertEqual(2, len(problems), problems)
        self.assertTrue(any(f"{CITING}:3 writes a <project-local> block" in note for note in problems), problems)
        self.assertEqual([(CITING, 4, DOCUMENT)], self.leaks())

    def test_a_citation_inside_a_straw_dog_is_a_leak_and_its_binding_is_not(self) -> None:
        self.write(
            CITING,
            f'# Notes\n\n<straw-dog question="q-0002">\n'
            f"See [it](../../../{DOCUMENT}).\n</straw-dog>\n",
        )

        self.assertEqual([(CITING, 4, DOCUMENT)], self.leaks())

    def test_a_fence_is_an_illustration_and_a_code_span_is_a_claim(self) -> None:
        self.write(CITING, f"# Notes\n\n```\n[x](../../../{DOCUMENT})\n```\n\nBut `{DOCUMENT}` is.\n")

        self.assertEqual([(CITING, 7, DOCUMENT)], self.leaks())

    def test_a_tag_written_in_a_code_span_is_neither_a_block_nor_a_retired_tag(self) -> None:
        self.write(CITING, f"# Notes\n\nEvery `<project-local>` block.\n\nSee [it](../../../{DOCUMENT}).\n")

        self.assertEqual([(CITING, 5, DOCUMENT)], self.leaks())
        self.assertEqual(1, len(self.problems()))

    def test_a_trailing_full_stop_is_not_part_of_the_path(self) -> None:
        self.write(CITING, "# Notes\n\nWrite it under docs/sessions.\n")

        self.assertEqual([], self.problems())
        self.assertEqual(["docs/sessions"], self.standing("painted door"))

    def test_a_citation_outside_docs_is_not_this_checks_business(self) -> None:
        self.write(CITING, "# Notes\n\nSee [the skill](./SKILL.md) and [the entry file](../../../AGENTS.md).\n")

        self.assertEqual([], self.problems())
        self.assertEqual([], self.cites_from(CITING))

    def test_a_todo_binds_its_question_and_a_ticket_path_in_one_is_a_leak(self) -> None:
        self.write(".agents/scripts/later.py", "# TODO q-0002: the shear strips this\nX = 1\n")
        self.assertEqual([], self.problems())

        self.write(".agents/scripts/later.py", "# TODO docs/tickets/01-0002-sweep.md: bound the old way\nX = 1\n")

        self.assertEqual([(".agents/scripts/later.py", 1, "docs/tickets/01-0002-sweep.md")], self.leaks())

    def test_a_string_literal_in_code_naming_a_document_fails(self) -> None:
        self.write(".agents/scripts/later.py", f'# a note\nNAME = "{DOCUMENT}"\n')

        self.assertEqual([(".agents/scripts/later.py", 2, DOCUMENT)], self.leaks())

    def test_a_test_file_is_fixture_data_and_is_not_read(self) -> None:
        self.write(".agents/scripts/gw/test/test_later.py", f'NAME = "{DOCUMENT}"\n')

        self.assertEqual([], self.problems())

    def test_a_python_file_that_cannot_be_read_is_a_diagnostic_not_a_pass(self) -> None:
        self.write(".agents/scripts/later.py", 'X = """never closed\n')

        problems = self.problems()

        self.assertEqual(1, len(problems))
        self.assertIn(".agents/scripts/later.py could not be read", problems[0])

    def test_the_entry_file_is_core_and_is_read(self) -> None:
        self.write("AGENTS.md", f"- Doing it {TRIGGER} /sample; see [it](./{DOCUMENT}).\n")

        self.assertEqual([("AGENTS.md", 1, DOCUMENT)], self.leaks())

    def test_the_report_carries_the_three_classes_and_no_total(self) -> None:
        self.write(CITING, f'# Notes\n\n<installed by="local">\n`{DOCUMENT}`\n</installed>\n`docs/adr/` and `{DOCUMENT}`.\n')

        report = self.checked().as_record()["core cites"]

        self.assertEqual({"painted doors", "skipped", "leaks"}, set(report))
        self.assertEqual(
            [{"file": CITING, "line": 4, "cites": DOCUMENT}],
            [entry for entry in report["skipped"] if entry["file"] == CITING],
        )
        self.assertEqual([{"file": CITING, "line": 6, "cites": "docs/adr/"}], report["painted doors"])
        self.assertEqual([{"file": CITING, "line": 6, "cites": DOCUMENT}], report["leaks"])


class InARecipient(Declared):
    """A tree whose entry file announces `<repository>@<ref>` received core by install: the shear
    stripped every binding and reason on the way, so an unbound `not yet` there is upstream's gap."""

    STAMPED = "Entry contract: goodwolf-harness@d441bed, 2026-09-20.\n\n"

    def setUp(self) -> None:
        super().setUp()
        self.write("AGENTS.md", self.STAMPED + f"- Doing it {TRIGGER} /sample.\n")

    def sheared_row(self) -> str:
        return "| moment | instructed by | kind, and why |\n|---|---|---|\n| sweeping | — | not yet |\n"

    def test_an_unbound_not_yet_row_draws_nothing(self) -> None:
        self.write(DOC, self.doc(moments=self.sheared_row()))

        checked = self.checked()

        self.assertEqual([], checked.diagnostics)
        self.assertEqual(("not yet", "", None), tuple(
            (row.kind, row.why, row.referent) for row in checked.declarations[0].moments
        )[0])

    def test_an_unbound_claim_draws_nothing(self) -> None:
        self.write(STRAY, FRONTMATTER + "Mechanism: not yet\n")

        self.assertEqual([], self.checked().diagnostics)

    def test_the_origin_line_keeps_both_diagnostics(self) -> None:
        self.write("AGENTS.md", "Entry contract: v14, 2026-09-20.\n\n" + f"- Doing it {TRIGGER} /sample.\n")
        self.write(DOC, self.doc(moments=self.sheared_row()))

        problems = self.problems()

        self.assertEqual(2, len(problems))
        self.assertTrue(any("unbound" in problem for problem in problems))
        self.assertTrue(any("does not say why" in problem for problem in problems))

    def test_a_recipients_own_leak_and_silent_skill_still_fail(self) -> None:
        self.write(STRAY, FRONTMATTER + "# Stray\n\nSee docs/tickets/01-0002-sweep.md.\n")

        problems = self.problems()

        self.assertEqual(2, len(problems))
        self.assertTrue(any("claims nothing" in problem for problem in problems))
        self.assertTrue(any("only the instance has" in problem for problem in problems))


if __name__ == "__main__":
    unittest.main()
