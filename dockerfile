FROM python:3.12

RUN mkdir /app
WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1


RUN pip install -i https://mirror-pypi.runflare.com/simple --upgrade pip

COPY requirements.txt  /app/
RUN pip install -i https://mirror-pypi.runflare.com/simple -r requirements.txt

COPY . .

EXPOSE 8000

WORKDIR /app/core

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]