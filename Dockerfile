FROM python:3-alpine

RUN pip install -U pip

ADD FindCars.py .

ADD emailer.py .

ADD requirements.txt .

RUN pip install -r requirements.txt --user

CMD [ "python", "FindCars.py" ]
