import subprocess
import syslog
import sys
import re
import time
import os

syslog.openlog('repo_service')

repo_name_re = re.compile(r'^[a-z][a-z0-9_-]{2,}$')
repo_desc_re = re.compile(r'^[\w\s]{5,}$')

repo_dir = os.path.dirname(os.path.realpath(__file__))
repo_dir = os.path.join(repo_dir, 'gitolite')
repo_git = 'git@git.sublab.org:gitolite-admin.git'
cgit_conf = '/etc/cgitrc.repo_service'

class GitException(Exception):
    pass

class RepoExistsException(Exception):
    pass

def git_call(args, **kwargs):
    try:
        subprocess.check_call(args, **kwargs)
    except subprocess.CalledProcessError as e:
        syslog.syslog('%s failed.' % ' '.join(args[:1]))
        raise GitException()

def gitolite_append(repo_owner, repo_name, repo_desc):
    if not os.path.isdir(repo_dir):
        git_call(['git', 'clone', repo_git, repo_dir])
    else:
        git_call(['git', 'fetch', repo_git, 'master'], cwd=repo_dir)
        git_call(['git', 'reset', '--hard', 'FETCH_HEAD'], cwd=repo_dir)

    grep = subprocess.call(
            ['grep', '-r' , '^\s*repo\s\s*%s\s*$' % repo_name, '.'],
            cwd=os.path.join(repo_dir, 'conf'))
    if grep != 1:
        raise RepoExistsException

    filename = os.path.join(repo_dir, 'conf', 'repo_service.conf')

    repo_date = time.strftime('%a, %d %b %Y %T %z')
    entry = '''
    # Automatically created by repo_service
    # at %(repo_date)s
    # for %(repo_owner)s
        repo     %(repo_name)s
                 R    = daemon
                 RW   = @members
''' % locals()

    try:
        with open(filename, 'a') as gitolite_conf:
            gitolite_conf.write(entry)
    except EnvironmentError as e:
        syslog.syslog('could not append to repo_service.conf: %s' % repr(e))
        raise GitException

    git_call(['git', 'add', filename], cwd=repo_dir)
    git_call(['git', 'commit',
            '--author=Repo Service <nobody@nowhere.ws>',
            '--message=repo_service: create %s for %s' % (repo_name, repo_owner)],
            cwd=repo_dir)
    git_call(['git', 'push', repo_git, 'master:master'], cwd=repo_dir)

def cgit_append(repo_owner, repo_name, repo_desc):
    repo_date = time.strftime('%a, %d %b %Y %T %z')
    cgit_entry = '''
# Automatically created by repo_service
# at %(repo_date)s
# for %(repo_owner)s
repo.url=%(repo_name)s
repo.path=/var/lib/git/repositories/%(repo_name)s.git
repo.desc=%(repo_desc)s
repo.owner=sublab
''' % locals()

    with open(cgit_conf, 'a') as cgit_config:
        cgit_config.write(cgit_entry)

def create_repo(repo_owner, repo_name, repo_desc):
    if repo_name_re.match(repo_name) is None:
        syslog.syslog('Declined repo_name %s to %s' % (
            repr(repo_name), repo_owner))
        return 'ERROR_NAME'

    if repo_desc_re.match(repo_desc) is None:
        syslog.syslog('Declined repo_desc %s to %s' % (
            repr(repo_desc), repo_owner))
        return 'ERROR_DESC'

    syslog.syslog('Handling create_repo for %s ' % (repo_owner) +
            'repo_name=%s, repo_desc=%s' % (repo_name, repo_desc))

    try:
        gitolite_append(repo_owner, repo_name, repo_desc)
    except RepoExistsException:
        return 'ERROR_EXISTS'
    except GitException:
        syslog.syslog('gitolite_append failed')
        return 'ERROR_GITOLITE'

    try:
        cgit_append(repo_owner, repo_name, repo_desc)
    except EnvironmentError:
        syslog.syslog('cgit_append failed')
        return 'ERROR_CGIT'

    syslog.syslog('created repo %s' % repo_name)
    return 'SUCCESS'

if __name__ == '__main__':
    from SimpleXMLRPCServer import SimpleXMLRPCServer
    import errno
    import select

    server = SimpleXMLRPCServer(("127.0.0.1", 8023))
    server.register_function(create_repo)

    while True:
        try:
            server.serve_forever()
        except select.error as e:
            if e.args[0] == errno.EINTR:
                continue
            raise
