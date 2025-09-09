def toast_breadloaf(robot_list):
    # robot_list = [robot1]
    # 0: Go to the Knife using robot1.
    GoToObject(robot_list[0], 'Knife')
    # 1: Pick up the Knife using robot1.
    PickupObject(robot_list[0], 'Knife')
    # 2: Go to the Breadloaf using robot1.
    GoToObject(robot_list[0], 'Bread')
    # 3: Slice the Breadloaf using robot1.
    SliceObject(robot_list[0], 'Bread')
    # 4: Put the Knife using robot1.
    DropHandObject(robot_list[0])
    # 5: Pick up the sliced Breadloaf using robot1.
    PickupObject(robot_list[0], 'BreadSliced_1')
    # 6: Go to the Toaster using robot1.
    GoToObject(robot_list[0], 'Toaster')
    # 7: Put the Bread in the Toaster using robot1.
    PutObject(robot_list[0], 'Toaster')
    # 8: Turn on the Toaster using robot1.
    ToggleObject(robot_list[0], 'Toaster')
    # 9: Pick up the toasted Breadloaf using robot1.
    PickupObject(robot_list[0], 'BreadSliced_1')

# Execute SubTask
toast_breadloaf([robots[0]])
