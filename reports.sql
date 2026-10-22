-- Report queries. The Flask app loads each query below by its "-- name:" line,
-- so this file is exactly what the Reports page runs. You can also run it directly:
--   mysql -u root -p campus_equipment < reports.sql
USE campus_equipment;
SET @equipment_id = 1;  -- instrument used by the maintenance_history report

-- name: equipment_by_lab_category
-- Equipment by laboratory and category: how many items each lab holds per category (INNER JOIN, GROUP BY).
SELECT l.lab_name, l.building, l.room_no, c.category_name,
       COUNT(*) AS total_items,
       SUM(e.status = 'active') AS active_items
FROM equipment e
JOIN labs l ON l.lab_id = e.lab_id
JOIN categories c ON c.category_id = e.category_id
GROUP BY l.lab_id, l.lab_name, l.building, l.room_no, c.category_id, c.category_name
ORDER BY l.lab_name, c.category_name;

-- name: reservations_by_requester
-- Reservation history by requester and instrument, with a count per outcome (conditional aggregation).
SELECT u.name AS requester, u.department, e.equipment_name, e.asset_tag,
       COUNT(*) AS total_requests,
       SUM(r.status = 'approved') AS approved,
       SUM(r.status = 'completed') AS completed,
       SUM(r.status IN ('rejected', 'cancelled')) AS rejected_or_cancelled,
       MAX(r.start_time) AS latest_slot
FROM reservations r
JOIN users u ON u.user_id = r.user_id
JOIN equipment e ON e.equipment_id = r.equipment_id
GROUP BY u.user_id, u.name, u.department, e.equipment_id, e.equipment_name, e.asset_tag
ORDER BY u.name, total_requests DESC;

-- name: most_reserved
-- Most frequently reserved instruments: approved or completed bookings per item (LEFT JOIN keeps unbooked items).
SELECT e.equipment_name, e.asset_tag, l.lab_name,
       COUNT(r.reservation_id) AS bookings,
       COALESCE(SUM(TIMESTAMPDIFF(MINUTE, r.start_time, r.end_time)), 0) / 60 AS hours_booked
FROM equipment e
JOIN labs l ON l.lab_id = e.lab_id
LEFT JOIN reservations r ON r.equipment_id = e.equipment_id AND r.status IN ('approved', 'completed')
GROUP BY e.equipment_id, e.equipment_name, e.asset_tag, l.lab_name
ORDER BY bookings DESC, e.equipment_name
LIMIT 10;

-- name: under_maintenance
-- Instruments currently under maintenance: items with at least one unresolved record (EXISTS subquery).
SELECT e.equipment_id, e.equipment_name, e.asset_tag, l.lab_name,
       (SELECT COUNT(*) FROM maintenance_records m
         WHERE m.equipment_id = e.equipment_id AND m.status <> 'resolved') AS open_issues,
       (SELECT MIN(m.reported_at) FROM maintenance_records m
         WHERE m.equipment_id = e.equipment_id AND m.status <> 'resolved') AS oldest_report
FROM equipment e
JOIN labs l ON l.lab_id = e.lab_id
WHERE EXISTS (SELECT 1 FROM maintenance_records m
              WHERE m.equipment_id = e.equipment_id AND m.status <> 'resolved')
ORDER BY oldest_report;

-- name: maintenance_history
-- Maintenance history for one instrument (@equipment_id). LEFT JOIN because the handler may still be NULL.
SELECT m.maintenance_id, m.issue, m.action_taken, m.status, m.reported_at, m.resolved_at,
       rep.name AS reporter, h.name AS handler
FROM maintenance_records m
JOIN users rep ON rep.user_id = m.reported_by
LEFT JOIN users h ON h.user_id = m.handled_by
WHERE m.equipment_id = @equipment_id
ORDER BY m.reported_at DESC;

-- name: pending_requests
-- Pending reservation requests, oldest slot first, with requester and equipment location.
SELECT r.reservation_id, u.name AS requester, u.department, e.equipment_name, e.asset_tag,
       l.lab_name, r.start_time, r.end_time, r.purpose, r.created_at
FROM reservations r
JOIN users u ON u.user_id = r.user_id
JOIN equipment e ON e.equipment_id = r.equipment_id
JOIN labs l ON l.lab_id = e.lab_id
WHERE r.status = 'pending'
ORDER BY r.start_time;
