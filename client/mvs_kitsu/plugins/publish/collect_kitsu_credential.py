# -*- coding: utf-8 -*-
import os

import gazu
import pyblish.api


class CollectKitsuSession(pyblish.api.ContextPlugin):  # rename log in
	"""Collect Kitsu session using user credentials"""

	order = pyblish.api.CollectorOrder
	label = "Kitsu user session"

	def process(self, context):
		self.log.warning(os.environ["KITSU_SERVER"] + "\n")
		self.log.warning(os.environ["KITSU_LOGIN"] + "\n")
		self.log.warning(os.environ["KITSU_PWD"] + "\n")
		gazu.client.set_host(os.environ["KITSU_SERVER"])
		gazu.log_in(os.environ["KITSU_LOGIN"], os.environ["KITSU_PWD"])
