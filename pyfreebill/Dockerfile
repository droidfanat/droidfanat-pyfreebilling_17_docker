FROM php:7.1-apache
COPY php.ini /usr/local/etc/php/
COPY certbot-auto /var/www/

RUN apt-get update \
  && apt-get install -y gnupg openssl git\
  && apt-get install -y python python-pip virtualenv libpq-dev python-dev swig libapache2-mod-wsgi \
  && a2enmod rewrite \
  && a2enmod ssl 

WORKDIR /usr/local/venv

COPY ./python /usr/local/venv/pyfreebilling
RUN pip install --upgrade -r pyfreebilling/requirements/requirements.txt
WORKDIR /usr/local/venv/pyfreebilling
RUN yes yes | python manage.py collectstatic

#RUN virtualenv venv --no-site-packages
  # /var/www/certbot-auto certonly --webroot -w /var/www/html/public -d crm.1stlfs.com -d sip.crm.1stlfs.com 

   
