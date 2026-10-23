.PHONY: install build run dev test
install:      ## установить зависимости
	cd backend && pip install -r requirements.txt
	cd frontend && npm install
build:        ## собрать фронтенд в frontend/dist
	cd frontend && npm run build
run: build    ## запустить всё на http://localhost:8000
	cd backend && python run.py
dev:          ## режим разработки: бэкенд :8000 и интерфейс с пересборкой :5173
	cd backend && python run.py & cd frontend && npm run dev
test:         ## автотесты бэкенда
	cd backend && python -m unittest discover -s tests -t .
