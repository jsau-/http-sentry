#!/usr/bin/python3
"""http-sentry.

A script for executing a series of web requests, and asserting an expected
response. See 'config_schema.json' for a list of available configuration
parameters.

Usage:
  http_sentry.py <config_file_path>
  http_sentry.py (-h | --help)
  http_sentry.py --version

Options:
  -h --help     Show this screen.
  --version     Show version.

"""

from docopt import docopt
from jsonschema import validate
import logging
import json
import re
import requests
import time

DEFAULT_REQUEST_HEADERS = {}
DEFAULT_REQUEST_TIMEOUT = 10
VERSION = '0.0.1'

def read_config_schema():
  with open('./config_schema.json', 'r') as config_schema_file:
    config_schema = json.load(config_schema_file)
    return config_schema

def read_config_file(config_file_path):
  with open(config_file_path, 'r') as config_file:
    config = json.load(config_file)
    return config

def handle_check_failure(check, reason, webhook, meta, response):
  logging.error(
    'Check \'%s\' failed. %s',
    check['name'],
    reason
  )

  if response:
    response_text = response.text

  if webhook:
    try:
      requests.post(
        webhook['url'],
        timeout = webhook.get('timeout', DEFAULT_REQUEST_TIMEOUT),
        headers = webhook.get('headers', DEFAULT_REQUEST_HEADERS),
        json = {
          'check': check,
          'meta': meta,
          'passed': False,
          'reason': reason,
          'response': {
            'text': response_text
          },
          'epoch': time.time()
        }
      )
    except Exception as e:
      logging.error(
        'Failed to invoke success webhook for check \'%s\': %s',
        check['name'],
        str(e)
      )

def handle_check_success(check, webhook, meta, response):
  logging.debug('Check \'%s\' completed successfully', check['name'])

  if response:
    response_text = response.text

  if webhook:
    try:
      requests.post(
        webhook['url'],
        timeout = webhook.get('timeout', DEFAULT_REQUEST_TIMEOUT),
        headers = webhook.get('headers', DEFAULT_REQUEST_HEADERS),
        json = {
          'check': check,
          'meta': meta,
          'passed': True,
          'response': {
            'text': response_text
          },
          'epoch': time.time()
        }
      )
    except Exception as e:
      logging.error(
        'Failed to invoke success webhook for check \'%s\': %s',
        check['name'],
        str(e)
      )

def run_check(check, webhook_success, webhook_failure, meta):
  request_method = getattr(requests, check['request'].get('method', 'get'))

  try:
    response = request_method(
      check['request']['url'],
      timeout = check['request'].get('timeout', DEFAULT_REQUEST_TIMEOUT),
      headers = check['request'].get('headers', DEFAULT_REQUEST_HEADERS),
      data = check['request'].get('body', {})
    )
  except requests.exceptions.RequestException as e:
    handle_check_failure(check, str(e), webhook_failure, meta, None)
    return

  expected_status_code = check['expect'].get('status')

  if expected_status_code and expected_status_code != response.status_code:
    handle_check_failure(
      check,
      'Expected status code %d, but received %d' % (expected_status_code, response.status_code),
      webhook_failure,
      meta,
      response
    )

    return

  expected_text = check['expect'].get('text')

  if expected_text is not None and expected_text != response.text:
    handle_check_failure(
      check,
      'Expected text \'%s\', but received \'%s\'' % (expected_text, response.text),
      webhook_failure,
      meta,
      response
    )

    return

  expected_json = check['expect'].get('json')

  if expected_json is not None:
    try:
      response_json = response.json()
    except:
      handle_check_failure(
        check,
        'Failed to parse response as JSON',
        webhook_failure,
        meta,
        response
      )

      return

    if response_json != expected_json:
      handle_check_failure(
        check,
        'Expected JSON \'%s\', but received \'%s\'' % (expected_json, response_json),
        webhook_failure,
        meta,
        response
      )

      return

  expected_regex = check['expect'].get('regex')

  if expected_regex is not None and not re.compile(expected_regex).match(response.text):
    handle_check_failure(
      check,
      'Expected content \'%s\' to match regex \'%s\', but did not.' % (response.text, expected_regex),
      webhook_failure,
      meta,
      response
    )

    return

  handle_check_success(check, webhook_success, meta, response)

def main():
  arguments = docopt(__doc__, version=VERSION)

  config = read_config_file(arguments.get('<config_file_path>'))
  config_schema = read_config_schema()

  logfile_location = config.get('logfile')

  log_prefix = config.get('name', 'http-sentry')

  logging.basicConfig(
    filename = logfile_location,
    filemode = 'a',
    level = logging.DEBUG,
    format = log_prefix +  ' - %(asctime)s - %(levelname)s: %(message)s',
    datefmt = '%m/%d/%Y %I:%M:%S %p'
  )

  # Disable debug logs from requests library
  logging.getLogger('requests').setLevel(logging.WARNING)
  logging.getLogger('urllib3').setLevel(logging.WARNING)

  try:
    validate(instance = config, schema = config_schema)
  except Exception as e:
    logging.error('Provided configuration did not match expected schema')
    logging.error('%s', str(e))
    exit(-1)

  webhooks = config.get('webhooks', {})
  meta = config.get('meta', {})

  webhook_success = webhooks.get('success')
  webhook_failure = webhooks.get('failure')

  for check in config['checks']:
    run_check(check, webhook_success, webhook_failure, meta)

if __name__== '__main__':
  main()
