FROM python:3.14.7-alpine3.23
WORKDIR /framework
COPY . .
RUN python -m pip install --upgrade pip && pip install -r requirements.txt
ENTRYPOINT ["pytest", "--alluredir=/framework/allure-results"]
