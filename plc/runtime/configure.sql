-- Headless OpenPLC setup, applied at image build. Slave devices come from mbconfig.cfg
-- (generated from contracts/modbus/sim-io.yaml), not from the Slave_dev table: do not edit
-- slave devices or settings in the web UI, it would regenerate mbconfig.cfg from the empty table.
UPDATE Settings SET Value = 'true'     WHERE Key = 'Start_run_mode';
UPDATE Settings SET Value = '502'      WHERE Key = 'Modbus_port';
UPDATE Settings SET Value = 'disabled' WHERE Key = 'Dnp3_port';
UPDATE Settings SET Value = 'disabled' WHERE Key = 'Enip_port';
UPDATE Settings SET Value = 'disabled' WHERE Key = 'Pstorage_polling';
UPDATE Settings SET Value = 'false'    WHERE Key = 'snap7';
INSERT INTO Programs (Name, Description, File, Date_upload)
VALUES ('Line1', 'Delfts Sap Line 1 control program', 'line1.st', strftime('%s', 'now'));
