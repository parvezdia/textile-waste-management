python manage.py truncate_db --no-input

python manage.py generate_dummy_data --factories 3 --designers 5 --buyers 8 --waste-items 10 --designs 10

python manage.py generate_analytics_data

python manage.py generate_dummy_orders --count 30

python manage.py generate_analytics_data (http://localhost:8000/accounts/admin/analytics/debug/)









python manage.py truncate_db --no-input

python manage.py generate_dummy_data --factories 3 --designers 5 --buyers 8 --waste-items 10 --designs 10


python manage.py generate_analytics_data

1. docker run --name redis-server -p 6379:6379 -d redis

2. docker start redis-server

3. daphne config.asgi:application


For locust performance testing, you can use the following commands to run the tests in different modes. Make sure you have Locust installed and your application running.

1. python manage.py truncate_db --no-input

2. cd performance_tests

3. python run_locust_with_data.py

4. python manage.py createsuperuser


if required use locust in the performance_tests folder

