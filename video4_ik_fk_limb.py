import maya.cmds as cmds

import maya.mel as mel

'''
duplicate skin joints and place with offsetParentMatrix to create our fk chain

create fk chain of controls and drive joints

'''

def duplicate_joints(skin_joints, search, replace):
    '''
    Duplicate skin joints and place the new joints using the offsetParentMatrix
    Args:
        skin_joints: (list) of skin joint names
        search: (string) search term
        replace: (string) replace term

    Returns:
        (list) of new joints
    '''

    new_joints = []

    for i in range(len(skin_joints)):

        # create new joints
        new_joint = cmds.createNode('joint', n=skin_joints[i].replace(search, replace))
        new_joints.append( new_joint )

        # get and set rotate order
        rotate_order = cmds.xform(skin_joints[i], q=True, roo=True)
        cmds.xform(new_joint, roo=rotate_order)

        # parent joints in hierarchy
        if i > 0:
            cmds.parent(new_joint, new_joints[i-1])

    # place using offset parent matrix
    for i in range(len(skin_joints)):
        cmds.connectAttr('{}.xformMatrix'.format(skin_joints[i]), '{}.offsetParentMatrix'.format(new_joints[i]))
        cmds.disconnectAttr('{}.xformMatrix'.format(skin_joints[i]), '{}.offsetParentMatrix'.format(new_joints[i]))

    return new_joints

def create_fk_controls(fk_joints, search, replace):
    '''
    Create fk controls based off fk joints and drive those joints
    Args:
        fk_joints: (list) of fk joint names
        search: (string) search term
        replace: (string) replace term

    Returns:
        (list) of controls
    '''
    controls = []

    for i in range(len(fk_joints)):
        # create control
        control = cmds.circle(ch=False, n=fk_joints[i].replace(search, replace))[0]
        controls.append(control)

        # parent the controls together
        if i > 0:
            cmds.parent(control, controls[i-1])

    # place using offset parent matrix
    for i in range(len(fk_joints)):
        # if it's not the first joint then we need to use a mult matrix node to negate the controls parents worldMatrix
        if i > 0:
            mult = cmds.createNode('multMatrix')
            cmds.connectAttr('{}.worldMatrix[0]'.format(fk_joints[i]), '{}.matrixIn[0]'.format(mult))
            cmds.connectAttr('{}.worldInverseMatrix[0]'.format(controls[i-1]), '{}.matrixIn[1]'.format(mult))
            cmds.connectAttr('{}.matrixSum'.format(mult), '{}.offsetParentMatrix'.format(controls[i]))

            cmds.disconnectAttr('{}.matrixSum'.format(mult), '{}.offsetParentMatrix'.format(controls[i]))
            cmds.delete(mult)
        # if it's the first control we can just use the worldMatrix
        else:
            cmds.connectAttr('{}.worldMatrix[0]'.format(fk_joints[i]), '{}.offsetParentMatrix'.format(controls[i]))
            cmds.disconnectAttr('{}.worldMatrix[0]'.format(fk_joints[i]), '{}.offsetParentMatrix'.format(controls[i]))

    # drive the fk joints
    for i in range(len(controls)):
        connect_trs(controls[i], fk_joints[i])

    return controls

def create_ik_control(end_joint):
    '''
    Creates an IK control in world space based the end joint position
    Args:
        end_joint: (string) end joint name

    Returns:
        (string) ik control name

    '''
    # generate name based off end joint side
    ik_control = 'C_ik_ctrl'
    if 'L_' in end_joint:
        ik_control = 'L_ik_ctrl'
    if 'R_' in end_joint:
        ik_control = 'R_ik_ctrl'

    # create control curve
    point_one = [0.0, 0.0, 1.0]
    point_two = [1.0, 0.0, 0.0]
    point_three = [0.0, 0.0, -1.0]
    point_four = [-1.0, 0.0, 0.0]
    point_five = [0.0, 0.0, 1.0]

    cmds.curve(p = [point_one, point_two, point_three, point_four, point_five], n=ik_control, d=1)

    # place control curve
    cmds.matchTransform(ik_control, end_joint, pos=True, rot=False, scl=False)

    # bake trs to offsetParentMatrix
    bake_trs_offsetParentMatrix(ik_control)

    return ik_control

def create_pv_control(start_joint, mid_joint, end_joint):
    '''
    Creates and places an Pole vector control
    Args:
        start_joint: (string) name of start joint
        mid_joint:  (string) name of mid joint
        end_joint:  (string) name of end joint

    Returns:

    '''
    # generate name based off end joint side
    pv_control = 'C_pv_ctrl'
    if 'L_' in end_joint:
        pv_control = 'L_pv_ctrl'
    if 'R_' in end_joint:
        pv_control = 'R_pv_ctrl'

    # create control curve
    point_one = [0.0, 0.0, 1.0]
    point_two = [1.0, 0.0, 0.0]
    point_three = [0.0, 0.0, -1.0]
    point_four = [-1.0, 0.0, 0.0]
    point_five = [0.0, 0.0, 1.0]

    cmds.curve(p=[point_one, point_two, point_three, point_four, point_five], n=pv_control, d=1)

    start_pos = cmds.xform(start_joint, q=True, ws=True, rp=True)
    mid_pos = cmds.xform(mid_joint, q=True, ws=True, rp=True)
    end_pos = cmds.xform(end_joint, q=True, ws=True, rp=True)

    start_to_end = subtract_vectors(end_pos, start_pos)
    scaled = scale_vector(start_to_end, 0.5)

    half_way = add_vectors(scaled, start_pos)

    subtract_half_way = subtract_vectors(mid_pos, half_way)

    length = mel.eval('mag <<{}, {}, {}>>;'.format(subtract_half_way[0], subtract_half_way[1], subtract_half_way[2]))

    if length < 5:
        multiplier = 5/length
        subtract_half_way = scale_vector(subtract_half_way, multiplier)

    pole_vector_pos = add_vectors(subtract_half_way, mid_pos)

    cmds.xform(pv_control, t=pole_vector_pos, ws=True)

    bake_trs_offsetParentMatrix(pv_control)

    return pv_control




def pole_vector_connection(start_joint, pv_control, ik_handle):
    '''
    Since the polevector constraint doesn't with offsetParentMatrix on joints
    We need to do it by hand
    Args:
        start_joint: (string) start joint name
        pv_control: (string) pv control name
        ik_handle: (string) ik handle name

    Returns:

    '''
    # create decompose matrix nodes
    start_decompose = cmds.createNode('decomposeMatrix', n='decomposeMatrix_{}'.format(start_joint))
    pv_decompose = cmds.createNode('decomposeMatrix', n='decomposeMatrix_{}'.format(pv_control))

    # connect them up
    cmds.connectAttr('{}.worldMatrix[0]'.format(start_joint), '{}.inputMatrix'.format(start_decompose))
    cmds.connectAttr('{}.worldMatrix[0]'.format(pv_control), '{}.inputMatrix'.format(pv_decompose))

    # subtract start joint pos from pv pos
    minus_node = cmds.createNode('plusMinusAverage')
    cmds.setAttr('{}.operation'.format(minus_node), 2)
    cmds.connectAttr('{}.outputTranslate'.format(pv_decompose), '{}.input3D[0]'.format(minus_node))
    cmds.connectAttr('{}.outputTranslate'.format(start_decompose), '{}.input3D[1]'.format(minus_node))

    # create plus minus average
    plus_node = cmds.createNode('plusMinusAverage', n='plusMinusAverage_{}'.format(ik_handle))
    cmds.connectAttr('{}.outputTranslate'.format(start_decompose), '{}.input3D[0]'.format(plus_node))
    cmds.connectAttr('{}.output3D'.format(minus_node), '{}.input3D[1]'.format(plus_node))

    # drive pole vector on ik handle
    cmds.connectAttr('{}.output3D'.format(plus_node), '{}.poleVector'.format(ik_handle))





def add_vectors(vectorA, vectorB):
    '''
    Adds two vectors together
    Args:
        vectorA: (list) of x y z values
        vectorB: (list) of x y z values

    Returns:
        (list) of x y z values

    '''
    result = []

    for i in range(len(vectorA)):
        value = vectorA[i] + vectorB[i]
        result.append(value)

    return result


def subtract_vectors(vectorA, vectorB):
    '''
    Subtacts one vector from another
    Args:
        vectorA: (list) of x y z values
        vectorB: (list) of x y z values

    Returns:
        (list) of x y z values

    '''
    result = []

    for i in range(len(vectorA)):
        value = vectorA[i] - vectorB[i]
        result.append(value)

    return result

def scale_vector(vector, scale_factor):
    '''
    Scales a vector by the scale factor
    Args:
        vector: (list) of x y z values
        scale_factor: (float) value to scale by

    Returns:
        (list) of x y z values
    '''
    result = []

    for i in range(len(vector)):
        value = vector[i] * scale_factor
        result.append(value)

    return result

def bake_trs_offsetParentMatrix(transform):
    '''
    Bakes TRS values into the offsetParentMatrix
    Args:
        transform: (string) name of the transform

    Returns:

    '''
    # duplicate transform to place with offsetParentMatrix
    temp = cmds.duplicate(transform, po=True)[0]

    # check for parent
    parent = None
    try:
        parent = cmds.listRelatives(transform, p=True)[0]
    except:
        pass

    # zero out trs values on the transform
    for attr in ['translate', 'rotate', 'scale']:
        for axis in 'XYZ':
            if attr == 'scale':
                cmds.setAttr('{}.{}{}'.format(transform, attr, axis), 1.0)
            else:
                cmds.setAttr('{}.{}{}'.format(transform, attr, axis), 0.0)

    # place with offsetParentMatrix
    if parent:
        mult = cmds.createNode('multMatrix')
        cmds.connectAttr('{}.worldMatrix[0]'.format(temp), '{}.matrixIn[0]'.format(mult))
        cmds.connectAttr('{}.worldInverseMatrix[0]'.format(parent), '{}.matrixIn[1]'.format(mult))
        cmds.connectAttr('{}.matrixSum'.format(mult), '{}.offsetParentMatrix'.format(transform))

        cmds.disconnectAttr('{}.matrixSum'.format(mult), '{}.offsetParentMatrix'.format(transform))
        cmds.delete(mult)
    # if there is not a parent
    else:
        cmds.connectAttr('{}.worldMatrix[0]'.format(temp), '{}.offsetParentMatrix'.format(transform))
        cmds.disconnectAttr('{}.worldMatrix[0]'.format(temp), '{}.offsetParentMatrix'.format(transform))

    # delete temp transform
    cmds.delete(temp)





def connect_trs(source, destination):
    '''
    Connects TRS from source to destination
    Args:
        source: (string) name of source transform
        destination: (string) name of destination transform

    Returns:

    '''
    for attribute in ['translate', 'rotate', 'scale']:
        for axis in 'XYZ':
            try:
                cmds.connectAttr('{}.{}{}'.format(source, attribute, axis), '{}.{}{}'.format(destination, attribute, axis))
            except:
                print 'Cannot connect {}.{}{} to {}.{}{}'.format(source, attribute, axis, destination, attribute, axis)
