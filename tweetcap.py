import tempfile, subprocess, os, re, os.path, urllib.parse
from datetime import datetime

from twython import Twython
from PIL import Image, ImageChops, ImageDraw
from jinja2 import Environment, FileSystemLoader, select_autoescape

import context
from util import short_human_time, normalize_time_format_str

def tweet_strptime(date):
	return datetime.strptime(date, '%a %b %d %H:%M:%S %z %Y')


def tweet_htmlize(value):
	return Twython.html_for_tweet(value)


def short_datetime(value):
	return short_human_time(tweet_strptime(value))


def long_datetime(value):
	return tweet_strptime(value).strftime(normalize_time_format_str('%-I:%M %p · %b %d, %Y'))


def tweet_source_name(value):
	return re.search(r'<a(?:.*)>(.*)<\/a>', value).group(1)


environment = Environment(
	loader=FileSystemLoader(context.template_path),
	autoescape=select_autoescape(['html', 'xml'])
)

environment.filters['tweet_htmlize'] = tweet_htmlize
environment.filters['short_datetime'] = short_datetime
environment.filters['long_datetime'] = long_datetime
environment.filters['tweet_source_name'] = tweet_source_name


def trim(path, margin):
	image = Image.open(path).convert('RGB')
	colour = image.getpixel((0,0))
	background = Image.new('RGB', image.size, colour)
	diff = ImageChops.difference(image, background)
	l,t,r,b = diff.getbbox()
	w = r - l
	h = b - t
	bbox = (l - margin, t - margin, r + margin, b + margin)
	image = image.crop(bbox)
	draw = ImageDraw.Draw(image)
	draw.rectangle([0, 0, w+2*margin-1, margin-1], fill=colour)
	draw.rectangle([0, margin, margin-1, h+margin-1], fill=colour)
	draw.rectangle([w+margin, margin, w+2*margin-1, h+margin-1], fill=colour)
	draw.rectangle([0, h+margin, w+2*margin-1, h+2*margin-1], fill=colour)
	del draw
	image.save(path)


def make_config():
	config = {}
	if context.custom_font is not None:
		path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'assets', 'css', f'{context.custom_font}.css'))
		normal_path = path.replace('\\', '/')
		url = f'file://{urllib.parse.quote(normal_path)}'
		config['custom_font'] = {'css_url': url, 'path': path}
	return config

def tweetcap(template_name, tweet):
	config = make_config()
	template = environment.get_template(template_name)

	html = template.render(tweet=tweet, config=config)

	temp = tempfile.NamedTemporaryFile(mode='wb', suffix='.html', delete=False)
	temp.write(html.encode('ascii', 'xmlcharrefreplace'))
	temp.close()

	image = tempfile.NamedTemporaryFile(mode='wb', suffix='.png', delete=False)
	image.close()

	args = ['wkhtmltoimage']
	if config.get('custom_font'):
		args.append('--enable-local-file-access')
	args += ['-f', 'png', temp.name, image.name]

	subprocess.check_call(args)
	os.remove(temp.name)
	trim(image.name, 5)
	return image.name
