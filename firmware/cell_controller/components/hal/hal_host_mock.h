/* Test-only control surface for hal_host_mock.c — never linked into hal_esp32. */
#ifndef MSFC_HAL_HOST_MOCK_H
#define MSFC_HAL_HOST_MOCK_H

#include "hal_interface.h"

void hal_host_mock_reset(void);
void hal_host_mock_set_inputs(const hal_inputs_t *in);
const hal_outputs_t *hal_host_mock_get_last_outputs(void);
void hal_host_mock_set_selftest_result(bool should_fail);

#endif /* MSFC_HAL_HOST_MOCK_H */
