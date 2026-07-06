"""
tests/test_adversarial.py
=========================
Adversarial data generator for SKACE-Time-Data academic validation.

Generates synthetic paradata covering four anomaly profiles defined in
thesis Section 5.1:

  - Normal      : log-normal RT (mu=ln(8000), sigma=0.5), Poisson back-nav
  - Fabricated  : compressed RT distributions, near-zero back-nav  [Wenz et al. 6]
  - Speeding    : RT scaled below realistic thresholds
  - Disengaged  : uniform slow RT, high pause frequency            [Conrad et al. 3]
  + DQ Issue    : sparse / zero-duration rows -> degenerate features

Interview IDs use a fixed mapping for reproducible ground-truth evaluation.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timezone, timedelta


class AdversarialDataGenerator:
    """
    Generates synthetic SurveyCTO and ODK audit log DataFrames for
    validation of the anomaly detection pipeline.

    Usage
    -----
    >>> gen = AdversarialDataGenerator(seed=42)
    >>> scto_df = gen.generate_adversarial_suite(is_odk=False)
    >>> odk_df  = gen.generate_adversarial_suite(is_odk=True)
    """

    # 2023-01-02 08:00:00 UTC in epoch-ms
    BASE_EPOCH_MS: int = 1672646400000
    N_QUESTIONS: int = 20
    # 1 hour between interview start times
    INTERVIEW_GAP_MS: int = 3_600_000

    SECTION_NAMES: list = [
        'demographics',  # q01-q04
        'household',     # q05-q08
        'health',        # q09-q12
        'economic',      # q13-q16
        'nutrition',     # q17-q20
    ]
    QUESTIONS_PER_SECTION: int = 4

    # Fixed per-question complexity multipliers for the 20-question instrument.
    # Real questionnaires mix short factual items (demographics) with longer
    # recall or calculation items (health, economic), so genuine respondents
    # produce complexity-correlated response times [Yan & Tourangeau 5].
    # Fabricated and speeding profiles deliberately ignore these weights:
    # complexity-blind uniform pacing is the fabrication signature [Wenz 6].
    COMPLEXITY_WEIGHTS: list = [
        0.50, 0.60, 0.55, 0.70,   # demographics: short factual items
        0.90, 1.00, 0.95, 1.10,   # household: roster-style items
        1.30, 1.40, 1.25, 1.35,   # health: recall-heavy items
        1.00, 1.15, 0.90, 1.05,   # economic: estimation items
        0.80, 0.85, 0.75, 0.90,   # nutrition: frequency items
    ]

    PROFILE_TO_EXPECTED_CATEGORY = {
        'normal': 'normal',
        'fabricated': 'anomalous',
        'speeding': 'anomalous',
        'disengaged': 'suspicious',
        'dq_issue': 'dq_issue',
    }

    BENCHMARK_INTERVIEW_GAP_MS: int = 600_000

    def __init__(self, seed: int = 42, difficulty: str = "canonical"):
        if difficulty not in {"canonical", "stress"}:
            raise ValueError("difficulty must be either 'canonical' or 'stress'")
        self.rng = np.random.default_rng(seed)
        self.difficulty = difficulty

    def _profile_plan(self, is_odk: bool = False) -> list:
        """Return the fixed interview-to-profile mapping for the canonical suite."""
        prefix = 'ODK' if is_odk else 'INT'
        base = self.BASE_EPOCH_MS
        step = self.INTERVIEW_GAP_MS
        return [
            (f'{prefix}400', 'normal',      base + 0  * step),
            (f'{prefix}401', 'fabricated',  base + 1  * step),
            (f'{prefix}402', 'dq_issue',    base + 2  * step),
            (f'{prefix}403', 'speeding',    base + 3  * step),
            (f'{prefix}404', 'disengaged',  base + 4  * step),
            (f'{prefix}405', 'normal',      base + 5  * step),
            (f'{prefix}406', 'normal',      base + 6  * step),
            (f'{prefix}407', 'fabricated',  base + 7  * step),
            (f'{prefix}408', 'dq_issue',    base + 8  * step),
            (f'{prefix}409', 'dq_issue',    base + 9  * step),
            (f'{prefix}410', 'disengaged',  base + 10 * step),
            (f'{prefix}411', 'speeding',    base + 11 * step),
        ]

    def build_ground_truth_labels(self, is_odk: bool = False) -> pd.DataFrame:
        """Build the ground-truth label table for one format."""
        records = []
        for interview_id, profile, _ in self._profile_plan(is_odk=is_odk):
            records.append({
                'interview_id': interview_id,
                'anomaly_type': profile,
                'expected_category': self.PROFILE_TO_EXPECTED_CATEGORY[profile],
                'is_anomalous_ground_truth': 0 if profile == 'normal' else 1,
            })
        return pd.DataFrame(records)

    def build_combined_ground_truth_labels(self) -> pd.DataFrame:
        """Build the combined SurveyCTO + ODK ground-truth table."""
        return pd.concat(
            [self.build_ground_truth_labels(is_odk=False),
             self.build_ground_truth_labels(is_odk=True)],
            ignore_index=True,
        )

    def build_benchmark_plan(self, dataset_size: int, anomaly_ratio: float = 0.2) -> list:
        """Build a randomized interview plan for a larger benchmark dataset."""
        if dataset_size <= 0:
            raise ValueError("dataset_size must be positive")
        if not 0 <= anomaly_ratio < 1:
            raise ValueError("anomaly_ratio must be in the range [0, 1)")

        n_anomalous = int(round(dataset_size * anomaly_ratio))
        n_normal = dataset_size - n_anomalous
        n_fabricated = n_anomalous // 3
        n_speeding = n_anomalous // 3
        n_disengaged = n_anomalous - n_fabricated - n_speeding

        profiles = (
            ['normal'] * n_normal +
            ['fabricated'] * n_fabricated +
            ['speeding'] * n_speeding +
            ['disengaged'] * n_disengaged
        )
        self.rng.shuffle(profiles)

        plan = []
        for idx, profile in enumerate(profiles, start=1):
            interview_id = f'INT-{idx:05d}'
            start_epoch = self.BASE_EPOCH_MS + (idx - 1) * self.BENCHMARK_INTERVIEW_GAP_MS
            plan.append((interview_id, profile, start_epoch))
        return plan

    def build_ground_truth_from_plan(self, plan: list) -> pd.DataFrame:
        """Build ground truth labels for a benchmark interview plan."""
        rows = []
        for interview_id, profile, _ in plan:
            rows.append({
                'interview_id': interview_id,
                'anomaly_type': profile,
                'expected_category': self.PROFILE_TO_EXPECTED_CATEGORY[profile],
                'is_anomalous': 0 if profile == 'normal' else 1,
            })
        return pd.DataFrame(rows)

    # ------------------------------------------------------------------
    # Timestamp helpers
    # ------------------------------------------------------------------

    def _ms_to_iso(self, ms: int) -> str:
        """Convert epoch-milliseconds to ISO 8601 string (ODK format)."""
        dt = datetime(1970, 1, 1, tzinfo=timezone.utc) + timedelta(milliseconds=int(ms))
        ms_part = int(ms) % 1000
        return dt.strftime('%Y-%m-%dT%H:%M:%S.') + f"{ms_part:03d}+00:00"

    # ------------------------------------------------------------------
    # Core row builder
    # ------------------------------------------------------------------

    def _build_interview(
        self,
        interview_id: str,
        rts_ms: list,
        back_nav_indices: list,
        pause_after_ms: list,
        start_epoch: int,
        is_odk: bool,
        constraint_indices: list | None = None,
    ) -> list:
        """
        Construct a list of raw audit-log rows for one interview.

        Emits the structural events present in real audit logs: a form-start
        row before the first question, question rows, optional constraint
        and navigation rows, and a form-end row after the last question.
        """
        rows = []
        constraint_indices = constraint_indices or []

        # Form-start row: real logs open with a form-level event whose node
        # is blank. A short load delay precedes the first question.
        load_ms = int(self.rng.integers(400, 2500))
        if is_odk:
            rows.append({
                'instance_id': interview_id,
                'name': None,
                'event': 'form start',
                'start_time': self._ms_to_iso(start_epoch),
                'end_time':   self._ms_to_iso(start_epoch + load_ms),
            })
        else:
            rows.append({
                'interview_id': interview_id,
                'node': None,
                'event': 'form-start',
                'start': start_epoch,
                'end': start_epoch + load_ms,
                'duration_ms': load_ms,
            })

        t = start_epoch + load_ms + int(self.rng.integers(50, 300))

        for i, rt in enumerate(rts_ms):
            section_idx = i // self.QUESTIONS_PER_SECTION
            section_name = self.SECTION_NAMES[min(section_idx, len(self.SECTION_NAMES) - 1)]
            q_within_section = (i % self.QUESTIONS_PER_SECTION) + 1
            q_name = f"{section_name}_q{q_within_section:02d}"
            q_start = t
            q_end = t + max(1, int(rt))

            if is_odk:
                rows.append({
                    'instance_id': interview_id,
                    'name': q_name,
                    'event': 'question-end',
                    'start_time': self._ms_to_iso(q_start),
                    'end_time':   self._ms_to_iso(q_end),
                })
            else:
                rows.append({
                    'interview_id': interview_id,
                    'node': q_name,
                    'event': 'question-end',
                    'start': q_start,
                    'end': q_end,
                    'duration_ms': max(1, int(rt)),
                })

            # Constraint violation: respondent input rejected by a validation
            # rule, then corrected. Logged against the same node.
            if i in constraint_indices:
                c_start = q_end + int(self.rng.integers(100, 400))
                c_dur = int(self.rng.integers(800, 4000))
                if is_odk:
                    rows.append({
                        'instance_id': interview_id,
                        'name': q_name,
                        'event': 'constraint error',
                        'start_time': self._ms_to_iso(c_start),
                        'end_time':   self._ms_to_iso(c_start + c_dur),
                    })
                else:
                    rows.append({
                        'interview_id': interview_id,
                        'node': q_name,
                        'event': 'constraint',
                        'start': c_start,
                        'end': c_start + c_dur,
                        'duration_ms': c_dur,
                    })
                q_end = c_start + c_dur

            inter_gap = int(pause_after_ms[i]) if pause_after_ms else int(
                self.rng.integers(100, 500)
            )
            t = q_end + inter_gap

            if i in back_nav_indices:
                nav_end = t + 300
                if is_odk:
                    rows.append({
                        'instance_id': interview_id,
                        'name': q_name,
                        'event': 'jump',
                        'start_time': self._ms_to_iso(t),
                        'end_time':   self._ms_to_iso(nav_end),
                    })
                else:
                    rows.append({
                        'interview_id': interview_id,
                        'node': q_name,
                        'event': 'jump',
                        'start': t,
                        'end': nav_end,
                        'duration_ms': 300,
                    })
                t = nav_end + 100

        # Form-end row: closes the session, blank node like the opening event.
        close_ms = int(self.rng.integers(200, 1500))
        if is_odk:
            rows.append({
                'instance_id': interview_id,
                'name': None,
                'event': 'end screen',
                'start_time': self._ms_to_iso(t),
                'end_time':   self._ms_to_iso(t + close_ms),
            })
        else:
            rows.append({
                'interview_id': interview_id,
                'node': None,
                'event': 'end',
                'start': t,
                'end': t + close_ms,
                'duration_ms': close_ms,
            })

        return rows

    # ------------------------------------------------------------------
    # Anomaly profile builders  (thesis Section 5.1)
    # ------------------------------------------------------------------

    def _normal_interview(self, iid: str, t0: int, is_odk: bool) -> list:
        """
        Normal profile: log-normal RT distribution, Poisson back-nav.
        Thesis Section 5.1: models realistic interviewer behavior with
        natural variation in response times and occasional back-navigation.
        """
        n = self.N_QUESTIONS
        if self.difficulty == "stress":
            profile = self.rng.choice(["typical", "fast_valid", "low_nav", "variable"])
            if profile == "fast_valid":
                rts = self.rng.lognormal(mean=np.log(4500), sigma=0.35, size=n)
                n_back = max(0, int(self.rng.poisson(lam=1)))
            elif profile == "low_nav":
                rts = self.rng.lognormal(mean=np.log(7500), sigma=0.45, size=n)
                n_back = 0
            elif profile == "variable":
                rts = self.rng.lognormal(mean=np.log(8500), sigma=0.75, size=n)
                n_back = max(0, int(self.rng.poisson(lam=2)))
            else:
                rts = self.rng.lognormal(mean=np.log(8000), sigma=0.5, size=n)
                n_back = max(0, int(self.rng.poisson(lam=2)))
            pauses = self.rng.integers(100, 900, size=n).tolist()
        else:
            rts = self.rng.lognormal(mean=np.log(8000), sigma=0.5, size=n)
            n_back = max(0, int(self.rng.poisson(lam=2)))
            pauses = self.rng.integers(150, 600, size=n).tolist()

        # Genuine respondents take longer on complex items [Yan & Tourangeau 5].
        rts = (rts * np.asarray(self.COMPLEXITY_WEIGHTS[:n])).tolist()

        backs = sorted(
            self.rng.choice(n, size=min(n_back, n), replace=False).tolist()
        )
        # Real interviews occasionally trip validation constraints.
        n_constraints = int(self.rng.poisson(lam=0.6))
        constraints = sorted(
            self.rng.choice(n, size=min(n_constraints, n), replace=False).tolist()
        )
        return self._build_interview(
            iid, rts, backs, pauses, t0, is_odk, constraint_indices=constraints
        )

    def _fabricated_interview(self, iid: str, t0: int, is_odk: bool) -> list:
        """
        Fabricated profile: compressed RT distribution with very low variance,
        near-zero back-navigation.

        Thesis Section 5.1: Wenz et al. [6] notes that fabricated interviews show
        'compressed timing distributions' with reduced IQR and low variance.

        Uses slightly varied RTs (not constant) so the profile is detectable
        through statistical properties rather than trivial exact-match.
        """
        n = self.N_QUESTIONS
        if self.difficulty == "stress":
            if self.rng.random() < 0.45:
                rts = self.rng.normal(loc=1800, scale=180, size=n).clip(min=700).tolist()
                backs = []
            else:
                rts = self.rng.normal(loc=3800, scale=650, size=n).clip(min=1200).tolist()
                n_back = int(self.rng.integers(0, 2))
                backs = sorted(self.rng.choice(n, size=n_back, replace=False).tolist()) if n_back else []
            pauses = self.rng.integers(60, 350, size=n).tolist()
        else:
            rts = self.rng.normal(loc=1200, scale=80, size=n).clip(min=500).tolist()
            pauses = self.rng.integers(50, 200, size=n).tolist()
            backs = []
        return self._build_interview(iid, rts, backs, pauses, t0, is_odk)

    def _speeding_interview(self, iid: str, t0: int, is_odk: bool) -> list:
        """
        Speeding profile: RTs below realistic completion thresholds.

        The total interview completes unrealistically quickly, and response
        times are uniformly fast regardless of question complexity.
        """
        n = self.N_QUESTIONS
        if self.difficulty == "stress":
            rts = self.rng.integers(1200, 3600, size=n).tolist()
            n_back = int(self.rng.integers(0, 2))
            backs = sorted(self.rng.choice(n, size=n_back, replace=False).tolist()) if n_back else []
            pauses = self.rng.integers(40, 250, size=n).tolist()
        else:
            rts = self.rng.integers(200, 800, size=n).tolist()
            pauses = self.rng.integers(30, 150, size=n).tolist()
            backs = []
        return self._build_interview(iid, rts, backs, pauses, t0, is_odk)

    def _disengaged_interview(self, iid: str, t0: int, is_odk: bool) -> list:
        """
        Disengaged profile: uniform slow RT, erratic back-navigation,
        extended pauses between questions.

        Thesis Section 5.1: Conrad et al. [3] describes disengagement as characterized
        by increased pause frequency and low timing variance.
        """
        n = self.N_QUESTIONS
        if self.difficulty == "stress":
            rts = self.rng.lognormal(mean=np.log(6500), sigma=0.28, size=n).clip(min=3000).tolist()
            n_back = int(self.rng.integers(4, 9))
            backs = sorted(self.rng.choice(n, size=n_back, replace=False).tolist())
            pauses = self.rng.integers(300, 2500, size=n).tolist()
            if self.rng.random() < 0.35:
                long_pause_idx = int(self.rng.integers(0, n))
                pauses[long_pause_idx] = int(self.rng.integers(30000, 90000))
        else:
            rts = self.rng.normal(loc=6000, scale=200, size=n).clip(min=4000).tolist()
            n_back = int(self.rng.integers(max(1, n // 3), n // 2 + 1))
            backs = sorted(self.rng.choice(n, size=n_back, replace=False).tolist())
            pauses = self.rng.integers(400, 1200, size=n).tolist()
        return self._build_interview(iid, rts, backs, pauses, t0, is_odk)

    def _dq_issue_interview(self, iid: str, t0: int, is_odk: bool) -> list:
        """
        Data quality issue: single row with zero duration.
        Forces T-06_rt_mean = 0 -> flag_missing_data = 1 -> dq_issue category.
        """
        if is_odk:
            return [{
                'instance_id': iid,
                'name': 'dq_field',
                'event': 'question-end',
                'start_time': self._ms_to_iso(t0),
                'end_time':   self._ms_to_iso(t0),
            }]
        else:
            return [{
                'interview_id': iid,
                'node': 'dq_field',
                'event': 'question-end',
                'start': t0,
                'end': t0,
                'duration_ms': 0,
            }]

    def _build_profile_rows(self, profile: str, interview_id: str, start_epoch: int, is_odk: bool) -> list:
        builder_map = {
            'normal': self._normal_interview,
            'fabricated': self._fabricated_interview,
            'speeding': self._speeding_interview,
            'disengaged': self._disengaged_interview,
            'dq_issue': self._dq_issue_interview,
        }
        if profile not in builder_map:
            raise ValueError(f"Unknown profile: {profile}")
        return builder_map[profile](interview_id, start_epoch, is_odk)

    # ------------------------------------------------------------------
    # Main generator
    # ------------------------------------------------------------------

    def generate_adversarial_suite(self, is_odk: bool = False) -> pd.DataFrame:
        """Generate the canonical adversarial suite (12 interviews)."""
        return self.generate_benchmark_suite(
            plan=self._profile_plan(is_odk=is_odk), is_odk=is_odk
        )

    def generate_benchmark_suite(self, plan: list, is_odk: bool = False) -> pd.DataFrame:
        """Generate a benchmark dataset from an explicit interview plan."""
        all_rows = []
        for interview_id, profile, start_epoch in plan:
            all_rows.extend(self._build_profile_rows(profile, interview_id, start_epoch, is_odk))
        return pd.DataFrame(all_rows)
