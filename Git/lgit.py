#!/usr/bin/env python3

import os
from datetime import datetime
from argparse import ArgumentParser
from time import time, mktime, strftime, localtime
from hashlib import sha1


def hash_sha1(file):
    '''
    Task: return hash sha1 of file passed
    '''
    with open(file, 'rb') as f:
        return sha1(f.read()).hexdigest()


def split_dir_file(hash_file):
    return hash_file[:2], hash_file[2:]


def get_info_index(line):
    '''
    Task: return format timestamp, hash current, hash add, hash commit, path
    '''
    line = line.strip()
    return line[0:14], line[15:55], line[56:96], line[97:137], line[138:]


def get_pos_track(files):
    '''
    Task: return dictionary with key is file, value is location in index file
    '''
    locations = {}
    for index, line in enumerate(read_file('.lgit/index')):
        _, _, _, _, path = get_info_index(line)
        if path in files:
            locations[path] = index
    return locations


def read_file(file, mode='r'):
    with open(file, mode) as f:
        return f.readlines()


def write_file(data, file, mode='w'):
    '''
    Task: overwrite content of file from content passed
    Param:
        + data: list of string element
        + file: path of file to write
    '''
    with open(file, mode) as f:
        f.writelines(data)


def get_tracked_files():
    '''
    Task: Return list tracked file in index file
    '''
    paths = []
    for line in read_file('.lgit/index'):
        _, _, _, _, file = get_info_index(line)
        paths.append(file)
    return paths


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
        direc_obj = os.path.join('.lgit/objects', direc_obj)
        if not os.path.exists(direc_obj):
            os.mkdir(direc_obj)
        file_obj = os.path.join(direc_obj, file_obj)
        if not os.path.exists(file_obj):
            write_file(read_file(path, mode='rb'), file_obj, mode='wb')


def handle_raw_input(files):
    '''
    Task:
        + Return list valid file is relative with lgit directory
        + Outside of lgit directory --> Show error
        + Path does not exist --> Show error
    '''
    valid_files = []
    for f in files:
        path = format_path(f, mode='absolute')
        if os.getcwd() in path:
            path = path.replace(os.getcwd() + "/", "")
            if os.path.isdir(path):
                sub_file = get_files_direc(path)
                valid_files = valid_files + sub_file
            elif os.path.exists(path):
                valid_files.append(path)
            else:
                print("fatal: pathspec '" + f + "' did not match any files")
        else:
            print("fatal: %s '%s' is outside repository" % (f, f))
    return valid_files


def add_git(files_add):
    '''
    Task:
        + Add untrack file or update unstaged file in index file
        + Store a copy of the file content in the lgit database
    '''
    files_new = handle_raw_input(files_add)
    if files_new:
        update_index(files_new, mode='add', location=get_pos_track(files_new))
        create_object(files_new)
    elif not files_add:
        print("Nothing specified, nothing added.\n\
Maybe you wanted to say 'git add .'?")


def get_files_direc(direc='.'):
    '''
    Task: return list file in subdirectory passed and directory passed
    '''
    dir_direc = [direc]
    file_direc = []
    # find all path of file in src
    while dir_direc:
        # take directory from src
        try:
            entry_direc = os.scandir(dir_direc.pop())
            for e in entry_direc:
                # store file in data_dir
                if e.is_file():
                    path = os.path.abspath(e.path).replace(
                        os.getcwd() + "/", '')
                    file_direc.append(path)
                # store directory in data_dir
                if e.is_dir() and ".lgit" not in e.path:
                    dir_direc.append(e.path)
        except PermissionError:
            pass

    return file_direc


def get_untracked(tracked_files):
    all_files = get_files_direc()
    return [file for file in all_files if file not in tracked_files]


def get_staged_unstaged():
    staged_file = []
    unstaged_file = []
    for line in read_file(file='.lgit/index'):
        _, h_current, h_add, h_commit, name = get_info_index(line)
        if h_current != h_add:
            unstaged_file.append(name)
        if h_add != h_commit:
            staged_file.append(name)
    return staged_file, unstaged_file


def status_git():
    tracked_files = get_tracked_files()
    update_index(tracked_files, mode='status')
    show_status(tracked_files)


def show_status(tracked_files):
    untracked = get_untracked(tracked_files)
    staged, unstaged = get_staged_unstaged()
    print('On branch master\n')
    if not os.listdir('.lgit/commits'):
        print("No commits yet\n")
    if staged:
        print("Changes to be committed:\n\
  (use \"./lgit.py reset HEAD ...\" to unstage)\n")
        print("\t modified:", '\n\t modified: '.join(
            [format_path(p, mode='relative') for p in staged]), end='\n\n')
    if unstaged:
        print("Changes not staged for commit:\n\
  (use \"./lgit.py add ...\" to update what will be committed)\n\
  (use \"./lgit.py checkout -- ...\" to discard changes \
in working directory)\n")
        print("\t modified:", '\n\t modified: '.join(
            [format_path(p, mode='relative') for p in unstaged]), end='\n\n')
    if untracked:
        print("Untracked files:\n\
  (use \"./lgit.py add <file>...\" to include in what will be committed)\n")
        print("\t", '\n\t'.join([format_path(p, mode='relative')
                                 for p in untracked]), sep='', end='\n\n')
    if not os.listdir('.lgit/commits') and not staged and untracked:
        print("nothing added to commit but untracked files\
 present (use \"./lgit.py add\" to track)")
    elif not staged:
        print('no changes added to commit')


def commit_git(message):
    '''
    Task:
        + Update hash commit in index file
        + Create name file is time commit in commits directory
        + Create name file is time commit in snapshots directory
        + Nothing added to commit then show status
    '''
    tracked_files = get_tracked_files()
    staged_file, _ = get_staged_unstaged()
    if staged_file:
        update_index(tracked_files, mode='commit')
        time_ns = format_time(time(), second=False)
        create_commit(message, time_ns)
        create_snapshot(os.path.join('.lgit/snapshots', time_ns))
    else:
        show_status(tracked_files)


def create_commit(message, time_ns):
    # save commit message and author
    author = read_file(file='.lgit/config')[0]
    time_commit = time_ns.split('.')[0]
    write_file(["%s%s\n\n%s\n" % (author, time_commit, message)],
               os.path.join('.lgit/commits', time_ns))


def create_snapshot(path):
    # save all of hash commit and path in index file
    # into timestamp of commit file at snapshot directory
    data_snap = []
    for line in read_file('.lgit/index'):
        _, _, _, h_commit, name = get_info_index(line)
        data_snap.append(h_commit + " " + name + '\n')
    write_file(data_snap, file=path)


def update_index(files, mode, location=''):
    '''
    Task: Update information of tracked file or untracked file in index file
        + With add command:
            - Update hash add and timestamp of file
            - Or add new line infomation file added in index file
        + With status command:
            - Update hash current and timestamp of file in index file
        + With commit command:
            - Update hash commit of file in index file
    '''
    data_index = read_file('.lgit/index')
    for i, file in enumerate(files):
        h_current = hash_sha1(file)
        if mode == 'add':
            # get index from mapping index of file
            # hash add equal hash of file right now
            # commit maybe nothing or have before
            line = location.get(file, -1)
            h_add = h_current
            if line != -1:
                _, _, _, h_commit, _ = get_info_index(data_index[line])
            else:
                h_commit = ''
        else:
            # index equal enunumerate coz run all name file in index file
            # hash add equal last time add of file
            # commit equal hash add if commit else still be same in last time
            line = i
            _, _, h_add, h_commit, _ = get_info_index(data_index[line])
            if mode == 'commit':
                h_commit = h_add
        # add new one in index file if first time tracking file
        # else override on location of file in index file
        if line != -1:
            data_index[line] = format_index(format_time(
                os.path.getmtime(file)), h_current, h_add, h_commit, file)
        else:
            data_index.append(format_index(format_time(
                os.path.getmtime(file)), h_current, h_add, h_commit, file))
    write_file(data_index, file='.lgit/index')


def format_date_log(timestamp):
    year = int(timestamp[0: 4])
    moth = int(timestamp[4: 6])
    day = int(timestamp[6: 8])
    hour = int(timestamp[8: 10])
    minute = int(timestamp[10: 12])
    second = int(timestamp[12: 14])
    # create Epoch time
    date = mktime((year, moth, day, hour, minute, second, 0, 0, 0))
    return strftime("%a %b %d %H:%M:%S %Y", localtime(date))


def log_git():
    for commit in sorted(os.listdir(".lgit/commits"), key=str, reverse=True):
        time_commit, author, message = get_info_commit(commit)
        date = format_date_log(time_commit)
        print("commit %s\nAuthor: %s\nDate: %s\n\n\t%s\n\n" %
              (commit, author, date, message))


def get_info_commit(commit):
    data = read_file(os.path.join(".lgit/commits", commit))
    # format time commit, author, message commit
    return data[1].strip(), data[0].strip(), data[3].strip()


def ls_files_git():
    files = get_trackfile_cwd(get_tracked_files())
    if files:
        print("\n".join(sorted(files, key=str)))


def get_trackfile_cwd(tracked_files):
    file_current = []
    for file in tracked_files:
        path = format_path(file, mode='relative')
        if not path.startswith('../'):
            file_current.append(path)
    return file_current


def rm_git(files):
    files_new = handle_raw_input(files)
    if files_new:
        data_index = read_file(file='.lgit/index')
        location = get_pos_track(files_new)
        for file in files_new:
            line = location.get(file, -1)  # get location of file
            # if not in index file print error
            if line != -1:
                if os.path.exists(file):
                    os.remove(file)
                    remove_empty_dirs(file)
                data_index[line] = ""
            else:
                print("fatal: pathspec '" + file + "' did not match any files")
        write_file(data_index, file='.lgit/index')
    elif not files:
        print('missing argument of file to removed')


def remove_empty_dirs(path):
    head, _ = os.path.split(path)
    # remove directory if it empty directory
    while head:
        if os.listdir(head):
            return
        os.rmdir(head)
        head, _ = os.path.split(head)


def init_git():
    direcs = ('.lgit/objects', '.lgit/commits', '.lgit/snapshots')
    files = ('.lgit/index', '.lgit/config')
    init_d = [d for d in direcs if not os.path.isdir(d)]
    init_f = [f for f in files if not os.path.isfile(f)]
    if not os.path.exists('.lgit'):
        os.mkdir('.lgit')
    elif os.path.isfile('.lgit'):
        print('fatal: Invalid gitfile format: .lgit')
        return
    for d in init_d:
        if os.path.isfile(d):
            print(os.path.join(os.getcwd(), dir) + ": Not a directory")
        else:
            os.mkdir(d)
    for f in init_f:
        if not os.path.isdir(f):
            open(f, 'w').close()
        else:
            print('error: unable to mmap ' + os.path.join(os.getcwd(), f)
                  + ' Is a directory')
    config_author(os.environ.get('LOGNAME'))
    if len(init_f) + len(init_d) < 5:
        print('Git repository already initialized.')


def config_author(name):
    write_file(['%s\n' % (name)], file='.lgit/config')


def find_parent_git():
    global cwd_path
    cwd_path = os.getcwd()
    while os.getcwd() != "/":
        if os.path.exists('.lgit/'):
            return True
        os.chdir('../')
    return False


def format_path(path, mode):
    if mode == 'absolute':
        return os.path.abspath(os.path.join(cwd_path, path))
    elif mode == 'relative':
        return os.path.relpath(os.path.join(os.getcwd(), path), start=cwd_path)


def format_time(timestamp, second=True):
    timestamp = datetime.fromtimestamp(timestamp)
    if second:
        return timestamp.strftime('%Y%m%d%H%M%S')
    return timestamp.strftime('%Y%m%d%H%M%S.%f')


# get string format index
def format_index(timestamp, current, add, commit, path):
    return '%s %s %s %40s %s\n' % (timestamp, current, add, commit, path)


def get_args():
    parser = ArgumentParser(prog="lgit")
    parser.add_argument('command', help="command options")
    parser.add_argument('files', nargs="*",
                        help=" Add file contents to the index")
    parser.add_argument('-m', '--message',
                        help="description about what you do")
    parser.add_argument('--author', help="set author for commit",)
    return parser.parse_args()


def main():
    args = get_args()
    try:
        if args.command == 'init':
            init_git()
        elif find_parent_git():
            if args.command == 'add':
                add_git(args.files)
            elif args.command == 'status':
                status_git()
            elif args.command == 'commit':
                commit_git(args.message)
            elif args.command == 'config':
                config_author(args.author)
            elif args.command == 'ls-files':
                ls_files_git()
            elif args.command == 'log':
                log_git()
            elif args.command == 'rm':
                rm_git(args.files)
            else:
                print("Git: '" + args.command + "' is not a git command.")
        else:
            print('fatal: not a git repository (or any \
of the parent directories)')
    except FileNotFoundError:
        print('fatal: not a git repository (or any of the parent directories)')
    except IsADirectoryError:
        pass


if __name__ == '__main__':
    main()
