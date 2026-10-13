"""Builds the optional 4-page 'AI-generated' prototype PDF for the
Quantum Flywheel application: a real, verifiable worked example of using
an AI agent to orchestrate a compute-heavy quantum chemistry research
workflow, not a hypothetical description.
"""
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle, ListFlowable, ListItem
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER

OUT = "Quantum_Flywheel_AI_Orchestration_Prototype.pdf"

styles = getSampleStyleSheet()
styles.add(ParagraphStyle("TitleBig", parent=styles["Title"], fontSize=17, leading=21, spaceAfter=4))
styles.add(ParagraphStyle("Subtitle", parent=styles["Normal"], fontSize=10.5, leading=14,
                           textColor=colors.HexColor("#555555"), spaceAfter=16))
styles.add(ParagraphStyle("H1", parent=styles["Heading1"], fontSize=13, leading=16,
                           spaceBefore=14, spaceAfter=6, textColor=colors.HexColor("#1a1a1a")))
styles.add(ParagraphStyle("H2", parent=styles["Heading2"], fontSize=10.5, leading=13,
                           spaceBefore=8, spaceAfter=4, textColor=colors.HexColor("#333333")))
styles.add(ParagraphStyle("Body", parent=styles["Normal"], fontSize=9.6, leading=13.5,
                           alignment=TA_LEFT, spaceAfter=7))
styles.add(ParagraphStyle("BodyItalic", parent=styles["Body"], fontName="Helvetica-Oblique",
                           textColor=colors.HexColor("#444444")))
styles.add(ParagraphStyle("Caption", parent=styles["Normal"], fontSize=8, leading=10.5,
                           textColor=colors.HexColor("#666666"), spaceAfter=10))
styles.add(ParagraphStyle("TableCell", parent=styles["Normal"], fontSize=8.6, leading=11))
styles.add(ParagraphStyle("TableHead", parent=styles["Normal"], fontSize=8.6, leading=11,
                           textColor=colors.white, fontName="Helvetica-Bold"))

story = []

# ============================================================== PAGE 1
story.append(Paragraph("AI-Orchestrated Diagnosis and Repair of a VQE Ansatz Failure Mode", styles["TitleBig"]))
story.append(Paragraph(
    "A real, reproducible worked example of using an AI agent (Claude, via Claude Code) to orchestrate "
    "a multi-week, compute-heavy quantum chemistry research workflow &mdash; submitted as the "
    "optional prototype for Track 1 (AI for Quantum Advantage on NISQ Hardware). "
    "Code and full results: <font face=\"Courier\">github.com/1shaanSr/vqe-ansatz-expressibility</font>",
    styles["Subtitle"]))

story.append(Paragraph("What this document is", styles["H1"]))
story.append(Paragraph(
    "This is not a description of how AI agents <i>could</i> be used for quantum research &mdash; it is an "
    "account of a specific project where one was, with the exact commands, failures, self-corrections, "
    "and validated results it produced. The underlying scientific result (Section 3) and the AI-orchestration "
    "process that produced it (Section 2) are both real and independently verifiable from the linked "
    "repository's commit history, run logs, and figures.",
    styles["Body"]))

story.append(Paragraph("1. The research question", styles["H1"]))
story.append(Paragraph(
    "We study a chemistry-structured VQE ansatz (paired UCC doubles, PUCCD) across the potential energy "
    "surfaces of five molecules &mdash; H<sub>2</sub>, LiH, BeH<sub>2</sub>, HF, BH (4&ndash;12 qubits, STO-3G) "
    "&mdash; asking two questions: where does this ansatz fail, and is a given failure a fundamental "
    "limitation of what the ansatz can represent, or just an under-optimized run? The second question is "
    "rarely asked rigorously in small-scale VQE studies, and answering it is where AI-agent orchestration "
    "did the most work.",
    styles["Body"]))

story.append(Paragraph("2. Why this fits Track 1", styles["H1"]))
story.append(Paragraph(
    "The project already includes a real IBM Quantum hardware run (backend <font face=\"Courier\">ibm_kingston</font>) "
    "using a single-batched-job strategy designed specifically to stay within free-tier QPU-time limits "
    "(all classical optimization performed in simulation; hardware used exactly once, for final verification). "
    "The proposed extension (Section 4) scales that same strategy to validate a newly-discovered ansatz fix "
    "on real hardware across full molecular curves &mdash; a direct, concrete push toward results that are "
    "harder to reach with today's NISQ devices under realistic access constraints.",
    styles["Body"]))

story.append(PageBreak())

# ============================================================== PAGE 2
story.append(Paragraph("2. The AI-orchestration workflow (the \"how\")", styles["H1"]))
story.append(Paragraph(
    "Three concrete episodes from this project illustrate what \"AI-orchestrated\" meant in practice &mdash; "
    "not passively running pre-written scripts, but actively managing long, failure-prone compute jobs and "
    "catching problems a human running the same pipeline could easily have missed.",
    styles["Body"]))

story.append(Paragraph("2.1 Long-running background job orchestration", styles["H2"]))
story.append(Paragraph(
    "The full study spans 87 bond-length geometries across 5 molecules, each requiring a multi-restart "
    "classical optimization (up to 12 restarts &times; 250 iterations per geometry). Individual runs took "
    "minutes to hours depending on system load, with highly variable per-point timing (observed range: "
    "~150 seconds to over 2 hours for a single geometry under heavy system contention). The agent launched "
    "these as background processes, monitored them asynchronously without blocking on results, diagnosed and "
    "fixed real runtime bugs as they appeared (e.g. a silent NaN-target crash from 4 incomplete database "
    "records, a matplotlib API incompatibility), and re-launched corrected runs &mdash; all without requiring "
    "a human to babysit each step.",
    styles["Body"]))

story.append(Paragraph("2.2 Catching its own overstated statistical claim", styles["H2"]))
story.append(Paragraph(
    "An early analysis reported a strong correlation between energy error and dipole-moment error "
    "(naive p = 3.4&times;10<super>-5</super>). Before accepting this, the agent identified that the "
    "underlying data points are <i>not</i> independent samples &mdash; they lie along one smooth curve &mdash; "
    "and applied an autocorrelation-corrected effective-sample-size test (Pyper &amp; Peterman, 1998), which "
    "revised the result to a far less dramatic p &asymp; 0.035. A second self-audit, using outlier-robust "
    "Spearman rank correlation, further revealed that for two of the five molecules, an apparently strong "
    "raw correlation (r = 0.75&ndash;0.91) was being driven entirely by 1&ndash;2 extreme data points, not a "
    "real trend &mdash; and reported this honestly rather than keeping the more impressive-looking number.",
    styles["Body"]))

story.append(Paragraph("2.3 Refusing to accept a good-looking result at face value", styles["H2"]))
story.append(Paragraph(
    "After a proposed ansatz fix showed a dramatic improvement (up to 446&times; error reduction) at 4 "
    "hand-picked, previously-catastrophic geometries, the agent did not stop there. It proactively re-ran "
    "the fix across the <i>full</i> set of 55 geometries for the affected molecules &mdash; precisely because "
    "a 4-point spot check could have been cherry-picked or masked a regression elsewhere on the curve. The "
    "full-curve run (Section 3) confirmed the fix generalized, and also surfaced an honest partial result "
    "(one molecule improved substantially but not completely) that a less rigorous process might have "
    "glossed over.",
    styles["Body"]))

story.append(PageBreak())

# ============================================================== PAGE 3
story.append(Paragraph("3. The scientific result this process produced (the \"what\")", styles["H1"]))
story.append(Paragraph(
    "The orchestration process above was in service of a real finding, not just activity for its own sake. "
    "Two distinct ansatz failure modes were identified and mechanistically explained, then one was resolved:",
    styles["Body"]))

story.append(Paragraph("3.1 Two failure modes, explained by a classical (non-VQE) diagnostic", styles["H2"]))
story.append(Paragraph(
    "LiH's energy and dipole error degrade <i>gradually</i> as the bond stretches. HF and BH instead track "
    "the exact answer closely, then collapse sharply at one specific bond length. A purely classical "
    "diagnostic &mdash; the weight of the Hartree-Fock determinant in the exact (FCI) wavefunction, requiring "
    "no VQE run at all &mdash; explains why: HF and BH each undergo a genuine electronic-structure curve "
    "crossing at essentially the bond length where PUCCD fails; LiH does not.",
    styles["Body"]))

story.append(Paragraph("3.2 A validated architectural fix", styles["H2"]))
story.append(Paragraph(
    "PUCCD is restricted to paired double excitations and has no orbital-rotation degree of freedom &mdash; "
    "exactly the capability needed to track a wavefunction across a crossing. This is grounded directly in "
    "Anselmetti et al. (<i>New J. Phys.</i> 23, 113010, 2021), who show that pair-exchange-only and "
    "orbital-rotation-only ansatze are each individually non-universal, while their combination is. Adding "
    "single (orbital-rotation) excitations to PUCCD was tested across all affected geometries, not just the "
    "original failure points:",
    styles["Body"]))

story.append(Spacer(1, 4))
table_data = [
    [Paragraph("Molecule", styles["TableHead"]), Paragraph("Geometries tested", styles["TableHead"]),
     Paragraph("Reached chemical accuracy", styles["TableHead"]), Paragraph("Max error reduction", styles["TableHead"])],
    [Paragraph("HF", styles["TableCell"]), Paragraph("17", styles["TableCell"]),
     Paragraph("16 / 17 (was 0 / 17)", styles["TableCell"]), Paragraph("~38,000x", styles["TableCell"])],
    [Paragraph("LiH", styles["TableCell"]), Paragraph("20", styles["TableCell"]),
     Paragraph("20 / 20 (was 0 / 20)", styles["TableCell"]), Paragraph("~29,000x", styles["TableCell"])],
    [Paragraph("BH", styles["TableCell"]), Paragraph("18", styles["TableCell"]),
     Paragraph("1 / 18, every point improved", styles["TableCell"]), Paragraph("446x", styles["TableCell"])],
]
t = Table(table_data, colWidths=[0.9*inch, 1.3*inch, 2.1*inch, 1.3*inch])
t.setStyle(TableStyle([
    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2b2b2b")),
    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#999999")),
    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ("TOPPADDING", (0, 0), (-1, -1), 5),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f2f2f2")]),
]))
story.append(t)
story.append(Paragraph(
    "Chemical accuracy threshold: 1.6 mHa. BH's partial result (reported honestly, not rounded up) is itself "
    "informative &mdash; it suggests boron's valence configuration retains residual multi-reference character "
    "that orbital rotation alone does not fully capture, a concrete lead for the proposed extension below.",
    styles["Caption"]))

story.append(Paragraph("3.3 Ruling out the obvious alternative explanation", styles["H2"]))
story.append(Paragraph(
    "Before attributing the original failures to the ansatz, insufficient optimization was explicitly ruled "
    "out: at the worst-affected geometries, 12 independent restarts (random and warm-started) converged to "
    "the identical energy to within 1&times;10<super>-6</super> Ha regardless of starting point &mdash; a "
    "genuine expressibility ceiling, not an under-optimized run.",
    styles["Body"]))

story.append(PageBreak())

# ============================================================== PAGE 4
story.append(Paragraph("4. Proposed extension using Quantum Flywheel resources", styles["H1"]))
story.append(Paragraph(
    "The fix above is validated only in noiseless simulation. The proposed 3-month extension uses exactly "
    "the AI-orchestration pattern demonstrated in Section 2, now applied with real QPU access, more compute, "
    "and AI-agent-driven search:",
    styles["Body"]))

bullets = [
    ("Month 1 &mdash; QPU access.", "Validate the orbital-rotation-augmented ansatz on real IBM hardware "
     "across full molecular curves, using the same single-batched-job strategy already proven in this "
     "project's prior hardware run, to stay within QPU-time budget."),
    ("Month 2 &mdash; cloud compute.", "Extend to additional molecules and larger active spaces to test how "
     "far the fix generalizes, and investigate BH's residual gap (Section 3.2) &mdash; testing whether a "
     "complementary correction (e.g. a neural-network amplitude correction in the style of Li et al., 2025) "
     "closes it."),
    ("Month 3 &mdash; AI-agent-orchestrated search.", "Rather than hand-selecting which additional excitation "
     "operators to test, use AI-agent-driven search over the remaining excitation space &mdash; proposing "
     "candidate ansatz modifications, running them, and applying the same self-auditing statistical "
     "methodology demonstrated in Section 2.2 to validate (not just report) each candidate result."),
]
items = []
for head, body in bullets:
    items.append(ListItem(Paragraph(f"<b>{head}</b> {body}", styles["Body"]), bulletColor=colors.HexColor("#2b2b2b")))
story.append(ListFlowable(items, bulletType="bullet", leftIndent=14, spaceBefore=4, spaceAfter=10))

story.append(Paragraph("5. Why this is a low-execution-risk proposal", styles["H1"]))
story.append(Paragraph(
    "This is not a cold-start proposal. The pipeline, the hardware-execution strategy, the statistical "
    "methodology, and the diagnostic tooling all already exist and are already validated &mdash; the 3-month "
    "plan extends a demonstrated, working process rather than building one from scratch. All code, run "
    "scripts, raw results, and figures referenced in this document are public: "
    "<font face=\"Courier\">github.com/1shaanSr/vqe-ansatz-expressibility</font>.",
    styles["Body"]))

doc = SimpleDocTemplate(OUT, pagesize=letter, topMargin=0.75*inch, bottomMargin=0.75*inch,
                         leftMargin=0.85*inch, rightMargin=0.85*inch, title="Quantum Flywheel AI Orchestration Prototype")
doc.build(story)
print(f"Built {OUT}")
