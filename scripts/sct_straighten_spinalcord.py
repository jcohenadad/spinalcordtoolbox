#!/usr/bin/env python

## @package sct_straighten_spinalcord
#
# - from spinal cord centerline (as nifti format), estimate deformation field with ANTS.
#
#
# Description about how the function works:
# This program takes as input an anatomic image and the centerline or segmentation of its spinal cord (that you can get
# using sct_get_centerline.py or sct_segmentation_propagation) and returns the anatomic image where the spinal
# cord was straightened.
#
#
# USAGE
# ---------------------------------------------------------------------------------------
# sct_straighten_spinalcord.py -i <data> -c <centerline>
#
# MANDATORY ARGUMENTS
# ---------------------------------------------------------------------------------------
#   -i       input volume.
#   -c       centerline (generated with sct_get_centerline).
#
# OPTIONAL ARGUMENTS
# ---------------------------------------------------------------------------------------
#
#   -f       'polynomial' or 'splines' fitting default is 'splines'
#
# EXAMPLES
# ---------------------------------------------------------------------------------------
#   sct_straighten_spinalcord.py -i t2.nii.gz -c centerline.nii.gz
#
#
# DEPENDENCIES
# ---------------------------------------------------------------------------------------
# EXTERNAL PYTHON PACKAGES
# - nibabel: <http://nipy.sourceforge.net/nibabel/>
# - numpy: <http://www.numpy.org>
# - sympy : <http://sympy.org/fr/index.html>
# EXTERNAL SOFTWARE
# - FSL: <http://fsl.fmrib.ox.ac.uk/fsl/>
# - ANTS
#
#
# ---------------------------------------------------------------------------------------
# Copyright (c) 2013 NeuroPoly, Polytechnique Montreal <www.neuro.polymtl.ca>
# Authors: Julien Cohen-Adad, Geoffrey Leveque, Julien Touati
# Modified: 2014-06-03
#
# License: see the LICENSE.TXT
#=======================================================================================================================


# TODO: fix bug of label creation when using splines (2014-06-05: error with data from Falk with small FOV along z)
# TODO: generate cross at both edge (top and bottom) and populate in between --> this will ensure better quality of the warping field.
# TODO: check if there is an overlap of labels, in case of high curvature and high density of cross along z.
# TODO: convert gap definition to mm (more intuitive than voxel)

# 2014-06-06: corrected bug related to small FOV volumes Solution: reduced spline order (3), computation of a lot of point (1000)

## Create a structure to pass important user parameters to the main function
class param:
    ## The constructor
    def __init__(self):
        self.debug = 0
        self.deg_poly = 10 # maximum degree of polynomial function for fitting centerline.
        self.gapxy = 20 # size of cross in x and y direction for the landmarks
        self.gapz = 15 # gap between landmarks along z
        self.padding = 30 # pad input volume in order to deal with the fact that some landmarks might be outside the FOV due to the curvature of the spinal cord
        self.fitting_method = 'splines' # splines | polynomial
        self.remove_temp_files = 1 # remove temporary files

# check if needed Python libraries are already installed or not
import os
import getopt
import commands
import sys
import sct_utils as sct
from sct_utils import fsloutput
from sct_nurbs import NURBS
import nibabel
import numpy
from scipy import interpolate # TODO: check if used
from sympy.solvers import solve
from sympy import Symbol

# check if dependant software are installed
sct.check_if_installed('flirt -help','FSL')
sct.check_if_installed('WarpImageMultiTransform -h','ANTS')



#=======================================================================================================================
# main
#=======================================================================================================================
def main():
    
    # Initialization
    fname_anat = ''
    fname_centerline = ''
    gapxy = param.gapxy
    gapz = param.gapz
    padding = param.padding
    remove_temp_files = param.remove_temp_files
    interpolation_warp = ''
    centerline_fitting = param.fitting_method
    
    # get path of the toolbox
    status, path_sct = commands.getstatusoutput('echo $SCT_DIR')
    print path_sct
    # extract path of the script
    path_script = os.path.dirname(__file__)+'/'
    
    # Parameters for debug mode
    if param.debug == 1:
        print '\n*** WARNING: DEBUG MODE ON ***\n'
        fname_anat = path_sct+'/testing/data/11shortFOV/t1_cropped_short.nii.gz'
        fname_centerline = path_sct+'/testing/data/11shortFOV/spine_cropped_short.nii.gz'
        # fname_anat = path_script+'../testing/sct_straighten_spinalcord/data/errsm_22_t2_cropped_rpi.nii.gz'
        # fname_centerline = path_script+'../testing/sct_straighten_spinalcord/data/errsm_22_t2_cropped_centerline.nii.gz'
        remove_temp_files = 0
        centerline_fitting = 'splines'
        import matplotlib.pyplot as plt
        from mpl_toolkits.mplot3d import Axes3D
    
    # Check input param
    try:
        opts, args = getopt.getopt(sys.argv[1:],'hi:c:r:w:f:')
    except getopt.GetoptError as err:
        print str(err)
        usage()
    for opt, arg in opts:
        if opt == '-h':
            usage()
        elif opt in ('-i'):
            fname_anat = arg
        elif opt in ('-c'):
            fname_centerline = arg
        elif opt in ('-r'):
            remove_temp_files = int(arg)
        elif opt in ('-w'):
            interpolation_warp = str(arg)
        elif opt in ('-f'):
            centerline_fitting = str(arg)
    
    
    
    # display usage if a mandatory argument is not provided
    if fname_anat == '' or fname_centerline == '':
        usage()
    
    # Display usage if optional arguments are not correctly provided
    if centerline_fitting == '':
        centerline_fitting = 'splines'
    elif not centerline_fitting == '' and not centerline_fitting == 'splines' and not centerline_fitting == 'polynomial':
        print '\n \n -f argument is not valid \n \n'
        usage()
    
    # check existence of input files
    sct.check_file_exist(fname_anat)
    sct.check_file_exist(fname_centerline)
    
    # Extract path/file/extension of the input image
    path_anat, file_anat, ext_anat = sct.extract_fname(fname_anat)
    # Extract path/file/extension of the centerline
    path_centerline, file_centerline, ext_centerline = sct.extract_fname(fname_centerline)
    
    # Display arguments
    print '\nCheck input arguments...'
    print '  Input volume ...................... '+fname_anat
    print '  Centerline ........................ '+fname_centerline
    print '  Centerline fitting option ......... '+centerline_fitting
    
    
    
    # Open centerline
    #==========================================================================================
    # Change orientation of the input centerline into RPI
    print '\nOrient centerline to RPI orientation...'
    fname_centerline_orient = 'tmp.centerline_rpi' + ext_centerline
    sct.run('sct_orientation -i ' + fname_centerline + ' -o ' + fname_centerline_orient + ' -orientation RPI')
    
    print '\nGet dimensions of input centerline...'
    nx, ny, nz, nt, px, py, pz, pt = sct.get_dimension(fname_centerline_orient)
    print '.. matrix size: '+str(nx)+' x '+str(ny)+' x '+str(nz)
    print '.. voxel size:  '+str(px)+'mm x '+str(py)+'mm x '+str(pz)+'mm'
    
    print '\nOpen centerline volume...'
    file = nibabel.load(fname_centerline_orient)
    data = file.get_data()
    
    # loop across z and associate x,y coordinate with the point having maximum intensity
    x_centerline = [0 for iz in range(0, nz, 1)]
    y_centerline = [0 for iz in range(0, nz, 1)]
    z_centerline = [iz for iz in range(0, nz, 1)]
    x_centerline_deriv = [0 for iz in range(0, nz, 1)]
    y_centerline_deriv = [0 for iz in range(0, nz, 1)]
    z_centerline_deriv = [0 for iz in range(0, nz, 1)]
    
    # Two possible scenario:
    # 1. the centerline is probabilistic: each slice contains voxels with the probability of containing the centerline [0:...:1]
    # We only take the maximum value of the image to aproximate the centerline.
    # 2. The centerline/segmentation image contains many pixels per slice with values {0,1}.
    # We take all the points and approximate the centerline on all these points.
    
    x_seg_start, y_seg_start = (data[:,:,0]>0).nonzero()
    x_seg_end, y_seg_end = (data[:,:,-1]>0).nonzero()
    # check if centerline covers all the image
    if len(x_seg_start)==0 or len(x_seg_end)==0:
        print '\nERROR: centerline/segmentation must cover all "z" slices of the input image.\n' \
              'To solve the problem, you need to crop the input image (you can use \'sct_crop_image\') and generate one' \
              'more time the spinal cord centerline/segmentation from this cropped image.\n'
        usage()
    
    X, Y, Z = ((data<1)*(data>0)).nonzero() # X is empty if binary image
    if (len(X) > 0): # Scenario 1
        for iz in range(0, nz, 1):
            x_centerline[iz], y_centerline[iz] = numpy.unravel_index(data[:,:,iz].argmax(), data[:,:,iz].shape)
    else: # Scenario 2
        for iz in range(0, nz, 1):
            x_seg, y_seg = (data[:,:,iz]>0).nonzero()
            x_centerline[iz] = numpy.mean(x_seg)
            y_centerline[iz] = numpy.mean(y_seg)
    
    # TODO: find a way to do the previous loop with this, which is more neat:
    # [numpy.unravel_index(data[:,:,iz].argmax(), data[:,:,iz].shape) for iz in range(0,nz,1)]
#    plt.plot(y_centerline,z_centerline)
#    plt.show()


    # clear variable
    del data
    
    
    # Fit the centerline points with the kind of curve given as argument of the script and return the new fitted coordinates
    if centerline_fitting == 'splines':
        x_centerline_fit, y_centerline_fit,x_centerline_deriv,y_centerline_deriv,z_centerline_deriv = b_spline_centerline(x_centerline,y_centerline,z_centerline)
    elif centerline_fitting == 'polynomial':
        x_centerline_fit, y_centerline_fit,polyx,polyy = polynome_centerline(x_centerline,y_centerline,z_centerline)

#    plt.plot(y_centerline,z_centerline)
#    plt.plot(y_centerline_fit,z_centerline)
#    plt.show()

    
    # Get coordinates of landmarks along curved centerline
    #==========================================================================================
    print '\nGet coordinates of landmarks along curved centerline...'
    # landmarks are created along the curved centerline every z=gapz. They consist of a "cross" of size gapx and gapy.
    
    # find derivative of polynomial
    step_z = round(nz/gapz)
    #iz_curved = [i for i in range (0, nz, gapz)]
    iz_curved = [i*step_z for i in range (0, gapz)]
    iz_curved.append(nz-1)     
    #print iz_curved, len(iz_curved)
    n_iz_curved = len(iz_curved)
    #print n_iz_curved
    landmark_curved = [ [ [ 0 for i in range(0,3)] for i in range(0,5) ] for i in iz_curved ]
    # print x_centerline_deriv,len(x_centerline_deriv)
    # landmark[a][b][c]
    #   a: index along z. E.g., the first cross with have index=0, the next index=1, and so on...
    #   b: index of element on the cross. I.e., 0: center of the cross, 1: +x, 2 -x, 3: +y, 4: -y
    #   c: dimension, i.e., 0: x, 1: y, 2: z
    # loop across index, which corresponds to iz (points along the centerline)
    
    if centerline_fitting=='polynomial':
        for index in range(0, n_iz_curved, 1):
            # set coordinates for landmark at the center of the cross
            landmark_curved[index][0][0], landmark_curved[index][0][1], landmark_curved[index][0][2] = x_centerline_fit[iz_curved[index]], y_centerline_fit[iz_curved[index]], iz_curved[index]
            # set x and z coordinates for landmarks +x and -x
            landmark_curved[index][1][2], landmark_curved[index][1][0], landmark_curved[index][2][2], landmark_curved[index][2][0] = get_points_perpendicular_to_curve(polyx, polyx.deriv(), iz_curved[index], gapxy)
            # set y coordinate to y_centerline_fit[iz] for elements 1 and 2 of the cross
            for i in range(1,3):
                landmark_curved[index][i][1] = y_centerline_fit[iz_curved[index]]
            # set coordinates for landmarks +y and -y. Here, x coordinate is 0 (already initialized).
            landmark_curved[index][3][2], landmark_curved[index][3][1], landmark_curved[index][4][2], landmark_curved[index][4][1] = get_points_perpendicular_to_curve(polyy, polyy.deriv(), iz_curved[index], gapxy)
            # set x coordinate to x_centerline_fit[iz] for elements 3 and 4 of the cross
            for i in range(3,5):
                landmark_curved[index][i][0] = x_centerline_fit[iz_curved[index]]
    
    elif centerline_fitting=='splines':
        for index in range(0, n_iz_curved, 1):
            # calculate d (ax+by+cz+d=0)
            # print iz_curved[index]
            a=x_centerline_deriv[iz_curved[index]]
            b=y_centerline_deriv[iz_curved[index]]
            c=z_centerline_deriv[iz_curved[index]]
            x=x_centerline_fit[iz_curved[index]]
            y=y_centerline_fit[iz_curved[index]]
            z=iz_curved[index]
            d=-(a*x+b*y+c*z)
            #print a,b,c,d,x,y,z
            # set coordinates for landmark at the center of the cross
            landmark_curved[index][0][0], landmark_curved[index][0][1], landmark_curved[index][0][2] = x_centerline_fit[iz_curved[index]], y_centerline_fit[iz_curved[index]], iz_curved[index]
            
            # set y coordinate to y_centerline_fit[iz] for elements 1 and 2 of the cross
            for i in range(1,3):
                landmark_curved[index][i][1] = y_centerline_fit[iz_curved[index]]
            
            # set x and z coordinates for landmarks +x and -x, forcing de landmark to be in the orthogonal plan and the distance landmark/curve to be gapxy
            x_n=Symbol('x_n')
            landmark_curved[index][2][0],landmark_curved[index][1][0]=solve((x_n-x)**2+((-1/c)*(a*x_n+b*y+d)-z)**2-gapxy**2,x_n)  #x for -x and +x
            landmark_curved[index][1][2]=(-1/c)*(a*landmark_curved[index][1][0]+b*y+d)  #z for +x
            landmark_curved[index][2][2]=(-1/c)*(a*landmark_curved[index][2][0]+b*y+d)  #z for -x
            
            # set x coordinate to x_centerline_fit[iz] for elements 3 and 4 of the cross
            for i in range(3,5):
                landmark_curved[index][i][0] = x_centerline_fit[iz_curved[index]]
            
            # set coordinates for landmarks +y and -y. Here, x coordinate is 0 (already initialized).
            y_n=Symbol('y_n')
            landmark_curved[index][4][1],landmark_curved[index][3][1]=solve((y_n-y)**2+((-1/c)*(a*x+b*y_n+d)-z)**2-gapxy**2,y_n)  #y for -y and +y
            landmark_curved[index][3][2]=(-1/c)*(a*x+b*landmark_curved[index][3][1]+d)#z for +y
            landmark_curved[index][4][2]=(-1/c)*(a*x+b*landmark_curved[index][4][1]+d)#z for -y
    
    
#    #display
#    fig = plt.figure()
#    ax = fig.add_subplot(111, projection='3d')
#    ax.plot(x_centerline_fit, y_centerline_fit,z_centerline, 'g')
#    ax.plot(x_centerline, y_centerline,z_centerline, 'r')
#    ax.plot([landmark_curved[i][j][0] for i in range(0, n_iz_curved) for j in range(0, 5)], \
#           [landmark_curved[i][j][1] for i in range(0, n_iz_curved) for j in range(0, 5)], \
#           [landmark_curved[i][j][2] for i in range(0, n_iz_curved) for j in range(0, 5)], '.')
#    ax.set_xlabel('x')
#    ax.set_ylabel('y')
#    ax.set_zlabel('z')
#    plt.show()

    # Get coordinates of landmarks along straight centerline
    #==========================================================================================
    print '\nGet coordinates of landmarks along straight centerline...'
    landmark_straight = [ [ [ 0 for i in range(0,3)] for i in range (0,5) ] for i in iz_curved ] # same structure as landmark_curved
    
    # calculate the z indices corresponding to the Euclidean distance between two consecutive points on the curved centerline (approximation curve --> line)
    iz_straight = [0 for i in range (0,gapz+1)]
    #print iz_straight,len(iz_straight)
    for index in range(1, n_iz_curved, 1):
        # compute vector between two consecutive points on the curved centerline
        vector_centerline = [x_centerline_fit[iz_curved[index]] - x_centerline_fit[iz_curved[index-1]], \
                             y_centerline_fit[iz_curved[index]] - y_centerline_fit[iz_curved[index-1]], \
                             iz_curved[index] - iz_curved[index-1]]
        # compute norm of this vector
        norm_vector_centerline = numpy.linalg.norm(vector_centerline, ord=2)
        # round to closest integer value
        norm_vector_centerline_rounded = int(round(norm_vector_centerline,0))
        # assign this value to the current z-coordinate on the straight centerline
        iz_straight[index] = iz_straight[index-1] + norm_vector_centerline_rounded
    
    # initialize x0 and y0 to be at the center of the FOV
    x0 = int(round(nx/2))
    y0 = int(round(ny/2))
    for index in range(0, n_iz_curved, 1):
        # set coordinates for landmark at the center of the cross
        landmark_straight[index][0][0], landmark_straight[index][0][1], landmark_straight[index][0][2] = x0, y0, iz_straight[index]
        # set x, y and z coordinates for landmarks +x
        landmark_straight[index][1][0], landmark_straight[index][1][1], landmark_straight[index][1][2] = x0 + gapxy, y0, iz_straight[index]
        # set x, y and z coordinates for landmarks -x
        landmark_straight[index][2][0], landmark_straight[index][2][1], landmark_straight[index][2][2] = x0-gapxy, y0, iz_straight[index]
        # set x, y and z coordinates for landmarks +y
        landmark_straight[index][3][0], landmark_straight[index][3][1], landmark_straight[index][3][2] = x0, y0+gapxy, iz_straight[index]
        # set x, y and z coordinates for landmarks -y
        landmark_straight[index][4][0], landmark_straight[index][4][1], landmark_straight[index][4][2] = x0, y0-gapxy, iz_straight[index]
    
    # # display
    # fig = plt.figure()
    # ax = fig.add_subplot(111, projection='3d')
    # #ax.plot(x_centerline_fit, y_centerline_fit,z_centerline, 'r')
    # ax.plot([landmark_straight[i][j][0] for i in range(0, n_iz_curved) for j in range(0, 5)], \
    #        [landmark_straight[i][j][1] for i in range(0, n_iz_curved) for j in range(0, 5)], \
    #        [landmark_straight[i][j][2] for i in range(0, n_iz_curved) for j in range(0, 5)], '.')
    # ax.set_xlabel('x')
    # ax.set_ylabel('y')
    # ax.set_zlabel('z')
    # plt.show()
    #
    
    # Create NIFTI volumes with landmarks
    #==========================================================================================
    # Pad input volume to deal with the fact that some landmarks on the curved centerline might be outside the FOV
    # N.B. IT IS VERY IMPORTANT TO PAD ALSO ALONG X and Y, OTHERWISE SOME LANDMARKS MIGHT GET OUT OF THE FOV!!!
    print '\nPad input volume to deal with the fact that some landmarks on the curved centerline might be outside the FOV...'
    sct.run('c3d '+fname_centerline_orient+' -pad '+str(padding)+'x'+str(padding)+'x'+str(padding)+'vox '+str(padding)+'x'+str(padding)+'x'+str(padding)+'vox 0 -o tmp.centerline_pad.nii.gz')
    
    # TODO: don't pad input volume: no need for that! instead, try to increase size of hdr when saving landmarks.
    
    # Open padded centerline for reading
    print '\nOpen padded centerline for reading...'
    file = nibabel.load('tmp.centerline_pad.nii.gz')
    data = file.get_data()
    hdr = file.get_header()
    
    # Create volumes containing curved and straight landmarks
    data_curved_landmarks = data * 0
    data_straight_landmarks = data * 0
    # initialize landmark value
    landmark_value = 1
    # Loop across cross index
    for index in range(0, n_iz_curved, 1):
        # loop across cross element index
        for i_element in range(0, 5, 1):
            # get x, y and z coordinates of curved landmark (rounded to closest integer)
            x, y, z = int(round(landmark_curved[index][i_element][0])), int(round(landmark_curved[index][i_element][1])), int(round(landmark_curved[index][i_element][2]))
            # attribute landmark_value to the voxel and its neighbours
            data_curved_landmarks[x+padding-1:x+padding+2, y+padding-1:y+padding+2, z+padding-1:z+padding+2] = landmark_value
            # get x, y and z coordinates of straight landmark (rounded to closest integer)
            x, y, z = int(round(landmark_straight[index][i_element][0])), int(round(landmark_straight[index][i_element][1])), int(round(landmark_straight[index][i_element][2]))
            # attribute landmark_value to the voxel and its neighbours
            data_straight_landmarks[x+padding-1:x+padding+2, y+padding-1:y+padding+2, z+padding-1:z+padding+2] = landmark_value
            # increment landmark value
            landmark_value = landmark_value + 1
    
    # Write NIFTI volumes
    hdr.set_data_dtype('uint32') # set imagetype to uint8 #TODO: maybe use int32
    print '\nWrite NIFTI volumes...'
    img = nibabel.Nifti1Image(data_curved_landmarks, None, hdr)
    nibabel.save(img, 'tmp.landmarks_curved.nii.gz')
    print '.. File created: tmp.landmarks_curved.nii.gz'
    img = nibabel.Nifti1Image(data_straight_landmarks, None, hdr)
    nibabel.save(img, 'tmp.landmarks_straight.nii.gz')
    print '.. File created: tmp.landmarks_straight.nii.gz'
    
    
    # Estimate deformation field by pairing landmarks
    #==========================================================================================
    
    # Dilate landmarks (because nearest neighbour interpolation will be later used, therefore some landmarks may "disapear" if they are single points)
    #print '\nDilate landmarks...'
    #sct.run(fsloutput+'fslmaths tmp.landmarks_curved.nii -kernel box 3x3x3 -dilD tmp.landmarks_curved_dilated -odt short')
    #sct.run(fsloutput+'fslmaths tmp.landmarks_straight.nii -kernel box 3x3x3 -dilD tmp.landmarks_straight_dilated -odt short')
    
    # Estimate rigid transformation
    print '\nEstimate rigid transformation between paired landmarks...'
    sct.run('ANTSUseLandmarkImagesToGetAffineTransform tmp.landmarks_straight.nii.gz tmp.landmarks_curved.nii.gz rigid tmp.curve2straight_rigid.txt')
    
    # Apply rigid transformation
    print '\nApply rigid transformation to curved landmarks...'
    sct.run('WarpImageMultiTransform 3 tmp.landmarks_curved.nii.gz tmp.landmarks_curved_rigid.nii.gz -R tmp.landmarks_straight.nii.gz tmp.curve2straight_rigid.txt --use-NN')
    
    # Estimate b-spline transformation curve --> straight
    print '\nEstimate b-spline transformation: curve --> straight...'
    sct.run('ANTSUseLandmarkImagesToGetBSplineDisplacementField tmp.landmarks_straight.nii.gz tmp.landmarks_curved_rigid.nii.gz tmp.warp_curve2straight.nii.gz 5x5x5 3 2 0')
    
    # Concatenate rigid and non-linear transformations...
    print '\nConcatenate rigid and non-linear transformations...'
    #sct.run('ComposeMultiTransform 3 tmp.warp_rigid.nii -R tmp.landmarks_straight.nii tmp.warp.nii tmp.curve2straight_rigid.txt')
    # TODO: use sct.run() when output from the following command will be different from 0 (currently there seem to be a bug)
    cmd = 'ComposeMultiTransform 3 tmp.curve2straight.nii.gz -R tmp.landmarks_straight.nii.gz tmp.warp_curve2straight.nii.gz tmp.curve2straight_rigid.txt'
    print('>> '+cmd)
    commands.getstatusoutput(cmd)
    
    # Estimate b-spline transformation straight --> curve
    # TODO: invert warping field instead of estimating a new one
    print '\nEstimate b-spline transformation: straight --> curve...'
    sct.run('ANTSUseLandmarkImagesToGetBSplineDisplacementField tmp.landmarks_curved_rigid.nii.gz tmp.landmarks_straight.nii.gz tmp.warp_straight2curve.nii.gz 5x5x5 3 2 0')
    
    # Concatenate rigid and non-linear transformations...
    print '\nConcatenate rigid and non-linear transformations...'
    #sct.run('ComposeMultiTransform 3 tmp.warp_rigid.nii -R tmp.landmarks_straight.nii tmp.warp.nii tmp.curve2straight_rigid.txt')
    # TODO: use sct.run() when output from the following command will be different from 0 (currently there seem to be a bug)
    cmd = 'ComposeMultiTransform 3 tmp.straight2curve.nii.gz -R tmp.landmarks_straight.nii.gz -i tmp.curve2straight_rigid.txt tmp.warp_straight2curve.nii.gz'
    print('>> '+cmd)
    commands.getstatusoutput(cmd)
    
    #print '\nPad input image...'
    #sct.run('c3d '+fname_anat+' -pad '+str(padz)+'x'+str(padz)+'x'+str(padz)+'vox '+str(padz)+'x'+str(padz)+'x'+str(padz)+'vox 0 -o tmp.anat_pad.nii')
    
    # Unpad landmarks...
    # THIS WAS REMOVED ON 2014-06-03 because the output data was cropped at the edge, which caused landmarks to sometimes disappear
    # print '\nUnpad landmarks...'
    # sct.run('fslroi tmp.landmarks_straight.nii.gz tmp.landmarks_straight_crop.nii.gz '+str(padding)+' '+str(nx)+' '+str(padding)+' '+str(ny)+' '+str(padding)+' '+str(nz))
    
    # Apply deformation to input image
    print '\nApply transformation to input image...'
    sct.run('WarpImageMultiTransform 3 '+fname_anat+' tmp.anat_rigid_warp.nii.gz -R tmp.landmarks_straight.nii.gz '+interpolation_warp+ ' tmp.curve2straight.nii.gz')
    # sct.run('WarpImageMultiTransform 3 '+fname_anat+' tmp.anat_rigid_warp.nii.gz -R tmp.landmarks_straight_crop.nii.gz '+interpolation_warp+ ' tmp.curve2straight.nii.gz')
    
    # Generate output file (in current folder)
    # TODO: do not uncompress the warping field, it is too time consuming!
    print '\nGenerate output file (in current folder)...'
    sct.generate_output_file('tmp.curve2straight.nii.gz','./','warp_curve2straight',ext_anat) # warping field
    sct.generate_output_file('tmp.straight2curve.nii.gz','./','warp_straight2curve',ext_anat) # warping field
    sct.generate_output_file('tmp.anat_rigid_warp.nii.gz','./',file_anat+'_straight',ext_anat) # straightened anatomic
    
    # Delete temporary files
    if remove_temp_files == 1:
        print '\nDelete temporary files...'
        sct.run('rm tmp.*')
    
    print '\nDone!\n'



#=======================================================================================================================
# get_points_perpendicular_to_curve
#=======================================================================================================================
# output: x1, y1, x2, y2
def get_points_perpendicular_to_curve(poly, dpoly, x, gap):
    # get a: slope of the line perpendicular to the tangent of the curve at a specific point
    if dpoly(x) != 0:
        a = -1/dpoly(x)
    else:
        print 'TODO: case of null derivative'
    # get y: ordinate that intersects the curve and the line
    y = poly(x)
    # convert slope to radian
    a_rad = numpy.arctan(a)
    # get coordinates of the two points on the line at a distance "gap" from the curve
    x1 = x + ( gap * numpy.cos(a_rad) * sct.sign(a_rad) )
    y1 = y + ( gap * numpy.sin(a_rad) * sct.sign(a_rad) )
    x2 = x - ( gap * numpy.cos(a_rad) * sct.sign(a_rad) )
    y2 = y - ( gap * numpy.sin(a_rad) * sct.sign(a_rad) )
    return x1, y1, x2, y2

#=======================================================================================================================
# B-Spline fitting
#=======================================================================================================================


def b_spline_centerline(x_centerline,y_centerline,z_centerline):
    """Give a better fitting of the centerline than the method 'spline_centerline' using b-splines"""
    
    print '\nFit centerline using B-spline approximation'
    points = [[x_centerline[n],y_centerline[n],z_centerline[n]] for n in range(len(x_centerline))]
    
    nurbs = NURBS(3,3000,points) # BE very careful with the spline order that you choose : if order is too high ( > 4 or 5) you need to set a higher number of Control Points (cf sct_nurbs ). For the third argument (number of points), give at least len(z_centerline)+500 or higher
    P = nurbs.getCourbe3D()
    x_centerline_fit=P[0]
    y_centerline_fit=P[1]
    Q = nurbs.getCourbe3D_deriv()
    x_centerline_deriv=Q[0]
    y_centerline_deriv=Q[1]
    z_centerline_deriv=Q[2]
    
    return x_centerline_fit, y_centerline_fit,x_centerline_deriv,y_centerline_deriv,z_centerline_deriv

#=======================================================================================================================
# Polynomial fitting
#=======================================================================================================================


def polynome_centerline(x_centerline,y_centerline,z_centerline):
    """Fit polynomial function through centerline"""
    
    # Fit centerline in the Z-X plane using polynomial function
    print '\nFit centerline in the Z-X plane using polynomial function...'
    coeffsx = numpy.polyfit(z_centerline, x_centerline, deg=param.deg_poly)
    polyx = numpy.poly1d(coeffsx)
    x_centerline_fit = numpy.polyval(polyx, z_centerline)
    
    #Fit centerline in the Z-Y plane using polynomial function
    print '\nFit centerline in the Z-Y plane using polynomial function...'
    coeffsy = numpy.polyfit(z_centerline, y_centerline, deg=param.deg_poly)
    polyy = numpy.poly1d(coeffsy)
    y_centerline_fit = numpy.polyval(polyy, z_centerline)
    
    
    return x_centerline_fit,y_centerline_fit,polyx,polyy



#=======================================================================================================================
# usage
#=======================================================================================================================
def usage():
    print '\n' \
        'sct_straighten_spinalcord\n' \
        '--------------------------------------------------------------------------------------------------------------\n' \
        'Part of the Spinal Cord Toolbox <https://sourceforge.net/projects/spinalcordtoolbox>\n' \
        '\n'\
        'DESCRIPTION\n' \
        '  This program takes as input an anatomic image and the centerline or segmentation of its spinal cord (that ' \
        'you can get using sct_get_centerline.py or sct_segmentation_propagation) and returns the anatomic image where' \
        'the spinal cord was straightened.\n' \
        '\n'\
        'USAGE\n' \
        '  sct_straighten_spinalcord.py -i <data> -c <centerline>\n' \
        '\n'\
        'MANDATORY ARGUMENTS\n' \
        '  -i           input volume.\n' \
        '  -c           centerline/segmentation (generated with sct_get_centerline or sct_segmentation_propagation, centerline must cover each "z" slices).\n' \
        '\n'\
        'OPTIONAL ARGUMENTS\n' \
        '  -r <0,1>     remove temporary files. Default=1. \n' \
        '  -w           interpolation option when applying the transformation to input image using the syntax of  \n'\
        '               WarpImageMultiTransform (example --use-BSpline to use 3rd order B-Spline Interpolation) \n' \
        '  -h           help. Show this message.\n' \
        '  -f           option to choose the centerline fitting method: splines to fit the centerline with \n'\
        '               splines, polynomial to fit the centerline with a polynome. Default='+str(param.fitting_method)+'\n'
    
    '\n'\
        'EXAMPLE:\n' \
        '  sct_straighten_spinalcord.py -i t2.nii.gz -c centerline.nii.gz\n'
    sys.exit(2)


#=======================================================================================================================
# Start program
#=======================================================================================================================
if __name__ == "__main__":
    # initialize parameters
    param = param()
    # call main function
    main()
