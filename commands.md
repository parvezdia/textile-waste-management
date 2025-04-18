python manage.py truncate_db --no-input

python manage.py generate_dummy_data --factories 3 --designers 5 --buyers 8 --waste-items 10 --designs 10

python manage.py generate_analytics_data

python manage.py generate_dummy_orders --count 30

python manage.py generate_analytics_data (http://localhost:8000/accounts/admin/analytics/debug/)









python manage.py truncate_db --no-input

python manage.py generate_dummy_data --factories 3 --designers 5 --buyers 8 --waste-items 10 --designs 10


python manage.py generate_analytics_data

docker run --name redis-server -p 6379:6379 -d redis


daphne config.asgi:application
