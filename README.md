cloud_manager
=============

cloud_manager is a small python progrom that provides simple command line
control of Amazon EC2 instances by the instance name.  You can start and stop
instances, see the status of all  your instances, connect by ssh or run a
command on an instance.

It's ideal for use with instances you start and stop regularly that don't have
elastic IP addresses - so the DNS name changes all the time.

For example:

	python ssh doozer

Will connect to an instance named doozer by ssh in the current terminal.

	python cloud_manager.py doozer run 'some_script.sh param1 param2'

Will run 'some_script.sh' on an instance named doozer, if doozer isn't running
CloudManager will start it and shut it down after the command is finished.  This
is really handy if you want to run a regular cron job on a micro instance that
will start a more powerful server to do some processing.

Setup
=====

CloudManager requires a recent version of python 2.x to run.  It has only been
tested on linux and Mac with python 2.6.? and 2.7.?.

It requires the boto python library for working with Amazon EC2.  See [here].
If you have setup tools [link to setup tools] installed you can simple run `sudo easy_install boto`

`boto` and `cloud_manager` requires some environment variables to be set with
access details for Amazon Web Services.

Two are standard for EC@ access [see here] and contain the credentials provided
by amazon.

	AWS_ACCESS_KEY_ID=
	AWS_SECRET_ACCESS_KEY=

The location of your private key for accessing yur EC2 servers is required for
ssh into instances:

	AWS_SSH_KEY='/Users/somebody/somewhere/a_key.pem'

By default the username used to connect to instances is `ec2-user`, to use a
different username (e.g. for ubuntu servers the username is usually `ubuntu`)
set the optional environment variable:

	AWS_USERNAME='ubuntu'

Alias (optional)
================
I alias `cloud_manager.py` to `cm` in my `.bash_profile`, e.g. `alias cm='python /somewhere/cloud_manager.py` so the commands become, for example:

	cm ssh doozer

Commands
========

### status
List the name instance type and status (running or stopped) for each of your
instances.

	python cloud_manager.py status

Output:
	doozer (t1.micro): running
	optimus (m1.large): stopped

### start
Start and instance if it isn't already running.

	python cloud_manager.py doozer start

### stop
Stop an instance if it's running.

	python cloud_manager.py doozer stop

### ssh
Connect to an instace by ssh in the current terminal window.
	
	python cloud_manager.py ssh doozer

NOTE this redirects the known hosts file to `/dev/null` for this command so the
address of the server isn't added to your permanent known_hosts file.


### run
Run a given command on an instance via ssh and wait for the command to complete.
If the instance isn't already running CloudManager will start the instance first
and stop it when finished.  If the instance is already running it won't be
stopped.

	python cloud_manager.py run 'some_script.sh param1'

If the command require parameters they should by quoted along with the command.
