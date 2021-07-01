SELECT me.id, 
from_unixtime(start_time, '%Y-%m-%d %H:%i:%s') as start_time, 
from_unixtime(end_time , '%Y-%m-%d %H:%i:%s') as end_time, 
entry_type, repeat_id, 
room_id, 
CONVERT(BINARY CONVERT(mr.room_name USING latin1) USING utf8) as room_name, 
`timestamp`, 
create_by, 
CONVERT(BINARY CONVERT(name USING latin1) USING utf8) as name, 
`type`, 
CONVERT(BINARY CONVERT(me.description USING latin1) USING utf8) as description
FROM mrbs.mrbs_entry me join mrbs.mrbs_room mr on room_id = mr.id
where me.id in (1715373, 1630460);
 
#and start_time >= UNIX_TIMESTAMP('2020-01-11') and 
#end_time < UNIX_TIMESTAMP('2020-01-12') ;
