#include "test_util.h"
#include "cell_sm.h"

static void test_boot_to_idle_requires_self_test(void) {
    cell_sm_t sm;
    cell_sm_init(&sm);
    CHECK_EQ(CELL_STATE_BOOT, sm.state);
    CHECK(cell_sm_self_test_passed(&sm));
    CHECK_EQ(CELL_STATE_IDLE, sm.state);
}

static void test_start_stop_cycle(void) {
    cell_sm_t sm;
    cell_sm_init(&sm);
    cell_sm_self_test_passed(&sm);

    CHECK(cell_sm_start(&sm));
    CHECK_EQ(CELL_STATE_STARTING, sm.state);
    CHECK(!cell_sm_start(&sm)); /* not idle anymore -- rejected */

    CHECK(cell_sm_start_settled(&sm));
    CHECK_EQ(CELL_STATE_RUNNING, sm.state);

    CHECK(cell_sm_stop(&sm));
    CHECK_EQ(CELL_STATE_STOPPING, sm.state);
    CHECK(cell_sm_stop_settled(&sm));
    CHECK_EQ(CELL_STATE_IDLE, sm.state);
}

static void test_estop_preempts_running_immediately(void) {
    cell_sm_t sm;
    cell_sm_init(&sm);
    cell_sm_self_test_passed(&sm);
    cell_sm_start(&sm);
    cell_sm_start_settled(&sm);
    CHECK_EQ(CELL_STATE_RUNNING, sm.state);

    cell_sm_update(&sm, /*estop=*/true, /*fault=*/false, /*safe_stop=*/false);
    CHECK_EQ(CELL_STATE_ESTOP, sm.state);

    /* Still active: reset must be rejected. */
    CHECK(!cell_sm_reset(&sm, true, false, false));
    CHECK_EQ(CELL_STATE_ESTOP, sm.state);

    /* Cleared: reset now succeeds, lands in IDLE (needs a fresh START, not auto-run). */
    CHECK(cell_sm_reset(&sm, false, false, false));
    CHECK_EQ(CELL_STATE_IDLE, sm.state);
}

static void test_estop_outranks_fault_and_safe_stop(void) {
    cell_sm_t sm;
    cell_sm_init(&sm);
    cell_sm_self_test_passed(&sm);
    cell_sm_start(&sm);
    cell_sm_start_settled(&sm);

    /* All three conditions true at once: ESTOP must win (priority order). */
    cell_sm_update(&sm, true, true, true);
    CHECK_EQ(CELL_STATE_ESTOP, sm.state);
}

static void test_fault_latches_until_reset(void) {
    cell_sm_t sm;
    cell_sm_init(&sm);
    cell_sm_self_test_passed(&sm);
    cell_sm_start(&sm);
    cell_sm_start_settled(&sm);

    cell_sm_update(&sm, false, true, false);
    CHECK_EQ(CELL_STATE_FAULT, sm.state);

    /* Fault condition no longer true, but state stays latched without an explicit reset. */
    cell_sm_update(&sm, false, false, false);
    CHECK_EQ(CELL_STATE_FAULT, sm.state);

    CHECK(cell_sm_reset(&sm, false, false, false));
    CHECK_EQ(CELL_STATE_IDLE, sm.state);
}

static void test_reset_rejected_when_nothing_latched(void) {
    cell_sm_t sm;
    cell_sm_init(&sm);
    cell_sm_self_test_passed(&sm);
    CHECK(!cell_sm_reset(&sm, false, false, false));
    CHECK_EQ(CELL_STATE_IDLE, sm.state);
}

int main(void) {
    test_boot_to_idle_requires_self_test();
    test_start_stop_cycle();
    test_estop_preempts_running_immediately();
    test_estop_outranks_fault_and_safe_stop();
    test_fault_latches_until_reset();
    test_reset_rejected_when_nothing_latched();
    TEST_SUMMARY_AND_RETURN();
}
