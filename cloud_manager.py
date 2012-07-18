#!/usr/bin/env python
# encoding: utf-8

import os
import sys
import subprocess
from time import time, sleep
from collections import defaultdict

from boto.ec2.connection import EC2Connection

# List all available ops, value is True if an instance name is required
VALID_OPS = {'start': True,
			 'stop': True,
			 'dns': True,
			 'status': False,
			 'ssh': True,
			 'run': True}

DEFAULT_USERNAME = 'ec2-user'

class CloudManager(object):

	def __init__(self):
		self.conn = EC2Connection()
		self.instances = defaultdict(dict)
		self._read_instances()

	def _read_instances(self):
		reservations = self.conn.get_all_instances()
		for res in reservations:
			for i in res.instances:
				name = i.tags['Name']
				self._update_instance(name, i)

	def _update_instance(self, name, instance):
		self.instances[name]['id'] = instance.id
		self.instances[name]['state'] = instance.state
		self.instances[name]['dns_name'] = instance.dns_name
		self.instances[name]['type'] = instance.instance_type
		self.instances[name]['instance'] = instance

	def _check_name(self, name, exit=True):
		'''
		Check that 'name' is a valid instance name, if exit=True print a message
		to the console and exit.  If exit=False return True/False whether the
		name is valid.
		'''
		if exit:
			if name not in self.instances:
				print ("No instance '%s', available names are: %s\n" %
					(name, ', '.join(self.instances.keys())))
				exit(1)
		else:
			return name in self.instances

	def start_instance(self, name):
		'''
		Start the named instance if it is not already running.
		'''
		self._check_name(name)
		instance = self.instances[name]['instance']
		print("\nStarting '%s' (%s), id = %s" %
			(name, self.instances[name]['type'], self.instances[name]['id']))

		start_time = time()
		if instance.state != 'running':
			instance.start()
			while not instance.update() == 'running':
				sleep(5)
			print "Started '%s' took: %.1fs\n" % (name, time() - start_time)
			self._update_instance(name, instance)
		else:
			print "'%s' was already running\n" % name
		return instance.dns_name

	def stop_instance(self, name):
		'''
		Stop the named instance if it is running and print a message.
		'''
		self._check_name(name)
		instance = self.instances[name]['instance']
		print("\nStopping '%s' (%s), id = %s" %
			(name, self.instances[name]['type'], self.instances[name]['id']))
		if instance.state == 'running':
			start_time = time()
			instance.stop()
			while not instance.update() == 'stopped':
				sleep(5)
			print "Stopped '%s' took: %.1fs\n" % (name, time() - start_time)
			self._update_instance(name, instance)
		else:
			print "'%s' was already stopped" % name

	def get_dns(self, name):
		'''
		Return the dns address of the named instance.  Exit if name is invalid.
		'''
		self._check_name(name)
		if self.is_running(name):
			return self.instances[name]['dns_name']
		return False

	def is_running(self, name):
		'''
		Return True if the named instance is running, return None if the name is
		invalid.
		'''
		if not self._check_name(name, exit=False):
			return None
		return self.instances[name]['state'] == 'running'

	def ssh(self, name):
		'''
		Connect to the named instance by ssh if it is running.  This method
		relies on the environment variable AWS_SSH_KEY to be set pointing to the
		private key used to ssh ssh into EC2 intances.  By default the username
		is 'ec2-user' unless the optional environment variable AWS_USERNAME is
		set.
		'''
		self._check_name(name)
		if not self.is_running(name):
			print "\n'%s' is not running, can't ssh in.\n" % name
			exit(1)
		dns = self.get_dns(name)
		user = os.getenv('AWS_USERNAME', DEFAULT_USERNAME)
		print 'Attempting to log into %s as %s...' % (name, user)

		login = user + '@' + dns
		key_file = self._get_key_file()

		# ssh without checking and recording known hosts, this may be a new DNS
		ret = subprocess.check_call(['ssh', '-o UserKnownHostsFile=/dev/null',
								 '-o StrictHostKeyChecking=no',
								 '-i' + key_file, login])

	def run_command(self, name, command):
		'''
		Connect to an instance by ssh and execute the given command on that
		instance.  If the instance isn't running it will be started first, if
		started by this method it will be stopped again.
		'''
		self._check_name(name)
		
		key_file = self._get_key_file()
		user = os.getenv('AWS_USERNAME', DEFAULT_USERNAME)

		try:
			was_running = cm.is_running(name)
			if not was_running:
				cm.start_instance(name)
				# ssh command was failing if run immediately after launch
				print 'Instance started, waiting a moment before connecting...'
				sleep(30)
			else:
				print "'%s' was already running." % name

			dns = cm.get_dns(name)
			login = user + '@' + dns

			print("Connecting to '%s' by ssh and executing command: %s" %
				(name, command))

			start_time = time()
			# ssh without checking and recording known hosts, this may be a new DNS
			ret = subprocess.check_call(['ssh', '-o UserKnownHostsFile=/dev/null',
										 '-o StrictHostKeyChecking=no',
										 '-i' + key_file,
										 login, command])
			took = time() - start_time
			print 'Success! took: %.3fs\n' % took if ret == 0 else 'Execution failed.\n'
		finally:
			# if we had to start the instance put it back as we found it
			if not was_running:
				cm.stop_instance(server_name)

	def _get_key_file(self):
		'''
		Read the AWS_SSH_KEY environment variable and return the private key
		file location it points to.  Print a message to the console and exit if
		it can't be found.
		'''
		key_file = os.getenv('AWS_SSH_KEY')
		if not key_file:
			print '\nCould not find AWS_SSH_KEY environment variable pointing \
				to private ssh key for EC2 login.\n'
			exit(1)
		return key_file

	def print_status(self):
		'''
		Output details of instances and whether they are running or stopped to
		the console.
		'''
		print
		for name in self.instances:
			print('%s (%s): %s' % (name, self.instances[name]['type'],
				self.instances[name]['state']))
		print


def perform_op(op, name, command=None):
	cm = CloudManager()

	if op == 'status':
		cm.print_status()
	elif op == 'dns':
		print cm.get_dns(name)
	elif op == 'start':
		cm.start_instance(name)
	elif op == 'stop':
		cm.stop_instance(name)
	elif op == 'ssh':
		cm.ssh(name)
	elif op == 'run':
		cm.run_command(name, command)
	else:
		print("\nInvalid operation '%s', valid ops are: %s" %
			(op, '|'.join(VALID_OPS.keys())))


if __name__ == '__main__':
	op_string = '|'.join(VALID_OPS.keys())
	name_ops = [op for op in VALID_OPS.keys() if VALID_OPS[op]]

	if len(sys.argv) not in [2, 3, 4]:
		print '\nUsage: %s [instance_name] %s' % (sys.argv[0], op_string) 
		print '\tinstance_name is required for: %s' % ', '.join(name_ops)
		print "\tinstance_name and a command to run is required for op 'run'"

	op = sys.argv[1]
	if op not in VALID_OPS:
		print "Operation was '%s' but must be one of: %s" % (op, op_string)
		exit(1)

	name = None
	command = None
	if op in name_ops:
		if op == 'run':
			if len(sys.argv) != 4:
				print "An instance name and a command to run are required for \
					op '%s'." % op
				exit(1)
			else:
				name = sys.argv[2]
				command = sys.argv[3]
		else:
			if len(sys.argv) != 3:
				print "An instance_name is required for op '%s'." % op
				exit(1)
			name = sys.argv[2]

	perform_op(op, name, command)






