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