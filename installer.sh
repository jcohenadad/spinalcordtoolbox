#!/bin/bash
#
# Installer for spinal cord toolbox.
#
# This script will install the spinal cord toolbox under and configure your environment.
# Must be run as an administrator.
# Installation location: /usr/local/spinalcordtoolbox/

# parameters
#PATH_INSTALL="/usr/local/"
SCT_DIR="/usr/local/spinalcordtoolbox"

echo

# check if user is sudoer
if [ "$(whoami)" != "root" ]; then
  echo "Sorry, you are not root. Please type: sudo ./installer"
  echo
  exit 1
fi

# check if folder already exists - if so, delete it
echo
echo "Check if spinalcordtoolbox is already installed (if so, delete it)..."
if [ -e "${SCT_DIR}" ]; then
  cmd="rm -rf ${SCT_DIR}"
  echo ">> $cmd"; $cmd
fi

# create folder
echo
echo "Create folder: /usr/local/spinalcordtoolbox..."
cmd="mkdir ${SCT_DIR}"
echo ">> $cmd"; $cmd

# copy files
echo
echo "Copy toolbox..."
cmd="cp -r spinalcordtoolbox/ ${SCT_DIR}"
echo ">> $cmd"; $cmd

# copy testing files
echo
echo "Copy example data & scripts..."
if [ -e "../sct_testing" ]; then
  cmd="rm -rf ../sct_testing"
  echo ">> $cmd"; $cmd
fi
cmd="mkdir ../sct_testing"
echo ">> $cmd"; $cmd
cmd="cp -r spinalcordtoolbox/testing/ ../sct_testing"
echo ">> $cmd"; $cmd
cmd="chmod -R 775 ../sct_testing"
echo ">> $cmd"; $cmd

# edit bash_profile
# check if .bash_profile was already modified
echo
echo "Edit .bash_profile..."
if grep -q "SPINALCORDTOOLBOX" ~/.bash_profile; then
  echo "  .bash_profile was already modified previously."
else
  echo '' >> ~/.bash_profile
  echo '# SPINALCORDTOOLBOX' >> ~/.bash_profile
  echo "SCT_DIR=\"${SCT_DIR}\"" >> ~/.bash_profile
  echo 'export PATH=${PATH}:$SCT_DIR/bin/OSX_10.6-7-8' >> ~/.bash_profile
  echo 'export PATH=${PATH}:$SCT_DIR/scripts' >> ~/.bash_profile
  echo 'export DYLD_LIBRARY_PATH=${SCT_DIR}/lib:$DYLD_LIBRARY_PATH' >> ~/.bash_profile
  echo 'export SCT_DIR PATH' >> ~/.bash_profile
fi

# check if other dependent software are installed
echo
echo "Check if other dependent software are installed..."
cmd="python ${SCT_DIR}/scripts/sct_check_library_existence.py"
echo ">> $cmd"; $cmd

# display stuff
echo
echo "---"
echo "Done! you can now delete this folder."
echo "To see all commands available, type \"sct\" then backslash"
echo "To get more info about the toolbox, please see /usr/local/spinalcordtoolbox/README.txt"
echo "To get started, look at the created folder: \"sct_testing\""
echo "Please send your comments here: http://sourceforge.net/p/spinalcordtoolbox/discussion/"
echo "Enjoy :-)"
echo "---"
echo