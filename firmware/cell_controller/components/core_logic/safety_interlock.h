/* Phase 2 — Safety / Interlock layer (P2.1-P2.4, P2.5, P2.6, P2.7, P2.8).
 *
 * SOFTWARE-ONLY SAFETY SIMULATION.
 * This module proves the interlock LOGIC is correct on the host, running against
 * hal_host_mock. It is NOT a claim of physical safety validation, and the software E-STOP
 * path here is NOT equivalent to a physical Emergency Stop circuit — the mandatory hardware
 * E-stop channel (SAF-01, IF-HW-01: NC contact, wire-cut = active, cuts SAFETY_RELAY directly)
 * is a separate, physical safety function that does not depend on any code running at all.
 * Physical E-stop electrical validation remains PENDING until real hardware exists —
 * see PHASE2_COMPLETION_REPORT.md.
 *
 * Purely additive: wraps the existing P1 modules (cell_sm, fault_manager, watchdog,
 * cmd_handler) into one supervisor with the PO-named safety-state view and a richer
 * interlock/reject-reason set. None of cell_sm.c/fault_manager.c/watchdog.c/cmd_handler.c
 * were modified to build this (D-038/D-039, DECISIONS.md).
 */
#ifndef MSFC_SAFETY_INTERLOCK_H
#define MSFC_SAFETY_INTERLOCK_H

#include <stdbool.h>
#include <stdint.h>

#include "cell_sm.h"
#include "cmd_handler.h"
#include "fault_manager.h"
#include "watchdog.h"

/* The 6 states named in the PO's Phase 2 directive. A VIEW derived from cell_sm_t's 9 states
 * (see safety_interlock_state()) plus one genuinely new concept, RECOVERY — see D-038 for the
 * exact mapping and why it isn't a parallel state machine. */
typedef enum {
    SAFETY_STATE_SAFE_IDLE = 0, /* cell_sm BOOT/SELF_TEST: booting, not yet self-tested */
    SAFETY_STATE_READY,         /* cell_sm IDLE: self-tested, no interlock active, can START */
    SAFETY_STATE_RUNNING,       /* cell_sm STARTING/RUNNING/STOPPING: motion may be live */
    SAFETY_STATE_FAULT,         /* cell_sm FAULT or SAFE_STOP: a non-ESTOP safety stop is latched */
    SAFETY_STATE_ESTOP,         /* cell_sm ESTOP: highest-priority latched stop */
    SAFETY_STATE_RECOVERY,      /* reset accepted, awaiting safety_interlock_confirm_recovery() */
} safety_state_t;

const char *safety_state_name(safety_state_t state);

/* Reasons this layer itself can reject a command, on top of cmd_handler's reject_reason_t
 * (see interlock_ack_t.cmd_reason). Firmware-local for now, not yet part of the shared
 * msfc.domain.enums.RejectReason / cmd_ack.v1 contract — see D-039. */
typedef enum {
    INTERLOCK_OK = 0,
    INTERLOCK_REJECT_FROM_CMD_HANDLER,   /* see cmd_reason for the specific P1 cause */
    INTERLOCK_REJECT_COMM_LOSS,          /* mirrors RejectReason.EDGE_HEARTBEAT_MISSING */
    INTERLOCK_REJECT_MOTOR_FAULT,
    INTERLOCK_REJECT_SENSOR_FAULT,
    INTERLOCK_REJECT_RECOVERY_NOT_COMPLETE,
} interlock_reject_t;

typedef struct {
    cmd_result_t result;
    interlock_reject_t interlock_reason;
    reject_reason_t cmd_reason; /* valid only when interlock_reason == INTERLOCK_REJECT_FROM_CMD_HANDLER */
} interlock_ack_t;

typedef struct {
    cell_sm_t sm;
    fault_manager_t faults;
    watchdog_t comm_watchdog;
    bool estop_active;    /* cached from the last safety_interlock_update() */
    bool motor_fault;
    bool sensor_fault;
    bool comm_loss;        /* cached result of watchdog_check() */
    bool recovery_pending; /* true from an accepted RESET until confirm_recovery() succeeds */
} safety_interlock_t;

void safety_interlock_init(safety_interlock_t *sup, uint32_t comm_heartbeat_timeout_ms, uint32_t now_mono_ms);

/* SF-05: boot self-test gate. On failure, raises the existing F050 fault (fault_manager.c,
 * unmodified) so the very next safety_interlock_update() call puts the system into FAULT
 * instead of READY. */
void safety_interlock_self_test(safety_interlock_t *sup, bool passed);

/* Comm heartbeat received -- feeds the comm watchdog (P2.5/P2.6). */
void safety_interlock_feed_comm_heartbeat(safety_interlock_t *sup, uint32_t now_mono_ms);

/* Call once per control cycle with the current interlock conditions. Derives cell_sm's
 * estop/fault overrides (motor fault OR sensor fault OR comm loss OR any latched
 * fault_manager fault all count as "fault_active" for cell_sm's priority logic). */
void safety_interlock_update(safety_interlock_t *sup, bool estop_active, bool motor_fault,
                              bool sensor_fault, uint32_t now_mono_ms);

safety_state_t safety_interlock_state(const safety_interlock_t *sup);

/* The P2 interlock matrix (P2.2/P2.3/P2.7): checks motor/sensor fault, comm loss and the
 * recovery gate first, then falls through to the existing, unmodified cmd_handler_dispatch()
 * for everything cell_sm/cmd_handler already knows how to reject (P2.1-era rules). A RESET
 * that cmd_handler accepts does NOT return the system to READY immediately -- it enters
 * RECOVERY and blocks START/SET_SPEED/PUSHER_TEST until safety_interlock_confirm_recovery()
 * succeeds (P2.8: no automatic recovery). */
interlock_ack_t safety_interlock_dispatch(safety_interlock_t *sup, cmd_action_t action, int32_t param);

/* P2.8: explicit second step of recovery. Fails (returns false, stays in RECOVERY) if a
 * blocking condition reappeared since the reset was accepted. */
bool safety_interlock_confirm_recovery(safety_interlock_t *sup, uint32_t now_mono_ms);

#endif /* MSFC_SAFETY_INTERLOCK_H */
