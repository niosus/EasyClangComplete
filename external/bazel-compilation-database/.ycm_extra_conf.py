#!/usr/bin/python

# Copyright 2018 GRAIL, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Configuration file for YouCompleteMe to fetch C++ compilation flags from
Bazel.

See https://valloric.github.io/YouCompleteMe/#c-family-semantic-completion for
how YCM works. In that section:
For Option 1 (compilation database), use the generate.sh script in this
repository.
For Option 2 (.ycm_extra_conf.py), symlink this file to the root of your
workspace and bazel's output_base, or set it as your global config.
"""

from __future__ import print_function

import json
import os
import re
import shlex
import subprocess
import sys
import xml.etree.ElementTree as ElementTree


def bazel_info():
    """Returns a dict containing key values from bazel info."""

    bazel_info_dict = dict()
    try:
        out = subprocess.check_output(['bazel', 'info']).decode('utf-8').strip().split('\n')
    except subprocess.CalledProcessError as err:
        # This exit code is returned when this command is run outside of a bazel workspace.
        if err.returncode == 2:
            sys.exit(0)

    for line in out:
        key_val = line.strip().partition(": ")
        bazel_info_dict[key_val[0]] = key_val[2]

    return bazel_info_dict

def bazel_query(args):
    """Executes bazel query with the given args and returns the output."""

    # TODO: switch to cquery when it supports siblings and less crash-y with external repos.
    query_cmd = ['bazel', 'query'] + args
    proc = subprocess.Popen(query_cmd, stdout=subprocess.PIPE)
    return proc.communicate()[0].decode('utf-8')

def file_to_target(filepath):
    """Returns a string that works as a bazel target specification for the given file."""
    if not filepath.startswith("external/"):
        # The file path relative to repo root works for genfiles and binfiles too.
        return filepath

    # For external repos, we have to find the owner package manually.
    repo_prefix = re.sub('external/([^/]*).*', '@\\1//', filepath)
    filepath = re.sub('external/[^/]*/', '', filepath)

    # Find out which package is the owner of this file.
    query_result = bazel_query(['-k', repo_prefix+'...', '--output=package'])
    packages = [package.strip() for package in query_result.split('\n')]

    owner = ""
    for package in packages:
        package = package[len(repo_prefix):]
        if filepath.startswith(package) and len(package) > len(owner):
            owner = package

    return repo_prefix + owner + ":" + os.path.relpath(filepath, owner)

def standardize_file_target(file_target):
    """For file targets that are not source files, return the target that generated them.

    This is needed because rdeps of generated files do not include targets that reference
    their generating rules.
    https://github.com/bazelbuild/bazel/issues/4949
    """

    query_result = bazel_query(['--output=xml', file_target])
    if not query_result:
        sys.exit("Empty query response for {}. It is probably not handled by bazel".format(file_target))

    target_xml = ElementTree.fromstringlist(query_result.split('\n'))
    source_element = target_xml.find('source-file')
    if source_element is not None:
        return file_target

    generated_element = target_xml.find('generated-file')
    if generated_element is not None:
        return generated_element.get('generating-rule')

    sys.exit("Error parsing query xml for " + file_target + ":\n" + query_result)

def get_aspects_filepath(label, bazel_bin):
    """Gets the file path for the generated aspects file that contains the
    compile commands json entries.
    """

    target_path = re.sub(':', '/', label)
    target_path = re.sub('^@(.*)//', 'external/\\1/', target_path)
    target_path = re.sub('^/*', '', target_path)
    relative_file_path = target_path + '.compile_commands.json'
    return os.path.join(bazel_bin, *relative_file_path.split('/'))

def get_compdb_json(aspects_filepath, bazel_exec_root):
    """Returns the JSON string read from the file after necessary processing."""

    compdb_json_str = "[\n"
    with open(aspects_filepath, 'r') as aspects_file:
        compdb_json_str += aspects_file.read()
    compdb_json_str += "\n]"
    return re.sub('__EXEC_ROOT__', bazel_exec_root, compdb_json_str)

def get_flags(filepath, compdb_json_str):
    """Gets the compile command flags from the compile command for the file."""

    compdb_dict = json.loads(compdb_json_str)
    for entry in compdb_dict:
        if entry['file'] != filepath:
            continue
        command = entry['command']
        return shlex.split(command)[1:]

    # This could imply we are fetching the wrong compile_commands.json or there
    # is a bug in aspects.bzl.
    sys.exit("File {f} not present in the compilation database".format(f=filepath))

def standardize_flags(flags, bazel_workspace):
    """Modifies flags obtained from the compile command for compilation outside of bazel."""

    # We need to add the workspace directly because the files symlinked in the
    # execroot during a build disappear after a different build action.
    flags.extend(['-iquote', bazel_workspace])

    return flags

def cfamily_settings(filename):
    """Returns C-family settings as a dict with at least a 'flags' key that
    points to an array of strings as flags.
    """

    bazel_info_dict = bazel_info()
    bazel_bin = bazel_info_dict['bazel-bin']
    bazel_genfiles = bazel_info_dict['bazel-genfiles']
    bazel_exec_root = bazel_info_dict['execution_root']
    bazel_workspace = bazel_info_dict['workspace']

    os.chdir(bazel_workspace)
    # Valid prefixes for the file, in decreasing order of specificity.
    file_prefix = [p for p in [bazel_genfiles, bazel_bin, bazel_exec_root, bazel_workspace]
                   if filename.startswith(p)]
    if not file_prefix:
        sys.exit("Not a valid file: " + filename)

    filepath = os.path.relpath(filename, file_prefix[0])
    file_target = standardize_file_target(file_to_target(filepath))

    # File path relative to execroot, as it will appear in the compile command.
    if file_prefix[0].startswith(bazel_exec_root):
        filepath = os.path.relpath(filename, bazel_exec_root)

    cc_rules = "cc_(library|binary|test|inc_library|proto_library)"
    query_result = bazel_query([('kind("{cc_rules}", rdeps(siblings({f}), {f}, 1))'
                                 .format(f=file_target, cc_rules=cc_rules)), '--keep_going'])

    labels = [label.partition(" ")[0] for label in query_result.split('\n') if label]

    if not labels:
        sys.exit("No cc rules depend on this source file.")

    repository_override = '--override_repository=bazel_compdb=' + os.path.dirname(
        os.path.realpath(__file__))

    aspect_definition = '--aspects=@bazel_compdb//:aspects.bzl%compilation_database_aspect'

    bazel_aspects = [
        'bazel',
        'build',
        aspect_definition,
        repository_override,
        '--output_groups=compdb_files',
    ] + labels
    proc = subprocess.Popen(bazel_aspects, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = proc.communicate()
    if proc.returncode != 0:
        errors = [e for e in out.splitlines() + err.splitlines()
                  if e.startswith("ERROR:")]
        if errors:
            raise Exception('/'.join(errors))
        else:
            raise Exception(err)

    aspects_filepath = get_aspects_filepath(labels[0], bazel_bin)

    compdb_json = get_compdb_json(aspects_filepath, bazel_exec_root)
    flags = standardize_flags(get_flags(filepath, compdb_json), bazel_workspace)

    return {
        'flags': flags,
        'include_paths_relative_to_dir': bazel_exec_root,
        }

#pylint: disable=C0103
def Settings(**kwargs):
    """Function that is called by YCM with language and filename arguments,
    and expects a dict of language-specific settings.
    """
    if kwargs['language'] == 'cfamily':
        return cfamily_settings(kwargs['filename'])
    return {}

# For testing; needs exactly one argument as path of file.
if __name__ == '__main__':
    filename = os.path.abspath(sys.argv[1])
    print(Settings(language='cfamily', filename=filename))
