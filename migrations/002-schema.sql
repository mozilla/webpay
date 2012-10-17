CREATE TABLE `issuers` (
    `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `domain` varchar(255) NOT NULL,
    `chargeback_url` varchar(200) NOT NULL,
    `postback_url` varchar(200) NOT NULL,
    `issuer_key` varchar(255) NOT NULL UNIQUE,
    `key_timestamp` varchar(10),
    `is_https` bool NOT NULL,
    `private_key` blob
) ENGINE=InnoDB CHARACTER SET utf8 COLLATE utf8_general_ci;
CREATE TABLE `transactions` (
    `uuid` varchar(128) NOT NULL PRIMARY KEY,
    `typ` integer NOT NULL,
    `state` integer NOT NULL,
    `issuer_key` varchar(255) NOT NULL,
    `issuer_id` integer NOT NULL,
    `amount` numeric(9, 2),
    `currency` varchar(3) NOT NULL,
    `name` varchar(100) NOT NULL,
    `description` varchar(255) NOT NULL,
    `json_request` longtext NOT NULL,
    `notify_url` varchar(255),
    `last_error` varchar(255)
) ENGINE=InnoDB CHARACTER SET utf8 COLLATE utf8_general_ci;
ALTER TABLE `transactions` ADD CONSTRAINT `issuer_id_refs_id_76735c35` FOREIGN KEY (`issuer_id`) REFERENCES `issuers` (`id`);
CREATE TABLE `notices` (
    `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `transaction_id` varchar(128) NOT NULL,
    `url` varchar(255) NOT NULL,
    `success` bool NOT NULL,
    `last_error` varchar(255)
) ENGINE=InnoDB CHARACTER SET utf8 COLLATE utf8_general_ci;
ALTER TABLE `notices` ADD CONSTRAINT `transaction_id_refs_uuid_42dc0546` FOREIGN KEY (`transaction_id`) REFERENCES `transactions` (`uuid`);
CREATE INDEX `issuers_667f58ba` ON `issuers` (`key_timestamp`);
CREATE INDEX `transactions_355bfc27` ON `transactions` (`state`);
CREATE INDEX `transactions_70c373c4` ON `transactions` (`issuer_key`);
CREATE INDEX `transactions_8372547` ON `transactions` (`issuer_id`);
CREATE INDEX `notices_ba2e654d` ON `notices` (`transaction_id`);
