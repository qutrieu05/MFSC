/* hal_host_mock — scripted HAL for unit-testing core_logic on the laptop (P1.5, no hardware).
 * Tests set inputs with hal_host_mock_set_inputs(), call into core_logic, then inspect the
 * outputs that were written via hal_host_mock_get_last_outputs(). Not linked into any
 * ESP32 build; hal_esp32 (P1.10, real hardware) implements the same three functions instead.
 */
#include "hal_interface.h"

static hal_inputs_t s_inputs;
static hal_outputs_t s_last_outputs;
static bool s_selftest_fail;

void hal_host_mock_reset(void) {
    hal_inputs_t empty_in = {0};
    hal_outputs_t empty_out = {0};
    s_inputs = empty_in;
    s_last_outputs = empty_out;
    s_selftest_fail = false;
}

void hal_host_mock_set_inputs(const hal_inputs_t *in) {
    s_inputs = *in;
}

const hal_outputs_t *hal_host_mock_get_last_outputs(void) {
    return &s_last_outputs;
}

void hal_host_mock_set_selftest_result(bool should_fail) {
    s_selftest_fail = should_fail;
}

hal_status_t hal_inputs_read(hal_inputs_t *out) {
    *out = s_inputs;
    return HAL_OK;
}

hal_status_t hal_outputs_write(const hal_outputs_t *in) {
    s_last_outputs = *in;
    return HAL_OK;
}

hal_status_t hal_selftest(uint32_t *fault_mask) {
    *fault_mask = s_selftest_fail ? 1u : 0u;
    return HAL_OK;
}
