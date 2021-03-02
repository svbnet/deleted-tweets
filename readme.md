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

### configuration

- environment variables you can set are in `context.py`.

### custom fonts

if you are running it on Linux the rendered output will probably look pretty bad. you can improve this with custom fonts, which the default template will automatically use. at the moment helvetica is included which looks fine (though not on Windows, which is fine since it'll just fallback to arial).

- download https://about.twitter.com/content/dam/about-twitter/en/brand-toolkit/downloads/twitter-tweet-template-helvetica-01272021.zip and copy everything from the `Fonts` directory to `assets/fonts`
- `export CUSTOM_FONT='helvetica'` before running

## to-dos
- rendering is slow because 