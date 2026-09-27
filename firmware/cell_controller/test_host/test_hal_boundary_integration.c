/* Proves core_logic drives real hardware ONLY through hal_interface.h, end to end:
 * hal_inputs_read() (mocked) -> cell_sm/fault_manager -> safety_supervisor -> hal_outputs_write()
 * (mocked). This is the firmware-side analogue of edge/tests/integration/test_full_pipeline_mvp.py
 * -- proof that the layers wire together, not a claim about real hardware behavior.
 */
#include "test_util.h"
#include "cell_sm.h"
#include "fault_manager.h"
#include "safety_supervisor.h"
#include "hal_interface.h"
#include "hal_host_mock.h"

static void one_cycle(cell_sm_t *sm, fault_manager_t *fm, uint32_t requested_pwm, bool requested_pusher) {
    hal_inputs_t in;
    hal_inputs_read(&in); /* reads whatever the test set via hal_host_mock_set_inputs() */

    if (in.estop_active) {
        fault_manager_raise(fm, FAULT_F001_ESTOP_ACTIVE);
    } else {
        fault_manager_ack(fm, FAULT_F001_ESTOP_ACTIVE);
    }

    cell_sm_update(sm, in.estop_active, fault_manager_any_latched_active(fm), false);

    hal_outputs_t out;
    safety_supervisor_compute_outputs(sm->state, (uint8_t)requested_pwm, true, requested_pusher, &out);
    hal_outputs_write(&out);
}

static void test_estop_wire_cut_forces_motor_and_relay_off(void) {
    cell_sm_t sm;
    fault_manager_t fm;
    cell_sm_init(&sm);
    fault_manager_init(&fm);
    cell_sm_self_test_passed(&sm);
    cell_sm_start(&sm);
    cell_sm_start_settled(&sm);
    hal_host_mock_reset();

    hal_inputs_t running_inputs = {0};
    running_inputs.now_mono_ms = 1000;
    hal_host_mock_set_inputs(&running_inputs);
    one_cycle(&sm, &fm, 70, true);

    const hal_outputs_t *out = hal_host_mock_get_last_outputs();
    CHECK(out->motor_enable);
    CHECK(out->safety_relay_closed);
    CHECK_EQ(70, out->motor_pwm_pct);

    /* IF-HW-01: a cut wire reads as estop_active = true (fail-safe), exactly like a real press. */
    hal_inputs_t estop_inputs = running_inputs;
    estop_inputs.estop_active = true;
    estop_inputs.now_mono_ms = 1010;
    hal_host_mock_set_inputs(&estop_inputs);
    one_cycle(&sm, &fm, 70, true);

    out = hal_host_mock_get_last_outputs();
    CHECK_EQ(CELL_STATE_ESTOP, sm.state);
    CHECK(!out->motor_enable);
    CHECK(!out->safety_relay_closed);
    CHECK_EQ(0, out->motor_pwm_pct);
    CHECK(!out->pusher_extend);
}

static void test_selftest_failure_is_visible_through_hal(void) {
    hal_host_mock_reset();
    hal_host_mock_set_selftest_result(/*should_fail=*/true);
    uint32_t fault_mask = 0;
    hal_selftest(&fault_mask);
    CHECK(fault_mask != 0);

    hal_host_mock_set_selftest_result(/*should_fail=*/false);
    hal_selftest(&fault_mask);
    CHECK_EQ(0, fault_mask);
}

int main(void) {
    test_estop_wire_cut_forces_motor_and_relay_off();
    test_selftest_failure_is_visible_through_hal();
    TEST_SUMMARY_AND_RETURN();
}
