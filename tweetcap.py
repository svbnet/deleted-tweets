import tempfile, subprocess, os, re
from datetime import datetime

from twython import Twython
from PIL import Image, ImageChops, ImageDraw
from jinja2 import Environment, FileSystemLoader, select_autoescape

import context
from util import short_human_time

def tweet_strptime(date):
	return datetime.strptime(date, '%a %b %d %H:%M:%S %z %Y')


def tweet_htmlize(value):
	return Twython.html_for_tweet(value)


def short_datetime(value):
	return short_human_time(tweet_strptime(value))


def long_datetime(value):
	return tweet_strptime(value).strftime('%I:%M %p · %b %d, %Y')


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


def tweetcap(template_name, tweet):
	template = environment.get_template(template_name)
	html = template.render(tweet=tweet)

	temp = tempfile.NamedTemporaryFile(mode='wb', suffix='.html', delete=False)
	temp.write(html.encode('ascii', 'xmlcharrefreplace'))
	temp.close()

	image = tempfile.NamedTemporaryFile(mode='wb', suffix='.png', delete=False)
	image.close()

	subprocess.check_call(['wkhtmltoimage', '-f', 'png', temp.name, image.name])
	os.remove(temp.name)
	trim(image.name, 5)
	return image.name
