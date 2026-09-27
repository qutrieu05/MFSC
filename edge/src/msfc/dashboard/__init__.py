"""Official S1 Web Dashboard (Layer 8) -- backend adapter + REST/WebSocket API.

Reserved since Phase 0 (ARCHITECTURE.md section 7.1, "cong nghe cho quyet dinh o Phase 4",
ADR-0012) and now built. Per the layer dependency rule
(edge/tests/unit/test_layer_dependencies.py), ``dashboard`` may import ``core``/``domain``/
``contracts``/``comm``/``storage`` (as originally declared) plus ``services``/``analytics``/
``sim``/``vision``/``ocr``/``decision`` (added this phase -- see DECISIONS.md): the dashboard's
whole purpose is to display ``CellRuntime``/OEE/health data (``services``/``analytics``), and
the demonstration-mode session needs to construct the same vision/OCR/decision engines and
stage configs a real deployment would (mirroring exactly what ``msfc.services`` itself is
already allowed to depend on) plus ``SimCellController`` (section 5: "Reuse: CellRuntime,
SimCellController, InMemoryBus...") since no hardware exists.

``msfc.sim``/``msfc.vision``/``msfc.ocr``/``msfc.decision`` are imported from exactly ONE module
in this package: :mod:`msfc.dashboard.session`, which owns the one ``SimCellController``
instance and the scripted engines backing the demo. Every other module here (``api.py``,
``dtos.py``) only ever sees ``CellRuntime``/``MachineMonitor``/``MachineHealthMonitor`` objects
that ``session.py`` hands them -- so ``session.py`` remains the single seam that would need to
change when real hardware/firmware replaces the simulator (section 15), not the routes or DTOs.
"""

from __future__ import annotations
