def toast_bread(robot_list):
    # robot_list = [robot1]
    # 0: Go to the Knife using robot1.
    GoToObject(robot_list[0], 'Knife')
    PickupObject(robot_list[0], 'Knife')
    # 1: Go to the Bread using robot1.
    GoToObject(robot_list[0], 'Bread')
    # 2: Slice the Bread using robot1.
    SliceObject(robot_list[0], 'Bread')
    # Check if the Bread is sliced to BreadSliced_1
    DropHandObject(robot_list[0])
    PickupObject(robot_list[0], 'BreadSliced_1')
    # 3: Go to the Toaster using robot1.
    GoToObject(robot_list[0], 'Toaster')
    # 4: Put the Bread in the Toaster using robot1.
    PutObject(robot_list[0], 'Toaster')
    # 5: Turn on the Toaster using robot1.
    ToggleObjectOn(robot_list[0], 'Toaster')
    # 6: Pick up the toasted Bread using robot1.
    PickupObject(robot_list[0], 'BreadSliced_1')

# Execute SubTask
toast_bread([robots[0]])
