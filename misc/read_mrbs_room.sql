SELECT 
id,area_id,room_zone,room_group,
CONVERT(BINARY CONVERT(room_name USING latin1) USING utf8) as room_name,
CONVERT(BINARY CONVERT(description USING latin1) USING utf8) as description,
CONVERT(BINARY CONVERT(equipment USING latin1) USING utf8) as equipment,
capacity,room_admin_email
FROM mrbs.mrbs_room
where id in (145, 216);