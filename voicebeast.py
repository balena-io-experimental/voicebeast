import flickr_api
from resin import Resin
import resin_config
import logging
from random import randint
from flask import Flask, render_template
from flask_ask import Ask, statement, question, session
import multiprocessing
import time

## Flickr setup
a = flickr_api.auth.AuthHandler() #creates the AuthHandler object

## resin.io setup
resin = Resin()
resin.auth.login_with_token(resin_config.TOKEN)
resin_app = resin.models.application.get_by_id(resin_config.APP_ID)

## Alexa setup
app = Flask(__name__)
ask = Ask(app, "/")
logging.getLogger("flask_ask").setLevel(logging.DEBUG)

def create_flickr_url(photo, size_suffix='z', extension='jpg'):
    """
    https://farm{farm-id}.staticflickr.com/{server-id}/{id}_{o-secret}_o.(jpg|gif|png)
    """
    if extension not in ['jpg', 'gif', 'png']:
        extension = 'jpg'

    # Cannot display original, 'o', yet, because API does not return 'originalsecret'
    suffixes = ['s', 'q', 't', 'm', 'n', '-', 'z', 'c', 'b', 'h', 'k']
    if size_suffix not in suffixes:
        size_suffix = 'z'

    return "https://farm{farm}.staticflickr.com/{server}/{id}_{secret}_{suffix}.{extension}".format(
        farm=photo.farm,
        server=photo.server,
        id=photo.id,
        secret=photo.secret,
        suffix=size_suffix,
        extension=extension,
        )

def flickr_search(text):
    """ Search images on Flickr for a given text, and update devices with the images found
    """
    resin_devices = resin.models.device.get_all_by_application(resin_app['app_name'])
    num_devices = len(resin_devices)
    w = flickr_api.Walker(flickr_api.Photo.search, text=text, sort='relevance')
    i = 0
    for photo in w:
        url = create_flickr_url(photo)
        set_or_update_env_var(resin_devices[i], 'URL', url)
        i += 1
        if i >= num_devices:
            break

def set_or_update_env_var(device, name, value):
    """ Set or update environment variables for a given device on resin.io
    """
    print("Updating env var")
    envs = resin.models.environment_variables.device.get_all(device['uuid'])
    found = False
    for env in envs:
        if env['env_var_name'] == name:
            found = True
            resin.models.environment_variables.device.update(env['id'], value)
            break
    if not found:
        resin.models.environment_variables.device.create(device['uuid'], name, value)

@ask.intent("SearchIntent")
def search(theme):
    text = render_template('image', theme=theme)
    d = multiprocessing.Process(target=flickr_search, kwargs={'text': theme})
    d.daemon = True
    d.start()
    return statement(text)


if __name__ == '__main__':
    # flickr_search("Tower bridge")
    app.run(debug=True)
    # print("sleeping")
    # time.sleep(20)
