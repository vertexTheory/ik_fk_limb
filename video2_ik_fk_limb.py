import maya.cmds as cmds

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
