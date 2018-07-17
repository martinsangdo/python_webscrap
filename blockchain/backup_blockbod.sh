#author: Martin SangDo, password in ~/db_backup/blockbod.cnf
NOW=$(date +"%Y%m%d")
FILENAME="blockbod_$NOW.sql.zip"
mysqldump --defaults-file=/var/www/vhosts/blockbod.com/db_backup/blockbod.cnf -u dbblockbod -h localhost --databases blockbod_db | gzip > /var/www/vhosts/blockbod.com/db_backup/$FILENAME
