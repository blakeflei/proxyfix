# proxyfix
----

Proxyfix is meant to simplify the steps needed to get [Anaconda](https://www.anaconda.com/download) working through https firewalls by appending certificates to the python [requests](http://docs.python-requests.org/en/master/) library, configuring pip, and setting and/or prepending environment variables (i.e. ```HTTPS_PROXY```) as needed. While proxyfix updates the certificates via [requests](http://docs.python-requests.org/en/master/), [certifi](https://github.com/certifi) will overwrite this configuration when updated, requiring a re-append of the certificates.

proxyfix will:
 - Append the SSL certificates (certs) contained in the folder specified by the path (ending with *.crt or *.pem) to the python [requests](http://docs.python-requests.org/en/master/) library.
 - Set and/or prepend necessary environment variables for python (```HTTPS_PROXY```)  and R (```R_LIBS_USER```).
 - Create/update pip config for ssl certs.

### Command line:
```
$ proxyfix.py --cert_path . --set_env VAR1=var1,VAR2=var2 --prepend_env PYTHONPATH=. --requests --pip --aws
```

### As python module:
```
import ./proxyfix
proxyfix.main(cert_path=path, set_env=set_envtings, prepend_env=prepend_envs, pip=True, aws=True )
```

**Where:**
- `path` is a path string to the folder containing certificates
- `set_env` and `prepend_envs` are dictionaries for prepending or setting environment variables
- `pip` is a True/False for configuring pip
- `aws` is a True/False for configuring the aws [boto3](https://boto3.readthedocs.io/en/latest/) library installed via the aws installer (a separate python installation). At the time of writing, it is only applicable to Windows.


