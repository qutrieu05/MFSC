"""OEE / machine monitoring / machine health (Layer 7, Phase 4-5 — FR-OEE, FR-HLT).

Depends only on ``msfc.core`` and ``msfc.domain`` (ARCHITECTURE.md section 7.2, pre-declared
since Phase 0 in edge/tests/unit/test_layer_dependencies.py — the same doc explicitly assigns
this one package "tinh OEE, phan tich suc khoe": OEE calculation AND health analysis, for
phases 4 and 5) — this package is purely observational: it consumes streams of
:class:`~msfc.analytics.events.MachineEvent`/:class:`~msfc.analytics.health_models.HealthEvent`
objects and produces OEE/health metrics. It cannot import ``msfc.sim``, ``msfc.decision``, or
the firmware, so it is architecturally incapable of commanding anything (P4.12/P5's safety
rule: this layer never overrides safety/interlocks).
"""

from __future__ import annotations

from msfc.analytics.anomaly import (
    AnomalyThresholds,
    combine_anomalies,
    detect_baseline_anomaly,
    detect_quality_anomaly,
    detect_trend_anomaly,
)
from msfc.analytics.baseline import HealthBaseline
from msfc.analytics.calculations import (
    calculate_availability,
    calculate_oee,
    calculate_performance,
    calculate_quality,
    to_oee_metrics_v1_payload,
)
from msfc.analytics.evaluation import (
    ClassificationMetrics,
    RegressionMetrics,
    evaluate_detection_delay,
    evaluate_detections,
    evaluate_regression,
)
from msfc.analytics.events import (
    MachineEvent,
    MachineEventType,
    from_fault_report,
    from_product_detected,
    from_product_sorted,
    from_state_changed,
)
from msfc.analytics.features import extract_features
from msfc.analytics.health_events import (
    from_anomaly,
    from_health_score_change,
    from_health_state_change,
    from_measurement as health_event_from_measurement,
)
from msfc.analytics.health_models import (
    AnomalyResult,
    AnomalySeverity,
    FeatureSet,
    HealthEvent,
    HealthEventType,
    HealthScore,
    HealthState,
    SensorMeasurement,
    SensorQuality,
    SensorType,
)
from msfc.analytics.health_monitor import MachineHealthMonitor, MachineHealthSnapshot
from msfc.analytics.health_p4_bridge import bridge_critical_health_to_machine_event
from msfc.analytics.health_repository import InMemorySensorHistoryRepository, SensorHistoryRepository
from msfc.analytics.health_score import compute_health_score, unknown_health_score
from msfc.analytics.models import (
    CycleStatistics,
    DowntimeCategory,
    DowntimeInterval,
    MachineStatus,
    OeeResult,
)
from msfc.analytics.monitor import MachineMonitor
from msfc.analytics.predictive import (
    ModelInputContract,
    PredictiveHealthModel,
    PredictiveHealthResult,
    RuleBasedReferenceModel,
)
from msfc.analytics.quality import QualityConfig, assess_quality, build_measurement
from msfc.analytics.repository import InMemoryOeeSnapshotRepository, OeeSnapshotRepository
from msfc.analytics.sensors import FixedSequenceSensorSource, SensorSource
from msfc.analytics.session import DEFAULT_STATE_CATEGORY, ProductionSession, SessionConfig

__all__ = [
    # P4 — OEE
    "OeeResult",
    "DowntimeCategory",
    "DowntimeInterval",
    "CycleStatistics",
    "MachineStatus",
    "MachineEvent",
    "MachineEventType",
    "from_state_changed",
    "from_product_detected",
    "from_product_sorted",
    "from_fault_report",
    "calculate_availability",
    "calculate_performance",
    "calculate_quality",
    "calculate_oee",
    "to_oee_metrics_v1_payload",
    "SessionConfig",
    "ProductionSession",
    "DEFAULT_STATE_CATEGORY",
    "MachineMonitor",
    "OeeSnapshotRepository",
    "InMemoryOeeSnapshotRepository",
    # P5 — machine health
    "SensorType",
    "SensorQuality",
    "SensorMeasurement",
    "FeatureSet",
    "AnomalySeverity",
    "AnomalyResult",
    "HealthState",
    "HealthScore",
    "HealthEventType",
    "HealthEvent",
    "SensorSource",
    "FixedSequenceSensorSource",
    "QualityConfig",
    "assess_quality",
    "build_measurement",
    "extract_features",
    "HealthBaseline",
    "AnomalyThresholds",
    "detect_baseline_anomaly",
    "detect_trend_anomaly",
    "detect_quality_anomaly",
    "combine_anomalies",
    "compute_health_score",
    "unknown_health_score",
    "health_event_from_measurement",
    "from_anomaly",
    "from_health_state_change",
    "from_health_score_change",
    "MachineHealthMonitor",
    "MachineHealthSnapshot",
    "ModelInputContract",
    "PredictiveHealthResult",
    "PredictiveHealthModel",
    "RuleBasedReferenceModel",
    "SensorHistoryRepository",
    "InMemorySensorHistoryRepository",
    "bridge_critical_health_to_machine_event",
    "ClassificationMetrics",
    "RegressionMetrics",
    "evaluate_detections",
    "evaluate_regression",
    "evaluate_detection_delay",
]
