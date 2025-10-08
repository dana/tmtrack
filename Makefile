.PHONY: all push

all:
	tox && docker build -t dana/tmtrack:latest .

push:
	docker push dana/tmtrack:latest

backup:
	ssh realms 'cd /home/dana/tmtrack && /usr/bin/python3 ./backup.py localhost:27017 tmtrack_db' && scp realms:/home/dana/tmtrack/tmtrack_backup.json /home/dana/notes/
