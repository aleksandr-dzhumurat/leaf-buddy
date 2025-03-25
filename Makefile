CURRENT_DIR = $(shell pwd)
NETWORK_NAME = service_network
 
include .env
export


prepare-dirs:
	mkdir -p ${CURRENT_DIR}/data || true & \
	mkdir -p ${CURRENT_DIR}/data/pipelines-data || true

build-network:
	docker network create backtier -d bridge || true

run-etl:
	ROOT_DATA_DIR=${CURRENT_DIR}/data python src/prepare_data.py

run-leafly-scraper:
	CONFIG_DIR=${CURRENT_DIR} \
	ROOT_DATA_DIR=${CURRENT_DIR}/data python src/${SCENARIO}.py

run-dialog:
	ROOT_DATA_DIR=${CURRENT_DIR}/data \
	CONFIG_DIR=${CURRENT_DIR} \
	python src/dialog_agent.py

run-jupyter:
	PYTHONPATH=${CURRENT_DIR}/src \
	ROOT_DATA_DIR=${CURRENT_DIR}/data jupyter notebook jupyter_notebooks --ip 0.0.0.0 --port 8887 \
	--NotebookApp.token='' --NotebookApp.password='' --allow-root --no-browser

run-tg-local:
	PYTHONPATH=${CURRENT_DIR}/src \
	CONFIG_DIR=${CURRENT_DIR} \
	ROOT_DATA_DIR=${CURRENT_DIR}/data python src/telagram_app.py

build-api:
	docker build -f services/api/Dockerfile -t adzhumurat/api:latest .

run-api:
	docker run --rm -d \
		--env-file ${CURRENT_DIR}/.env  \
	    -v "${CURRENT_DIR}/src:/srv/src" \
		-p 8000:8000 \
		-e RUN_ENV=docker \
	    -v "${CURRENT_DIR}/data:/srv/data" \
		--network backtier \
	    --name api_container \
		adzhumurat/api:latest

run-tg:
	docker run --rm \
		--env-file ${CURRENT_DIR}/.env  \
	    -v "${CURRENT_DIR}/src:/srv/src" \
		-e RUN_ENV=docker \
	    -v "${CURRENT_DIR}/data:/srv/data" \
		--network backtier \
	    --name tg_container \
		adzhumurat/api:latest \
		"python" src/telagram_app.py

run: build-network run-tg run-api