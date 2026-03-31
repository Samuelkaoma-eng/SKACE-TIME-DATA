"""
tests/test_adversarial.py
=========================
Adversarial data generator for SKACE-Time-Data academic validation.

Generates the full 400-series synthetic paradata suite (12 interviews per format)
covering four anomaly profiles mandated by thesis §5.1:

  - Normal      : log-normal RT (μ=ln(8000), σ=0.5), Poisson back-nav [Wenz et al. 6]
  - Fabricated  : constant RT (zero variance/IQR), zero back-nav       [Wenz et al. 6]
  - Speeding    : RT scaled below 500ms threshold
  - Disengaged  : uniform slow RT, high pause frequency                [Conrad et al. 3]
  + DQ Issue    : sparse / zero-duration rows → T-06_rt_mean = 0

Interview IDs are fixed to match the ground-truth table in
calculate_academic_metrics.py  (INT400–INT411 / ODK400–ODK411).
"""

import pandas as pd
import numpy as np
from datetime import datetime, timezone, timedelta


class AdversarialDataGenerator:
    """
    Generates synthetic SurveyCTO and ODK audit log DataFrames for the
    400-series adversarial validation suite.

    Usage
    -----
    >>> gen = AdversarialDataGenerator(seed=42)
    >>> scto_df = gen.generate_adversarial_suite(is_odk=False)
    >>> odk_df  = gen.generate_adversarial_suite(is_odk=True)
    """

    # 2023-01-02 08:00:00 UTC in epoch-ms (SurveyCTO format base timestamp)
    BASE_EPOCH_MS: int = 1672646400000
    N_QUESTIONS: int = 20
    # 1 hour between interview start times so they don't overlap
    INTERVIEW_GAP_MS: int = 3_600_000

    def __init__(self, seed: int = 42):
        self.rng = np.random.default_rng(seed)

    # ------------------------------------------------------------------
    # Timestamp helpers
    # ------------------------------------------------------------------

    def _ms_to_iso(self, ms: int) -> str:
        """Convert epoch-milliseconds → ISO 8601 string (ODK format)."""
        dt = datetime(1970, 1, 1, tzinfo=timezone.utc) + timedelta(milliseconds=int(ms))
        return dt.strftime('%Y-%m-%dT%H:%M:%S+00:00')

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
    ) -> list:
        """
        Construct a list of raw audit-log rows for one interview.

        Parameters
        ----------
        interview_id    : Value to place in instance_id (ODK) or interview_id (SurveyCTO)
        rts_ms          : Response time per question (ms)
        back_nav_indices: Question indices (0-based) after which a 'jump' event is inserted
        pause_after_ms  : Extra inter-question gap injected after each question (ms list)
        start_epoch     : UNIX epoch-ms of the first question start
        is_odk          : True → ODK column schema, False → SurveyCTO column schema
        """
        rows = []
        t = start_epoch

        for i, rt in enumerate(rts_ms):
            q_name = f"section_q{i + 1:02d}"
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

            # Advance clock by rt + small natural inter-question gap
            inter_gap = int(pause_after_ms[i]) if pause_after_ms else int(
                self.rng.integers(100, 500)
            )
            t = q_end + inter_gap

            # Insert a backward navigation event if requested
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

        return rows

    # ------------------------------------------------------------------
    # Anomaly profile builders  (thesis §5.1)
    # ------------------------------------------------------------------

    def _normal_interview(self, iid: str, t0: int, is_odk: bool) -> list:
        """
        Normal profile: log-normal RT distribution, Poisson back-nav.
        Thesis §5.1 — Wenz et al. [6] baseline.
        """
        n = self.N_QUESTIONS
        rts = self.rng.lognormal(mean=np.log(8000), sigma=0.5, size=n).tolist()
        n_back = max(0, int(self.rng.poisson(lam=2)))
        backs = sorted(
            self.rng.choice(n, size=min(n_back, n), replace=False).tolist()
        )
        pauses = self.rng.integers(150, 600, size=n).tolist()
        return self._build_interview(iid, rts, backs, pauses, t0, is_odk)

    def _fabricated_interview(self, iid: str, t0: int, is_odk: bool) -> list:
        """
        Fabricated profile: constant RT (zero variance/IQR), zero back-nav.
        Compresses total duration below 5 000 ms → triggers flag_too_fast.
        Thesis §5.1 — Wenz et al. [6]: 'compressed timing distributions'.
        """
        n = self.N_QUESTIONS
        rts = [180] * n              # constant → T-01_rt_variance = 0
        pauses = [10] * n            # minimal gaps
        return self._build_interview(iid, rts, [], pauses, t0, is_odk)

    def _speeding_interview(self, iid: str, t0: int, is_odk: bool) -> list:
        """
        Speeding profile: all RTs below 400 ms realistic threshold.
        Total < 5 000 ms → flag_too_fast; low entropy → flag_low_entropy.
        """
        n = self.N_QUESTIONS
        rts = self.rng.integers(60, 380, size=n).tolist()
        pauses = [10] * n
        return self._build_interview(iid, rts, [], pauses, t0, is_odk)

    def _disengaged_interview(self, iid: str, t0: int, is_odk: bool) -> list:
        """
        Disengaged profile: uniform slow RT, erratic back-navigation.
        Uniform RT → T-01_rt_variance ≈ 0 → flag_uniform_timing;
        entropy = 0 → flag_low_entropy.  (Conrad et al. [3])
        """
        n = self.N_QUESTIONS
        rts = [6000] * n             # constant → zero variance, zero entropy
        n_back = n // 2
        backs = list(range(0, n, 2))[:n_back]
        pauses = [500] * n           # consistent inter-question gaps
        return self._build_interview(iid, rts, backs, pauses, t0, is_odk)

    def _dq_issue_interview(self, iid: str, t0: int, is_odk: bool) -> list:
        """
        Data quality issue: single row with zero duration.
        Forces T-06_rt_mean = 0 → flag_missing_data = 1 → dq_issue category.
        """
        if is_odk:
            return [{
                'instance_id': iid,
                'name': 'dq_field',
                'event': 'question-end',
                'start_time': self._ms_to_iso(t0),
                'end_time':   self._ms_to_iso(t0),   # zero duration
            }]
        else:
            return [{
                'interview_id': iid,
                'node': 'dq_field',
                'event': 'question-end',
                'start': t0,
                'end': t0,                            # zero duration
                'duration_ms': 0,
            }]

    # ------------------------------------------------------------------
    # Main generator
    # ------------------------------------------------------------------

    def generate_adversarial_suite(self, is_odk: bool = False) -> pd.DataFrame:
        """
        Generate the full 400-series adversarial suite (12 interviews).

        Interview-to-profile mapping is fixed to match
        ``tests/calculate_academic_metrics.py`` ground-truth labels:

        +-----------+------------+---------------------+-----------------------+
        | ID        | Profile    | Expected category   | Binary anomalous?     |
        +===========+============+=====================+=======================+
        | *400      | normal     | normal              | 0                     |
        | *401      | fabricated | suspicious/anomalous| 1                     |
        | *402      | dq_issue   | dq_issue            | 1                     |
        | *403      | speeding   | suspicious          | 1                     |
        | *404      | disengaged | suspicious          | 1                     |
        | *405      | normal     | normal              | 0                     |
        | *406      | normal     | normal              | 0                     |
        | *407      | fabricated | suspicious/anomalous| 1                     |
        | *408      | dq_issue   | dq_issue            | 1                     |
        | *409      | dq_issue   | dq_issue            | 1                     |
        | *410      | disengaged | suspicious          | 1                     |
        | *411      | speeding   | suspicious          | 1                     |
        +-----------+------------+---------------------+-----------------------+

        Parameters
        ----------
        is_odk : bool
            False → SurveyCTO column schema (interview_id, node, event, start, end, duration_ms)
            True  → ODK column schema (instance_id, name, event, start_time, end_time)

        Returns
        -------
        pd.DataFrame
            All rows for all 12 interviews concatenated.
        """
        prefix = 'ODK' if is_odk else 'INT'
        base = self.BASE_EPOCH_MS
        step = self.INTERVIEW_GAP_MS

        # (interview_id_suffix, profile, start_epoch_ms)
        profiles = [
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

        all_rows = []
        builder_map = {
            'normal':     self._normal_interview,
            'fabricated': self._fabricated_interview,
            'speeding':   self._speeding_interview,
            'disengaged': self._disengaged_interview,
            'dq_issue':   self._dq_issue_interview,
        }

        for iid, profile, t0 in profiles:
            rows = builder_map[profile](iid, t0, is_odk)
            all_rows.extend(rows)

        return pd.DataFrame(all_rows)
