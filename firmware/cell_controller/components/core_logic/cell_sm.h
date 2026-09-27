/* Cell Controller state machine (ARCHITECTURE.md section 4, cell_state.v1).
 * C99, no ESP-IDF dependency (README.md rule 1) — mirrors msfc.domain.enums.MachineState and
 * msfc.sim.engine.SimCellController's transition behavior so firmware and simulator agree.
 */
#ifndef MSFC_CELL_SM_H
#define MSFC_CELL_SM_H

#include <stdbool.h>
#include <stdint.h>

typedef enum {
    CELL_STATE_BOOT = 0,
    CELL_STATE_SELF_TEST,
    CELL_STATE_IDLE,
    CELL_STATE_STARTING,
    CELL_STATE_RUNNING,
    CELL_STATE_STOPPING,
    CELL_STATE_SAFE_STOP,
    CELL_STATE_FAULT,
    CELL_STATE_ESTOP,
} cell_state_t;

typedef struct {
    cell_state_t state;
} cell_sm_t;

void cell_sm_init(cell_sm_t *sm);
const char *cell_sm_state_name(cell_state_t state);
bool cell_sm_is_non_production(cell_state_t state);
bool cell_sm_is_latched(cell_state_t state);

/* Called once per control cycle with the current safety conditions. Enforces
 * ESTOP > SAFE_STOP > FAULT priority (HARDWARE_INTERFACE.md section "Quy tắc thiết kế" rule 7):
 * any active override latches the corresponding state regardless of what the explicit command
 * functions below do. Latched states persist until cell_sm_reset() succeeds. */
void cell_sm_update(cell_sm_t *sm, bool estop_active, bool fault_active, bool safe_stop_active);

/* Explicit commands. Each returns false (no-op) if the state doesn't allow it. */
bool cell_sm_self_test_passed(cell_sm_t *sm);   /* BOOT/SELF_TEST -> IDLE */
bool cell_sm_start(cell_sm_t *sm);              /* IDLE -> STARTING */
bool cell_sm_start_settled(cell_sm_t *sm);      /* STARTING -> RUNNING */
bool cell_sm_stop(cell_sm_t *sm);               /* RUNNING -> STOPPING */
bool cell_sm_stop_settled(cell_sm_t *sm);       /* STOPPING -> IDLE */

/* Clears a latched state and returns to IDLE. Only succeeds if none of the three override
 * conditions are still active (SAFETY_CONCEPT.md: "sau mọi reset -> IDLE, cần START mới"). */
bool cell_sm_reset(cell_sm_t *sm, bool estop_active, bool fault_active, bool safe_stop_active);

#endif /* MSFC_CELL_SM_H */
