-- Campus Equipment & Lab Instrument Reservation with Maintenance Ledger
-- Re-running this file drops and recreates every table (all data is lost).

CREATE DATABASE IF NOT EXISTS campus_equipment;
USE campus_equipment;

DROP TABLE IF EXISTS maintenance_records;
DROP TABLE IF EXISTS reservations;
DROP TABLE IF EXISTS equipment;
DROP TABLE IF EXISTS categories;
DROP TABLE IF EXISTS labs;
DROP TABLE IF EXISTS users;

CREATE TABLE users (
    user_id       INT AUTO_INCREMENT PRIMARY KEY,
    name          VARCHAR(100) NOT NULL,
    email         VARCHAR(120) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    department    VARCHAR(100) NOT NULL,
    role          ENUM('student', 'lab_staff', 'admin') NOT NULL DEFAULT 'student',
    created_at    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE = InnoDB;

CREATE TABLE labs (
    lab_id   INT AUTO_INCREMENT PRIMARY KEY,
    lab_name VARCHAR(100) NOT NULL,
    building VARCHAR(100) NOT NULL,
    room_no  VARCHAR(20)  NOT NULL,
    UNIQUE KEY uq_lab_location (building, room_no)
) ENGINE = InnoDB;

CREATE TABLE categories (
    category_id   INT AUTO_INCREMENT PRIMARY KEY,
    category_name VARCHAR(100) NOT NULL UNIQUE
) ENGINE = InnoDB;

-- Labs and categories cannot be deleted while equipment refers to them (RESTRICT).
CREATE TABLE equipment (
    equipment_id   INT AUTO_INCREMENT PRIMARY KEY,
    asset_tag      VARCHAR(30)  NOT NULL UNIQUE,
    equipment_name VARCHAR(150) NOT NULL,
    category_id    INT NOT NULL,
    lab_id         INT NOT NULL,
    details        TEXT,
    purchase_date  DATE,
    status         ENUM('active', 'retired') NOT NULL DEFAULT 'active',
    FOREIGN KEY (category_id) REFERENCES categories (category_id) ON DELETE RESTRICT,
    FOREIGN KEY (lab_id)      REFERENCES labs (lab_id)             ON DELETE RESTRICT,
    INDEX idx_equipment_name (equipment_name)
) ENGINE = InnoDB;

-- History is never deleted: RESTRICT stops removal of users/equipment that have reservations.
CREATE TABLE reservations (
    reservation_id INT AUTO_INCREMENT PRIMARY KEY,
    equipment_id   INT NOT NULL,
    user_id        INT NOT NULL,
    start_time     DATETIME NOT NULL,
    end_time       DATETIME NOT NULL,
    purpose        VARCHAR(255) NOT NULL,
    status         ENUM('pending', 'approved', 'rejected', 'cancelled', 'completed') NOT NULL DEFAULT 'pending',
    reviewed_by    INT NULL,
    created_at     DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_reservation_time CHECK (end_time > start_time),
    FOREIGN KEY (equipment_id) REFERENCES equipment (equipment_id) ON DELETE RESTRICT,
    FOREIGN KEY (user_id)      REFERENCES users (user_id)           ON DELETE RESTRICT,
    FOREIGN KEY (reviewed_by)  REFERENCES users (user_id)           ON DELETE RESTRICT,
    -- Serves the overlap check: same equipment, approved, time range.
    INDEX idx_reservation_slot (equipment_id, status, start_time, end_time)
) ENGINE = InnoDB;

CREATE TABLE maintenance_records (
    maintenance_id INT AUTO_INCREMENT PRIMARY KEY,
    equipment_id   INT NOT NULL,
    reported_by    INT NOT NULL,
    issue          TEXT NOT NULL,
    action_taken   TEXT NULL,
    status         ENUM('open', 'in_progress', 'resolved') NOT NULL DEFAULT 'open',
    handled_by     INT NULL,
    reported_at    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    resolved_at    DATETIME NULL,
    -- A record has a resolution date exactly when it is resolved.
    CONSTRAINT chk_resolved_at CHECK ((status = 'resolved') = (resolved_at IS NOT NULL)),
    FOREIGN KEY (equipment_id) REFERENCES equipment (equipment_id) ON DELETE RESTRICT,
    FOREIGN KEY (reported_by)  REFERENCES users (user_id)           ON DELETE RESTRICT,
    FOREIGN KEY (handled_by)   REFERENCES users (user_id)           ON DELETE RESTRICT,
    INDEX idx_maintenance_status (equipment_id, status)
) ENGINE = InnoDB;
