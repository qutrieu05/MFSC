#include "test_util.h"
#include "fault_manager.h"
#include <string.h>

static void test_init_has_no_active_faults(void) {
    fault_manager_t fm;
    fault_manager_init(&fm);
    CHECK(!fault_manager_is_active(&fm, FAULT_F001_ESTOP_ACTIVE));
    CHECK(!fault_manager_any_latched_active(&fm));
}

static void test_latching_fault_survives_clear_attempt(void) {
    fault_manager_t fm;
    fault_manager_init(&fm);
    fault_manager_raise(&fm, FAULT_F010_COMM_LOSS_EDGE);
    CHECK(fault_manager_is_active(&fm, FAULT_F010_COMM_LOSS_EDGE));
    CHECK(fault_manager_any_latched_active(&fm));

    fault_manager_clear_if_not_latching(&fm, FAULT_F010_COMM_LOSS_EDGE);
    CHECK(fault_manager_is_active(&fm, FAULT_F010_COMM_LOSS_EDGE)); /* still active: it latches */

    fault_manager_ack(&fm, FAULT_F010_COMM_LOSS_EDGE);
    CHECK(!fault_manager_is_active(&fm, FAULT_F010_COMM_LOSS_EDGE));
    CHECK(!fault_manager_any_latched_active(&fm));
}

static void test_non_latching_fault_self_clears(void) {
    fault_manager_t fm;
    fault_manager_init(&fm);
    fault_manager_raise(&fm, FAULT_F051_WATCHDOG_RESET);
    CHECK(fault_manager_is_active(&fm, FAULT_F051_WATCHDOG_RESET));
    CHECK(!fault_manager_any_latched_active(&fm)); /* not a latching code */

    fault_manager_clear_if_not_latching(&fm, FAULT_F051_WATCHDOG_RESET);
    CHECK(!fault_manager_is_active(&fm, FAULT_F051_WATCHDOG_RESET));
}

static void test_catalog_codes_match_domain_faults(void) {
    /* Cross-check against msfc.domain.faults.FAULT_CATALOG string codes (edge/src/msfc/domain/faults.py). */
    CHECK(FAULT_TABLE[FAULT_F001_ESTOP_ACTIVE].code[0] == 'F');
    CHECK_EQ(0, strcmp(FAULT_TABLE[FAULT_F001_ESTOP_ACTIVE].code, "F001"));
    CHECK_EQ(0, strcmp(FAULT_TABLE[FAULT_F010_COMM_LOSS_EDGE].code, "F010"));
    CHECK_EQ(0, strcmp(FAULT_TABLE[FAULT_F050_SELF_TEST_FAILED].code, "F050"));
    CHECK_EQ(0, strcmp(FAULT_TABLE[FAULT_F051_WATCHDOG_RESET].code, "F051"));
}

int main(void) {
    test_init_has_no_active_faults();
    test_latching_fault_survives_clear_attempt();
    test_non_latching_fault_self_clears();
    test_catalog_codes_match_domain_faults();
    TEST_SUMMARY_AND_RETURN();
}
