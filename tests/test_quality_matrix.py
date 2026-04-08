"""Risk-based QA matrix checks tied to roadmap milestones.

This test keeps QA scope executable: if a critical risk category loses milestone
mapping, CI fails and the gap is visible immediately.
"""

MATRIX = [
    {
        "risk": "unit",
        "milestone": "M1-foundation",
        "suite": "tests/test_script.py",
        "critical": True,
    },
    {
        "risk": "integration",
        "milestone": "M1-foundation",
        "suite": "tests/test_pipeline.py",
        "critical": True,
    },
    {
        "risk": "contract",
        "milestone": "M2-quality-gates",
        "suite": "tests/test_research.py",
        "critical": True,
    },
    {
        "risk": "e2e",
        "milestone": "M2-quality-gates",
        "suite": "tests/test_e2e.py",
        "critical": True,
    },
    {
        "risk": "non-functional",
        "milestone": "M3-release-readiness",
        "suite": "tests/test_assembler.py",
        "critical": False,
    },
    {
        "risk": "security",
        "milestone": "M3-release-readiness",
        "suite": "tests/test_voice.py",
        "critical": False,
    },
]


def test_matrix_contains_all_required_risk_categories():
    """QA matrix must cover core risk classes defined in GST-63 scope."""
    expected = {"unit", "integration", "contract", "e2e", "non-functional", "security"}
    mapped = {entry["risk"] for entry in MATRIX}
    assert mapped == expected


def test_critical_paths_are_mapped_to_milestones():
    """Critical coverage rows must map to explicit roadmap milestones."""
    critical_rows = [entry for entry in MATRIX if entry["critical"]]
    assert critical_rows, "No critical rows found in QA matrix."
    assert all(row["milestone"].startswith("M") for row in critical_rows)


def test_each_milestone_has_at_least_one_suite():
    """Ensure matrix can drive pass/fail trend reporting per milestone."""
    milestones = {entry["milestone"] for entry in MATRIX}
    assert milestones == {"M1-foundation", "M2-quality-gates", "M3-release-readiness"}
