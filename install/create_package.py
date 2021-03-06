#!/usr/bin/env python
#
# Create package with appropriate version number.
#
# Author: Julien Cohen-Adad, Benjamin De Leener
#

# TODO: remove quick fix with folder_sct_temp

import os
import getopt
import sys
from numpy import loadtxt
sys.path.append('../scripts')
import sct_utils as sct

#=======================================================================================================================
# usage
#=======================================================================================================================
def usage():
    print 'USAGE: \n' \
        ''+os.path.basename(__file__)+'\n' \
        '~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~\n' \
        'Part of the Spinal Cord Toolbox <https://sourceforge.net/projects/spinalcordtoolbox>\n' \
        '\n'\
        'DESCRIPTION\n' \
        '  Create a package of the Spinal Cord Toolbox.\n' \
        '\n' \
        'USAGE\n' \
        '  '+os.path.basename(__file__)+'\n' \
        '\n' \
        'MANDATORY ARGUMENTS\n' \
        '  -s <OS name>      name of the OS {osx,debian}.\n' \
        '\n'\
        'EXAMPLE:\n' \
        '  create_package.py -s debian\n'
    sys.exit(2)

listOS = ['osx', 'debian']
OSname = ''
# Check input param
try:
    opts, args = getopt.getopt(sys.argv[1:],'hs:')
except getopt.GetoptError as err:
    print str(err)
    usage()
for opt, arg in opts:
    if opt == '-h':
        usage()
    elif opt in ('-s'):
        OSname = str(arg)

if OSname not in listOS:
    print 'ERROR: OS name should be one of the following: '+'[%s]' % ', '.join(map(str,listOS))
    usage()

# get version
with open ("../version.txt", "r") as myfile:
    version = myfile.read().replace('\n', '')

# create output folder
folder_sct = '../spinalcordtoolbox_v'+version+'_'+OSname+'/'
if os.path.exists(folder_sct):
    sct.run('rm -rf '+folder_sct)
sct.run('mkdir '+folder_sct)

# copy folders
sct.run('mkdir '+folder_sct+'spinalcordtoolbox')
sct.run('cp installer.sh '+folder_sct)
sct.run('cp ../README.md '+folder_sct+'spinalcordtoolbox/')
sct.run('cp ../LICENSE '+folder_sct+'spinalcordtoolbox/')
sct.run('cp ../version.txt '+folder_sct+'spinalcordtoolbox/')
sct.run('cp -r ../flirtsch '+folder_sct+'spinalcordtoolbox/')
sct.run('cp -r ../scripts '+folder_sct+'spinalcordtoolbox/')
sct.run('mkdir '+folder_sct+'spinalcordtoolbox/bin')
if OSname == 'osx':
    sct.run('cp -r ../bin/osx/* '+folder_sct+'spinalcordtoolbox/bin/')
    sct.run('cp -r osx/ants/* '+folder_sct+'spinalcordtoolbox/bin/')
    sct.run('cp -r osx/c3d/* '+folder_sct+'spinalcordtoolbox/bin/')
elif OSname == 'debian':
    sct.run('cp -r ../bin/debian/* '+folder_sct+'spinalcordtoolbox/bin/')
    sct.run('cp -r debian/ants/* '+folder_sct+'spinalcordtoolbox/bin/')
    sct.run('cp -r debian/c3d/* '+folder_sct+'spinalcordtoolbox/bin/')

# copy colormap
sct.run('mkdir '+folder_sct+'spinalcordtoolbox/data/')
sct.run('cp -rf ../data/colormap '+folder_sct+'spinalcordtoolbox/data/')

# copy atlas
sct.run('mkdir '+folder_sct+'spinalcordtoolbox/data/atlas')
sct.run('ls ../data/atlas/vol*.* | while read F; do cp $F '+folder_sct+'spinalcordtoolbox/data/atlas/; done')
sct.run('cp ../data/atlas/list.txt '+folder_sct+'spinalcordtoolbox/data/atlas/')

# copy spinal_level
sct.run('mkdir '+folder_sct+'spinalcordtoolbox/data/spinal_level')
sct.run('cp -rf ../data/spinal_level '+folder_sct+'spinalcordtoolbox/data/')

# copy template
sct.run('mkdir '+folder_sct+'spinalcordtoolbox/data/template')
sct.run('cp ../data/template/MNI-Poly-AMU_T2.nii.gz '+folder_sct+'spinalcordtoolbox/data/template/')
sct.run('cp ../data/template/landmarks_center.nii.gz '+folder_sct+'spinalcordtoolbox/data/template/')
sct.run('cp ../data/template/mask_gaussian_templatespace_sigma20.nii.gz '+folder_sct+'spinalcordtoolbox/data/template/')
sct.run('cp ../data/template/MNI-Poly-AMU_cord.nii.gz '+folder_sct+'spinalcordtoolbox/data/template/')
sct.run('cp ../data/template/MNI-Poly-AMU_CSF.nii.gz '+folder_sct+'spinalcordtoolbox/data/template/')
sct.run('cp ../data/template/MNI-Poly-AMU_GM.nii.gz '+folder_sct+'spinalcordtoolbox/data/template/')
sct.run('cp ../data/template/MNI-Poly-AMU_level.nii.gz '+folder_sct+'spinalcordtoolbox/data/template/')
sct.run('cp ../data/template/MNI-Poly-AMU_seg.nii.gz '+folder_sct+'spinalcordtoolbox/data/template/')
sct.run('cp ../data/template/MNI-Poly-AMU_WM.nii.gz '+folder_sct+'spinalcordtoolbox/data/template/')
sct.run('cp ../data/template/version.txt '+folder_sct+'spinalcordtoolbox/data/template/')

# testing
sct.run('mkdir '+folder_sct+'spinalcordtoolbox/testing')

# testing - sct_segmentation_propagation
sct.run('mkdir '+folder_sct+'spinalcordtoolbox/testing/sct_segmentation_propagation')
sct.run('cp ../testing/sct_segmentation_propagation/test_sct_segmentation_propagation.sh '+folder_sct+'spinalcordtoolbox/testing/sct_segmentation_propagation/')
sct.run('cp -r ../testing/sct_segmentation_propagation/snapshots '+folder_sct+'spinalcordtoolbox/testing/sct_segmentation_propagation/')

# testing - sct_register_to_template
sct.run('mkdir '+folder_sct+'spinalcordtoolbox/testing/sct_register_to_template')
sct.run('cp ../testing/sct_register_to_template/test_sct_register_to_template.sh '+folder_sct+'spinalcordtoolbox/testing/sct_register_to_template/')

# testing - sct_register_multimodal
sct.run('mkdir '+folder_sct+'spinalcordtoolbox/testing/sct_register_multimodal')
sct.run('cp ../testing/sct_register_multimodal/test_sct_register_multimodal.sh '+folder_sct+'spinalcordtoolbox/testing/sct_register_multimodal/')
sct.run('cp -r ../testing/sct_register_multimodal/snapshots '+folder_sct+'spinalcordtoolbox/testing/sct_register_multimodal/')
sct.run('cp -r ../testing/sct_register_multimodal/check_integrity '+folder_sct+'spinalcordtoolbox/testing/sct_register_multimodal/')

# testing - sct_warp_atlas2metric
sct.run('mkdir '+folder_sct+'spinalcordtoolbox/testing/sct_warp_atlas2metric')
sct.run('cp ../testing/sct_warp_atlas2metric/test_sct_warp_atlas2metric.sh '+folder_sct+'spinalcordtoolbox/testing/sct_warp_atlas2metric/')
sct.run('cp -r ../testing/sct_warp_atlas2metric/snapshots '+folder_sct+'spinalcordtoolbox/testing/sct_warp_atlas2metric/')

# testing - sct_estimate_MAP_tracts
sct.run('mkdir '+folder_sct+'spinalcordtoolbox/testing/sct_estimate_MAP_tracts')
sct.run('cp ../testing/sct_estimate_MAP_tracts/test_sct_estimate_MAP_tracts.sh '+folder_sct+'spinalcordtoolbox/testing/sct_estimate_MAP_tracts/')

# testing - data
sct.run('mkdir '+folder_sct+'spinalcordtoolbox/testing/data')
sct.run('cp -r ../testing/data/errsm_23 '+folder_sct+'spinalcordtoolbox/testing/data/')

# remove .DS_Store files
sct.run('find '+folder_sct+' -type f -name .DS_Store -delete')

# remove AppleDouble files - doesn't work on Linux
if OSname == 'osx':
    sct.run('find '+folder_sct+' -type d | xargs dot_clean -m')

# remove pycharm files
sct.run('rm '+folder_sct+'spinalcordtoolbox/scripts/*.pyc')
if os.path.exists(folder_sct+'spinalcordtoolbox/scripts/.idea'):
    sct.run('rm -rf '+folder_sct+'spinalcordtoolbox/scripts/.idea')

# go to parent directory to be able to tar without de-tarring error in mac OSX
os.chdir('../')

# compress folder
folder_sct_temp = 'spinalcordtoolbox_v'+version+'_'+OSname+'/'

sct.run('tar -cvzf spinalcordtoolbox_v'+version+'_'+OSname+'.tar.gz '+folder_sct_temp)

print "done!\n"


