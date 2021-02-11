use mrbs;

insert into mrbs_facility_type (type, area_id) values (convert(_latin1"鋼琴" using utf8), 1);
insert into mrbs_facility_type (type, area_id) values (convert(_latin1"電子琴" using utf8), 1);
insert into mrbs_facility_type (type, area_id) values (convert(_latin1"桌上電腦" using utf8), 1);
insert into mrbs_facility_type (type, area_id) values (convert(_latin1"觸屏式電腦" using utf8), 1);
insert into mrbs_facility_type (type, area_id) values (convert(_latin1"LG TV" using utf8), 1);
insert into mrbs_facility_type (type, area_id) values (convert(_latin1"DVD" using utf8), 1);
insert into mrbs_facility_type (type, area_id) values (convert(_latin1"投影屏幕" using utf8), 1);
insert into mrbs_facility_type (type, area_id) values (convert(_latin1"活動白板" using utf8), 1);

insert into mrbs_facility_type (type, area_id) values (convert(_latin1"譜架" using utf8), 1);
insert into mrbs_facility_type (type, area_id) values (convert(_latin1"兒童摺檯" using utf8), 1);
insert into mrbs_facility_type (type, area_id) values (convert(_latin1"方檯" using utf8), 1);
insert into mrbs_facility_type (type, area_id) values (convert(_latin1"長檯" using utf8), 1);
insert into mrbs_facility_type (type, area_id) values (convert(_latin1"半檯" using utf8), 1);
insert into mrbs_facility_type (type, area_id) values (convert(_latin1"大字版聖經" using utf8), 1);

insert into mrbs_facility_type (type, area_id) values (convert(_latin1"高映機" using utf8), 2);
insert into mrbs_facility_type (type, area_id) values (convert(_latin1"鋼琴" using utf8), 2);
insert into mrbs_facility_type (type, area_id) values (convert(_latin1"LCD 投影機" using utf8), 2);
insert into mrbs_facility_type (type, area_id) values (convert(_latin1"電視" using utf8), 2);

select id, CONVERT(BINARY CONVERT(type USING latin1) USING utf8) as type, area_id from mrbs_facility_type;
