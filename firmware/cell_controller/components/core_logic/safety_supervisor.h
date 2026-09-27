/* Safety supervisor — the ONLY place allowed to decide hal_outputs_t (CODING_STANDARDS rule 4:
 * "Ngo ra an toan chi duoc ghi o mot cho duy nhat"). Combines the current cell state with the
 * requested motor/pusher values and enforces:
 *  - SF-07: pusher stays retracted outside RUNNING.
 *  - SF-10 / IF-HW-08/09 fail-safe: motor_enable and safety_relay_closed are false outside
 *    RUNNING, so a floating/boot GPIO state already means "off".
 *  - HARDWARE_INTERFACE.md section 4 ordering: relay closes before PWM rises (enabling), and
 *    motor_enable/relay open before anything else (disabling) — expressed here by simply never
 *    producing a PWM/pusher-extend value unless relay+enable are also true in the same struct;
 *    hal_esp32's writer is responsible for the physical write order.
 */
#ifndef MSFC_SAFETY_SUPERVISOR_H
#define MSFC_SAFETY_SUPERVISOR_H

#include <stdint.h>
#include "cell_sm.h"
#include "hal_interface.h"

void safety_supervisor_compute_outputs(cell_state_t state, uint8_t requested_motor_pwm_pct,
                                        bool requested_motor_forward, bool requested_pusher_extend,
                                        hal_outputs_t *out);

#endif /* MSFC_SAFETY_SUPERVISOR_H */
