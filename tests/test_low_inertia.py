import quantumgridos as qgo
from quantumgridos.power_systems.low_inertia import (
    FrequencySecurityCriteria,
    LowInertiaDynamicLabeler,
    LowInertiaOption,
    LowInertiaStudy,
    LowInertiaValidation,
    label_low_inertia_dynamics,
    solve_low_inertia_counterfactual,
)


def test_low_inertia_one_call_api_finds_secure_candidate():
    result = qgo.solve_low_inertia_counterfactual(
        solvers=("exact", "annealing"),
        top_k=24,
    )

    assert result.baseline.violations
    assert result.best is not None
    assert result.best.feasible
    assert result.best.metrics["nadir_hz"] >= 49.2
    assert "Coal G1 online" in result.best.portfolio.selected_labels


def test_low_inertia_custom_study_can_run_exact_only():
    study = LowInertiaStudy(
        name="tiny_custom_case",
        nominal_hz=50.0,
        base_contingency_mw=250.0,
        der_trip_mw=80.0,
        base_damping_mw_per_hz=80.0,
        default_der_trip_threshold_hz=49.2,
        baseline_options=["g1", "bess_off", "der_default"],
        criteria=FrequencySecurityCriteria(
            min_capacity_mw=300.0,
            min_inertia_mw_s_per_hz=300.0,
            min_ffr_mw=50.0,
            min_damping_mw_per_hz=50.0,
            max_rocof_hz_s=1.0,
            min_nadir_hz=49.0,
            min_settling_hz=49.4,
        ),
        options=[
            LowInertiaOption(
                "g1",
                "G1 online",
                "sync",
                cost=20.0,
                capacity_mw=300.0,
                inertia_mw_s_per_hz=320.0,
                pfr_mw=70.0,
                damping_mw_per_hz=30.0,
            ),
            LowInertiaOption(
                "g2",
                "G2 online",
                "sync",
                cost=25.0,
                capacity_mw=250.0,
                inertia_mw_s_per_hz=280.0,
                pfr_mw=60.0,
                damping_mw_per_hz=25.0,
            ),
            LowInertiaOption("bess_off", "BESS off", "bess", "onehot"),
            LowInertiaOption(
                "bess_ffr",
                "BESS FFR",
                "bess",
                "onehot",
                cost=10.0,
                ffr_mw=90.0,
                ffr_tau_s=0.2,
                damping_mw_per_hz=25.0,
            ),
            LowInertiaOption(
                "der_default",
                "DER default ride-through",
                "der",
                "onehot",
                der_trip_threshold_hz=49.2,
            ),
            LowInertiaOption(
                "der_wide",
                "DER wide ride-through",
                "der",
                "onehot",
                cost=5.0,
                der_trip_threshold_hz=48.7,
                ffr_mw=20.0,
                damping_mw_per_hz=10.0,
            ),
        ],
    )

    result = solve_low_inertia_counterfactual(study, solvers=("exact",), top_k=10)

    assert result.candidates
    assert result.best is not None
    assert result.best.feasible


def test_low_inertia_api_can_run_constrained_qaoa():
    result = qgo.solve_low_inertia_counterfactual(
        solvers=("constrained_qaoa", "constrained_qaoa_warm"),
        top_k=12,
        qaoa_layers=1,
        qaoa_maxiter=20,
        constrained_qaoa_restarts=1,
    )

    assert result.candidates
    assert not result.solver_errors
    assert all(not candidate.portfolio.one_hot_violations for candidate in result.candidates)


def test_dynamic_labeler_returns_interarea_metrics_and_trace():
    study = qgo.create_low_inertia_study()
    portfolio = study.decode(study.baseline_bits())

    validation = LowInertiaDynamicLabeler(study).validate(portfolio)

    assert isinstance(validation, LowInertiaValidation)
    assert validation.time_s
    assert validation.frequency_hz
    assert len(validation.time_s) == len(validation.frequency_hz)
    assert validation.metrics["dynamic_model"] == "two_area_reduced_electromechanical_surrogate"
    assert "max_relative_angle_rad" in validation.metrics
    assert "max_area_frequency_split_hz" in validation.metrics
    assert "dominant_eigenvalue_real" in validation.metrics
    assert "min_electromechanical_damping_ratio" in validation.metrics


def test_low_inertia_one_call_dynamic_label_api():
    study = qgo.create_low_inertia_study()
    validation = label_low_inertia_dynamics(study, bits=study.baseline_bits())

    assert isinstance(validation, LowInertiaValidation)
    assert validation.metrics["nadir_hz"] < study.nominal_hz
    assert validation.metrics["validated_objective"] >= validation.portfolio.cost


def test_counterfactual_solver_can_use_dynamic_labels():
    result = qgo.solve_low_inertia_counterfactual(
        solvers=("exact",),
        top_k=12,
        dynamic_labels=True,
        include_traces=True,
    )

    assert result.candidates
    assert result.baseline.metrics["dynamic_model"] == "two_area_reduced_electromechanical_surrogate"
    assert result.baseline.time_s
    assert all(
        candidate.metrics["dynamic_model"] == "two_area_reduced_electromechanical_surrogate"
        for candidate in result.candidates
    )


def test_low_inertia_public_data_catalog_exposes_stable_links_without_signed_url():
    catalog = qgo.get_low_inertia_public_data_catalog()

    assert catalog["quantumgridos"]["repository"] == "https://github.com/saralsystems/quantumgridos"
    assert catalog["s3_public_handoff_bundle"]["bucket"] == "qgo-low-inertia-public-data-20260706-654777652612"
    assert catalog["execution_requirements"]["cuda_required"] is True
    assert "rts_gmlc_repository" in catalog["public_sources"]

    rendered = repr(catalog)
    assert "X-Amz-" not in rendered
    assert "AKIA" not in rendered
