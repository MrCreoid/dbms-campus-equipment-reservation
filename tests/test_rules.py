import unittest
from datetime import datetime, timedelta

from app import load_reports, maintenance_step_allowed, validate_slot

NOW = datetime(2026, 1, 10, 12, 0)


class SlotValidationTest(unittest.TestCase):
    def test_valid_future_slot(self):
        self.assertIsNone(validate_slot(NOW + timedelta(hours=1), NOW + timedelta(hours=2), NOW))

    def test_end_must_be_after_start(self):
        start = NOW + timedelta(hours=2)
        self.assertIn("later", validate_slot(start, start, NOW))
        self.assertIn("later", validate_slot(start, start - timedelta(minutes=1), NOW))

    def test_slot_must_be_in_future(self):
        self.assertIn("future", validate_slot(NOW - timedelta(hours=1), NOW + timedelta(hours=1), NOW))
        self.assertIn("future", validate_slot(NOW, NOW + timedelta(hours=1), NOW))

    def test_missing_times(self):
        self.assertIsNotNone(validate_slot(None, NOW, NOW))


class MaintenanceStepTest(unittest.TestCase):
    def test_forward_steps_allowed(self):
        self.assertTrue(maintenance_step_allowed("open", "in_progress"))
        self.assertTrue(maintenance_step_allowed("open", "resolved"))
        self.assertTrue(maintenance_step_allowed("in_progress", "resolved"))

    def test_backward_same_or_unknown_rejected(self):
        self.assertFalse(maintenance_step_allowed("resolved", "open"))
        self.assertFalse(maintenance_step_allowed("in_progress", "open"))
        self.assertFalse(maintenance_step_allowed("open", "open"))
        self.assertFalse(maintenance_step_allowed("open", "deleted"))
        self.assertFalse(maintenance_step_allowed("open", None))


class ReportsFileTest(unittest.TestCase):
    def test_every_report_used_by_the_app_is_present(self):
        reports = load_reports()
        expected = {"equipment_by_lab_category", "reservations_by_requester", "most_reserved",
                    "under_maintenance", "maintenance_history", "pending_requests"}
        self.assertEqual(set(reports), expected)
        for sql in reports.values():
            self.assertIn("SELECT", sql)
            self.assertFalse(sql.endswith(";"))


if __name__ == "__main__":
    unittest.main()
