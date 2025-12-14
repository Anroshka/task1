from __future__ import annotations

import os
import re

from locust import HttpUser, between, task


CSRF_RE = re.compile(r"name='csrfmiddlewaretoken' value='([^']+)'|name=\"csrfmiddlewaretoken\" value=\"([^\"]+)\"")


class AppUser(HttpUser):
	wait_time = between(0.1, 0.5)

	def on_start(self):
		username = os.environ.get('LOADTEST_USERNAME', 'engineer_demo')
		password = os.environ.get('LOADTEST_PASSWORD', 'engineer12345')

		# 1) Получаем csrftoken
		resp = self.client.get('/login/', name='GET /login/')
		token = resp.cookies.get('csrftoken')
		if not token:
			m = CSRF_RE.search(resp.text or '')
			if m:
				token = m.group(1) or m.group(2)

		# 2) Логинимся
		headers = {}
		if token:
			headers['X-CSRFToken'] = token
			self.client.cookies.set('csrftoken', token)

		self.client.post(
			'/login/',
			data={'username': username, 'password': password},
			headers=headers,
			name='POST /login/',
		)

	@task(8)
	def dashboard(self):
		self.client.get('/', name='GET / (dashboard)')

	@task(2)
	def projects(self):
		self.client.get('/projects/', name='GET /projects/')
