#!/usr/bin/env python
#
# June 11, 2017; Blake C. Fleischer
# Only supported for Anaconda Python 3

# Can be called as python module or from command line directly via argparse.
#
# 1 - Append the SSL certificates (certs) contained in the specified path
# (ending with *.crt or *.pem) to the python requests library (maintained by
# python certifi). When updated, certifi will overwrite this configuration,
# requiring a re-append of the certs.
# 2 - Set necessary environment variables for python and R
# 3 - Create/update pip config for ssl certs.
#
# Usage from command line:
# python ./conda_set_envup.py --cert_path . --set_env VAR1=var1,VAR2=var2 --prepend_env PYTHONPATH=. --pip
#
# Usage as python module:
# import conda_set_envup
# conda_set_envup.main(cert_path=path, set_env=set_envtings, prepend_env=prepend_envs, do_pip=True)
# - where path is a string, set_env and prepend_envs are dictionaries, and do_pip is boolean.

import os
import sys
from io import open
import six
import platform
from datetime import datetime
from shutil import copy2
import requests
import ssl
import argparse
import glob
import re


# Module variables
script_loc = os.path.dirname(os.path.abspath(__file__))


# Module functions
def _path_update(path):
    '''Update path for potential null (\0) characters.'''
    return path.replace('\\', '\\\\')


def _yes_no(string_for_yn=''):
    '''Yes or no prompt.'''
    yes = {'yes', 'y', 'ye', ''}
    no = {'no', 'n'}
    yn = input(string_for_yn).lower()
    if yn in yes:
        return True
    elif yn in no:
        return False
    else:
        sys.stdout.write("Please respond with 'y' or 'n'.")


def _set_env(env_var, env_val, prepend=False):
    ''' Set or append environment variables, OS specific.'''
    operating_sys = platform.system()
    if prepend:  # Prepend env variables
        if operating_sys == 'Windows':
            print(''.join(["Prepending: \"", env_var, "\" with \"", env_val, "\""]))
            os.system("SETX {0} {1};%{2}%".format(env_var, env_val, env_var))  # Permanent
            os.system("set \"{0}={1};%{2}%\"".format(env_var, env_val, env_var))  # Current
        # IMPLEMENT LINUX AND MAC('Darwin')
    else:  # Set env variables
        if operating_sys == 'Windows':
            print("".join(["Setting: \"", env_var, "=", env_val, "\""]))
            os.system("SETX {0} {1}".format(env_var, env_val))  # Permanent
            os.system("set \"{0}={1}\"".format(env_var, env_val))  # Current
        # IMPLEMENT LINUX AND MAC('Darwin')


def _set_env_check(env_var, env_val, prepend=False):
    '''Prompt user before calling _set_env.'''
    set_var = False
    if env_var in os.environ:
        if (prepend) & (env_val not in os.environ[env_var]):
            set_var = True
        else:
            set_var = False
        if (not prepend) & (os.environ[env_var] != env_val):  # Only ask if var is not the same
            if _yes_no(''.join(["Environment variable already set: \"",
                                env_var, "=", os.environ[env_var],
                                "\".\n Change to ", env_val, "?"])):
                set_var = True
            else:
                set_var = False
    else:  # Var not set
        set_var = True
    if set_var:
        _set_env(env_var, env_val, prepend=prepend)
    else:
        print("".join(["Leaving: \"", env_var,
                       "=", os.environ[env_var], "\""]))


def set_prepend_envs(set_env, prepend_env):
    """ Update/set system environment variables via dictionary. """
    if set_env:
        for env_var in set_env.keys():  # Set environment variables
            _set_env_check(env_var, set_env[env_var], prepend=False)
    if prepend_env:
        for env_var in prepend_env.keys():  # Prepend environment variables
            _set_env_check(env_var, prepend_env[env_var], prepend=True)


def _backup_file(pth_old):
    """ Back up file to timestamped filename in same location. """
    curr_datetime = datetime.now().strftime("%Y%m%d_%H%M")
    file_ext = os.path.splitext(pth_old)[1]
    file_name = os.path.splitext(pth_old)[0]
    pth_backup = ('').join([file_name, '-backup_', curr_datetime, file_ext])
    copy2(pth_old, pth_backup)  # Make backup copy of original
    return pth_backup


def _append_text(pth_prev_textfile, path_new_textfile, backup=True):
    """ Check if text present in file, if not append. """
    with open(pth_prev_textfile, encoding='utf-8') as f:
        existing_contents = f.readlines()
    with open(path_new_textfile, encoding='utf-8') as f:
        new_contents = f.readlines()
        new_contents.insert(0, "\n")
    if not set(new_contents).issubset(existing_contents):  # If new text is not in existing, append
        if backup:
            backup_filename = _backup_file(pth_prev_textfile)
            status = 'Backed up: {}\nat {}.\n'.format(pth_prev_textfile,
                                                      backup_filename)
        with open(pth_prev_textfile, 'a+') as f:  # Append new to existing
            existing_contents = f.writelines([six.text_type(x) for x in new_contents])
        return True
    else:
        return False


# def update_cert(pth_orig_cert, pth_new_cert):
#    """ Add some certificate specific responses to _append_text. """
#    if _append_text(pth_orig_cert, pth_new_cert):
#        print('Backed up cert file: {}\nat {}...'.format(pth_orig_cert, pth_new_cert))
#    else:
#        print('Certs are already added to cert file: {}'.format(pth_orig_cert))


def update_certs(pth_orig_cert, pth_new_cert_list):
    """ Add multiple certificates located at pth_new_certs_list to path_orig_cert via _append_text. """
    if not isinstance(pth_new_cert_list, list):
        pth_new_cert_list = [pth_new_cert_list]
    if len(pth_new_cert_list) > 0:
        backed_up = False
        status = ""
        for loc_cert in pth_new_cert_list:
            if not os.path.isfile(loc_cert):  # Check for cert
                raise ValueError(''.join(["Certificate location \'", loc_cert,
                                          "\' is not valid. Is this the right location?"]))
            if _append_text(pth_orig_cert, loc_cert, backup=(not backed_up)):
                status = "".join([status, "Appended {} to {}.\n".format(loc_cert, pth_orig_cert)])
                backed_up = True
        if status is "":
            status = "Certs are already added to: {}".format(pth_orig_cert)
    else:
        status = "No cert files ending in *.crt or *.pem in specified path."
    return status


def cert_config(pth_config, config_str, pth_prepend="cert="):
    """ Update config file located at pth_config with a string(config_str). """

    # Determine path of cert from config_str list of strings (first str containing pth_prepend)
    path_cert = [x.split(pth_prepend) for x in config_str if pth_prepend in x][0][1]
    path_cert = re.sub('[\n\r]', '', _path_update(path_cert))

    if not os.path.exists(pth_config):  # if config file does not exist, create and populate
        if not os.path.exists(os.path.dirname(pth_config)):
            os.makedirs(os.path.dirname(pth_config))
        with open(pth_config, 'w', encoding='utf-8') as file:
            for line in config_str:
                # Use re to print filename consistently.
                file.write(six.text_type(re.sub('{}.*$'.format(pth_prepend), ''.join([pth_prepend, path_cert]), line)))
        status = "".join(["Created and updated ", pth_config])
    else:  # If config file exists, replace or append if pth_prepend not present
        with open(pth_config, encoding='utf-8') as f:
            pip_contents = f.readlines()  # Read contents
            pip_contents = [_path_update(x) for x in pip_contents]  # Update windows paths for string literals
        if pth_prepend not in '\t'.join(pip_contents):  # Append pip.ini cert
            with open(pth_config, 'a', encoding='utf-8') as file:
                # Use re to print filename consistently.
                file.write(six.text_type(re.sub('{}.*$'.format(pth_prepend),
                                  ''.join([pth_prepend, path_cert]),
                                  '{}{}\r\n'.format(pth_prepend, path_cert))))
            status = "".join(["Appended to ", pth_config])
        else:  # Update path_cert:
            if path_cert not in '\t'.join(pip_contents):
                # Update pip.ini cert location:
                config_loc_backup = _backup_file(pth_config)
                copy2(pth_config, config_loc_backup)  # Make backup copy of original
                with open(pth_config, 'w', encoding='utf-8') as file:
                    for line in pip_contents:
                        # Use re to print filename consistently.
                        file.write(re.sub('{}.*$'.format(pth_prepend),
                                          ''.join([pth_prepend, path_cert]),
                                          line))
                status = "Backed up config to {}.\nUpdated config file to contain new location.".format(config_loc_backup)
            else:
                status = "Config file already refers to right location."
    return status


def ssl_pip(pth_cert=requests.certs.where(), pth_prepend="cert="):
    """ Update pip SSL install configuration. """
    operating_sys = platform.system()

    # Locate pip.ini config file:
    if 'envs' in sys.prefix:  # Completely unscientific way of checking if in python virtual env
        loc_pip_ini = os.path.join(sys.prefix, 'pip.conf')
    else:
        # Determine pip location depending on os: https://pip.pypa.io/en/stable/user_guide/
        if operating_sys == 'Windows':  # Windows
            loc_pip_ini = os.path.join(os.environ['APPDATA'], 'pip', 'pip.ini')
        elif operating_sys == 'Darwin':  # Mac OS
            mac_pip_1 = os.path.join(os.environ['HOME'], 'Library',
                                     'Application Support', 'pip')
            mac_pip_2 = os.path.join(os.environ['HOME'], '.config', 'pip')
            if os.path.isdir(mac_pip_1):
                loc_pip_ini = os.path.join(mac_pip_1, 'pip.conf')
            else:
                loc_pip_ini = os.path.join(mac_pip_2, 'pip.conf')
        elif operating_sys == 'Linux':  # Linux
            loc_pip_ini = os.path.join(os.environ['HOME'], '.config', 'pip',
                                       'pip.conf')
#    # Copy Pip Cert - skipped b/c we can point to requests cert
#    if pth_cert=='default':
#        pth_cert = os.path.join(os.path.basename(loc_pip_ini), os.path.basename(loc_cert_req))
#        if not os.path.exists(pth_cert):  # Copy cert
#            print(''.join(['Pip config: Copying cert to ', pth_cert]))
#            os.makedirs(os.path.dirname(pth_cert), exist_ok=True)
#            copy2(loc_cert_req, pth_cert)
#        else:  # Check if append to cert
#            update_cert(pth_cert, loc_cert_req)
#        pth_cert = _path_update(pth_cert)  # Determine final loc_cert_pip:
    pip_text = ['\r\n[global]\r\n',
                ''.join([pth_prepend, pth_cert, '\r\n'])]  # Text to write if not present
    # Update/create config file, return output
    status = cert_config(loc_pip_ini, pip_text, pth_prepend="cert=")
 
    return status

def run_argparse():  # User inputs
    ''' Run argparse on all the incoming script arguments.'''
    parser = argparse.ArgumentParser(
                description='''
                Automated means for setting up environment:

                (1) Append SSL certificates to python Requests (certifi) so conda commands work
                (2) Optionally configure system environment variables (i.e. HTTPS_PROXY)
                (3) Optionally update pip configuration to use certificates.''')
    parser.add_argument("-c", "--cert_path", type=str,
                        help="Specify path to folder of ssl certificate(s) in .pem format (*.crt, *.pem). Default is the same folder as the conda_set_envup module.",
                        default=os.path.dirname(os.path.abspath(__file__)))

    set_env = {}  # https://stackoverflow.com/questions/29986185/python-argparse-dict-arg

    class StoreDictKeyPair_set(argparse.Action):
        def __call__(self, parser, namespace, values, option_string=None):
            for kv in values.split(","):
                k, v = kv.split("=")
                set_env[k] = v
            setattr(namespace, self.dest, set_env)

    parser.add_argument("-es", "--set_env",
                        help="Set system environment variables.",
                        action=StoreDictKeyPair_set,
                        dest="set_env",
                        metavar="KEY1=VAL1,KEY2=VAL2...")
    prepend_env = {}

    class StoreDictKeyPair_prepend(argparse.Action):
        def __call__(self, parser, namespace, values, option_string=None):
            for kv in values.split(","):
                k, v = kv.split("=")
                prepend_env[k] = v
            setattr(namespace, self.dest, prepend_env)

    parser.add_argument("-ep", "--prepend_env",
                        help="Prepend system environment variables.",
                        action=StoreDictKeyPair_prepend,
                        dest="prepend_env",
                        metavar="KEY1=VAL1,KEY2=VAL2...")
    parser.add_argument("-p", "--pip", help="Configure ssl for pip.",
                        action="store_true")
    parser.add_argument("-r", "--requests", help="Configure requests ssl for conda.",
                        action="store_true")
    parser.add_argument("-a", "--aws", help="Configure for boto3 in windows being a separate installation",
                        action="store_true")
    args = parser.parse_args()

    main(cert_path=args.cert_path, set_env=set_env, prepend_env=prepend_env,
         do_pip=args.pip, do_requests=args.requests, do_aws=args.aws)

def main(cert_path=script_loc, set_env={}, prepend_env={}, do_pip=False,
         do_aws=False, do_requests=False):
    ''' This is the main script. '''

    if not do_requests and not do_pip and not prepend_env and not set_env and not do_aws:
        print("Please specify at least one of the following: --requests, --pip, --prepend-env, --set_env, --aws (windows only).")

    # Automated inputs:
    if do_requests or do_pip or do_aws:
        loc_certs = [glob.glob(os.path.join(cert_path, x)) for x in ['*.pem', '*.crt']]
        loc_certs = [_path_update(cert) for sublist in loc_certs for cert in sublist]

    # Update requests certificates - for Conda install:
    if do_requests:
        if ('requests' in sys.modules) and ('certifi' in sys.modules) and len(loc_certs)>0:
            print("Requests SSL configuration started...")
            req_status = update_certs(requests.certs.where(), loc_certs)  # Location of Python's requests cert file
            print(" ".join(["Requests Config:", req_status]))
            print("Requests SSL configuration complete.")
        elif 'requests' not in sys.modules:
            print("Python requests library not installed, skipping requests update. Is conda installed?") 
        elif 'certifi' not in sys.modules:
            print("Python certifi library not installed, skipping certifi update. Is conda installed?")
        elif len(loc_certs) < 1:
            print("No certificate *.pem or *.crt' files found at {}, skipping certificate update.".format(os.path.abspath(loc_certs)))
        
    # Update environment variables:
    if (prepend_env) or (set_env):
        print("Environment variables configuration started...")
        set_prepend_envs(set_env, prepend_env)
        print("Environment variables configuration complete.")

    # Update pip config:
    if do_pip:
        print("Pip SSL configuration started...")
        if do_requests and ('requests' in sys.modules) and ('certifi' in sys.modules):
            pip_cert_loc = requests.certs.where()
        else:
            pip_cert_loc = ssl.get_default_verify_paths().cafile
            pip_status = update_certs(pip_cert_loc, loc_certs)
            print(" ".join(["Pip Config:", pip_status]))
   
        pip_status = ssl_pip(pth_cert=pip_cert_loc, pth_prepend="cert=")
        print(" ".join(["Pip Config:", pip_status]))
        print("Pip SSL configuration complete.")

    # Update AWS config (if present). Requires admin priviledges.
    if do_aws:
        if platform.system() == 'Windows':
            aws_cert_win = "C:\\Program Files\\Amazon\\AWSCLI\\botocore\\vendored\\requests\\cacert.pem"
            aws_cert_win = _path_update(aws_cert_win)
            print(aws_cert_win)
            if os.path.isfile(aws_cert_win):
                print("AWS CLI SSL configuration started...")
                aws_cert_status = update_certs(aws_cert_win, loc_certs)
                print(" ".join(["AWS CLI SSL config:", aws_cert_status]))
                print("AWS CLI SSL configuration complete.")
        else:
            print("The --aws flag only applies to windows. Skipping...")

if __name__ == "__main__":
    run_argparse()
