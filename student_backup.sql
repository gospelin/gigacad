-- Table structure for `student`
CREATE TABLE `student` (
  `id` int NOT NULL AUTO_INCREMENT,
  `first_name` varchar(50) NOT NULL,
  `last_name` varchar(50) NOT NULL,
  `username` varchar(50) NOT NULL,
  `password` varchar(200) NOT NULL,
  `gender` varchar(10) NOT NULL,
  `date_of_birth` date DEFAULT NULL,
  `parent_phone_number` varchar(11) DEFAULT NULL,
  `address` varchar(255) DEFAULT NULL,
  `parent_occupation` varchar(100) DEFAULT NULL,
  `previous_class` varchar(50) DEFAULT NULL,
  `state_of_origin` varchar(50) DEFAULT NULL,
  `local_government_area` varchar(50) DEFAULT NULL,
  `religion` varchar(50) DEFAULT NULL,
  `date_registered` datetime DEFAULT CURRENT_TIMESTAMP,
  `approved` tinyint(1) DEFAULT NULL,
  `user_id` int DEFAULT NULL,
  `middle_name` varchar(50) DEFAULT NULL,
  `parent_name` varchar(70) DEFAULT NULL,
  `has_paid_fee` tinyint(1) DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `username` (`username`),
  KEY `user_id` (`user_id`),
  CONSTRAINT `student_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `user` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=100 DEFAULT CHARSET=utf8mb3;

-- Data for `student`
INSERT INTO student VALUES (5, 'Helen', 'Charles ', 'helen.charles', 'mCCVEXV9', 'female', datetime.date(2024, 6, 18), '', '', '', 'Creche', '', '', '', datetime.datetime(2024, 6, 18, 18, 24, 38), 0, 7, 'Mkpuruoma ', '', None);
INSERT INTO student VALUES (6, 'Chinenye', 'Victory', 'chinenye.victory', 'NDNN6Qfv', 'female', datetime.date(2024, 6, 18), '', '', '', 'Creche', '', '', '', datetime.datetime(2024, 6, 18, 18, 26, 46), 0, 8, '', '', None);
INSERT INTO student VALUES (7, 'Ogochukwu', 'Okoye', 'ogochukwu.okoye', 'xpnxtn6J', 'female', datetime.date(2024, 6, 18), '', '', '', 'Creche', '', '', '', datetime.datetime(2024, 6, 18, 18, 27, 38), 0, 9, 'Obioma', '', None);
INSERT INTO student VALUES (8, 'David', 'Ndubueze', 'david.ndubueze', '2gNRYTeV', 'male', datetime.date(2024, 6, 18), '', '', '', 'Creche', '', '', '', datetime.datetime(2024, 6, 18, 18, 28, 13), 0, 10, 'Chidiebube ', '', None);
INSERT INTO student VALUES (9, 'Taylor', 'Imeole', 'taylor.imeole', 'mPzgOCqN', 'male', datetime.date(2024, 6, 18), '', '', '', 'Creche', '', '', '', datetime.datetime(2024, 6, 18, 18, 29, 14), 1, 11, 'Ayor', '', None);
INSERT INTO student VALUES (10, 'Temple', 'Williams', 'temple.williams', 'GoAK3cbm', 'male', datetime.date(2024, 6, 18), '', '', '', 'Creche', '', '', '', datetime.datetime(2024, 6, 18, 18, 30, 56), 1, 12, 'Akachukwu', '', None);
INSERT INTO student VALUES (11, 'Jadon', 'Nwoji', 'jadon.nwoji', 'LBMwAX41', 'male', datetime.date(2024, 6, 18), '', '', '', 'Creche', '', '', '', datetime.datetime(2024, 6, 18, 18, 32, 7), 1, 13, 'Chukwudi', '', None);
INSERT INTO student VALUES (12, 'Joshua ', 'Nwoji', 'joshua.nwoji', 'MQ15gqSw', 'male', datetime.date(2024, 6, 18), '', '', '', 'Creche', '', '', '', datetime.datetime(2024, 6, 18, 18, 32, 59), 1, 14, 'Chimeremeze', '', None);
INSERT INTO student VALUES (13, 'Ezinne', 'Chinenye ', 'ezinne.chinenye', 'gNEwSKBq', 'female', datetime.date(2024, 6, 18), '', '', '', 'Creche', '', '', '', datetime.datetime(2024, 6, 18, 18, 33, 45), 1, 15, 'Esther', '', None);
INSERT INTO student VALUES (14, 'John', 'Miracle ', 'john.miracle', 'aQY1dkjv', 'male', datetime.date(2024, 6, 18), '', '', '', 'Creche', '', '', '', datetime.datetime(2024, 6, 18, 18, 34, 16), 1, 16, '', '', None);
INSERT INTO student VALUES (15, 'Adaeze ', 'Okechukwu', 'adaeze.okechukwu', 'jRsa0ffv', 'female', datetime.date(2024, 6, 18), '', '', '', 'Creche', '', '', '', datetime.datetime(2024, 6, 18, 18, 35, 4), 1, 17, 'Nnennaya', '', None);
INSERT INTO student VALUES (16, 'Ikechukwu', 'Chukwubuikem', 'ikechukwu.chukwubuikem', 'HrewNB4h', 'male', datetime.date(2024, 6, 18), '', '', '', 'Creche', '', '', '', datetime.datetime(2024, 6, 18, 18, 35, 56), 1, 18, '', '', None);
INSERT INTO student VALUES (17, 'Goodluck', 'Nwankpa', 'goodluck.nwankpa', 'hdX60ogx', 'male', datetime.date(2024, 6, 18), '', '', '', 'Pre-Nursery', '', '', '', datetime.datetime(2024, 6, 18, 18, 50, 18), 1, 19, '', '', None);
INSERT INTO student VALUES (18, 'Wisdom', 'Ndubueze ', 'wisdom.ndubueze', 'RKtUtizz', 'male', datetime.date(2024, 6, 18), '', '', '', 'Pre-Nursery', '', '', '', datetime.datetime(2024, 6, 18, 18, 51), 1, 20, 'Chijindu', '', None);
INSERT INTO student VALUES (19, 'Wisdom ', 'Chinyeaka', 'wisdom.chinyeaka', 'kftmiW9w', 'male', datetime.date(2024, 6, 18), '', '', '', 'Pre-Nursery', '', '', '', datetime.datetime(2024, 6, 18, 18, 51, 43), 1, 21, '', '', None);
INSERT INTO student VALUES (20, 'Oluchukwu', 'Chinedu', 'oluchukwu.chinedu', 'cS2gWINc', 'female', datetime.date(2024, 6, 18), '', '', '', 'Pre-Nursery', '', '', '', datetime.datetime(2024, 6, 18, 18, 52, 53), 1, 22, 'Jessica', '', None);
INSERT INTO student VALUES (21, 'Miracle ', 'Ezeribe', 'miracle.ezeribe', 'WFu5ByOR', 'female', datetime.date(2024, 6, 18), '', '', '', 'Pre-Nursery', '', '', '', datetime.datetime(2024, 6, 18, 18, 54, 43), 1, 23, 'Ifunaya', '', None);
INSERT INTO student VALUES (22, 'Ifunanya', 'Charles', 'ifunanya.charles', 'wqVxvtEF', 'female', datetime.date(2024, 6, 18), '', '', '', 'Pre-Nursery', '', '', '', datetime.datetime(2024, 6, 18, 18, 56, 2), 1, 24, 'Exceedinggrace', '', None);
INSERT INTO student VALUES (23, 'Elder ', 'udochukwu', 'elder.udochukwu', 'seL9qo8v', 'male', datetime.date(2024, 6, 18), '', '', '', 'Pre-Nursery', '', '', '', datetime.datetime(2024, 6, 18, 18, 56, 41), 1, 25, '', '', None);
INSERT INTO student VALUES (24, 'Special ', 'Chidi', 'special.chidi', 'mktDPBiM', 'male', datetime.date(2024, 6, 18), '', '', '', 'Pre-Nursery', '', '', '', datetime.datetime(2024, 6, 18, 18, 57, 9), 1, 26, '', '', None);
INSERT INTO student VALUES (25, 'Ijeoma', 'Moses', 'ijeoma.moses', '4oi0AVxX', 'female', datetime.date(2024, 6, 18), '', '', '', 'Pre-Nursery', '', '', '', datetime.datetime(2024, 6, 18, 18, 57, 48), 1, 27, '', '', None);
INSERT INTO student VALUES (26, 'Genevieve ', 'Joseph ', 'genevieve.joseph', 'PLZb3IuI', 'female', datetime.date(2024, 6, 18), '', '', '', 'Pre-Nursery', '', '', '', datetime.datetime(2024, 6, 18, 18, 58, 15), 1, 28, '', '', None);
INSERT INTO student VALUES (27, 'David ', 'Asoegwu', 'david.asoegwu', 'nCg4tmIg', 'male', datetime.date(2024, 6, 18), '', '', '', 'Pre-Nursery', '', '', '', datetime.datetime(2024, 6, 18, 18, 58, 42), 1, 29, '', '', None);
INSERT INTO student VALUES (28, 'DivineFavour', 'Israel ', 'divinefavour.israel', '4RYQpoea', 'female', datetime.date(2024, 6, 18), '', '', '', 'Nursery 1', '', '', '', datetime.datetime(2024, 6, 18, 19, 1, 52), 1, 30, '', '', None);
INSERT INTO student VALUES (29, 'Emmanuel ', 'Divine', 'emmanuel.divine', 'E4flNR4W', 'female', datetime.date(2024, 6, 18), '', '', '', 'Nursery 1', '', '', '', datetime.datetime(2024, 6, 18, 19, 2, 41), 1, 31, '', '', None);
INSERT INTO student VALUES (30, 'MaryJane', 'Joseph ', 'maryjane.joseph', 'pHukyH9M', 'female', datetime.date(2024, 6, 18), '', '', '', 'Nursery 1', '', '', '', datetime.datetime(2024, 6, 18, 19, 4, 21), 1, 32, '', '', None);
INSERT INTO student VALUES (31, 'Gift', 'John', 'gift.john', 'QSydm9V5', 'female', datetime.date(2024, 6, 18), '', '', '', 'Nursery 1', '', '', '', datetime.datetime(2024, 6, 18, 19, 4, 55), 1, 33, '', '', None);
INSERT INTO student VALUES (32, 'Excel', 'Maduabuchi', 'excel.maduabuchi', 'EQzAl2vJ', 'male', datetime.date(2024, 6, 18), '', '', '', 'Nursery 1', '', '', '', datetime.datetime(2024, 6, 18, 19, 12, 13), 1, 34, '', '', None);
INSERT INTO student VALUES (33, 'Prince', 'Tochukwu', 'prince.tochukwu', 'utvRurBI', 'male', datetime.date(2024, 6, 18), '', '', '', 'Nursery 1', '', '', '', datetime.datetime(2024, 6, 18, 19, 13, 18), 1, 35, '', '', None);
INSERT INTO student VALUES (34, 'Mary', 'John', 'mary.john', 'iQezoRvx', 'female', datetime.date(2024, 6, 18), '', '', '', 'Nursery 1', '', '', '', datetime.datetime(2024, 6, 18, 19, 14, 13), 1, 36, '', '', None);
INSERT INTO student VALUES (35, 'Great', 'Chinyeaka', 'great.chinyeaka', 'jyI4gmT1', 'male', datetime.date(2024, 6, 18), '', '', '', 'Nursery 2', '', '', '', datetime.datetime(2024, 6, 18, 19, 16, 23), 1, 37, 'Chibuikem', '', None);
INSERT INTO student VALUES (36, 'Adaeze ', 'Moses', 'adaeze.moses', 'Tg6sPrTO', 'female', datetime.date(2024, 6, 18), '', '', '', 'Nursery 2', '', '', '', datetime.datetime(2024, 6, 18, 19, 17, 23), 1, 38, 'Benedita', '', None);
INSERT INTO student VALUES (37, 'Amarachi', 'Chinedu', 'amarachi.chinedu', 'fR1FdbLX', 'female', datetime.date(2024, 6, 18), '', '', '', 'Nursery 2', '', '', '', datetime.datetime(2024, 6, 18, 19, 18, 57), 1, 39, 'Mary', '', None);
INSERT INTO student VALUES (38, 'Nneomannaya', 'Nwankpa', 'nneomannaya.nwankpa', 'shnu3ZTj', 'female', datetime.date(2024, 6, 18), '', '', '', 'Nursery 2', '', '', '', datetime.datetime(2024, 6, 18, 19, 20, 16), 1, 40, '', '', None);
INSERT INTO student VALUES (39, 'Ugoeze', 'Chidi', 'ugoeze.chidi', 'GUTrgk0y', 'female', datetime.date(2024, 6, 18), '', '', '', 'Nursery 2', '', '', '', datetime.datetime(2024, 6, 18, 19, 21, 3), 1, 41, 'Delight', '', None);
INSERT INTO student VALUES (40, 'Chikamso', 'Odimegwu', 'chikamso.odimegwu', 'jsePBrvn', 'male', datetime.date(2024, 6, 18), '', '', '', 'Nursery 2', '', '', '', datetime.datetime(2024, 6, 18, 19, 22, 43), 1, 42, 'Daniel', '', None);
INSERT INTO student VALUES (41, 'Divine', 'Ndubueze ', 'divine.ndubueze', '11yCv6L0', 'female', datetime.date(2024, 6, 18), '', '', '', 'Nursery 2', '', '', '', datetime.datetime(2024, 6, 18, 19, 23, 44), 1, 43, 'Chinaecherem', '', None);
INSERT INTO student VALUES (42, 'Future', 'Anosike', 'future.anosike', 'yo5676AI', 'male', datetime.date(2024, 6, 18), '', '', '', 'Nursery 3', '', '', '', datetime.datetime(2024, 6, 18, 22, 47, 30), 1, 44, 'Junior', '', None);
INSERT INTO student VALUES (43, 'Daniel ', 'Asoegwu', 'daniel.asoegwu', 'acQWAhZ8', 'male', datetime.date(2024, 6, 18), '', '', '', 'Nursery 3', '', '', '', datetime.datetime(2024, 6, 18, 22, 48, 2), 1, 45, '', '', None);
INSERT INTO student VALUES (44, 'Flourish ', 'Maduabuchi ', 'flourish.maduabuchi', 'MpIxURvj', 'female', datetime.date(2024, 6, 18), '', '', '', 'Nursery 3', '', '', '', datetime.datetime(2024, 6, 18, 22, 48, 53), 1, 46, 'Chimamanda', '', None);
INSERT INTO student VALUES (46, 'Nice', 'Freedom ', 'nice.freedom', 'PaAuhG5r', 'female', datetime.date(2024, 6, 18), '', '', '', 'Nursery 3', '', '', '', datetime.datetime(2024, 6, 18, 22, 50, 41), 1, 48, 'Chibuikem ', '', None);
INSERT INTO student VALUES (47, 'David', 'Chinenye ', 'david.chinenye', 'JrO0eKrr', 'male', datetime.date(2024, 6, 18), '', '', '', 'Nursery 3', '', '', '', datetime.datetime(2024, 6, 18, 22, 51, 55), 1, 49, 'Chimnadinda', '', None);
INSERT INTO student VALUES (48, 'Victory', 'Gideon', 'victory.gideon', 'HoKNuO0M', 'male', datetime.date(2024, 6, 18), '', '', '', 'Basic 1', '', '', '', datetime.datetime(2024, 6, 18, 22, 55, 27), 1, 50, 'Chibuikem', '', None);
INSERT INTO student VALUES (49, 'Callistus', 'Moses', 'callistus.moses', '1FPsg1yh', 'male', datetime.date(2024, 6, 18), '', '', '', 'Basic 1', '', '', '', datetime.datetime(2024, 6, 18, 22, 56, 13), 1, 51, 'Ekeoma', '', None);
INSERT INTO student VALUES (50, 'Samuel ', 'Ime', 'samuel.ime', 'pcABbphG', 'male', datetime.date(2024, 6, 18), '', '', '', 'Basic 1', '', '', '', datetime.datetime(2024, 6, 18, 22, 56, 40), 1, 52, 'Chidiebere', '', None);
INSERT INTO student VALUES (51, 'Winner', 'Chidi', 'winner.chidi', 'uSKYzatg', 'male', datetime.date(2024, 6, 18), '', '', '', 'Basic 1', '', '', '', datetime.datetime(2024, 6, 18, 22, 58, 8), 1, 53, '', '', None);
INSERT INTO student VALUES (52, 'Miracle ', 'Ndubueze ', 'miracle.ndubueze', 'NzUCYjy1', 'female', datetime.date(2024, 6, 18), '', '', '', 'Basic 1', '', '', '', datetime.datetime(2024, 6, 18, 22, 59, 1), 1, 54, 'Chizimdiri', '', None);
INSERT INTO student VALUES (53, 'Esther ', 'Nwankpa', 'esther.nwankpa', 'cNNufffU', 'female', datetime.date(2024, 6, 18), '', '', '', 'Basic 1', '', '', '', datetime.datetime(2024, 6, 18, 22, 59, 55), 1, 55, 'Chiwenmeri', '', None);
INSERT INTO student VALUES (54, 'Prince', 'Nwankpa', 'prince.nwankpa', 'jw93DayE', 'male', datetime.date(2024, 6, 19), '', '', '', 'Basic 1', '', '', '', datetime.datetime(2024, 6, 18, 23, 0, 35), 1, 56, 'Chizaram', '', None);
INSERT INTO student VALUES (55, 'Chinyere ', 'Emmanuel ', 'chinyere.emmanuel', 'suqz2114', 'female', datetime.date(2024, 6, 19), '', '', '', 'Basic 2', '', '', '', datetime.datetime(2024, 6, 18, 23, 1, 55), 1, 57, 'Precious', '', None);
INSERT INTO student VALUES (56, 'Marvellous ', 'Maduabuchi', 'marvellous.maduabuchi', 'Cw3RWk81', 'male', datetime.date(2024, 6, 19), '', '', '', 'Basic 2', '', '', '', datetime.datetime(2024, 6, 18, 23, 2, 37), 1, 58, 'Kamsi', '', None);
INSERT INTO student VALUES (57, 'Treasure ', 'Chidi', 'treasure.chidi', 'HYRwmXyI', 'female', datetime.date(2024, 6, 19), '', '', '', 'Basic 2', '', '', '', datetime.datetime(2024, 6, 18, 23, 3, 37), 1, 59, 'Chinaecherem ', '', None);
INSERT INTO student VALUES (58, 'Believe ', 'Kanu', 'believe.kanu', 'uJAeRBz4', 'male', datetime.date(2024, 6, 19), '', '', '', 'Basic 2', '', '', '', datetime.datetime(2024, 6, 18, 23, 4, 5), 1, 60, '', '', None);
INSERT INTO student VALUES (59, 'Amazing', 'Kanu', 'amazing.kanu', '8CL8fuW7', 'female', datetime.date(2024, 6, 19), '', '', '', 'Basic 2', '', '', '', datetime.datetime(2024, 6, 18, 23, 4, 58), 1, 61, 'Amarachi ', '', None);
INSERT INTO student VALUES (60, 'Chukwuemeka', 'Nwaobia', 'chukwuemeka.nwaobia', '7TkZb4mo', 'male', datetime.date(2024, 6, 19), '', '', '', 'Basic 2', '', '', '', datetime.datetime(2024, 6, 18, 23, 6, 7), 1, 62, 'Michael', '', None);
INSERT INTO student VALUES (61, 'Light', 'Chinyeaka', 'light.chinyeaka', 'PnuRAViN', 'male', datetime.date(2024, 6, 19), '', '', '', 'Basic 3', '', '', '', datetime.datetime(2024, 6, 18, 23, 7, 51), 1, 63, 'Chizaram ', '', None);
INSERT INTO student VALUES (62, 'Chisom', 'Chinedu', 'chisom.chinedu', 'ayNeAE5W', 'female', datetime.date(2024, 6, 19), '', '', '', 'Basic 3', '', '', '', datetime.datetime(2024, 6, 18, 23, 8, 45), 1, 64, 'Christabel', '', None);
INSERT INTO student VALUES (63, 'Esther ', 'Asoegwu ', 'esther.asoegwu', 'rSo13w3A', 'female', datetime.date(2024, 6, 19), '', '', '', 'Basic 3', '', '', '', datetime.datetime(2024, 6, 18, 23, 9, 26), 1, 65, 'Kosisochukwu', '', None);
INSERT INTO student VALUES (64, 'Somotochukwu', 'Eze', 'somotochukwu.eze', 'wA4nN5vg', 'male', datetime.date(2024, 6, 19), '', '', '', 'Basic 3', '', '', '', datetime.datetime(2024, 6, 18, 23, 10, 33), 1, 66, 'Destiny', '', None);
INSERT INTO student VALUES (65, 'Victoria ', 'Uwadiegwu ', 'victoria.uwadiegwu', 'f62Ura6v', 'female', datetime.date(2012, 2, 23), '07069941822', '291 yellow avenue', 'Trader ', 'Basic 2', 'Imo state ', 'Ahiara  Ahiazu Mbaise ', 'Christianity', datetime.datetime(2024, 6, 19, 9, 54, 23), 1, 67, 'Chizitere ', 'Uwadiegwu chinwe ', None);
INSERT INTO student VALUES (66, 'Prevailer ', 'Ekene', 'prevailer.ekene', '3ovxrJuX', 'female', datetime.date(2013, 5, 9), '08033463725', 'Alaukwu ', 'Pharmacy ', 'Basic 5', 'Imo state ', 'Ihioma orlu', 'Christianity', datetime.datetime(2024, 6, 19, 10, 7, 47), 1, 68, 'Chimnadindu', 'Ekene eboh', None);
INSERT INTO student VALUES (67, 'Beauty ', 'Ime ', 'beauty.ime', 'WV1j0y2A', 'female', datetime.date(2011, 11, 24), '', '', 'Police Man ', 'Basic 5', 'Akwa ibom ', '', 'Christianity', datetime.datetime(2024, 6, 19, 10, 17, 18), 1, 69, 'Chidinma ', 'Ime  Emmanuel ', None);
INSERT INTO student VALUES (68, 'Chidiebube', 'Nwaobia ', 'chidiebube.nwaobia', 'L59GK6Ok', 'male', datetime.date(2014, 2, 1), '07064672394', 'No 7 udezuka street ', 'Banker ', 'Basic 4', 'Imo state ', 'Abom mbaise', 'Christianity', datetime.datetime(2024, 6, 19, 10, 42, 12), 1, 70, 'Kingsley', 'Anosike Anulika Dominica', None);
INSERT INTO student VALUES (70, 'Oluchukwu ', 'Okoye ', 'oluchukwu.okoye', 'r1gFWmkc', 'female', datetime.date(2012, 12, 12), '07034477956', 'No 33 Agalaba ', 'Trade', 'Basic 4', 'Anambra ', 'Nneofia', 'Christianity', datetime.datetime(2024, 6, 19, 10, 51, 8), 1, 72, 'Esther ', 'Ndubueze ', None);
INSERT INTO student VALUES (71, 'Olivia', 'Gideon', 'olivia.gideon', '6qMJTV4c', 'female', datetime.date(2014, 6, 7), '', 'No  9 Umunwankwo street', 'Lecturing', 'Basic 4', 'Abia state ', 'Isiala Ngwa', 'Christianity', datetime.datetime(2024, 6, 19, 11, 6, 53), 1, 73, 'Somtochi ', 'Gideon Ngozi Sunday ', None);
INSERT INTO student VALUES (72, 'Prince Charles ', 'Asoegwu', 'charles.asoegwu', 'JF8w3xpv', 'male', datetime.date(2012, 8, 26), '08037597170', 'No 271 Aba Owerri Road', 'Navy Man ', 'Basic 4', 'Anambra ', 'Nnewi ', 'Christianity', datetime.datetime(2024, 6, 19, 11, 19, 51), 1, 74, 'Ugochukwu ', 'Asoegwu Jeremiah ', None);
INSERT INTO student VALUES (73, 'Delight', 'Ezeribe', 'delight.ezeribe', 'o55mUwwr', 'female', datetime.date(2012, 8, 6), '08038684734', 'No  4  MCC Road', 'Business woman ', 'Basic 4', 'Imo state ', 'Oru  East', 'Christianity', datetime.datetime(2024, 6, 19, 11, 34, 9), 1, 75, 'Ujunwa', 'Loveth Chidinma Ezeribe', None);
INSERT INTO student VALUES (74, 'Chimaobi', 'Uwadiegwu ', 'chimaobi.uwadiegwu', 'tW9kJgIs', 'male', datetime.date(2011, 3, 27), '+9715541617', '291 yellow avenue', 'Business Man', 'Basic 6', 'Imo state ', 'Ahiara  Ahiazu Mbaise ', 'Christianity', datetime.datetime(2024, 6, 19, 11, 47, 12), 1, 76, 'David', 'Uwadiegwu Chinemerem', 0);
INSERT INTO student VALUES (76, 'Ime ', 'Goodluck ', 'ime.goodluck', 'yjLJD6YA', 'male', datetime.date(2008, 12, 3), '07065511818', 'Osisioma Barack ', 'Police woman', 'JSS 1', 'Akwa Ibom ', '', 'Christianity', datetime.datetime(2024, 6, 19, 12, 9, 27), 1, 78, 'Chiweotito ', 'Lynda ime ', None);
INSERT INTO student VALUES (78, 'Precious ', 'Ekene', 'precious.ekene', 'HAja5XIO', 'female', datetime.date(2011, 8, 1), '08033463725', 'Elebele ', 'Pharmacy ', 'JSS 1', 'Imo state ', 'Ihioma orlu', 'Christianity', datetime.datetime(2024, 6, 25, 14, 12, 11), 1, 87, 'Adaeze', 'Ekene eboh', None);
INSERT INTO student VALUES (81, 'Destiny', 'Chiemela ', 'destiny.chiemela', 'nDnhTuxT', 'female', datetime.date(2012, 7, 30), '07031885006', 'Uratta', 'Painter ', 'Basic 5', 'Abia', 'Isiala Ngwa south', 'Christianity', datetime.datetime(2024, 6, 27, 11, 58, 39), 0, 91, 'Chigozirim', 'Mr Chiemela George ', None);
INSERT INTO student VALUES (82, 'Chijindu', 'Williams', 'chijindu.williams', 'MTuDu2R2', 'male', None, '', '', '', 'Nursery 3', '', '', '', datetime.datetime(2024, 6, 27, 12, 12, 2), 1, 92, '', '', None);
INSERT INTO student VALUES (83, 'Chimamanda', 'Nwaobia', 'chimamanda.nwaobia', 'CNSnhnA3', 'female', datetime.date(2017, 11, 10), '07064672394', 'No 7 udezuka street ', 'Banker ', 'Nursery 3', 'Imo state ', 'Abom mbaise', 'Christianity', datetime.datetime(2024, 6, 27, 12, 17, 19), 1, 93, 'Daniela', 'Anulika Anosike Dominica', None);
INSERT INTO student VALUES (84, 'Glory ', 'Uwadiegwu ', 'glory.uwadiegwu', 'Jti75keD', 'female', datetime.date(2007, 12, 29), 'O7o69941822', 'Yellow avenue ', 'Business woman ', 'JSS 1', 'Imo state ', 'Mbaise ', 'Christianity ', datetime.datetime(2024, 7, 2, 10, 37, 1), 1, 94, 'Ogochukwu ', 'Chinwe ', None);
INSERT INTO student VALUES (85, 'Success', 'Israel', 'success.israel', 'GujfiUGx', 'male', None, '', '', '', 'Basic 1', '', '', '', datetime.datetime(2024, 7, 15, 10, 32, 12), 1, 95, '', '', None);
INSERT INTO student VALUES (86, 'Sochima', 'Samuel ', 'sochima.samuel', 'vg4qGxzY', 'female', None, '', '', '', 'Creche', '', '', '', datetime.datetime(2024, 7, 26, 7, 33, 22), 1, 96, 'Kindness', '', None);
INSERT INTO student VALUES (87, 'Joshua', 'Iheanyi', 'joshua.iheanyi', 'eqMQlhmD', 'male', None, '', '', '', None, '', '', '', datetime.datetime(2024, 11, 10, 11, 19, 27), 0, 98, '', '', 0);
INSERT INTO student VALUES (88, 'Stanley', 'Alexander', 'stanley.alexander', 'RftVfcas', 'male', None, '', '', '', None, '', '', '', datetime.datetime(2024, 11, 10, 11, 22, 12), 0, 99, '', '', 0);
INSERT INTO student VALUES (89, 'Excel', 'Joseph', 'excel.joseph', 'LgE17Mqy', 'male', None, '', '', '', None, '', '', '', datetime.datetime(2024, 11, 12, 15, 42, 27), 0, 100, '', '', 0);
INSERT INTO student VALUES (90, 'Royalty', 'Anosike', 'royalty.anosike', '7sVnGKJC', 'male', None, '', '', '', None, '', '', '', datetime.datetime(2024, 11, 12, 15, 42, 54), 0, 101, '', '', 0);
INSERT INTO student VALUES (91, 'Wisdom', 'Augustine', 'wisdom.augustine', 'XpFZ1c3q', 'male', None, '', '', '', None, '', '', '', datetime.datetime(2024, 11, 12, 15, 43, 21), 0, 102, '', '', 0);
INSERT INTO student VALUES (92, 'Miracle', 'John', 'miracle.john', 'QaQ3dgar', 'male', None, '', '', '', None, '', '', '', datetime.datetime(2024, 11, 12, 15, 43, 54), 0, 103, '', '', 0);
INSERT INTO student VALUES (93, 'Onyinyechi', 'Augustine', 'onyinyechi.augustine', 'ajpwSmN2', 'female', None, '', '', '', None, '', '', '', datetime.datetime(2024, 11, 12, 15, 44, 38), 0, 104, '', '', 0);
INSERT INTO student VALUES (94, 'Emmanuel', 'Joseph', 'emmanuel.joseph', 'IxG9dLJl', 'male', None, '', '', '', None, '', '', '', datetime.datetime(2024, 11, 12, 15, 45, 9), 0, 105, '', '', 0);
INSERT INTO student VALUES (95, 'Chijindu', 'Sunday', 'chijindu.sunday', 'ye87ZdZr', 'female', None, '', '', '', None, '', '', '', datetime.datetime(2024, 11, 12, 15, 53, 10), 0, 106, '', '', 0);
INSERT INTO student VALUES (96, 'Great', 'Augustine', 'great.augustine', 'FzCi6XNL', 'male', None, '', '', '', None, '', '', '', datetime.datetime(2024, 11, 12, 15, 54, 13), 0, 107, '', '', 0);
INSERT INTO student VALUES (97, 'David', 'Onyenwe', 'david.onyenwe', '1Pauc491', 'male', None, '', '', '', None, '', '', '', datetime.datetime(2024, 11, 12, 15, 56, 8), 0, 108, '', '', 0);
INSERT INTO student VALUES (98, 'Joyful', 'Praise', 'joyful.praise', 'LOgrhKYV', 'female', None, '', '', '', None, '', '', '', datetime.datetime(2024, 11, 12, 15, 56, 36), 0, 109, '', '', 0);
INSERT INTO student VALUES (99, 'Munachimso', 'David', 'munachimso.david', 'sAbvRIuq', 'female', None, '', '', '', None, '', '', '', datetime.datetime(2024, 11, 12, 15, 58, 40), 0, 110, '', '', 0);

