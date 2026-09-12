import os

from app import create_app
from config import config

# gunicorn serves `run:app`, so the config has to be chosen here rather than by
# the Flask CLI. Importing the app package loads .env first, which is where
# FLASK_ENV comes from. An unrecognised value falls back to the default so a
# typo in the environment cannot stop the app from booting.
config_name = os.environ.get('FLASK_ENV', 'default')
if config_name not in config:
    config_name = 'default'

app = create_app(config_name)

if __name__ == '__main__':
    app.run()
