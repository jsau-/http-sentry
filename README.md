# http-sentry

A quick and dirty script for asserting a set of HTTP requests resolve with
expected status codes, plaintext content, or match a regex.

## Running

`python3 http_sentry.py <config_file_path>`

## Configuration

A schema describing all available options can be found at
`./config_schema.json`.

An example configuration file has been included as `./example_config.json`.

## Installation

Install dependencies: `pip3 install -r requirements.txt`

Suggestion: Move the script to somewhere accessible on your path, eg:
`cp http-sentry.py /usr/bin/http-sentry`
