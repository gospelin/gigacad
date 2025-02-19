-- Table structure for `subject`
CREATE TABLE `subject` (
  `id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(100) NOT NULL,
  `section` varchar(20) NOT NULL,
  `deactivated` tinyint(1) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `_name_section_uc` (`name`,`section`)
) ENGINE=InnoDB AUTO_INCREMENT=125 DEFAULT CHARSET=utf8mb3;

-- Data for `subject`
INSERT INTO subject VALUES (40, 'Mathematics', 'Secondary', 0);
INSERT INTO subject VALUES (41, 'Number Work/Quantitative Reasoning', 'Nursery', 0);
INSERT INTO subject VALUES (43, 'English Language', 'Secondary', 0);
INSERT INTO subject VALUES (44, 'Letter Work/Verbal Reasoning', 'Nursery', 0);
INSERT INTO subject VALUES (46, 'Basic Science', 'Secondary', 0);
INSERT INTO subject VALUES (48, 'Basic Technology', 'Secondary', 0);
INSERT INTO subject VALUES (49, 'Business Studies', 'Secondary', 0);
INSERT INTO subject VALUES (54, 'History', 'Secondary', 0);
INSERT INTO subject VALUES (58, 'Agricultural Science', 'Secondary', 0);
INSERT INTO subject VALUES (59, 'Oral reading ', 'Nursery', 1);
INSERT INTO subject VALUES (61, 'Poetry', 'Nursery', 1);
INSERT INTO subject VALUES (62, 'Verbal Reasoning', 'Nursery', 1);
INSERT INTO subject VALUES (63, 'Igbo Language', 'Nursery', 0);
INSERT INTO subject VALUES (64, 'Quantitative Reasoning ', 'Nursery', 1);
INSERT INTO subject VALUES (66, 'Civic Education', 'Nursery', 0);
INSERT INTO subject VALUES (67, 'Christian Religious Studies', 'Nursery', 0);
INSERT INTO subject VALUES (68, 'Security Education', 'Nursery', 0);
INSERT INTO subject VALUES (71, 'Computer Studies', 'Nursery', 0);
INSERT INTO subject VALUES (72, 'Vocational Studies', 'Nursery', 0);
INSERT INTO subject VALUES (73, 'Agricultural Science', 'Nursery', 0);
INSERT INTO subject VALUES (74, 'Home Economics', 'Nursery', 0);
INSERT INTO subject VALUES (75, 'Creative and Cultural Arts', 'Nursery', 0);
INSERT INTO subject VALUES (76, 'Calligraphy ', 'Nursery', 0);
INSERT INTO subject VALUES (77, 'General Studies', 'Nursery', 1);
INSERT INTO subject VALUES (79, 'Information Technology', 'Secondary', 0);
INSERT INTO subject VALUES (81, 'Physical and Health Education', 'Secondary', 0);
INSERT INTO subject VALUES (83, 'Civic Education', 'Secondary', 0);
INSERT INTO subject VALUES (85, 'Social Studies', 'Secondary', 0);
INSERT INTO subject VALUES (87, 'Christian Religious Studies', 'Secondary', 0);
INSERT INTO subject VALUES (89, 'Security Education', 'Secondary', 0);
INSERT INTO subject VALUES (91, 'Home Economics', 'Secondary', 0);
INSERT INTO subject VALUES (94, 'Igbo Language', 'Secondary', 0);
INSERT INTO subject VALUES (95, 'Mathematics', 'Basic', 0);
INSERT INTO subject VALUES (96, 'Information Technology', 'Basic', 0);
INSERT INTO subject VALUES (97, 'Quantitative Reasoning ', 'Basic', 0);
INSERT INTO subject VALUES (98, 'Basic Science', 'Basic', 0);
INSERT INTO subject VALUES (99, 'Basic Technology', 'Basic', 0);
INSERT INTO subject VALUES (100, 'Agricultural Science', 'Basic', 0);
INSERT INTO subject VALUES (101, 'Home Economics', 'Basic', 0);
INSERT INTO subject VALUES (102, 'Social Studies', 'Basic', 0);
INSERT INTO subject VALUES (103, 'Security Education', 'Basic', 0);
INSERT INTO subject VALUES (104, 'Civic Education', 'Basic', 0);
INSERT INTO subject VALUES (105, 'Christian Religious Studies', 'Basic', 0);
INSERT INTO subject VALUES (106, 'Creative and Cultural Arts', 'Basic', 0);
INSERT INTO subject VALUES (107, 'Igbo Language', 'Basic', 0);
INSERT INTO subject VALUES (108, 'History', 'Basic', 0);
INSERT INTO subject VALUES (109, 'English Language', 'Basic', 0);
INSERT INTO subject VALUES (110, 'Physical and Health Education', 'Basic', 0);
INSERT INTO subject VALUES (111, 'Verbal Reasoning ', 'Basic', 0);
INSERT INTO subject VALUES (112, 'Oral English', 'Basic', 1);
INSERT INTO subject VALUES (113, 'Reading / Dictation', 'Basic', 1);
INSERT INTO subject VALUES (114, 'Poetry', 'Basic', 1);
INSERT INTO subject VALUES (115, 'Handwriting / Calligraphy', 'Basic', 0);
INSERT INTO subject VALUES (116, 'General Studies ', 'Basic', 1);
INSERT INTO subject VALUES (117, 'Social Habit', 'Nursery', 0);
INSERT INTO subject VALUES (118, 'Nursery Science', 'Nursery', 0);
INSERT INTO subject VALUES (119, 'Physical and Health Education', 'Nursery', 0);
INSERT INTO subject VALUES (120, 'Speech work', 'Nursery', 1);

