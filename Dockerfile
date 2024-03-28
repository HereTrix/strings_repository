FROM python:3.11-alpine AS base
WORKDIR /app
EXPOSE 8080

# ENV APP_SECRET_KEY
# ENV ALLOWED_HOSTS
# ENV DB_ENGINE
# ENV DB_NAME
# ENV DB_HOST
# ENV DB_PORT
# ENV DB_USER
# ENV DB_PASSWORD
# ENV DJANGO_SUPERUSER_USERNAME
# ENV DJANGO_SUPERUSER_EMAIL
# ENV DJANGO_SUPERUSER_PASSWORD

FROM node:lts-alpine AS fronend
WORKDIR /app/webui
COPY ./webui/package*.json /app/webui
RUN npm ci
COPY ./webui/ /app/webui
RUN npm run build

FROM base AS backend
COPY requirements.txt /app/
RUN pip install psycopg2-binary
RUN pip install --no-cache-dir -r requirements.txt
COPY . /app/
COPY --from=fronend /app/webui/ /app/webui/

RUN chown -R 1000:1000 /app
USER 1000:1000

CMD python manage.py makemigrations api \
&& python manage.py migrate \
&& (python manage.py createsuperuser --noinput || true) \
&& python manage.py runserver 0.0.0.0:8080
