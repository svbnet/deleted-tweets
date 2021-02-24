## deleted-tweets

this is a twitter bot that monitors specific twitter account(s) and tweets screenshots of any messages which they subsequently delete

### dependencies

- wkhtmltopdf - in most cases it's best to just download it from [here](https://wkhtmltopdf.org/downloads.html) then install it rather than directly through your package manager.
- Python 3 (>= 3.7) and `pip`
- `virtualenv`

### install

- clone
- `virtualenv venv`
- `. venv/bin/activate`
- `pip3 install -r requirements.txt`

### initial setup

- create a new twitter app with write permission
- run `./init.py`
- enter consumer key and secret
- go to the url provided and log in to twitter
- enter the pin shown in your web browser
- enter list of users to track, separated by whitespace or commas

## use

- run `./watch.py`
- you'll probably want to use something like `runit` for process supervision

## configuration

- environment variables you can set are in `context.py`.
