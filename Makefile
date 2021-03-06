.env/bin/activate:
	virtualenv -p python .env
	. .env/bin/activate && pip install -U setuptools pip && pip install -r requirements.txt

develop: .env/bin/activate
	git submodule update --init
	cd messages && ./generate.sh
	cd orwell && [ -e messages ] || ln -s ../messages/orwell/messages .

test: .env/bin/activate
	. .env/bin/activate && nosetests

coverage: .env/bin/activate
	. .env/bin/activate && nosetests --with-coverage --cover-package=orwell --cover-tests

clean: .env/bin/activate
	. .env/bin/activate && coverage erase

start: .env/bin/activate
	. .env/bin/activate && python orwell/client/main.py -v
