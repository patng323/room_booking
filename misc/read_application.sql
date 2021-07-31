select
id,
register_time,
CONVERT(BINARY CONVERT(event_site USING latin1) USING utf8) as event_site,
size,
CONVERT(BINARY CONVERT(unit1 USING latin1) USING utf8) as unit1,
CONVERT(BINARY CONVERT(unit2 USING latin1) USING utf8) as unit2,
CONVERT(BINARY CONVERT(unit_title USING latin1) USING utf8) as unit_title,
CONVERT(BINARY CONVERT(subject USING latin1) USING utf8) as subject,
CONVERT(BINARY CONVERT(content USING latin1) USING utf8) as content,
CONVERT(BINARY CONVERT(note USING latin1) USING utf8) as note,
CONVERT(BINARY CONVERT(supplement1 USING latin1) USING utf8) as supplement1,
CONVERT(BINARY CONVERT(in_charge USING latin1) USING utf8) as in_charge,
phone_no,
create_time,
update_time
from mrbs_application;

select * 
from mrbs_application_entry;


