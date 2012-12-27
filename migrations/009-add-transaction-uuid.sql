ALTER TABLE `notices` ADD COLUMN `transaction_uuid` varchar(255) NOT NULL;
ALTER TABLE `notices` DROP FOREIGN KEY `transaction_id_refs_uuid_42dc0546`;
ALTER TABLE `notices` DROP COLUMN `transaction`;
