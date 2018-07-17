#author: Martin SangDo, password in ~/db_backup/blockbod.cnf
NOW=$(date +"%Y%m%d")
FILENAME="blockbod_$NOW.sql.zip"
mysqldump --defaults-file=~/db_backup/blockbod.cnf -u blockbod_user -h localhost --databases blockbod_db | gzip > ~/db_backup/$FILENAME
