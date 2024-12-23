-- Table structure for `session`
CREATE TABLE `session` (
  `id` int NOT NULL AUTO_INCREMENT,
  `year` varchar(20) NOT NULL,
  `is_current` tinyint(1) DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `year` (`year`)
) ENGINE=InnoDB AUTO_INCREMENT=6 DEFAULT CHARSET=utf8mb3;

-- Data for `session`
INSERT INTO session VALUES (1, '2023/2024', 0);
INSERT INTO session VALUES (2, '2024/2025', 1);
INSERT INTO session VALUES (3, '2026/2027', 0);
INSERT INTO session VALUES (4, '2027/2028', 0);
INSERT INTO session VALUES (5, '2028/2029', 0);

