"""Low-inertia grid counterfactual optimization.

This module exposes a small native QuantumGridOS API for the workflow:

1. encode approved grid and DER settings as binary options,
2. generate candidates with QUBO solvers and optional QAOA,
3. validate candidates with reduced frequency-security physics.

The QUBO is only a candidate generator. Classical validation remains the
authority for RoCoF, nadir, settling frequency, DER cascade, and load shedding.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

import numpy as np

from quantumgridos.algorithms.qubo import (
    QUBOProblem,
    QUBOSolution,
    dedupe_solutions,
    solve_constrained_qubo_qaoa_statevector,
    solve_qubo_exact,
    solve_qubo_qaoa_statevector,
    solve_qubo_simulated_annealing,
)

LOW_INERTIA_PUBLIC_DATA_CATALOG: Dict[str, Dict] = {
    "quantumgridos": {
        "repository": "https://github.com/saralsystems/quantumgridos",
        "pypi": "https://pypi.org/project/quantumgridos/",
        "install": "pip install quantumgridos",
        "low_inertia_pr": "https://github.com/saralsystems/quantumgridos/pull/2",
    },
    "project_repository": {
        "repository": "https://github.com/sayonsom/low-inertia-quantum-counterfactuals",
        "docs": "https://github.com/sayonsom/low-inertia-quantum-counterfactuals/tree/main/docs",
    },
    "s3_public_handoff_bundle": {
        "bucket": "qgo-low-inertia-public-data-20260706-654777652612",
        "key": "public/low_inertia_quantum_public_handoff_20260706.zip",
        "s3_uri": "s3://qgo-low-inertia-public-data-20260706-654777652612/public/low_inertia_quantum_public_handoff_20260706.zip",
        "sha256": "534e4c6b01845f3ac9e48d4fb3f4b0104db025b2f4f6db833eef26ed65bc3fc2",
        "size_mb": 91,
        "access_note": (
            "This object currently requires a presigned HTTPS URL. Do not commit "
            "expiring signed URLs to source control; share them out-of-band or "
            "generate a fresh presigned URL from the owning AWS account."
        ),
    },
    "public_sources": {
        "neso_august_2019_frequency": "https://www.neso.energy/data-portal/system-frequency-data/august_2019_-_historic_frequency_data",
        "neso_9_aug_2019_incident_report": "https://www.neso.energy/document/152346/download",
        "power_grid_frequency_database": "https://power-grid-frequency.org/database/",
        "matpower_example_cases": "https://matpower.app/manual/matpower/ExamplematpowerCases.html",
        "matpower_case39": "https://matpower.org/docs/ref/matpower5.0/case39.html",
        "matpower_case118": "https://matpower.org/docs/ref/matpower5.0/case118.html",
        "rts_gmlc_repository": "https://github.com/GridMod/RTS-GMLC",
        "nrel_rts_gmlc_overview": "https://www.nlr.gov/grid/reliability-test-system",
    },
    "execution_requirements": {
        "cuda_required": True,
        "gpu_baseline": "Run CUDA/cuOpt on the same package-variable schema as CPU and Qiskit solvers.",
        "timing_rule": "Report end-to-end wall-clock: load, build, solve, postprocess, and validation.",
    },
}


@dataclass(frozen=True)
class LowInertiaOption:
    """One binary grid/DER setting available to the optimizer."""

    name: str
    label: str
    group: str
    group_type: str = "binary"
    cost: float = 0.0
    capacity_mw: float = 0.0
    inertia_mw_s_per_hz: float = 0.0
    ffr_mw: float = 0.0
    ffr_tau_s: float = 0.35
    pfr_mw: float = 0.0
    pfr_tau_s: float = 2.2
    damping_mw_per_hz: float = 0.0
    der_trip_threshold_hz: Optional[float] = None
    contingency_reduction_mw: float = 0.0


@dataclass
class FrequencySecurityCriteria:
    """Frequency-security thresholds used in classical validation."""

    min_capacity_mw: float = 0.0
    min_inertia_mw_s_per_hz: float = 0.0
    min_ffr_mw: float = 0.0
    min_damping_mw_per_hz: float = 0.0
    max_rocof_hz_s: float = 0.65
    min_nadir_hz: float = 49.2
    min_settling_hz: float = 49.55
    max_load_shed_mw: float = 0.0


@dataclass
class LowInertiaStudy:
    """A bounded low-inertia disturbance study case."""

    name: str
    nominal_hz: float
    base_contingency_mw: float
    der_trip_mw: float
    base_damping_mw_per_hz: float
    default_der_trip_threshold_hz: float
    options: List[LowInertiaOption]
    criteria: FrequencySecurityCriteria
    baseline_options: List[str] = field(default_factory=list)
    metadata: Dict = field(default_factory=dict)

    @property
    def option_names(self) -> List[str]:
        return [option.name for option in self.options]

    @property
    def one_hot_groups(self) -> Dict[str, List[int]]:
        groups: Dict[str, List[int]] = {}
        for index, option in enumerate(self.options):
            if option.group_type == "onehot":
                groups.setdefault(option.group, []).append(index)
        return groups

    def baseline_bits(self) -> Tuple[int, ...]:
        baseline = set(self.baseline_options)
        return tuple(1 if option.name in baseline else 0 for option in self.options)

    def decode(self, bits: Sequence[int]) -> "LowInertiaPortfolio":
        bit_tuple = tuple(int(bit) for bit in bits)
        if len(bit_tuple) != len(self.options):
            raise ValueError("bitstring length does not match study options")

        selected = [option for bit, option in zip(bit_tuple, self.options) if bit]
        one_hot_violations = [
            group for group, indices in self.one_hot_groups.items() if sum(bit_tuple[i] for i in indices) != 1
        ]

        def weighted_average(field_name: str, weight_field: str, default: float) -> float:
            numerator = 0.0
            denominator = 0.0
            for option in selected:
                value = getattr(option, field_name)
                weight = getattr(option, weight_field)
                if value and weight > 0.0:
                    numerator += value * weight
                    denominator += weight
            return numerator / denominator if denominator else default

        thresholds = [
            option.der_trip_threshold_hz
            for option in selected
            if option.der_trip_threshold_hz is not None
        ]

        return LowInertiaPortfolio(
            bitstring=bit_tuple,
            selected_options=[option.name for option in selected],
            selected_labels=[option.label for option in selected],
            cost=float(sum(option.cost for option in selected)),
            capacity_mw=float(sum(option.capacity_mw for option in selected)),
            inertia_mw_s_per_hz=float(sum(option.inertia_mw_s_per_hz for option in selected)),
            ffr_mw=float(sum(option.ffr_mw for option in selected)),
            ffr_tau_s=float(weighted_average("ffr_tau_s", "ffr_mw", 0.35)),
            pfr_mw=float(sum(option.pfr_mw for option in selected)),
            pfr_tau_s=float(weighted_average("pfr_tau_s", "pfr_mw", 2.2)),
            damping_mw_per_hz=float(sum(option.damping_mw_per_hz for option in selected)),
            der_trip_threshold_hz=float(min(thresholds) if thresholds else self.default_der_trip_threshold_hz),
            contingency_reduction_mw=float(sum(option.contingency_reduction_mw for option in selected)),
            one_hot_violations=one_hot_violations,
        )

    @classmethod
    def gb_2019_style_demo(cls) -> "LowInertiaStudy":
        """Return a small Braket-scale demo case."""

        return cls(
            name="gb_2019_style_low_inertia_demo",
            nominal_hz=50.0,
            base_contingency_mw=520.0,
            der_trip_mw=260.0,
            base_damping_mw_per_hz=90.0,
            default_der_trip_threshold_hz=49.45,
            baseline_options=[
                "ccgt_g2",
                "bess_off",
                "legacy_der_ride_through",
                "normal_export",
            ],
            criteria=FrequencySecurityCriteria(
                min_capacity_mw=880.0,
                min_inertia_mw_s_per_hz=950.0,
                min_ffr_mw=180.0,
                min_damping_mw_per_hz=135.0,
                max_rocof_hz_s=0.65,
                min_nadir_hz=49.2,
                min_settling_hz=49.55,
                max_load_shed_mw=0.0,
            ),
            metadata={
                "purpose": "frequency-secure operations demo with approved DER/GFM packages",
                "source_event": "GB 9 Aug 2019 style synthetic replay",
            },
            options=[
                LowInertiaOption(
                    "coal_g1",
                    "Coal G1 online",
                    "sync_commitment",
                    cost=68.0,
                    capacity_mw=550.0,
                    inertia_mw_s_per_hz=650.0,
                    pfr_mw=90.0,
                    pfr_tau_s=2.5,
                    damping_mw_per_hz=45.0,
                ),
                LowInertiaOption(
                    "ccgt_g2",
                    "CCGT G2 online",
                    "sync_commitment",
                    cost=54.0,
                    capacity_mw=420.0,
                    inertia_mw_s_per_hz=360.0,
                    pfr_mw=85.0,
                    pfr_tau_s=1.9,
                    damping_mw_per_hz=35.0,
                ),
                LowInertiaOption(
                    "hydro_g3",
                    "Hydro G3 online",
                    "sync_commitment",
                    cost=32.0,
                    capacity_mw=260.0,
                    inertia_mw_s_per_hz=240.0,
                    pfr_mw=70.0,
                    pfr_tau_s=1.2,
                    damping_mw_per_hz=30.0,
                ),
                LowInertiaOption(
                    "sync_condenser",
                    "Synchronous condenser enabled",
                    "sync_commitment",
                    cost=18.0,
                    inertia_mw_s_per_hz=300.0,
                    damping_mw_per_hz=25.0,
                ),
                LowInertiaOption("bess_off", "BESS frequency mode off", "bess_mode", "onehot"),
                LowInertiaOption(
                    "bess_ffr_200",
                    "BESS 200 MW fast-frequency response",
                    "bess_mode",
                    "onehot",
                    cost=25.0,
                    ffr_mw=200.0,
                    ffr_tau_s=0.22,
                ),
                LowInertiaOption(
                    "bess_gfm_160",
                    "BESS grid-forming package",
                    "bess_mode",
                    "onehot",
                    cost=34.0,
                    ffr_mw=160.0,
                    ffr_tau_s=0.18,
                    inertia_mw_s_per_hz=350.0,
                    damping_mw_per_hz=50.0,
                ),
                LowInertiaOption(
                    "legacy_der_ride_through",
                    "Legacy DER ride-through curve",
                    "der_ride_through",
                    "onehot",
                    der_trip_threshold_hz=49.45,
                ),
                LowInertiaOption(
                    "wide_der_ride_through",
                    "Wide DER ride-through curve",
                    "der_ride_through",
                    "onehot",
                    cost=12.0,
                    der_trip_threshold_hz=48.9,
                ),
                LowInertiaOption(
                    "gfm_der_support",
                    "DER grid-support package",
                    "der_ride_through",
                    "onehot",
                    cost=20.0,
                    der_trip_threshold_hz=48.6,
                    ffr_mw=60.0,
                    ffr_tau_s=0.28,
                    inertia_mw_s_per_hz=120.0,
                    damping_mw_per_hz=25.0,
                ),
                LowInertiaOption("normal_export", "Normal pre-event export", "export_policy", "onehot"),
                LowInertiaOption(
                    "reduce_export_180",
                    "Reduce export/interconnector exposure by 180 MW",
                    "export_policy",
                    "onehot",
                    cost=22.0,
                    contingency_reduction_mw=180.0,
                ),
            ],
        )


@dataclass
class LowInertiaPortfolio:
    """Decoded portfolio from one binary candidate."""

    bitstring: Tuple[int, ...]
    selected_options: List[str]
    selected_labels: List[str]
    cost: float
    capacity_mw: float
    inertia_mw_s_per_hz: float
    ffr_mw: float
    ffr_tau_s: float
    pfr_mw: float
    pfr_tau_s: float
    damping_mw_per_hz: float
    der_trip_threshold_hz: float
    contingency_reduction_mw: float
    one_hot_violations: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "bitstring": "".join(str(bit) for bit in self.bitstring),
            "selected_options": self.selected_options,
            "selected_labels": self.selected_labels,
            "cost": self.cost,
            "capacity_mw": self.capacity_mw,
            "inertia_mw_s_per_hz": self.inertia_mw_s_per_hz,
            "ffr_mw": self.ffr_mw,
            "ffr_tau_s": self.ffr_tau_s,
            "pfr_mw": self.pfr_mw,
            "pfr_tau_s": self.pfr_tau_s,
            "damping_mw_per_hz": self.damping_mw_per_hz,
            "der_trip_threshold_hz": self.der_trip_threshold_hz,
            "contingency_reduction_mw": self.contingency_reduction_mw,
            "one_hot_violations": self.one_hot_violations,
        }


@dataclass
class LowInertiaValidation:
    """Classical validation result for a portfolio."""

    portfolio: LowInertiaPortfolio
    feasible: bool
    metrics: Dict[str, float]
    violations: List[str]
    time_s: List[float] = field(default_factory=list)
    frequency_hz: List[float] = field(default_factory=list)

    def to_dict(self, include_trace: bool = False) -> Dict:
        payload = {
            "portfolio": self.portfolio.to_dict(),
            "feasible": self.feasible,
            "metrics": self.metrics,
            "violations": self.violations,
        }
        if include_trace:
            payload["time_s"] = self.time_s
            payload["frequency_hz"] = self.frequency_hz
        return payload


@dataclass
class LowInertiaSearchResult:
    """Result from native low-inertia counterfactual search."""

    study_name: str
    baseline: LowInertiaValidation
    candidates: List[LowInertiaValidation]
    solver_errors: List[str] = field(default_factory=list)
    qiskit_used: bool = False

    @property
    def feasible(self) -> List[LowInertiaValidation]:
        return [candidate for candidate in self.candidates if candidate.feasible]

    @property
    def best(self) -> Optional[LowInertiaValidation]:
        return self.feasible[0] if self.feasible else None

    def to_dict(self, include_traces: bool = False) -> Dict:
        return {
            "study_name": self.study_name,
            "qiskit_used": self.qiskit_used,
            "solver_errors": self.solver_errors,
            "baseline": self.baseline.to_dict(include_trace=include_traces),
            "best": self.best.to_dict(include_trace=include_traces) if self.best else None,
            "candidates": [
                candidate.to_dict(include_trace=False) for candidate in self.candidates
            ],
        }


@dataclass
class LowInertiaQUBOWeights:
    """Candidate-generation weights."""

    cost: float = 1.0
    one_hot: float = 250.0
    capacity_reward: float = 35.0
    inertia_reward: float = 80.0
    ffr_reward: float = 70.0
    damping_reward: float = 45.0
    legacy_der_trip_risk: float = 45.0
    no_bess_risk: float = 35.0


class LowInertiaOptimizer:
    """Native QuantumGridOS optimizer for low-inertia counterfactuals."""

    def __init__(
        self,
        study: Optional[LowInertiaStudy] = None,
        *,
        weights: Optional[LowInertiaQUBOWeights] = None,
        dt_s: float = 0.05,
        seconds: float = 30.0,
    ) -> None:
        self.study = study or LowInertiaStudy.gb_2019_style_demo()
        self.weights = weights or LowInertiaQUBOWeights()
        self.dt_s = dt_s
        self.seconds = seconds

    def solve(
        self,
        *,
        solvers: Sequence[str] = ("exact", "annealing", "qaoa"),
        top_k: int = 24,
        qaoa_layers: int = 1,
        qaoa_maxiter: int = 60,
        constrained_qaoa_restarts: int = 2,
        warm_start_strength: float = 0.8,
        annealing_reads: int = 128,
        annealing_sweeps: int = 350,
        seed: int = 7,
        include_traces: bool = False,
        dynamic_labels: bool = False,
        dynamic_label_kwargs: Optional[Dict] = None,
    ) -> LowInertiaSearchResult:
        problem = self.build_qubo()
        solutions: List[QUBOSolution] = []
        solver_errors: List[str] = []
        qiskit_used = False
        validator = (
            LowInertiaDynamicLabeler(self.study, **(dynamic_label_kwargs or {}))
            if dynamic_labels
            else self
        )

        if "exact" in solvers:
            solutions.extend(solve_qubo_exact(problem, top_k=top_k))
        if "annealing" in solvers:
            solutions.extend(
                solve_qubo_simulated_annealing(
                    problem,
                    reads=annealing_reads,
                    sweeps=annealing_sweeps,
                    top_k=top_k,
                    seed=seed,
                )
            )
        if "qaoa" in solvers:
            try:
                solutions.extend(
                    solve_qubo_qaoa_statevector(
                        problem,
                        layers=qaoa_layers,
                        maxiter=qaoa_maxiter,
                        top_k=top_k,
                        seed=seed + 101,
                    )
                )
                qiskit_used = True
            except Exception as exc:  # pragma: no cover - optional runtime path
                solver_errors.append(f"qaoa:{type(exc).__name__}:{exc}")
        if "constrained_qaoa" in solvers:
            try:
                solutions.extend(
                    solve_constrained_qubo_qaoa_statevector(
                        problem,
                        one_hot_groups=self.study.one_hot_groups,
                        layers=qaoa_layers,
                        maxiter=qaoa_maxiter,
                        top_k=top_k,
                        seed=seed + 201,
                        restarts=constrained_qaoa_restarts,
                    )
                )
            except Exception as exc:  # pragma: no cover - optional runtime path
                solver_errors.append(f"constrained_qaoa:{type(exc).__name__}:{exc}")
        if "constrained_qaoa_warm" in solvers:
            try:
                solutions.extend(
                    solve_constrained_qubo_qaoa_statevector(
                        problem,
                        one_hot_groups=self.study.one_hot_groups,
                        layers=qaoa_layers,
                        maxiter=qaoa_maxiter,
                        top_k=top_k,
                        seed=seed + 301,
                        restarts=constrained_qaoa_restarts,
                        warm_start_bitstring=self.study.baseline_bits(),
                        warm_start_strength=warm_start_strength,
                    )
                )
            except Exception as exc:  # pragma: no cover - optional runtime path
                solver_errors.append(f"constrained_qaoa_warm:{type(exc).__name__}:{exc}")

        validations: List[LowInertiaValidation] = []
        seen: set[Tuple[int, ...]] = set()
        for solution in dedupe_solutions(solutions):
            if solution.bitstring in seen:
                continue
            seen.add(solution.bitstring)
            validation = validator.validate(
                self.study.decode(solution.bitstring),
                include_trace=include_traces,
            )
            validation.metrics["qubo_energy"] = float(solution.energy)
            validation.metrics["candidate_solver"] = solution.solver
            if solution.probability is not None:
                validation.metrics["qaoa_probability"] = float(solution.probability)
            validations.append(validation)

        validations.sort(key=lambda item: (not item.feasible, item.metrics["validated_objective"]))
        baseline = validator.validate(self.study.decode(self.study.baseline_bits()), include_trace=True)

        return LowInertiaSearchResult(
            study_name=self.study.name,
            baseline=baseline,
            candidates=validations,
            solver_errors=solver_errors,
            qiskit_used=qiskit_used,
        )

    def build_qubo(self) -> QUBOProblem:
        n = len(self.study.options)
        linear = np.zeros(n, dtype=float)
        quadratic = np.zeros((n, n), dtype=float)
        constant = 0.0

        linear += self.weights.cost * np.array([option.cost for option in self.study.options])
        constant += self._add_one_hot(linear, quadratic)
        self._add_reward(linear, "capacity_mw", self.study.criteria.min_capacity_mw, self.weights.capacity_reward)
        self._add_reward(
            linear,
            "inertia_mw_s_per_hz",
            self.study.criteria.min_inertia_mw_s_per_hz,
            self.weights.inertia_reward,
        )
        self._add_reward(linear, "ffr_mw", self.study.criteria.min_ffr_mw, self.weights.ffr_reward)
        self._add_reward(
            linear,
            "damping_mw_per_hz",
            self.study.criteria.min_damping_mw_per_hz,
            self.weights.damping_reward,
        )
        self._add_low_inertia_priors(linear, quadratic)

        return QUBOProblem(
            linear=linear,
            quadratic=quadratic,
            constant=constant,
            variable_names=self.study.option_names,
            metadata={"study": self.study.name},
        )

    def validate(
        self, portfolio: LowInertiaPortfolio, *, include_trace: bool = False
    ) -> LowInertiaValidation:
        time_s, frequency, metrics = self.simulate(portfolio)
        violations = self._violations(portfolio, metrics)
        return LowInertiaValidation(
            portfolio=portfolio,
            feasible=not violations,
            metrics=metrics,
            violations=violations,
            time_s=[float(value) for value in time_s] if include_trace else [],
            frequency_hz=[float(value) for value in frequency] if include_trace else [],
        )

    def simulate(self, portfolio: LowInertiaPortfolio) -> Tuple[np.ndarray, np.ndarray, Dict[str, float]]:
        n_steps = int(self.seconds / self.dt_s) + 1
        time_s = np.linspace(0.0, self.seconds, n_steps)
        frequency = np.empty(n_steps, dtype=float)
        frequency[0] = self.study.nominal_hz

        inertia = max(portfolio.inertia_mw_s_per_hz, 80.0)
        damping = self.study.base_damping_mw_per_hz + portfolio.damping_mw_per_hz
        contingency = max(0.0, self.study.base_contingency_mw - portfolio.contingency_reduction_mw)
        der_tripped = False
        der_trip_time = -1.0
        der_loss_mw = 0.0
        load_shed_mw = 0.0
        uf_stage_1 = False
        uf_stage_2 = False

        for step in range(1, n_steps):
            t = time_s[step - 1]
            f_prev = frequency[step - 1]

            if not der_tripped and f_prev <= portfolio.der_trip_threshold_hz:
                der_tripped = True
                der_trip_time = float(t)
                der_loss_mw = self.study.der_trip_mw
            if not uf_stage_1 and f_prev <= 49.0:
                uf_stage_1 = True
                load_shed_mw += 120.0
            if not uf_stage_2 and f_prev <= 48.75:
                uf_stage_2 = True
                load_shed_mw += 180.0

            ffr = portfolio.ffr_mw * (1.0 - np.exp(-t / max(portfolio.ffr_tau_s, 0.05)))
            pfr = portfolio.pfr_mw * (1.0 - np.exp(-t / max(portfolio.pfr_tau_s, 0.1)))
            frequency_damping = damping * (f_prev - self.study.nominal_hz)
            imbalance_mw = -contingency - der_loss_mw + ffr + pfr + load_shed_mw - frequency_damping
            frequency[step] = f_prev + self.dt_s * imbalance_mw / inertia

        rocof = np.gradient(frequency, time_s)
        static_penalty = self._static_penalty(portfolio)
        metrics = {
            "contingency_mw": float(contingency),
            "effective_inertia_mw_s_per_hz": float(inertia),
            "effective_damping_mw_per_hz": float(damping),
            "nadir_hz": float(np.min(frequency)),
            "max_abs_rocof_hz_s": float(np.max(np.abs(rocof))),
            "settling_hz": float(frequency[-1]),
            "der_tripped": float(1.0 if der_tripped else 0.0),
            "der_trip_time_s": float(der_trip_time),
            "load_shed_mw": float(load_shed_mw),
            "validated_objective": float(
                portfolio.cost
                + static_penalty
                + 2000.0 * max(0.0, self.study.criteria.min_nadir_hz - np.min(frequency))
                + 1800.0 * max(0.0, self.study.criteria.min_settling_hz - frequency[-1])
                + 1200.0 * max(0.0, np.max(np.abs(rocof)) - self.study.criteria.max_rocof_hz_s)
                + 8.0 * load_shed_mw
                + 150.0 * (1.0 if der_tripped else 0.0)
            ),
        }
        return time_s, frequency, metrics

    def _add_one_hot(self, linear: np.ndarray, quadratic: np.ndarray) -> float:
        constant = 0.0
        for indices in self.study.one_hot_groups.values():
            constant += self.weights.one_hot
            for i in indices:
                linear[i] += -self.weights.one_hot
            for offset, i in enumerate(indices):
                for j in indices[offset + 1 :]:
                    quadratic[min(i, j), max(i, j)] += 2.0 * self.weights.one_hot
        return constant

    def _add_reward(self, linear: np.ndarray, field_name: str, target: float, weight: float) -> None:
        if target <= 0.0 or weight == 0.0:
            return
        for i, option in enumerate(self.study.options):
            linear[i] += -weight * getattr(option, field_name) / target

    def _add_low_inertia_priors(self, linear: np.ndarray, quadratic: np.ndarray) -> None:
        names = self.study.option_names

        def index(name: str) -> Optional[int]:
            return names.index(name) if name in names else None

        legacy = index("legacy_der_ride_through")
        no_bess = index("bess_off")
        normal_export = index("normal_export")

        if legacy is not None:
            linear[legacy] += self.weights.legacy_der_trip_risk
        if no_bess is not None:
            linear[no_bess] += self.weights.no_bess_risk
        if legacy is not None and normal_export is not None:
            quadratic[min(legacy, normal_export), max(legacy, normal_export)] += 40.0
        if no_bess is not None and normal_export is not None:
            quadratic[min(no_bess, normal_export), max(no_bess, normal_export)] += 30.0

    def _static_penalty(self, portfolio: LowInertiaPortfolio) -> float:
        penalty = 1000.0 * len(portfolio.one_hot_violations)
        checks = [
            ("capacity_mw", self.study.criteria.min_capacity_mw, 350.0),
            ("inertia_mw_s_per_hz", self.study.criteria.min_inertia_mw_s_per_hz, 450.0),
            ("ffr_mw", self.study.criteria.min_ffr_mw, 350.0),
            ("damping_mw_per_hz", self.study.criteria.min_damping_mw_per_hz, 250.0),
        ]
        for field_name, target, scale in checks:
            if target <= 0.0:
                continue
            value = getattr(portfolio, field_name)
            penalty += scale * max(0.0, target - value) / target
        return float(penalty)

    def _violations(self, portfolio: LowInertiaPortfolio, metrics: Dict[str, float]) -> List[str]:
        criteria = self.study.criteria
        violations: List[str] = []
        violations.extend([f"one_hot:{group}" for group in portfolio.one_hot_violations])
        if portfolio.capacity_mw < criteria.min_capacity_mw:
            violations.append("capacity_shortage")
        if portfolio.inertia_mw_s_per_hz < criteria.min_inertia_mw_s_per_hz:
            violations.append("inertia_shortage")
        if portfolio.ffr_mw < criteria.min_ffr_mw:
            violations.append("ffr_shortage")
        if portfolio.damping_mw_per_hz < criteria.min_damping_mw_per_hz:
            violations.append("damping_shortage")
        if metrics["max_abs_rocof_hz_s"] > criteria.max_rocof_hz_s:
            violations.append("rocof_limit")
        if metrics["nadir_hz"] < criteria.min_nadir_hz:
            violations.append("frequency_nadir")
        if metrics["settling_hz"] < criteria.min_settling_hz:
            violations.append("settling_frequency")
        if metrics["load_shed_mw"] > criteria.max_load_shed_mw:
            violations.append("load_shed")
        if metrics["der_tripped"] > 0.0:
            violations.append("der_cascade_trip")
        return violations


@dataclass
class LowInertiaDynamicLabeler:
    """Two-area electromechanical dynamic-label surrogate.

    This validator is a publication-screening layer above the reduced
    center-of-inertia frequency model. It adds inter-area angle, area-frequency
    split, and small-signal damping labels. It is not an RMS/EMT model.
    """

    study: LowInertiaStudy
    dt_s: float = 0.02
    seconds: float = 30.0
    max_relative_angle_rad: float = 1.2
    max_area_frequency_split_hz: float = 0.75
    min_damping_ratio: float = 0.03

    def validate(
        self,
        portfolio: LowInertiaPortfolio,
        *,
        include_trace: bool = True,
    ) -> LowInertiaValidation:
        time_s, center_frequency, metrics = self.simulate(portfolio)
        violations = self._violations(portfolio, metrics)
        return LowInertiaValidation(
            portfolio=portfolio,
            feasible=not violations,
            metrics=metrics,
            violations=violations,
            time_s=[float(value) for value in time_s] if include_trace else [],
            frequency_hz=[float(value) for value in center_frequency] if include_trace else [],
        )

    def simulate(self, portfolio: LowInertiaPortfolio) -> Tuple[np.ndarray, np.ndarray, Dict[str, float]]:
        n_steps = int(self.seconds / self.dt_s) + 1
        time_s = np.linspace(0.0, self.seconds, n_steps)
        state = np.zeros(5, dtype=float)
        history = np.zeros((n_steps, len(state)), dtype=float)

        params = self._parameters(portfolio)
        der_tripped = False
        der_trip_time = -1.0
        der_loss_mw = 0.0
        load_shed_mw = 0.0
        uf_stage_1 = False
        uf_stage_2 = False

        for step in range(1, n_steps):
            center_hz = self._center_frequency_hz(state, params)
            t = time_s[step - 1]

            if not der_tripped and center_hz <= portfolio.der_trip_threshold_hz:
                der_tripped = True
                der_trip_time = float(t)
                der_loss_mw = self.study.der_trip_mw
            if not uf_stage_1 and center_hz <= 49.0:
                uf_stage_1 = True
                load_shed_mw += 120.0
            if not uf_stage_2 and center_hz <= 48.75:
                uf_stage_2 = True
                load_shed_mw += 180.0

            state = self._rk4_step(
                state,
                portfolio,
                params,
                der_loss_mw=der_loss_mw,
                load_shed_mw=load_shed_mw,
            )
            history[step] = state

        f1_hz = self.study.nominal_hz + history[:, 1]
        f2_hz = self.study.nominal_hz + history[:, 2]
        center_frequency = self.study.nominal_hz + (
            params["m1"] * history[:, 1] + params["m2"] * history[:, 2]
        ) / (params["m1"] + params["m2"])
        rocof = np.gradient(center_frequency, time_s)
        eigvals = self.small_signal_eigenvalues(portfolio)
        complex_eigs = [value for value in eigvals if abs(float(np.imag(value))) > 1e-9]
        damping_ratios = [
            float(-np.real(value) / max(abs(value), 1e-12))
            for value in complex_eigs
            if np.real(value) < 0.0
        ]
        dominant_real = float(np.max(np.real(eigvals)))
        min_damping = float(min(damping_ratios)) if damping_ratios else 1.0
        electromech_frequency_hz = (
            float(max(abs(np.imag(value)) for value in complex_eigs) / (2.0 * np.pi))
            if complex_eigs
            else 0.0
        )
        static_penalty = LowInertiaOptimizer(self.study)._static_penalty(portfolio)
        dynamic_penalty = (
            2200.0 * max(0.0, self.study.criteria.min_nadir_hz - np.min(center_frequency))
            + 1600.0
            * max(0.0, np.max(np.abs(rocof)) - self.study.criteria.max_rocof_hz_s)
            + 1200.0 * max(0.0, np.max(np.abs(history[:, 0])) - self.max_relative_angle_rad)
            + 1000.0 * max(0.0, np.max(np.abs(f1_hz - f2_hz)) - self.max_area_frequency_split_hz)
            + 8.0 * load_shed_mw
            + 150.0 * (1.0 if der_tripped else 0.0)
            + 900.0 * max(0.0, self.min_damping_ratio - min_damping)
            + 900.0 * max(0.0, dominant_real)
        )

        metrics = {
            "dynamic_model": "two_area_reduced_electromechanical_surrogate",
            "contingency_mw": float(max(0.0, self.study.base_contingency_mw - portfolio.contingency_reduction_mw)),
            "area1_inertia_mw_s_per_hz": float(params["m1"]),
            "area2_inertia_mw_s_per_hz": float(params["m2"]),
            "synchronizing_power_mw_per_rad": float(params["k_sync"]),
            "nadir_hz": float(np.min(center_frequency)),
            "area1_nadir_hz": float(np.min(f1_hz)),
            "area2_nadir_hz": float(np.min(f2_hz)),
            "max_abs_rocof_hz_s": float(np.max(np.abs(rocof))),
            "settling_hz": float(center_frequency[-1]),
            "max_relative_angle_rad": float(np.max(np.abs(history[:, 0]))),
            "max_area_frequency_split_hz": float(np.max(np.abs(f1_hz - f2_hz))),
            "delivered_ffr_mw_final": float(history[-1, 3]),
            "delivered_pfr_mw_final": float(history[-1, 4]),
            "dominant_eigenvalue_real": dominant_real,
            "min_electromechanical_damping_ratio": min_damping,
            "electromechanical_frequency_hz": electromech_frequency_hz,
            "small_signal_stable": float(1.0 if dominant_real < -1e-6 else 0.0),
            "der_tripped": float(1.0 if der_tripped else 0.0),
            "der_trip_time_s": float(der_trip_time),
            "load_shed_mw": float(load_shed_mw),
            "validated_objective": float(portfolio.cost + static_penalty + dynamic_penalty),
        }
        return time_s, center_frequency, metrics

    def small_signal_eigenvalues(self, portfolio: LowInertiaPortfolio) -> np.ndarray:
        params = self._parameters(portfolio)
        m1 = params["m1"]
        m2 = params["m2"]
        d1 = params["d1"]
        d2 = params["d2"]
        k_sync = params["k_sync"]
        area2_response_fraction = params["area2_response_fraction"]
        tau_ffr = max(portfolio.ffr_tau_s, 0.05)
        tau_pfr = max(portfolio.pfr_tau_s, 0.1)
        a_matrix = np.array(
            [
                [0.0, 2.0 * np.pi, -2.0 * np.pi, 0.0, 0.0],
                [
                    -k_sync / m1,
                    -d1 / m1,
                    0.0,
                    (1.0 - area2_response_fraction) / m1,
                    (1.0 - area2_response_fraction) / m1,
                ],
                [
                    k_sync / m2,
                    0.0,
                    -d2 / m2,
                    area2_response_fraction / m2,
                    area2_response_fraction / m2,
                ],
                [0.0, 0.0, 0.0, -1.0 / tau_ffr, 0.0],
                [0.0, 0.0, 0.0, 0.0, -1.0 / tau_pfr],
            ],
            dtype=float,
        )
        return np.linalg.eigvals(a_matrix)

    def _parameters(self, portfolio: LowInertiaPortfolio) -> Dict[str, float]:
        total_inertia = max(portfolio.inertia_mw_s_per_hz, 80.0)
        total_damping = max(self.study.base_damping_mw_per_hz + portfolio.damping_mw_per_hz, 1.0)
        resource_support = any(
            name in portfolio.selected_options for name in ("bess_gfm_160", "gfm_der_support", "bess_ffr_200")
        )
        area2_response_fraction = 0.65 if resource_support else 0.45
        capacity = max(portfolio.capacity_mw + portfolio.ffr_mw + portfolio.pfr_mw, 1.0)
        return {
            "m1": 0.56 * total_inertia,
            "m2": 0.44 * total_inertia,
            "d1": 0.52 * total_damping,
            "d2": 0.48 * total_damping,
            "k_sync": max(80.0, 0.18 * capacity),
            "area2_response_fraction": area2_response_fraction,
        }

    def _center_frequency_hz(self, state: np.ndarray, params: Dict[str, float]) -> float:
        f_dev = (params["m1"] * state[1] + params["m2"] * state[2]) / (params["m1"] + params["m2"])
        return float(self.study.nominal_hz + f_dev)

    def _derivatives(
        self,
        state: np.ndarray,
        portfolio: LowInertiaPortfolio,
        params: Dict[str, float],
        *,
        der_loss_mw: float,
        load_shed_mw: float,
    ) -> np.ndarray:
        delta, f1, f2, ffr, pfr = state
        contingency = max(0.0, self.study.base_contingency_mw - portfolio.contingency_reduction_mw)
        disturbance_area2 = contingency + der_loss_mw - load_shed_mw
        response_area2 = params["area2_response_fraction"] * (ffr + pfr)
        response_area1 = (1.0 - params["area2_response_fraction"]) * (ffr + pfr)
        tie_power = params["k_sync"] * np.sin(delta)
        return np.array(
            [
                2.0 * np.pi * (f1 - f2),
                (-params["d1"] * f1 - tie_power + response_area1) / params["m1"],
                (-params["d2"] * f2 + tie_power + response_area2 - disturbance_area2) / params["m2"],
                (portfolio.ffr_mw - ffr) / max(portfolio.ffr_tau_s, 0.05),
                (portfolio.pfr_mw - pfr) / max(portfolio.pfr_tau_s, 0.1),
            ],
            dtype=float,
        )

    def _rk4_step(
        self,
        state: np.ndarray,
        portfolio: LowInertiaPortfolio,
        params: Dict[str, float],
        *,
        der_loss_mw: float,
        load_shed_mw: float,
    ) -> np.ndarray:
        h = self.dt_s
        k1 = self._derivatives(state, portfolio, params, der_loss_mw=der_loss_mw, load_shed_mw=load_shed_mw)
        k2 = self._derivatives(
            state + 0.5 * h * k1,
            portfolio,
            params,
            der_loss_mw=der_loss_mw,
            load_shed_mw=load_shed_mw,
        )
        k3 = self._derivatives(
            state + 0.5 * h * k2,
            portfolio,
            params,
            der_loss_mw=der_loss_mw,
            load_shed_mw=load_shed_mw,
        )
        k4 = self._derivatives(
            state + h * k3,
            portfolio,
            params,
            der_loss_mw=der_loss_mw,
            load_shed_mw=load_shed_mw,
        )
        return state + (h / 6.0) * (k1 + 2.0 * k2 + 2.0 * k3 + k4)

    def _violations(self, portfolio: LowInertiaPortfolio, metrics: Dict[str, float]) -> List[str]:
        criteria = self.study.criteria
        violations: List[str] = []
        violations.extend([f"one_hot:{group}" for group in portfolio.one_hot_violations])
        if portfolio.capacity_mw < criteria.min_capacity_mw:
            violations.append("capacity_shortage")
        if portfolio.inertia_mw_s_per_hz < criteria.min_inertia_mw_s_per_hz:
            violations.append("inertia_shortage")
        if portfolio.ffr_mw < criteria.min_ffr_mw:
            violations.append("ffr_shortage")
        if portfolio.damping_mw_per_hz < criteria.min_damping_mw_per_hz:
            violations.append("damping_shortage")
        if metrics["max_abs_rocof_hz_s"] > criteria.max_rocof_hz_s:
            violations.append("dynamic_rocof_limit")
        if metrics["nadir_hz"] < criteria.min_nadir_hz:
            violations.append("dynamic_frequency_nadir")
        if metrics["settling_hz"] < criteria.min_settling_hz:
            violations.append("dynamic_settling_frequency")
        if metrics["max_relative_angle_rad"] > self.max_relative_angle_rad:
            violations.append("interarea_angle_separation")
        if metrics["max_area_frequency_split_hz"] > self.max_area_frequency_split_hz:
            violations.append("interarea_frequency_split")
        if metrics["min_electromechanical_damping_ratio"] < self.min_damping_ratio:
            violations.append("low_electromechanical_damping")
        if metrics["small_signal_stable"] < 1.0:
            violations.append("small_signal_unstable")
        if metrics["load_shed_mw"] > criteria.max_load_shed_mw:
            violations.append("dynamic_load_shed")
        if metrics["der_tripped"] > 0.0:
            violations.append("dynamic_der_cascade_trip")
        return violations


def create_low_inertia_study(name: str = "gb_2019_style_demo") -> LowInertiaStudy:
    """Create a built-in low-inertia study case."""

    if name not in {"gb_2019_style_demo", "default"}:
        raise ValueError(f"Unknown built-in low-inertia study: {name}")
    return LowInertiaStudy.gb_2019_style_demo()


def get_low_inertia_public_data_catalog() -> Dict[str, Dict]:
    """Return public links and handoff metadata for low-inertia studies.

    The catalog intentionally excludes expiring S3 presigned URLs. Those URLs
    behave as bearer links and should be shared out-of-band or regenerated by
    the data owner.
    """

    return {
        section: dict(values)
        for section, values in LOW_INERTIA_PUBLIC_DATA_CATALOG.items()
    }


def solve_low_inertia_counterfactual(
    study: Optional[LowInertiaStudy] = None,
    **kwargs,
) -> LowInertiaSearchResult:
    """Solve a low-inertia counterfactual search with a one-call API."""

    return LowInertiaOptimizer(study).solve(**kwargs)


def label_low_inertia_dynamics(
    study: Optional[LowInertiaStudy] = None,
    *,
    portfolio: Optional[LowInertiaPortfolio] = None,
    bits: Optional[Sequence[int]] = None,
    include_trace: bool = True,
    **kwargs,
) -> LowInertiaValidation:
    """Label one low-inertia portfolio with the two-area dynamic surrogate."""

    active_study = study or LowInertiaStudy.gb_2019_style_demo()
    if portfolio is None:
        portfolio = active_study.decode(bits if bits is not None else active_study.baseline_bits())
    return LowInertiaDynamicLabeler(active_study, **kwargs).validate(
        portfolio,
        include_trace=include_trace,
    )
