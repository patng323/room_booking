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


