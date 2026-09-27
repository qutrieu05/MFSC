/* HAL API — contract between core_logic and hardware (docs/HARDWARE_INTERFACE.md section 4).
 *
 * core_logic calls ONLY these functions; it never sees GPIO/ESP-IDF/pin numbers, so it stays
 * host-testable and hardware swaps (P1.10) never touch decision logic (rule 1, README.md).
 *
 * Deviation from docs/HARDWARE_INTERFACE.md's snippet: functions return hal_status_t here,
 * not esp_err_t. esp_err_t is an ESP-IDF type, and core_logic (this header included) must not
 * depend on ESP-IDF (rule 1). hal_esp32's implementation (P1.10, real hardware) converts its
 * internal esp_err_t to hal_status_t at this boundary; the signal contract itself is unchanged.
 */
#ifndef MSFC_HAL_INTERFACE_H
#define MSFC_HAL_INTERFACE_H

#include <stdbool.h>
#include <stdint.h>

typedef enum {
    HAL_OK = 0,
    HAL_ERROR = -1,
} hal_status_t;

/* Read once per control cycle (~10 ms). */
typedef struct {
    bool     estop_active;     /* IF-HW-01, fail-safe already applied (wire cut = active) */
    bool     reset_pressed;    /* IF-HW-02, debounced, edge-detected */
    bool     start_pressed;    /* IF-HW-03, debounced, edge-detected */
    bool     s1_edge;          /* IF-HW-04, new edge since last read */
    uint32_t s1_edge_mono_ms;
    bool     s2_edge;          /* IF-HW-05 */
    uint32_t s2_edge_mono_ms;
    uint32_t now_mono_ms;      /* device's own monotonic clock */
} hal_inputs_t;

/* Written from exactly one place, after safety_supervisor has decided the values
 * (CODING_STANDARDS rule 4 / safety_supervisor.h). */
typedef struct {
    bool    motor_enable;        /* IF-HW-08 */
    bool    safety_relay_closed; /* IF-HW-09 */
    uint8_t motor_pwm_pct;       /* IF-HW-06, 0..100 */
    bool    motor_forward;       /* IF-HW-07 */
    bool    pusher_extend;       /* IF-HW-10 */
    bool    led_green;
    bool    led_yellow;
    bool    led_red;
    bool    buzzer;
} hal_outputs_t;

hal_status_t hal_inputs_read(hal_inputs_t *out);
hal_status_t hal_outputs_write(const hal_outputs_t *in);
hal_status_t hal_selftest(uint32_t *fault_mask);

#endif /* MSFC_HAL_INTERFACE_H */
