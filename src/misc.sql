-- mrbs.mrbs_facility definition

use mrbs;

drop table `mrbs_facility`;
CREATE TABLE `mrbs_facility` (
    `id` int(11) NOT NULL AUTO_INCREMENT,
    `room_id` int(11) NOT NULL,
    `area_id` int(11) NOT NULL,
    `facility_type_id` int(11) NOT NULL,
    `notes` varchar(300) DEFAULT NULL,
    PRIMARY KEY (`id`),
    UNIQUE KEY `room_id_facility_type` (`room_id`,`facility_type_id`)
) ENGINE=MyISAM AUTO_INCREMENT=1 DEFAULT CHARSET=utf8;

drop table `mrbs_facility_type`;
CREATE TABLE `mrbs_facility_type` (
    `id` int(11) NOT NULL AUTO_INCREMENT,
    `type` varchar(50) NOT NULL,
    `area_id` int(11) NOT NULL,
    PRIMARY KEY (`id`)
) ENGINE=MyISAM AUTO_INCREMENT=1 DEFAULT CHARSET=utf8;

drop table `mrbs_application`;
CREATE TABLE `mrbs_application` (
    `id` varchar(256) NOT NULL,
    `register_time` DATETIME NOT NULL, -- Time of application
    `event_site` varchar(256) NOT NULL,
    `size` int NULL, -- Meeting size; the count filed in the application form
    `unit1` varchar(256) NULL,
    `unit2` varchar(256) NULL,
    `unit_title` varchar(256) NULL, -- unitTitle in the form
    `subject` varchar(256) NULL,
    `content` varchar(1024) NULL,
    `note` varchar(1024) NULL,
    `supplement1` varchar(1024) NULL,
    `in_charge` varchar(1024) NULL,
    `phone_no` varchar(100) NULL,

    `create_time` DATETIME NOT NULL, -- Time of record creation

    PRIMARY KEY (`application_key`)
) ENGINE=MyISAM AUTO_INCREMENT=1 DEFAULT CHARSET=utf8;

drop table `mrbs_application_entry`;
CREATE TABLE `mrbs_application_entry` (
    `application_id` varchar(256) NOT NULL,
    `entry_no` tinyint NOT NULL, -- the entry position in the file; 1-based, up to 5
    `event_date` DATE NOT NULL,
    `start_time` DATETIME NOT NULL,
    `stop_time` DATETIME NOT NULL,

    `update_time` DATETIME NOT NULL, -- Time of last record update

    `status` enum('pending', 'too_late', 'success', 'failed') DEFAULT 'pending',
    PRIMARY KEY(`application_id`, `entry`),
    FOREIGN KEY (`application_id`) REFERENCES `mrbs_application`(`id`)
) ENGINE=MyISAM AUTO_INCREMENT=1 DEFAULT CHARSET=utf8;



