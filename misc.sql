-- mrbs.mrbs_facility definition

use mrbs;

drop table `mrbs_facility`;
CREATE TABLE `mrbs_facility` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `room_id` int(11) NOT NULL,
  `facility_type_id` int(11) NOT NULL,
  `notes` varchar(300) DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `room_id_facility_type` (`room_id`,`facility_type_id`)
) ENGINE=MyISAM AUTO_INCREMENT=1 DEFAULT CHARSET=utf8;

drop table `mrbs_facility_type`;
CREATE TABLE `mrbs_facility_type` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `type` varchar(50) NOT NULL,
  `area` int(11) NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=MyISAM AUTO_INCREMENT=1 DEFAULT CHARSET=utf8;

insert into mrbs_facility_type (type, area) values (convert(_latin1"鋼琴" using utf8), 1);
insert into mrbs_facility_type (type, area) values (convert(_latin1"電子琴" using utf8), 1);
insert into mrbs_facility_type (type, area) values (convert(_latin1"桌上電腦" using utf8), 1);
insert into mrbs_facility_type (type, area) values (convert(_latin1"觸屏式電腦" using utf8), 1);
insert into mrbs_facility_type (type, area) values (convert(_latin1"LG TV" using utf8), 1);
insert into mrbs_facility_type (type, area) values (convert(_latin1"DVD" using utf8), 1);
insert into mrbs_facility_type (type, area) values (convert(_latin1"投影屏幕" using utf8), 1);
insert into mrbs_facility_type (type, area) values (convert(_latin1"活動白板" using utf8), 1);
insert into mrbs_facility_type (type, area) values (convert(_latin1"譜架" using utf8), 1);
insert into mrbs_facility_type (type, area) values (convert(_latin1"兒童摺檯" using utf8), 1);
insert into mrbs_facility_type (type, area) values (convert(_latin1"方檯" using utf8), 1);
insert into mrbs_facility_type (type, area) values (convert(_latin1"長檯" using utf8), 1);
insert into mrbs_facility_type (type, area) values (convert(_latin1"半檯" using utf8), 1);
insert into mrbs_facility_type (type, area) values (convert(_latin1"大字版聖經" using utf8), 1);

insert into mrbs_facility_type (type, area) values (convert(_latin1"高映機" using utf8), 2);
insert into mrbs_facility_type (type, area) values (convert(_latin1"鋼琴" using utf8), 2);
insert into mrbs_facility_type (type, area) values (convert(_latin1"LCD 投影機" using utf8), 2);
insert into mrbs_facility_type (type, area) values (convert(_latin1"電視" using utf8), 2);



select id, CONVERT(BINARY CONVERT(type USING latin1) USING utf8) as type, area from mrbs_facility_type;