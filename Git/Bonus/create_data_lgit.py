import os
import print_message
import get_data_lgit as lgit_g
from utils import write_file, read_file, hash_sha1, split_dir_file
from sys import exit as exit_program


def create_branch(name, commit):
    os.makedirs('.lgit/stash/heads/%s/objects' % (name))
    write_file(['%s\n' % (commit)],
               '.lgit/refs/heads/%s' % (name))


def create_commit(message, time_ns):
    # save commit message and author
    author = lgit_g.get_author()
    t_commit = time_ns.split('.')[0]
    p_commit = lgit_g.get_commit_branch()
    write_file(["%s\n%s\n%s\n\n%s\n" %
                (author, t_commit, p_commit, message)],
               '.lgit/commits/%s' % (time_ns))


def create_snapshot(path):
    # save all of hash commit and path in index file
    # into timestamp of commit file at snapshot directory
    data_snap = []
    for line in read_file('.lgit/index'):
        _, _, _, h_commit, name = lgit_g.get_info_index(line)
        data_snap.append(h_commit + " " + name + '\n')
    write_file(data_snap, file=path)


def create_object(files_add):
    '''
    Task:
        + Store a copy of the file content in the lgit database
        + Each file will be stocked in the following way:
            - first two characters of the SHA1 will be the directory name
            - last 38 characters will be the file name
    '''
    for path in files_add:
        hash_f = hash_sha1(path)
        direc_obj, file_obj = split_dir_file(hash_f)
        direc_obj = '.lgit/objects/%s' % (direc_obj)
        if not os.path.exists(direc_obj):
            os.makedirs(direc_obj)
        file_obj = os.path.join(direc_obj, file_obj)
        if not os.path.exists(file_obj):
            write_file(read_file(path, mode='rb'), file_obj, mode='wb')


def create_info_branch(branch):
    write_file(['%s\n' % (lgit_g.get_commit_branch())],
               '.lgit/info/%s' % (branch))


def create_structure_lgit(direcs, files):
    if not os.path.exists('.lgit'):
        os.makedirs('.lgit')
    elif os.path.isfile('.lgit'):
        print('fatal: Invalid gitfile format: .lgit')
        exit_program()
    for d in direcs:
        if os.path.isfile(d):
            print("%s: Not a directory" % (os.path.join(os.getcwd(), d)))
        else:
            os.makedirs(d)
    for f in files:
        if not os.path.isdir(f):
            open(f, 'w').close()
        else:
            print("error: unable to mmap '%s' Is a directory" %
                  (os.path.join(os.getcwd(), f)))


def create_stash(modified_file, time_ns):
    if _is_valid_stash(modified_file):
        create_object(modified_file)
        data_stash = []
        for file in modified_file:
            data_stash.append("%s %s\n" % (hash_sha1(file), file))
        write_file(data_stash, '.lgit/refs/stash/%s' % (time_ns))


def _is_valid_stash(files):
    for f in files:
        if not os.access(f, os.R_OK):
            print_message.PERMISSION_DENIED_STASH(f)
            exit_program()
    return True
